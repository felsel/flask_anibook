from flask import (Blueprint, Response, g, redirect, render_template, request,
                   session, url_for)

from flask_anibook import db_configs
from flask_anibook.auth import login_required
from flask_anibook.db import get_connection, sql

anime_bp = Blueprint("animes", __name__, url_prefix="/animes")


@anime_bp.route("/index")
def listless_index():
    session.permanent = True
    get_connection(db_configs["db_name"], g)
    cur = g.db.cursor()
    cur.execute("select * from watching;")
    animes = cur.fetchall()
    cur.close()
    g.db.close()
    del g.db
    return render_template("animes/index.html", animes=animes)


@anime_bp.route("/index/<string:list>", methods=["GET", "POST"])
def index(list):
    if request.method == "POST":
        redirect(url_for("animes.search"))

    get_connection(db_configs["db_name"], g)
    cur = g.db.cursor()
    # anime_list = request.args.get("list")
    # cur.execute("select * from %s escape '' ;", [list]) """
    cur.execute(sql.SQL("select * from {};").format(sql.Identifier(list)))
    animes = cur.fetchall()
    return render_template("animes/index.html", animes=animes)


@anime_bp.route("/search")
def search():
    search_list = request.args.get("list")
    title = request.args.get("title")
    get_connection(db_configs["db_name"], g)
    cur = g.db.cursor()
    cur.execute(
        sql.SQL("select * from {} where title like %s escape ''").format(
            sql.Identifier(search_list)
        ),
        [title],
    )
    result = cur.fetchall()
    cur.close()
    g.db.close()
    del g.db
    return render_template("animes/index.html", result=result)


# updating titles
@anime_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit_anime():
    if request.method == "POST":
        if request.form.get("_method") == "put":
            edit_value = request.form.get("edit-value")
            if edit_value:
                anime_list = request.form.get("list")
                title = request.form.get("title")
                get_connection(db_configs["db_name"], g)
                cur = g.db.cursor()
                cur.execute(
                    sql.SQL(
                        "update {} set title=(%s) where title like %s escape ''"
                    ).format(sql.Identifier(anime_list)),
                    [edit_value, title],
                )
                g.db.commit()
                cur.close()
                g.db.close()
                del g.db
                return redirect(
                    url_for("animes.index", list="completed")
                )  # need to remove the quotes some how
            else:
                return "edit value not found"
        else:
            return "_method=put not working"
    return f"method was not post. itch was {request.method}"


# adding an anime
@anime_bp.route("/edit", methods=["GET", "PUT"])
@login_required
def add_anime():
    return "adding"


# droppingan anime
@anime_bp.route("/edit", methods=["GET", "PUT"])
@login_required
def delete_anime():
    return "deleting"
