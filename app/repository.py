"""All database access lives here.

The UI layers never write SQL. They call these functions, which return plain
``sqlite3.Row`` objects (dict-like) or simple Python types.

Stock is always derived: ``current_stock = SUM(stock_in) - SUM(stock_out)``
filtered by product and (optionally) color/size. **Stock is reduced only when
an order is shipped** (see :func:`ship_order`), not when it is created, so the
on-hand count reflects only what has actually left the warehouse.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any, Iterable, Optional, Sequence

from app.db import get_connection, transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


def _today() -> str:
    return date.today().isoformat()


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
def list_products(
    search: Optional[str] = None,
    color: Optional[str] = None,
    size: Optional[str] = None,
    stock_filter: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Return products with their total current stock.

    Optional filters:

    * ``search``  — case-insensitive substring on product code or name.
    * ``color``   — keep only products that have a variant with this color.
    * ``size``    — keep only products that have a variant with this size.
    * ``stock_filter`` — one of ``"in_stock"``, ``"out_of_stock"`` or None.

    Products are returned ordered by code.
    """

    clauses: list[str] = []
    params: list[Any] = []

    if search:
        clauses.append("(LOWER(p.code) LIKE ? OR LOWER(p.name) LIKE ?)")
        like = f"%{search.lower()}%"
        params.extend([like, like])
    if color:
        clauses.append(
            "EXISTS (SELECT 1 FROM product_variants v WHERE v.product_id = p.id AND v.color = ?)"
        )
        params.append(color)
    if size:
        clauses.append(
            "EXISTS (SELECT 1 FROM product_variants v WHERE v.product_id = p.id AND v.size = ?)"
        )
        params.append(size)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    sql = f"""
        SELECT p.id, p.code, p.name, p.image_path, p.base_price, p.created_at,
               COALESCE(si.qty, 0) - COALESCE(so.qty, 0) AS stock
        FROM products p
        LEFT JOIN (
            SELECT product_id, SUM(quantity) AS qty
            FROM stock_in
            GROUP BY product_id
        ) si ON si.product_id = p.id
        LEFT JOIN (
            SELECT product_id, SUM(quantity) AS qty
            FROM stock_out
            GROUP BY product_id
        ) so ON so.product_id = p.id
        {where}
        ORDER BY p.code
    """
    with get_connection() as conn:
        rows = _rows_to_dicts(conn.execute(sql, params))

    if stock_filter == "in_stock":
        rows = [r for r in rows if r["stock"] > 0]
    elif stock_filter == "out_of_stock":
        rows = [r for r in rows if r["stock"] <= 0]
    return rows


def list_all_colors() -> list[str]:
    """Distinct colors across all variants, sorted alphabetically."""

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT color FROM product_variants "
            "WHERE color IS NOT NULL AND color <> '' ORDER BY color"
        ).fetchall()
    return [r["color"] for r in rows]


def list_all_sizes() -> list[str]:
    """Distinct sizes across all variants, sorted alphabetically."""

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT size FROM product_variants "
            "WHERE size IS NOT NULL AND size <> '' ORDER BY size"
        ).fetchall()
    return [r["size"] for r in rows]


def get_product(product_id: int) -> Optional[dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        return dict(row) if row else None


def create_product(
    code: str,
    name: str,
    base_price: float,
    image_path: Optional[str],
    variants: Sequence[tuple[str, str]],
) -> int:
    """Create a product together with its (color, size) variants.

    Returns the new product id.
    """

    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO products (code, name, base_price, image_path) "
            "VALUES (?, ?, ?, ?)",
            (code, name, base_price, image_path),
        )
        product_id = cur.lastrowid
        for color, size in variants:
            conn.execute(
                "INSERT OR IGNORE INTO product_variants (product_id, color, size) "
                "VALUES (?, ?, ?)",
                (product_id, color or "", size or ""),
            )
        return product_id


def update_product(
    product_id: int,
    code: str,
    name: str,
    base_price: float,
    image_path: Optional[str],
    variants: Sequence[tuple[str, str]],
) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE products SET code = ?, name = ?, base_price = ?, image_path = ? "
            "WHERE id = ?",
            (code, name, base_price, image_path, product_id),
        )
        # Rebuild variants: simplest correct approach.
        conn.execute("DELETE FROM product_variants WHERE product_id = ?", (product_id,))
        for color, size in variants:
            conn.execute(
                "INSERT OR IGNORE INTO product_variants (product_id, color, size) "
                "VALUES (?, ?, ?)",
                (product_id, color or "", size or ""),
            )


