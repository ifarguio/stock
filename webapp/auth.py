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

    def __init__(self, id: int, username: str, display_name: str = "",
                 is_admin: bool = False):
        self.id = id
        self.username = username
        self.display_name = display_name or username
        self.is_admin = bool(is_admin)

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
    return User(row["id"], row["username"], row.get("display_name") or "",
                row.get("is_admin") or False)


def verify_password(stored_hash: str, plain: str) -> bool:
    return check_password_hash(stored_hash, plain)


def create_user(username: str, password: str, display_name: str = "",
                is_admin: bool = False) -> int:
    """Create a new login account. Returns the new user id."""

    with db.transaction() as cur:
        cur.execute(
            "INSERT INTO users (username, password_hash, display_name, is_admin) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (username, generate_password_hash(password),
             display_name or username, is_admin),
        )
        return cur.fetchone()["id"]


def change_password(user_id: int, new_password: str) -> None:
    """Set a new password for a user."""

    db.execute(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (generate_password_hash(new_password), user_id),
    )


def list_users() -> list[dict]:
    return db.query(
        "SELECT id, username, display_name, is_admin, created_at "
        "FROM users ORDER BY id"
    )


def delete_user(user_id: int) -> None:
    db.execute("DELETE FROM users WHERE id = %s", (user_id,))


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


def admin_required(view):
    """Decorator: require a signed-in admin. 404 for non-admins."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        if not user.is_admin:
            from flask import abort
            abort(404)
        return view(*args, **kwargs)

    return wrapped
