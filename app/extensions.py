# ========================
# extensions.py
# ========================

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import signing as rt  # セッション署名ユーティリティ

# ========================
# Flask拡張機能の初期化
# ========================
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
SESSION_SIGNING_SALT = rt.token_digest("session")
login_manager.session_protection = "strong"


