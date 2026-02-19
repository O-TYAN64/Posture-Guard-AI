# =========================
# models/admin.py
# =========================

from flask import Flask
from extensions import db
from models.user import User
from werkzeug.security import generate_password_hash

# =========================
# 管理者ユーザーの初期化
# =========================

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "secret"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    admin = User(
        username="admin",
        password=generate_password_hash("admin123"),
        is_admin=True
    )
    db.session.add(admin)
    db.session.commit()
    print("管理者ユーザー作成完了")
