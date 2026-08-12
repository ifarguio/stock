"""Authentication: users, login/logout, the login_required guard.

Passwords are hashed with Werkzeug (PBKDF2). The first user is created via
the CLI command ``flask create-user``. Sessions are signed cookies handled
by Flask-Login.
"""

from __future__ import annotations

from functools import wraps
from typing import Optional

from flask import session, redirect, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash

import db


class User:
    """A minimal user object stored in the Flask session."""

    def __init__(self, id: int, username: str, display_name: str = ""):
        self.id = id
        self.username = username
        self.display_name = display_name or username

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return str(self.id)


def get_user_by_username(username: str) -> Optional[dict]:
    return db.query_one("SELECT * FROM users WHERE username = %s", (username,))


def get_user_by_id(user_id: int) -> Optional[User]:
    row = db.query_one("SELECT * FROM users WHERE id = %s", (user_id,))
    if not row:
        return None
    return User(row["id"], row["username"], row.get("display_name") or "")


def verify_password(stored_hash: str, plain: str) -> bool:
    return check_password_hash(stored_hash, plain)


def create_user(username: str, password: str, display_name: str = "") -> int:
    """Create a new login account. Returns the new user id."""

    with db.transaction() as cur:
        cur.execute(
            "INSERT INTO users (username, password_hash, display_name) "
            "VALUES (%s, %s, %s) RETURNING id",
            (username, generate_password_hash(password), display_name or username),
        )
        return cur.fetchone()["id"]


def login_user(user: User) -> None:
    session["user_id"] = user.id


def logout_current_user() -> None:
    session.pop("user_id", None)


def current_user() -> Optional[User]:
    uid = session.get("user_id")
    if uid is None:
        return None
    return get_user_by_id(uid)


def login_required(view):
    """Decorator: redirect to the login page if not signed in."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped
