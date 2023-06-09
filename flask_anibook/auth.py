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
    token = s.dumps({"user_id": str(user_id)})
    return token


def verify_reset_token(token, expire_sec=900):
    s = serializer(str(current_app.config["SECRET_KEY"]))
    try:
        # our serializer inherited from TimedSerializer,
        # which has a loads method that has a max_age property
        user_id = s.loads(token, max_age=expire_sec)["user_id"]
    except BadSignature:
        return ""
    except SignatureExpired:
        return ""
    return user_id


@auth_bp.route("/reset", methods=["GET", "POST"])
def reset():
    reset_email = str(request.form.get("email"))
    item_to_reset = str(request.form.get("reset"))
    error = ""
    category = ""
    if request.method == "POST":
        with sqlalchemy_db.engine.connect() as conn:
            query = text("select * from anibook_users where email = :y")
            result = conn.execute(query, {"y": reset_email})
            user = result.mappings().first()
            if not user:
                return f"{reset_email}"
                error = "We did not find any data related to the email provided."
                category = "warning"
            elif item_to_reset == "password":
                token = get_reset_token(user.get("user_id"))
                send_reset_password(user, token)
                return render_template("auth/checkEmail.html")
            elif item_to_reset == "username":
                send_reset_username(user)
                return render_template("auth/checkEmail.html")
            else:
                error = "Must select which information you forgot."
                category = "warning"
    flash(error, category)
    return render_template("auth/reset.html")


@auth_bp.route("/reset-token", methods=["GET", "POST"])
def verified_reset():
    error = ""
    category = ""
    password = request.form.get("password")
    password_two = request.form.get("password_two")
    token = request.args.get("token")
    if not token:
        token = request.form.get("token")
    user_id = verify_reset_token(token)

    if request.method == "POST":
        if password != password_two:
            error = "Passwords do not match."
            category = "failure"
        else:
            password_hash = hashpw(bytes(password, "utf-8"), gensalt())
            try:
                with sqlalchemy_db.engine.connect() as conn:
                    query = text(
                        "update anibook_users set password_hash = :y where user_id = :z"
                    )
                    result = conn.execute(
                        query, {"y": password_hash, "z": user_id})
                    conn.commit()
                return redirect(url_for("auth.login"))
            except:
                error = "Error510. Something went wrong please contact support."
                category = "failure"
                raise
        flash(error, category)
        return render_template("auth/resetPassword.html", token=token)

    if not user_id:
        error = "Invalid reset token or Token has expired. Try reseting again."
        category = "failure"
        return redirect(url_for("auth.reset"))
    else:
        with sqlalchemy_db.engine.connect() as conn:
            query = text(
                "select user_id from anibook_users where user_id = :y")
            result = conn.execute(query, {"y": user_id})
            if result.mappings().first()["user_id"]:
                return render_template("auth/resetPassword.html", token=token)
    # may add a custom error page
    return "Something went wrong whith resetting your password. Go back to home."
