"""All database access for the web app.

This is a port of the desktop app's ``repository.py`` to PostgreSQL. The
business rules are preserved exactly:

  * Stock is always derived: ``current = SUM(stock_in) - SUM(stock_out)``.
  * ``create_order`` does NOT reduce stock — the order starts as 'new'.
  * ``ship_order`` is what reduces stock (writes ``stock_out`` rows).
  * ``unship_order`` returns stock (deletes the matching ``stock_out`` rows).
  * A shipped order cannot be deleted.

Differences from the SQLite original:
  * Placeholders are ``%s`` (psycopg2) instead of ``?``.
  * ``stock_out`` has a real ``order_id`` FK instead of the fragile
    ``note = 'Order #N'`` tag — so unship/deletion are robust.
  * Product images live in the ``products.image`` BYTEA column instead of
    files on disk (Render's free filesystem is ephemeral).
  * Dates are real ``DATE`` columns.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional, Sequence

import db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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
    """Products with computed current stock, optionally filtered.

    Filters:
      * ``search``       — case-insensitive substring on code or name.
      * ``color``/``size``— keep only products that have a variant with this value.
      * ``stock_filter`` — "in_stock" (stock > 0) or "out_of_stock" (stock <= 0).
    """

    clauses: list[str] = []
    params: list[Any] = []

    if search:
        clauses.append("(LOWER(p.code) LIKE %s OR LOWER(p.name) LIKE %s)")
        like = f"%{search.lower()}%"
        params += [like, like]
    if color is not None and color != "":
        clauses.append(
            "EXISTS (SELECT 1 FROM product_variants v "
            "WHERE v.product_id = p.id AND v.color = %s)"
        )
        params.append(color)
    if size is not None and size != "":
        clauses.append(
            "EXISTS (SELECT 1 FROM product_variants v "
            "WHERE v.product_id = p.id AND v.size = %s)"
        )
        params.append(size)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT p.id, p.code, p.name, p.base_price, p.created_at,
               (COALESCE(si.qty, 0) - COALESCE(so.qty, 0)) AS stock,
               (p.image IS NOT NULL) AS has_image
        FROM products p
        LEFT JOIN (
            SELECT product_id, SUM(quantity) AS qty
            FROM stock_in GROUP BY product_id
        ) si ON si.product_id = p.id
        LEFT JOIN (
            SELECT product_id, SUM(quantity) AS qty
            FROM stock_out GROUP BY product_id
        ) so ON so.product_id = p.id
        {where}
        ORDER BY p.code
    """
    rows = db.query(sql, params)
    if stock_filter == "in_stock":
        rows = [r for r in rows if r["stock"] > 0]
    elif stock_filter == "out_of_stock":
        rows = [r for r in rows if r["stock"] <= 0]
    return rows


def list_all_colors() -> list[str]:
    return [
        r["color"]
        for r in db.query(
            "SELECT DISTINCT color FROM product_variants "
            "WHERE color <> '' ORDER BY color"
        )
    ]


def list_all_sizes() -> list[str]:
    return [
        r["size"]
        for r in db.query(
            "SELECT DISTINCT size FROM product_variants "
            "WHERE size <> '' ORDER BY size"
        )
    ]


def get_product(product_id: int) -> Optional[dict[str, Any]]:
    return db.query_one(
        "SELECT id, code, name, base_price, image_ext, created_at, "
        "(image IS NOT NULL) AS has_image FROM products WHERE id = %s",
        (product_id,),
    )


def get_product_image(product_id: int) -> Optional[bytes]:
    """Return the raw image bytes for a product, or None."""

    row = db.query_one("SELECT image FROM products WHERE id = %s", (product_id,))
    return row["image"] if row else None


