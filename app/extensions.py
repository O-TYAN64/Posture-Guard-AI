# ========================
# extensions.py
# ========================

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# ========================
# Flask拡張機能の初期化
# ========================
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


