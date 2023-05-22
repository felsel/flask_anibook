import psycopg2
from psycopg2 import sql

from flask_anibook import db_configs

# db_path = "postgresql::joelly:Madara12@localhost:5432/anibook"


def get_db(db_name, user, password, host, port):
    db = psycopg2.connect(
        dbname=db_name, user=user, password=password, host=host, port=port
    )
    return db


def get_connection(db_name, g):
    g.db = get_db(
        db_name,
        db_configs["user"],
        db_configs["password"],
        db_configs["host"],
        db_configs["port"],
    )