def create_product(
    code: str,
    name: str,
    base_price: float,
    image_bytes: Optional[bytes],
    image_ext: Optional[str],
    variants: Sequence[tuple[str, str]],
) -> int:
    """Create a product + its variants. Returns the new product id."""

    with db.transaction() as cur:
        cur.execute(
            "INSERT INTO products (code, name, base_price, image, image_ext) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (code, name, base_price, image_bytes, image_ext),
        )
        product_id = cur.fetchone()["id"]
        _upsert_variants(cur, product_id, variants)
        return product_id


def update_product(
    product_id: int,
    code: str,
    name: str,
    base_price: float,
    image_bytes: Optional[bytes],
    image_ext: Optional[str],
    variants: Sequence[tuple[str, str]],
    keep_old_image: bool = True,
) -> None:
    """Update a product. If ``image_bytes`` is None and ``keep_old_image``
    is True, the existing image is preserved; otherwise the image is cleared.
    """

    with db.transaction() as cur:
        if image_bytes is not None:
            cur.execute(
                "UPDATE products SET code=%s, name=%s, base_price=%s, "
                "image=%s, image_ext=%s WHERE id=%s",
                (code, name, base_price, image_bytes, image_ext, product_id),
            )
        elif keep_old_image:
            cur.execute(
                "UPDATE products SET code=%s, name=%s, base_price=%s WHERE id=%s",
                (code, name, base_price, product_id),
            )
        else:
            cur.execute(
                "UPDATE products SET code=%s, name=%s, base_price=%s, "
                "image=NULL, image_ext=NULL WHERE id=%s",
                (code, name, base_price, product_id),
            )
        _upsert_variants(cur, product_id, variants)


def _upsert_variants(cur, product_id: int, variants: Sequence[tuple[str, str]]) -> None:
    cur.execute("DELETE FROM product_variants WHERE product_id = %s", (product_id,))
    for color, size in variants:
        cur.execute(
            "INSERT INTO product_variants (product_id, color, size) "
            "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (product_id, color or "", size or ""),
        )


def delete_product(product_id: int) -> None:
    """Delete a product. Will fail (FK RESTRICT) if it appears in order_items."""

    db.execute("DELETE FROM products WHERE id = %s", (product_id,))


def list_variants(product_id: int) -> list[dict[str, Any]]:
    return db.query(
        """
        SELECT v.id, v.color, v.size,
               (COALESCE(si.qty, 0) - COALESCE(so.qty, 0)) AS stock
        FROM product_variants v
        LEFT JOIN (
            SELECT color, size, SUM(quantity) AS qty
            FROM stock_in WHERE product_id = %s GROUP BY color, size
        ) si ON si.color = v.color AND si.size = v.size
        LEFT JOIN (
            SELECT color, size, SUM(quantity) AS qty
            FROM stock_out WHERE product_id = %s GROUP BY color, size
        ) so ON so.color = v.color AND so.size = v.size
        WHERE v.product_id = %s
        ORDER BY v.color, v.size
        """,
        (product_id, product_id, product_id),
    )


def product_stock_total(product_id: int) -> int:
    row = db.query_one(
        """
        SELECT
          COALESCE((SELECT SUM(quantity) FROM stock_in  WHERE product_id = %s), 0)
        - COALESCE((SELECT SUM(quantity) FROM stock_out WHERE product_id = %s), 0)
          AS stock
        """,
        (product_id, product_id),
    )
    return int(row["stock"]) if row else 0


# ---------------------------------------------------------------------------
# Stock movements
# ---------------------------------------------------------------------------
def add_stock_in(
    product_id: int, color: str, size: str, quantity: int,
    unit_cost: float, move_date: str, note: str = "",
) -> None:
    with db.transaction() as cur:
        cur.execute(
            "INSERT INTO stock_in "
            "(product_id, color, size, quantity, unit_cost, date, note) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (product_id, color or "", size or "", quantity, unit_cost, move_date, note),
        )
        cur.execute(
            "INSERT INTO product_variants (product_id, color, size) "
            "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (product_id, color or "", size or ""),
        )


