"""SQLite connection management and schema initialisation.

The schema models a small wholesale/retail inventory system:

* ``products`` and ``product_variants`` describe what is being sold. A variant
  is a (color, size) combination of a product.
* ``stock_in`` / ``stock_out`` are append-only movement logs. Current stock for
  any variant is ``SUM(stock_in) - SUM(stock_out)``.
* ``orders`` + ``order_items`` record customer orders. Marking an order as
  "shipped" automatically writes matching ``stock_out`` rows so sales and stock
  never drift out of sync.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.paths import DB_PATH, ensure_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    image_path    TEXT,
    base_price    REAL NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS product_variants (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER NOT NULL,
    color         TEXT,
    size          TEXT,
    UNIQUE (product_id, color, size),
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stock_in (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER NOT NULL,
    color         TEXT,
    size          TEXT,
    quantity      INTEGER NOT NULL DEFAULT 0,
    unit_cost     REAL NOT NULL DEFAULT 0,
    date          TEXT NOT NULL,
    note          TEXT,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stock_out (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER NOT NULL,
    color         TEXT,
    size          TEXT,
    quantity      INTEGER NOT NULL DEFAULT 0,
    date          TEXT NOT NULL,
    customer_name TEXT,
    note          TEXT,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    order_date    TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'new',
    shipped_date  TEXT,
    total         REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS order_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      INTEGER NOT NULL,
    product_id    INTEGER NOT NULL,
    color         TEXT,
    size          TEXT,
    quantity      INTEGER NOT NULL DEFAULT 0,
    unit_price    REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (order_id)   REFERENCES orders (id)   ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE RESTRICT
);
"""


def get_connection() -> sqlite3.Connection:
    """Open a new SQLite connection with sensible defaults.

    ``row_factory`` is set so rows behave like dictionaries which keeps the
    UI and repository code readable. Foreign-key enforcement is turned on so
    cascade deletes work as expected.
    """

    ensure_dirs()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Create any missing tables. Safe to call on every startup."""

    with get_connection() as conn:
        conn.executescript(SCHEMA)
        _migrate_image_paths(conn)
        _migrate_order_items_size(conn)


def _migrate_image_paths(conn: sqlite3.Connection) -> None:
    """Collapse legacy absolute ``image_path`` values to bare filenames.

    Older versions stored the full path (e.g.
    ``C:\\Users\\someone\\ZCodeProject\\images\\foo.jpg``), which broke as soon
    as the project moved to another machine. New rows store only the filename.
    This one-time pass rewrites any row still holding a path with a separator.

    Idempotent: values without a separator are left untouched, so re-running
    on an already-migrated database is a no-op.
    """

    rows = conn.execute("SELECT id, image_path FROM products").fetchall()
    for row in rows:
        value = row["image_path"]
        if not value or os.sep not in value and "/" not in value and "\\" not in value:
            continue
        conn.execute(
            "UPDATE products SET image_path = ? WHERE id = ?",
            (os.path.basename(value), row["id"]),
        )


def _migrate_order_items_size(conn: sqlite3.Connection) -> None:
    """Add the ``size`` column to ``order_items`` on legacy databases.

    The column was added later to track the size chosen on each order line. New
    databases get it from the schema directly; existing ones need ``ALTER
    TABLE``. SQLite raises if the column already exists, so we swallow that
    single, expected error — the result is idempotent across startups.
    """

    try:
        conn.execute("ALTER TABLE order_items ADD COLUMN size TEXT")
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc):
            raise


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """Context manager that commits on success and rolls back on error."""

    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
