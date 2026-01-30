from extensions import db
from datetime import datetime
import pytz

JST = pytz.timezone("Asia/Tokyo")

def now_jst():
    return datetime.now(JST)

POSTURE_LOG_MODELS = {}

def get_posture_log_model(username):
    if username not in POSTURE_LOG_MODELS:
        tablename = f"posture_log_{username}"

        class PostureLog(db.Model):
            __tablename__ = tablename

            id = db.Column(db.Integer, primary_key=True)
            posture = db.Column(db.String(16))
            posture_type = db.Column(db.String(32))
            torso_angle = db.Column(db.Float)
            neck_angle = db.Column(db.Float)
            shoulder_tilt = db.Column(db.Float)

            # ★修正：callable を渡す（UTC推奨）
            created_at = db.Column(db.DateTime, default=now_jst, nullable=False)

            user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
            user = db.relationship("User", backref=f"{username}_logs")

        POSTURE_LOG_MODELS[username] = PostureLog

    return POSTURE_LOG_MODELS[username]

PostureLog = get_posture_log_model