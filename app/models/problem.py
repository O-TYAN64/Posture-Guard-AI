# =========================
# models/problem.py
# =========================

from extensions import db

# =========================
# 問題モデル
# =========================
class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    level = db.Column(db.Integer)
