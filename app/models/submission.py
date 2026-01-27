from extensions import db

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    problem_id = db.Column(db.Integer)
    code = db.Column(db.Text)
    result = db.Column(db.String(10))
