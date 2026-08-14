"""PostgreSQL connection helpers with a connection pool.

A pool of reusable connections is kept open for the lifetime of the process.
This is the single biggest performance win for a web app talking to a remote
database: instead of paying a full TCP + TLS handshake (~200-400 ms) on every
single query, the connection is taken from the pool (sub-millisecond) and
returned after use.

Works with any cloud PostgreSQL (Supabase, Neon, Render, Aiven, ...).
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import psycopg2
import psycopg2.extras
from psycopg2 import pool as pgpool

from config import Config

# Module-level pool, lazily created on first use. Kept alive for the whole
# process so connections are reused across requests.
_pool: pgpool.ThreadedConnectionPool | None = None


def _normalise_url(url: str) -> str:
    """Accept both 'postgres://' and 'postgresql://' schemes."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def _get_pool() -> pgpool.ThreadedConnectionPool:
    """Lazily create and return the shared connection pool."""

    global _pool
    if _pool is not None:
        return _pool

    url = Config.DATABASE_URL
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Set it in your environment (.env file "
            "locally, or as an environment variable on Render)."
        )
    url = _normalise_url(url)

    # minconn=2 so a few concurrent requests can be served; maxconn leaves
    # headroom. Supabase's pooler allows plenty of connections on free tier.
    _pool = pgpool.ThreadedConnectionPool(
        minconn=2,
        maxconn=8,
        dsn=url,
        connect_timeout=10,
    )
    return _pool


def close_all_connections() -> None:
    """Close every pooled connection (call on app shutdown if ever needed)."""

    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


@contextmanager
def _conn() -> Iterator[Any]:
    """Borrow a connection from the pool, commit/rollback, return it."""

    p = _get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


def query(sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    """Run a SELECT and return all rows as a list of dicts."""

    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return [dict(r) for r in cur.fetchall()]


def query_one(sql: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
    """Run a SELECT and return the first row as a dict, or None."""

    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            row = cur.fetchone()
            return dict(row) if row else None


@contextmanager
def transaction() -> Iterator[Any]:
    """Context manager yielding a cursor; commits on success, rolls back on error."""

    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur


def execute(sql: str, params: Sequence[Any] | None = None) -> None:
    """Run a statement that does not return rows (INSERT/UPDATE/DELETE), commit."""

    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())


def init_schema() -> None:
    """Create all tables if they do not exist. Safe to re-run."""

    here = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(here, "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
            # Migration for databases created before the is_admin column:
            # add it silently if missing (swallow "duplicate column").
            try:
                cur.execute(
                    "ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE"
                )
            except Exception:
                conn.rollback()
                cur = conn.cursor()
            # Ensure at least one admin exists: promote the earliest user.
            cur.execute(
                """
                UPDATE users SET is_admin = TRUE
                WHERE id = (SELECT MIN(id) FROM users)
                  AND NOT EXISTS (SELECT 1 FROM users WHERE is_admin)
                """
            )
