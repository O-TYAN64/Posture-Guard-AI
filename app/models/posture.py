from extensions import db
from datetime import datetime

class PostureLog(db.Model):
    __tablename__ = "posture_logs"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    posture = db.Column(db.String(16))        # good / bad
    posture_type = db.Column(db.String(32))   # slouch / normal など

    torso_angle = db.Column(db.Float)
    neck_angle = db.Column(db.Float)
    shoulder_tilt = db.Column(db.Float)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
