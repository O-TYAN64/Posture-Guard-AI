# ========================
# app.py
# ========================

from flask import Flask, request, render_template, jsonify
import os
import cv2
import numpy as np

from posture_check import PosePostureAnalyzer, PostureConfig
from flask_login import login_required, current_user

from config import Config
from routes.auth import auth
from extensions import db, login_manager

from models.problem import Problem
from models.user import User
from models.posture import PostureLog  # ← これは「関数」
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================
# Flask 初期化
# =========================
app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager.init_app(app)

# =========================
# Login Manager
# =========================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================
# Blueprint 登録
# =========================
app.register_blueprint(auth)

# =========================
# DB 初期化
# （静的なテーブル(User, Problem等)はここで作る）
# =========================
with app.app_context():
    db.create_all()

# =========================
# 姿勢解析器 初期化（アプリ起動時に1回）
# =========================
MODEL_PATH = os.path.join(
    BASE_DIR, "static", "models", "pose_landmarker_full.task"
)
analyzer = PosePostureAnalyzer(MODEL_PATH, PostureConfig())


@app.route("/")
def index():
    problems = Problem.query.all()
    return render_template("index.html", problems=problems)

@app.route("/debug")
def debug():
    return render_template("debug.html")


# =========================
# 画像解析
# =========================
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

    # ★ 動的テーブルがまだないユーザーの場合に備えて作成
    # （毎回呼ぶと重いので本番は「初回だけ」にするのが理想）
    LogModel = PostureLog(current_user.username)
    db.create_all()

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


# =========================
# キャリブレーション
# =========================
@app.route("/calibrate", methods=["POST"])
@login_required
def calibrate():
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "no image"}), 400

    img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
    out = analyzer.analyze(img)

    if out is None:
        return jsonify({"error": "no pose detected"}), 400

    analyzer.calibrate(out["metrics"])

    return jsonify({
        "status": "calibrated",
        "baseline": {k: round(v, 3) for k, v in out["metrics"].items()}
    })


# =========================
# ログ表示
# =========================
@app.route('/logs')
@login_required
def show_logs():
    page = int(request.args.get('page', 1))

    # ユーザーごとの動的モデルを取得して query する
    LogModel = PostureLog(current_user.username)
    db.create_all()  # 念のため（初回ユーザー）

    query = (
        LogModel.query
        .filter_by(user_id=current_user.id)
        .order_by(LogModel.created_at.asc())
    )
    logs = query.all()

    pages = []
    current_page = []
    last_time = None
    last_page_time = None

    for log in logs:
        if last_time is None:
            current_page.append(log)
            last_time = log.created_at
            last_page_time = log.created_at
            continue

        time_diff = (log.created_at - last_time).total_seconds()
        page_diff = (log.created_at - last_page_time).total_seconds()

        # 5分以上空いたらページを分ける
        if page_diff >= 5 * 60:
            pages.append(current_page)
            current_page = [log]
            last_page_time = log.created_at
            last_time = log.created_at
            continue

        # 2.5秒以上間隔があれば追加
        if time_diff >= 2.5:
            current_page.append(log)
            last_time = log.created_at

    if current_page:
        pages.append(current_page)

    # ページ番号に応じて出力
    if page - 1 < len(pages):
        page_logs = pages[page - 1]
        has_next = page < len(pages)
    else:
        page_logs = []
        has_next = False

    return render_template('logs.html', logs=page_logs, page=page, has_next=has_next)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True, threaded=True)