"""PostgreSQL connection helpers.

A single connection is opened per database operation and closed when done.
For a small team this is plenty — PostgreSQL handles many short connections
efficiently. The connection string comes from ``DATABASE_URL`` (set by
Render, or your local environment / .env file).

Usage::

    from app.db import query, query_one, execute, transaction

    rows = query("SELECT * FROM products ORDER BY code")
    one  = query_one("SELECT * FROM products WHERE id = %s", (pid,))
    with transaction() as conn:
        conn.execute("INSERT INTO ...")
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import psycopg2
import psycopg2.extras

from config import Config


def _connect():
    """Open a new PostgreSQL connection configured for dict-like rows.

    Works with any cloud PostgreSQL (Supabase, Neon, Render, Aiven, ...).
    The connection string from DATABASE_URL is normalised so both
    ``postgres://`` and ``postgresql://`` schemes are accepted, and a
    connect timeout is set so the app never hangs on a dead DB.
    """

    url = Config.DATABASE_URL
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Set it in your environment (.env file "
            "locally, or as an environment variable on Render)."
        )
    # Some providers prefix the URL with 'postgres://' which newer psycopg2
    # wants as 'postgresql://'. Normalise to be safe.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    conn = psycopg2.connect(url, connect_timeout=10)
    conn.autocommit = False
    return conn


def query(sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    """Run a SELECT and return all rows as a list of dicts."""

    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return [dict(r) for r in cur.fetchall()]


def query_one(sql: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
    """Run a SELECT and return the first row as a dict, or None."""

    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            row = cur.fetchone()
            return dict(row) if row else None


@contextmanager
def transaction() -> Iterator[Any]:
    """Context manager yielding a cursor; commits on success, rolls back on error."""

    conn = _connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute(sql: str, params: Sequence[Any] | None = None) -> None:
    """Run a statement that does not return rows (INSERT/UPDATE/DELETE), commit."""

    with transaction() as cur:
        cur.execute(sql, params or ())


def init_schema() -> None:
    """Create all tables if they do not exist. Safe to re-run."""

    here = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(here, "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()
