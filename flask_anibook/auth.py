import functools

from bcrypt import checkpw, gensalt, hashpw
from flask import (Blueprint, Response, current_app, flash, g, redirect,
                   render_template, request, session, url_for)
from itsdangerous.url_safe import URLSafeTimedSerializer as serializer
from sqlalchemy import text

from flask_anibook import db_configs, sqlalchemy_db
from flask_anibook.db import get_connection, sql
from flask_anibook.error_handling import UndetectedQueryError, UsernameTaken
from flask_anibook.mails import send_reset_password, send_reset_username


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not g.get("user"):
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    session.permanent = True
    username = request.form.get("username")
    password = request.form.get("password")
    remember = request.form.get("remember")
    error = ""
    category = ""

    if request.method == "POST":
        username = request.form.get("username")
        with sqlalchemy_db.engine.connect() as conn:
            try:
                result = conn.execute(
                    text("select * from anibook_users where user_name=:x").bindparams(
                        x=username
                    )
                )
                user = result.mappings().first()
            except:
                raise

            if not user:
                error = "Username not in records."
                category = "failure"
            else:
                if checkpw(bytes(password, "utf-8"), bytes(user["password_hash"])):
                    session["user_id"] = user["user_id"]
                    return redirect(url_for("home", _method="GET"))
                else:
                    error = "Password incorrect."
                    category = "warning"
        flash(error, category)
    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.pop("user_id")  # debug : add None option to avoid crash
    g.pop("user", None)
    return redirect(url_for("home"))


@auth_bp.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        password_two = request.form.get("password-two")
        error = ""
        category = ""

        with sqlalchemy_db.engine.connect() as conn:
            cur = conn.connection.cursor()
            cur.execute(
                sql.SQL("select * from {} where user_name = %s;").format(
                    sql.Identifier(db_configs["users_table"])
                ),
                (username,),
            )
            user = cur.fetchall()
            if user:
                error = "Username already taken."
                category = "failure"
            elif not user:
                if password != password_two:
                    error = "Password do not match."
                    category = "failure"
                else:
                    try:
                        password_hash = hashpw(
                            bytes(password, "utf-8"), gensalt())
                        conn.execute(
                            text(
                                "insert into anibook_users (user_name,email,password_hash) values (:x, :y, :z);"
                            ).bindparams(x=username, y=email, z=password_hash)
                        )
                        conn.commit()
                    except:
                        error = "Email already taken,"
                        category = "failure"
                        raise

            if not error:
                return redirect(url_for("auth.login"))
        flash(error, category)
    return render_template("auth/register.html")


def get_reset_token(user_id):
    s = serializer(str(current_app.config["SECRET_KEY"]))
    token = s.dumps({"user_id": user_id})
    return token


def verify_reset_token(token, expire_sec=900):
    s = serializer(str(current_app.config["SECRET_KEY"], expire_sec))
    try:
        user_id = s.loads(token, max_age=expire_sec)["user_id"]
    except BadSignature:
        return ""
    except SignatureExpired:
        return ""
    return user_id


@auth_bp.route("/reset", methods=["GET", "POST"])
def reset():
    reset_email = request.form.get("email")
    reset_username = request.form.get("username")
    reset_password = request.form.get("password")
    error = ""
    category = ""
    if request.method == "POST":
        with sqlalchemy_db.engine() as conn:
            query = text("select * from anibook_users where email = :y")
            result = conn.execute(query, {"y": reset_email})
            user = result.mappings().first()
            if not user:
                error = "We did not find any data related to the email provided."
                category = "warning"
            elif not reset_password and not reset_username:
                error = "Must select which information you forgot."
                category = "warning"
            elif reset_username:
                send_reset_username(user)
            else:
                token = get_reset_token(user)
                send_reset_password(user, token)
                return render_template("auth/checkEmail.html")
    flash(error, category)
    return render_template("auth/reset.html")


@auth_bp.route("/reset/<string:token>", methods=["GET", "POST"])
def verified_reset(token):
    error = ""
    category = ""
    password = request.form.get("password")
    password_two = request.form.get("passwordTwo")
    user_id = verify_reset_token(token)

    if request.method == "POST":
        if password != password_two:
            error = "Passwords do not match."
            category = "failure"
        else:
            password_hash = hashpw(bytes(password, "utf-8"), gensalt())
            try:
                with sqlalchemy_db.engine() as conn:
                    query = text(
                        "update table anibook_users set password_hash = :y where user_id = :z"
                    )
                    result = conn.execute(
                        query, {"y": password_hash, "z": user_id})
                    conn.commit()
            except:
                error = "Error510. Something went wrong please contact support."
                category = "failure"
        flash(error, category)
        return redirect(url_for("auth.login"))

    if not user_id:
        error = "Invalid reset token or Token has expired. Try reseting again."
        return redirect(url_for("auth.reset"))
    else:
        with sqlalchemy_db.engine() as conn:
            query = text(
                "select user_id from anibook_users where user_id = :y")
            result = conn.execute(query, {"y": user_id})
            if result.mappings().first()["user_name"]:
                return render_template("auth/resetPassword.html")
    # may add a custom error page
    return "Something went wrong whith resetting your password. Go back to home."
