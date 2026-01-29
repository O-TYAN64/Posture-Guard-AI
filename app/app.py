from flask import Flask, request,  render_template, jsonify
import os
import cv2
import numpy as np
from flask_sqlalchemy import SQLAlchemy
from posture_check import PosePostureAnalyzer, PostureConfig
from config import Config
from routes.auth import auth
from extensions import db, login_manager
from models.problem import Problem
from models.user import User

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================
# Flask 初期化
# =========================
app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager.init_app(app)

# -----------------------------
# Login Manager
# -----------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -----------------------------
# Blueprint 登録
# -----------------------------
app.register_blueprint(auth)

# -----------------------------
# DB 初期化
# -----------------------------
with app.app_context():
    db.create_all()
# =========================
# 姿勢解析器 初期化
# （※ アプリ起動時に1回だけ）
# =========================


MODEL_PATH = os.path.join(
    BASE_DIR,
    "static",
    "models",
    "pose_landmarker_full.task"
)

analyzer = PosePostureAnalyzer(MODEL_PATH, PostureConfig())


@app.route("/")
def index():
    problems = Problem.query.all()
    return render_template("index.html", problems=problems)

@app.route("/problem/<int:id>")
def show_problem(id):
    p = Problem.query.get(id)
    return render_template("problem.html", problem=p)

@app.route("/debug")
def debug():
    return render_template("debug.html")




@app.post("/analyze")
def analyze():
    file = request.files.get("image", None)
    if file is None:
        return jsonify({"posture": "unknown"}), 400

    file_bytes = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({"posture": "unknown"}), 400

    out = analyzer.analyze(frame)
    if out is None:
        # 人なし（pose_world_landmarksなし）
        return jsonify({"posture": "unknown", "landmarks": []})

    posture = analyzer.judge(out["metrics"])

    # 2Dランドマークがないフレームのケア（描画しないがUIは更新可能）
    landmarks_2d = out["landmarks"] if out["landmarks"] is not None else []

    return jsonify({
        "posture": posture,                    # "good" / "bad"
        "metrics": out["metrics"],
        "landmarks": landmarks_2d,             # ← None の代わりに []
        "world_landmarks": out["world_landmarks"],
        "connections": out["connections"]
    })




@app.route("/calibrate", methods=["POST"])
def calibrate():
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "no image"}), 400

    img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
    out = analyzer.analyze(img)
    
    if out is None:
        return jsonify({"error": "no pose detected"}), 400
    
    analyzer.calibrate(out["metrics"])  # ← metrics だけ渡す
    
    return jsonify({
        "status": "calibrated",
        "baseline": {k: round(v, 3) for k, v in out["metrics"].items()}
    })



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True, threaded=True)