def add_stock_out(
    product_id: int, color: str, size: str, quantity: int,
    move_date: str, customer_name: str = "", note: str = "",
) -> None:
    db.execute(
        "INSERT INTO stock_out "
        "(product_id, color, size, quantity, date, customer_name, note) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (product_id, color or "", size or "", quantity, move_date, customer_name, note),
    )


def list_stock_in(product_id: int) -> list[dict[str, Any]]:
    return db.query(
        "SELECT * FROM stock_in WHERE product_id = %s ORDER BY date DESC, id DESC",
        (product_id,),
    )


def list_stock_out(product_id: int) -> list[dict[str, Any]]:
    return db.query(
        "SELECT * FROM stock_out WHERE product_id = %s ORDER BY date DESC, id DESC",
        (product_id,),
    )


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
def list_orders(
    search: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if search:
        clauses.append("(LOWER(customer_name) LIKE %s OR CAST(id AS TEXT) LIKE %s)")
        like = f"%{search.lower()}%"
        params += [like, like]
    if status in ("new", "shipped"):
        clauses.append("status = %s")
        params.append(status)
    if date_from:
        clauses.append("order_date >= %s")
        params.append(date_from)
    if date_to:
        clauses.append("order_date <= %s")
        params.append(date_to)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return db.query(f"SELECT * FROM orders {where} ORDER BY id DESC", params)


def get_order(order_id: int) -> Optional[dict[str, Any]]:
    return db.query_one("SELECT * FROM orders WHERE id = %s", (order_id,))


def list_order_items(order_id: int) -> list[dict[str, Any]]:
    return db.query(
        """
        SELECT oi.*, p.code AS product_code, p.name AS product_name,
               (p.image IS NOT NULL) AS has_image
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        WHERE oi.order_id = %s
        ORDER BY oi.id
        """,
        (order_id,),
    )


def create_order(
    customer_name: str, order_date: str, items: Sequence[dict[str, Any]],
) -> int:
    """Create an order with status 'new'. Stock is NOT reduced here."""

    total = sum(i["quantity"] * i["unit_price"] for i in items)
    with db.transaction() as cur:
        cur.execute(
            "INSERT INTO orders (customer_name, order_date, status, total) "
            "VALUES (%s, %s, 'new', %s) RETURNING id",
            (customer_name, order_date, total),
        )
        order_id = cur.fetchone()["id"]
        for item in items:
            cur.execute(
                "INSERT INTO order_items "
                "(order_id, product_id, color, size, quantity, unit_price) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
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
    """Mark an order as shipped and reduce stock. Idempotent (no-op if shipped)."""

    order = get_order(order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found")
    if order["status"] == "shipped":
        return

    shipped_date = shipped_date or _today()
    items = list_order_items(order_id)
    with db.transaction() as cur:
        cur.execute(
            "UPDATE orders SET status='shipped', shipped_date=%s WHERE id=%s",
            (shipped_date, order_id),
        )
        for item in items:
            cur.execute(
                "INSERT INTO stock_out "
                "(product_id, color, size, quantity, date, customer_name, note, order_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    item["product_id"],
                    item["color"] or "",
                    item["size"] or "",
                    item["quantity"],
                    shipped_date,
                    order["customer_name"],
                    f"Order #{order_id}",
                    order_id,
                ),
            )


def unship_order(order_id: int) -> None:
    """Revert a shipped order to 'new' and return the stock it consumed."""

    order = get_order(order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found")
    if order["status"] != "shipped":
        return
    with db.transaction() as cur:
        # The real order_id FK makes this exact — manual stock_out rows are
        # never touched (they have order_id = NULL).
        cur.execute("DELETE FROM stock_out WHERE order_id = %s", (order_id,))
        cur.execute(
            "UPDATE orders SET status='new', shipped_date=NULL WHERE id=%s",
            (order_id,),
        )


def delete_order(order_id: int) -> None:
    """Delete a new (unshipped) order. Shipped orders are rejected."""

    order = get_order(order_id)
    if order and order["status"] == "shipped":
        raise ValueError(
            "Cannot delete a shipped order. The stock has already been reduced."
        )
    db.execute("DELETE FROM orders WHERE id = %s", (order_id,))


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def sales_summary(
    start_date: str, end_date: str, product_id: Optional[int] = None,
) -> dict[str, Any]:
    """Shipped-sales aggregates for [start, end]. Optionally per product."""

    product_clause = " AND oi.product_id = %s" if product_id is not None else ""
    summary_params: list[Any] = [start_date, end_date]
    top_params: list[Any] = [start_date, end_date]
    if product_id is not None:
        summary_params.append(product_id)
        top_params.append(product_id)

    summary = db.query_one(
        f"""
        SELECT COUNT(DISTINCT o.id) AS order_count,
               COALESCE(SUM(oi.quantity), 0) AS units,
               COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS revenue
        FROM orders o JOIN order_items oi ON oi.order_id = o.id
        WHERE o.status = 'shipped' AND o.shipped_date BETWEEN %s AND %s
              {product_clause}
        """,
        summary_params,
    )
    top = db.query(
        f"""
        SELECT p.code, p.name,
               SUM(oi.quantity) AS units,
               SUM(oi.quantity * oi.unit_price) AS revenue
        FROM orders o JOIN order_items oi ON oi.order_id = o.id
                      JOIN products p ON p.id = oi.product_id
        WHERE o.status = 'shipped' AND o.shipped_date BETWEEN %s AND %s
              {product_clause}
        GROUP BY p.id ORDER BY revenue DESC LIMIT 10
        """,
        top_params,
    )
    return {
        "order_count": int(summary["order_count"] or 0),
        "units": int(summary["units"] or 0),
        "revenue": float(summary["revenue"] or 0.0),
        "top_products": top,
    }


def sales_timeseries(
    start_date: str, end_date: str, bucket: str = "day",
    product_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Continuous time series of shipped sales for charting."""

    product_clause = " AND oi.product_id = %s" if product_id is not None else ""
    params: list[Any] = [start_date, end_date]
    if product_id is not None:
        params.append(product_id)

    raw = db.query(
        f"""
        SELECT o.shipped_date AS d,
               COUNT(DISTINCT o.id) AS orders,
               COALESCE(SUM(oi.quantity), 0) AS units,
               COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS revenue
        FROM orders o JOIN order_items oi ON oi.order_id = o.id
        WHERE o.status = 'shipped' AND o.shipped_date BETWEEN %s AND %s
              {product_clause}
        GROUP BY o.shipped_date ORDER BY o.shipped_date
        """,
        params,
    )

    by_date: dict[str, dict[str, Any]] = {}
    for row in raw:
        d = row["d"].isoformat() if hasattr(row["d"], "isoformat") else str(row["d"])[:10]
        by_date.setdefault(d, {"orders": 0, "units": 0, "revenue": 0.0})
        by_date[d]["orders"] += int(row["orders"])
        by_date[d]["units"] += int(row["units"])
        by_date[d]["revenue"] += float(row["revenue"])

    from datetime import date as _date, timedelta as _timedelta
    start = _date.fromisoformat(start_date)
    end = _date.fromisoformat(end_date)

    def week_key(d: _date) -> str:
        return (d - _timedelta(days=d.weekday())).isoformat()

    def month_key(d: _date) -> str:
        return d.replace(day=1).isoformat()

    series: dict[str, dict[str, Any]] = {}
    cur = start
    while cur <= end:
        key = (cur.isoformat() if bucket == "day"
               else week_key(cur) if bucket == "week"
               else month_key(cur))
        series.setdefault(key, {"bucket": key, "orders": 0, "units": 0, "revenue": 0.0})
        stats = by_date.get(cur.isoformat())
        if stats:
            series[key]["orders"] += stats["orders"]
            series[key]["units"] += stats["units"]
            series[key]["revenue"] += stats["revenue"]
        cur += _timedelta(days=1)
    return [series[k] for k in sorted(series.keys())]