def delete_product(product_id: int) -> None:
    with transaction() as conn:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))


def list_variants(product_id: int) -> list[dict[str, Any]]:
    """Return variants of a product with per-variant current stock."""

    sql = """
        SELECT v.id, v.color, v.size,
               COALESCE(si.qty, 0) - COALESCE(so.qty, 0) AS stock
        FROM product_variants v
        LEFT JOIN (
            SELECT product_id, color, size, SUM(quantity) AS qty
            FROM stock_in
            WHERE product_id = ?
            GROUP BY product_id, color, size
        ) si ON si.color = v.color AND si.size = v.size
        LEFT JOIN (
            SELECT product_id, color, size, SUM(quantity) AS qty
            FROM stock_out
            WHERE product_id = ?
            GROUP BY product_id, color, size
        ) so ON so.color = v.color AND so.size = v.size
        WHERE v.product_id = ?
        ORDER BY v.color, v.size
    """
    with get_connection() as conn:
        return _rows_to_dicts(conn.execute(sql, (product_id, product_id, product_id)))


# ---------------------------------------------------------------------------
# Stock movements
# ---------------------------------------------------------------------------
def add_stock_in(
    product_id: int,
    color: str,
    size: str,
    quantity: int,
    unit_cost: float,
    move_date: str,
    note: str = "",
) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO stock_in "
            "(product_id, color, size, quantity, unit_cost, date, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (product_id, color or "", size or "", quantity, unit_cost, move_date, note),
        )
        # Make sure the variant exists so it shows up in inventory views.
        conn.execute(
            "INSERT OR IGNORE INTO product_variants (product_id, color, size) "
            "VALUES (?, ?, ?)",
            (product_id, color or "", size or ""),
        )


def add_stock_out(
    product_id: int,
    color: str,
    size: str,
    quantity: int,
    move_date: str,
    customer_name: str = "",
    note: str = "",
) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO stock_out "
            "(product_id, color, size, quantity, date, customer_name, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (product_id, color or "", size or "", quantity, move_date, customer_name, note),
        )


