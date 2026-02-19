# ========================
# config.py
# ========================

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================
# Flask設定クラス
# =========================
class Config:
    SECRET_KEY = "dev-key"
    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" + os.path.join(BASE_DIR, "database.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False