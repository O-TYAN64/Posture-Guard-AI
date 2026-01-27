from flask import Blueprint, render_template, request, redirect, url_for,flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user
from extensions import db
from models.user import User

auth = Blueprint("auth", __name__)

@auth.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        if not request.form["username"].strip() or not request.form["password"].strip():
            flash("ユーザー名とパスワードは必須です。", "error")
            return render_template("register.html")
        elif User.query.filter_by(username =request.form["username"]).first():
            flash("ユーザー名が既に使われています。違うユーザー名でお試しください。", "error")
            return render_template("register.html")

        user = User(
            username=request.form["username"],
            password=generate_password_hash(request.form["password"])
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("auth.login"))
    return render_template("register.html")

@auth.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            return redirect("/")    
        else:
            flash("ユーザー名またはパスワードが正しくありません", "error")
            return render_template("login.html", error="ユーザー名またはパスワードが間違っています。")
    return render_template("login.html")

@auth.route("/logout")
def logout():
    logout_user()
    return redirect("/")
