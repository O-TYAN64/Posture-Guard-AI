# =========================
# models/posture.py
# =========================

from extensions import db
from datetime import datetime
# =========================
# グローバルキャッシュ
# =========================
POSTURE_LOG_MODELS = {}

def get_posture_log_model(username):
    """ユーザー名から PostureLog モデルを返す"""
    if username not in POSTURE_LOG_MODELS:
        tablename = f"posture_log_{username}"

        class PostureLog(db.Model):
            __tablename__ = tablename

            id = db.Column(db.Integer, primary_key=True)  # primary key 必須
            posture = db.Column(db.String(16))       # good / bad
            posture_type = db.Column(db.String(32))  # slouch / normal
            torso_angle = db.Column(db.Float)
            neck_angle = db.Column(db.Float)
            shoulder_tilt = db.Column(db.Float)
            created_at = db.Column(db.DateTime, default=datetime.utcnow)
            user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

            user = db.relationship("User", backref=f"{username}_logs")

        POSTURE_LOG_MODELS[username] = PostureLog
    return POSTURE_LOG_MODELS[username]


# ここで PostureLog として「ユーザーごとにモデルを取得する関数」を公開
PostureLog = get_posture_log_model  # ← from models.posture import PostureLog で使える
