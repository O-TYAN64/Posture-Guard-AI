# ========================
# config.py
# ========================

import os as _o
import signing as _sg
BASE_DIR = _o.path.dirname(_o.path.abspath(__file__))

# セッション署名鍵（signing モジュールから導出）
_k = _sg.secret_key()

# =========================
# Flask設定クラス
# =========================
class Config:
    SECRET_KEY = _k
    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" + _o.path.join(BASE_DIR, "database.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False