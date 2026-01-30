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

from datetime import timedelta

@app.route('/logs')
def show_logs():
    if not current_user.is_authenticated:
        return "ログインしてください", 401

    page = int(request.args.get('page', 1))
    per_page = 60  # 最終的にページに出すログ数

    # ログイン中ユーザーのログを最新順で取得
    query = PostureLog.query.filter_by(user_id=current_user.id).order_by(PostureLog.created_at.desc())
    
    # 一度に多めに取得（間引きや日付分割用）
    logs = query.limit(1000).all()  # 1000件くらい取って間引く
    logs.reverse()  # 古い順に

    filtered_logs = []
    last_time = None
    for log in logs:
        # 前回ログがない場合は追加
        if last_time is None:
            filtered_logs.append(log)
            last_time = log.created_at
            continue

        # 2秒以上空いている場合は追加
        if (log.created_at - last_time).total_seconds() >= 2:
            filtered_logs.append(log)
            last_time = log.created_at
            continue

        # 日付が変わった場合は追加
        if log.created_at.date() != last_time.date():
            filtered_logs.append(log)
            last_time = log.created_at
            continue

    # ページング
    start = (page - 1) * per_page
    end = start + per_page
    page_logs = filtered_logs[start:end]
    has_next = end < len(filtered_logs)

    return render_template('logs.html', logs=page_logs, page=page, has_next=has_next)



@app.route("/vrm-pose")
@login_required
def vrm_pose():
    return render_template("vrm_pose.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True, threaded=True)
