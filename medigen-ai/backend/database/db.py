"""SQLite helpers.

We use Python's built-in sqlite3 module directly (no ORM) so the SQL is
easy to read and explain in a viva.
"""
import os
import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS generations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt        TEXT    NOT NULL,
    full_prompt   TEXT    NOT NULL,
    category      TEXT    NOT NULL,
    style         TEXT    NOT NULL,
    aspect_ratio  TEXT    NOT NULL,
    width         INTEGER NOT NULL,
    height        INTEGER NOT NULL,
    seed          INTEGER,
    model_name    TEXT    NOT NULL,
    provider      TEXT    NOT NULL,
    is_demo       INTEGER NOT NULL DEFAULT 0,
    filename      TEXT    NOT NULL UNIQUE,
    created_at    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_generations_created ON generations (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generations_category ON generations (category);
"""


def get_db():
    """One connection per request, stored on Flask's `g` object."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create the database file, tables and image folder if they do not exist."""
    path = app.config["DATABASE_PATH"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    os.makedirs(app.config["IMAGE_DIR"], exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
    app.teardown_appcontext(close_db)
