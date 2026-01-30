from flask import Flask, request,  render_template, jsonify
import os
import cv2
import numpy as np
from flask_sqlalchemy import SQLAlchemy
from posture_check import PosePostureAnalyzer, PostureConfig
from flask_login import login_required, current_user
from config import Config
from routes.auth import auth
from extensions import db, login_manager
from models.problem import Problem
from models.user import User
from models.posture import PostureLog
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
@login_required
def analyze():
    file = request.files.get("image", None)
    if file is None:
        return jsonify({"posture": "unknown"}), 400

    file_bytes = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({"posture": "unknown"}), 400

    out = analyzer.analyze_and_save(frame)

    if out is None:
        return jsonify({"posture": "unknown", "landmarks": []})

    landmarks_2d = out["landmarks"] if out["landmarks"] is not None else []

    return jsonify({
        "posture": out["judge"],               # good / bad
        "posture_type": out["posture_type"],   # slouch 等
        "metrics": out["metrics"],
        "landmarks": landmarks_2d,
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

@app.route('/logs')
def show_logs():
    page = int(request.args.get('page', 1))
    per_page = 30  # まず大量に取得してから間引く
    query = PostureLog.query.order_by(PostureLog.created_at.desc())
    
    logs = query.offset((page-1)*per_page).limit(per_page).all()
    logs.reverse()  # 古い順に戻す

    # 2秒ごとに間引く
    filtered_logs = []
    last_time = None
    for log in logs:
        if last_time is None or (log.created_at - last_time).total_seconds() >= 2:
            filtered_logs.append(log)
            last_time = log.created_at

    # 次ページがあるかチェック
    has_next = query.offset(page*per_page).first() is not None
    
    return render_template('logs.html', logs=filtered_logs, page=page, has_next=has_next)


@app.route("/vrm-pose")
@login_required
def vrm_pose():
    return render_template("vrm_pose.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True, threaded=True)
