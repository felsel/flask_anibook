import toml
from flask import Flask, g, session
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

toml_configs = toml.load(".envs.toml")
db_configs = toml_configs["DATABASE"]
sqlalchemy_db = SQLAlchemy(engine_options={"future": True})
mail = Mail()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile("config.py")
    sqlalchemy_db.init_app(app)
    mail.init_app(app)

    @app.before_request
    def lead_user():
        user_id = session.get("user_id")
        if user_id:
            with sqlalchemy_db.engine.connect() as conn:
                rows = conn.execute(
                    text("select * from anibook_users where user_id=:y;").bindparams(
                        y=user_id
                    )
                )
                g.user = rows.mappings().first()

    from .animes import anime_bp, listless_index

    app.register_blueprint(anime_bp)

    from .auth import auth_bp

    app.register_blueprint(auth_bp)

    # '/' is handled by the index endpoint which is associated
    # with the index view_function of the  anime_bp (so '/animes/index')
    app.add_url_rule("/", "home", listless_index)
    return app