def list_stock_in(product_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        return _rows_to_dicts(
            conn.execute(
                "SELECT * FROM stock_in WHERE product_id = ? ORDER BY date DESC, id DESC",
                (product_id,),
            )
        )


def list_stock_out(product_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        return _rows_to_dicts(
            conn.execute(
                "SELECT * FROM stock_out WHERE product_id = ? ORDER BY date DESC, id DESC",
                (product_id,),
            )
        )


def product_stock_total(product_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
              COALESCE((SELECT SUM(quantity) FROM stock_in  WHERE product_id = ?), 0)
            - COALESCE((SELECT SUM(quantity) FROM stock_out WHERE product_id = ?), 0)
              AS stock
            """,
            (product_id, product_id),
        ).fetchone()
        return int(row["stock"])


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
def list_orders(
    search: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Return orders, optionally filtered.

    * ``search`` — case-insensitive substring on customer name or order id.
    * ``status`` — ``"new"`` or ``"shipped"`` (None = all).
    * ``date_from`` / ``date_to`` — inclusive bounds on ``order_date``.
    """

    clauses: list[str] = []
    params: list[Any] = []

    if search:
        clauses.append("(LOWER(customer_name) LIKE ? OR CAST(id AS TEXT) LIKE ?)")
        like = f"%{search.lower()}%"
        params.extend([like, like])
    if status in ("new", "shipped"):
        clauses.append("status = ?")
        params.append(status)
    if date_from:
        clauses.append("order_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("order_date <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM orders {where} ORDER BY id DESC"
    with get_connection() as conn:
        return _rows_to_dicts(conn.execute(sql, params))


def get_order(order_id: int) -> Optional[dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return dict(row) if row else None


def list_order_items(order_id: int) -> list[dict[str, Any]]:
    """Return line items for an order, including the product image path.

    ``image_path`` is the raw stored value; the caller resolves it to an
    absolute path via :func:`app.paths.resolve_stored_image` before display.
    """

    sql = """
        SELECT oi.*, p.code AS product_code, p.name AS product_name,
               p.image_path AS image_path
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        WHERE oi.order_id = ?
        ORDER BY oi.id
    """
    with get_connection() as conn:
        return _rows_to_dicts(conn.execute(sql, (order_id,)))


def create_order(
    customer_name: str,
    order_date: str,
    items: Sequence[dict[str, Any]],
) -> int:
    """Create an order with its line items.

    Stock is **not** reduced here. The order is created with status ``new``
    and only reduces stock when it is marked as shipped via
    :func:`ship_order`. This keeps the inventory count representing only what
    has actually been dispatched. ``items`` is a list of dicts with keys:
    product_id, color, size, quantity, unit_price.
    """

    total = sum(i["quantity"] * i["unit_price"] for i in items)
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO orders (customer_name, order_date, status, total) "
            "VALUES (?, ?, 'new', ?)",
            (customer_name, order_date, total),
        )
        order_id = cur.lastrowid
        for item in items:
            conn.execute(
                "INSERT INTO order_items "
                "(order_id, product_id, color, size, quantity, unit_price) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    order_id,
                    item["product_id"],
                    item.get("color", "") or "",
                    item.get("size", "") or "",
                    item["quantity"],
                    item["unit_price"],
                ),
            )
        return order_id


def ship_order(order_id: int, shipped_date: Optional[str] = None) -> None:
    """Mark an order as shipped and reduce stock for every line item.

    Stock (``stock_out`` rows) is written here, at dispatch time — not when
    the order is created. This makes the on-hand stock reflect only what has
    actually left the warehouse. If the order was already shipped this is a
    no-op.
    """

    order = get_order(order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found")
    if order["status"] == "shipped":
        return

    shipped_date = shipped_date or _today()
    items = list_order_items(order_id)

    with transaction() as conn:
        conn.execute(
            "UPDATE orders SET status = 'shipped', shipped_date = ? WHERE id = ?",
            (shipped_date, order_id),
        )
        for item in items:
            conn.execute(
                "INSERT INTO stock_out "
                "(product_id, color, size, quantity, date, customer_name, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    item["product_id"],
                    item.get("color", "") or "",
                    item.get("size", "") or "",
                    item["quantity"],
                    shipped_date,
                    order["customer_name"],
                    f"Order #{order_id}",
                ),
            )


def unship_order(order_id: int) -> None:
    """Revert an order from "shipped" back to "new".

    The opposite of :func:`ship_order`: the matching ``stock_out`` rows that
    were written when the order was dispatched are removed, so the stock
    returns to the warehouse. If the order is not currently shipped this is
    a no-op.

    The ``stock_out`` rows created at ship time are tagged with
    ``note = 'Order #{id}'`` so we can find and delete exactly those rows
    (and only those) — manual stock-out entries are untouched.
    """

    order = get_order(order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found")
    if order["status"] != "shipped":
        return

    with transaction() as conn:
        conn.execute(
            "DELETE FROM stock_out WHERE note = ?",
            (f"Order #{order_id}",),
        )
        conn.execute(
            "UPDATE orders SET status = 'new', shipped_date = NULL WHERE id = ?",
            (order_id,),
        )


def delete_order(order_id: int) -> None:
    """Delete an order and its line items.

    Because stock is only reduced at ship time (see :func:`ship_order`), an
    order that has not been shipped consumes no stock and is safe to delete.
    A shipped order is rejected so the historical stock-out trail is never
    silently broken.
    """

    order = get_order(order_id)
    if order and order["status"] == "shipped":
        raise ValueError(
            "Cannot delete a shipped order. The stock has already been reduced."
        )
    with transaction() as conn:
        conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def sales_summary(
    start_date: str,
    end_date: str,
    product_id: Optional[int] = None,
) -> dict[str, Any]:
    """Aggregate shipped sales for the inclusive [start_date, end_date] range.

    Returns revenue, order count, total units sold, and the top products.

    ``product_id`` (optional) restricts every metric to a single product so
    the Statistics tab can filter by product.
    """

    product_clause = " AND oi.product_id = ?" if product_id is not None else ""
    summary_params: list[Any] = [start_date, end_date]
    top_params: list[Any] = [start_date, end_date]
    if product_id is not None:
        summary_params.append(product_id)
        top_params.append(product_id)

    sql = f"""
        SELECT
            COUNT(DISTINCT o.id) AS order_count,
            COALESCE(SUM(oi.quantity), 0)         AS units,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE o.status = 'shipped'
          AND o.shipped_date BETWEEN ? AND ?
          {product_clause}
    """
    top_sql = f"""
        SELECT p.code, p.name,
               SUM(oi.quantity) AS units,
               SUM(oi.quantity * oi.unit_price) AS revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        JOIN products p ON p.id = oi.product_id
        WHERE o.status = 'shipped'
          AND o.shipped_date BETWEEN ? AND ?
          {product_clause}
        GROUP BY p.id
        ORDER BY revenue DESC
        LIMIT 10
    """
    with get_connection() as conn:
        summary = dict(conn.execute(sql, summary_params).fetchone())
        top = _rows_to_dicts(conn.execute(top_sql, top_params))
    summary["order_count"] = int(summary["order_count"] or 0)
    summary["units"] = int(summary["units"] or 0)
    summary["revenue"] = float(summary["revenue"] or 0.0)
    summary["top_products"] = top
    return summary


def sales_timeseries(
    start_date: str,
    end_date: str,
    bucket: str = "day",
    product_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Return a time series of shipped sales for charting.

    Each item is ``{"bucket": "YYYY-MM-DD", "orders": int, "units": int,
    "revenue": float}`` covering every period between ``start_date`` and
    ``end_date`` (inclusive). Periods with no sales are filled with zeros so
    the chart shows a continuous timeline.

    ``bucket`` is one of ``"day"`` / ``"week"`` / ``"month"``. Weeks are
    bucketed by their Monday, months by their first day.
    """

    product_clause = " AND oi.product_id = ?" if product_id is not None else ""
    params: list[Any] = [start_date, end_date]
    if product_id is not None:
        params.append(product_id)

    # SQLite stores shipped_date as an ISO string, so a direct GROUP BY on the
    # formatted date works. We compute the bucket label in Python below.
    sql = f"""
        SELECT o.shipped_date AS d,
               COUNT(DISTINCT o.id) AS orders,
               COALESCE(SUM(oi.quantity), 0) AS units,
               COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE o.status = 'shipped'
          AND o.shipped_date BETWEEN ? AND ?
          {product_clause}
        GROUP BY o.shipped_date
        ORDER BY o.shipped_date
    """
    with get_connection() as conn:
        raw = _rows_to_dicts(conn.execute(sql, params))

    # Build a date -> stats lookup.
    by_date: dict[str, dict[str, Any]] = {}
    for row in raw:
        d = (row["d"] or "")[:10]
        by_date.setdefault(d, {"orders": 0, "units": 0, "revenue": 0.0})
        by_date[d]["orders"] += int(row["orders"])
        by_date[d]["units"] += int(row["units"])
        by_date[d]["revenue"] += float(row["revenue"])

    # Walk the range and emit one bucket at a time, filling gaps with zeros.
    from datetime import date as _date, timedelta as _timedelta

    start = _date.fromisoformat(start_date)
    end = _date.fromisoformat(end_date)

    def _week_key(d: _date) -> str:
        # ISO week: Monday is the first day.
        monday = d - _timedelta(days=d.weekday())
        return monday.isoformat()

    def _month_key(d: _date) -> str:
        return d.replace(day=1).isoformat()

    series: dict[str, dict[str, Any]] = {}
    cur = start
    while cur <= end:
        if bucket == "day":
            key = cur.isoformat()
        elif bucket == "week":
            key = _week_key(cur)
        else:  # month
            key = _month_key(cur)
        series.setdefault(key, {"bucket": key, "orders": 0, "units": 0, "revenue": 0.0})
        day_stats = by_date.get(cur.isoformat())
        if day_stats:
            series[key]["orders"] += day_stats["orders"]
            series[key]["units"] += day_stats["units"]
            series[key]["revenue"] += day_stats["revenue"]
        cur += _timedelta(days=1)

    # Return buckets sorted chronologically.
    return [series[k] for k in sorted(series.keys())]
