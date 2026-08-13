"""Flask application: Inventory & Order Management (web version).

Routes:
  /login, /logout           — authentication
  /lang/<lang>              — switch language (EN/ZH)
  /                         — redirect to inventory
  /inventory                — product list (Stage 2)
  /inventory/new, /edit/<id>, /<id>, /delete/<id>, /image/<id>
  /orders, /orders/new, /orders/<id>, ship/unship/delete
  /stats
  /api/timeseries           — JSON for the chart

CLI (run with `flask <command>`):
  flask init-db              — create all tables
  flask create-user <user> <password> [--display "Name"]
"""

from __future__ import annotations

import click
from datetime import date, timedelta

from flask import (
    Flask, render_template, redirect, url_for, request, session,
    Response, flash, jsonify,
)

import db
import repository
from auth import (
    User, current_user, login_required, login_user, logout_current_user,
    get_user_by_username, verify_password, create_user,
)
from config import Config
import translations


def _to_rgb(img):
    """Convert any PIL image to RGB, compositing transparency onto white."""
    from PIL import Image
    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        return background
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _optimise_image(data: bytes, max_size: int = 800, quality: int = 82) -> tuple[bytes, str]:
    """Resize and compress an uploaded image before storing it (full version).

    Caps the longest edge at ``max_size`` and re-encodes as JPEG. This is the
    version served for the full-size lightbox viewer. Returns ``(bytes, ext)``.
    """

    import io
    from PIL import Image

    img = _to_rgb(Image.open(io.BytesIO(data)))
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue(), ".jpg"


def _make_thumbnail(data: bytes, size: int = 160, quality: int = 70) -> bytes:
    """Build a tiny square thumbnail (~3-5 KB) for use in lists/tables.

    Used by the ``/product/<id>/thumb`` endpoint so lists never download the
    full image. Result is cropped to a square (cover) at ``size`` px.
    """

    import io
    from PIL import Image

    img = _to_rgb(Image.open(io.BytesIO(data)))
    # Center-crop to a square, then shrink — gives a clean cover thumbnail
    # without distorted aspect ratios.
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


# In-memory thumbnail cache: product_id -> bytes. Rebuilt lazily on first
# access after a deploy; cheap because each thumbnail is only ~3-5 KB.
_thumb_cache: dict[int, bytes] = {}


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # ---- gzip compression ------------------------------------------------
    # Compresses HTML/JSON responses (~3-5x smaller). Implemented as a tiny
    # after_request hook so no extra dependency (Flask-Compress) is needed.
    import gzip
    import io as _io

    @app.after_request
    def _gzip_response(response):
        accept = request.headers.get("Accept-Encoding", "")
        if "gzip" not in accept.lower():
            return response
        ctype = response.content_type or ""
        if not (ctype.startswith("text/") or "json" in ctype or "javascript" in ctype or "css" in ctype):
            return response
        data = response.get_data()
        if len(data) < 512:
            return response
        buf = _io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6, mtime=0) as gz:
            gz.write(data)
        response.set_data(buf.getvalue())
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Vary"] = "Accept-Encoding"
        response.headers["Content-Length"] = len(response.get_data())
        return response

    # ---- Template globals / filters ------------------------------------
    @app.context_processor
    def inject_globals():
        return {
            "current_user": current_user(),
            "tr": translations.tr,
            "lang": translations.get_language(),
        }

    # ---- Authentication -------------------------------------------------
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            row = get_user_by_username(username)
            if row and verify_password(row["password_hash"], password):
                login_user(User(row["id"], row["username"], row.get("display_name") or ""))
                next_url = request.args.get("next") or url_for("inventory")
                return redirect(next_url)
            flash(translations.tr("login.bad"), "danger")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        logout_current_user()
        flash(translations.tr("login.signed_out"), "info")
        return redirect(url_for("login"))

    @app.route("/lang/<lang>")
    def set_lang(lang):
        translations.set_language(lang)
        return redirect(request.referrer or url_for("inventory"))

    # ---- Product image serving (binary stored in the DB) ---------------
    @app.route("/product/<int:product_id>/image")
    def product_image(product_id: int):
        """Full-size image — used only by the click-to-zoom lightbox."""
        img = repository.get_product_image(product_id)
        if not img:
            return Response(_PLACEHOLDER_PNG, mimetype="image/png")
        return Response(img, mimetype="image/jpeg",
                        headers={"Cache-Control": "public, max-age=86400"})

    @app.route("/product/<int:product_id>/thumb")
    def product_thumb(product_id: int):
        """Tiny square thumbnail (~3-5 KB) for lists and tables.

        Cached in memory per product id. Lists load this instead of the full
        image, so a page with 50 products downloads ~200 KB instead of ~5 MB.
        """
        thumb = _thumb_cache.get(product_id)
        if thumb is None:
            img = repository.get_product_image(product_id)
            if not img:
                return Response(_PLACEHOLDER_PNG, mimetype="image/png")
            try:
                thumb = _make_thumbnail(img)
            except Exception:
                return Response(_PLACEHOLDER_PNG, mimetype="image/png")
            _thumb_cache[product_id] = thumb
        return Response(thumb, mimetype="image/jpeg",
                        headers={"Cache-Control": "public, max-age=86400"})

    # ---- Inventory ------------------------------------------------------
    @app.route("/")
    def index():
        return redirect(url_for("inventory"))

    @app.route("/inventory")
    @login_required
    def inventory():
        search = request.args.get("search", "").strip() or None
        color = request.args.get("color", "").strip() or None
        size = request.args.get("size", "").strip() or None
        stock_filter = request.args.get("stock", "").strip() or None
        products = repository.list_products(
            search=search, color=color, size=size, stock_filter=stock_filter
        )
        return render_template(
            "inventory/list.html",
            products=products,
            colors=repository.list_all_colors(),
            sizes=repository.list_all_sizes(),
            filters={"search": search or "", "color": color or "", "size": size or "",
                     "stock": stock_filter or ""},
        )

    @app.route("/inventory/new", methods=["GET", "POST"])
    @login_required
    def product_new():
        if request.method == "POST":
            return _save_product(None)
        return render_template("inventory/form.html", product=None,
                               variants=[], colors=repository.list_all_colors(),
                               sizes=repository.list_all_sizes())

    @app.route("/inventory/<int:product_id>/edit", methods=["GET", "POST"])
    @login_required
    def product_edit(product_id: int):
        product = repository.get_product(product_id)
        if not product:
            flash("Product not found.", "danger")
            return redirect(url_for("inventory"))
        if request.method == "POST":
            return _save_product(product_id)
        return render_template("inventory/form.html", product=product,
                               variants=repository.list_variants(product_id),
                               colors=repository.list_all_colors(),
                               sizes=repository.list_all_sizes())

    def _save_product(product_id):
        code = request.form.get("code", "").strip()
        name = request.form.get("name", "").strip()
        if not code or not name:
            flash(translations.tr("err.missing"), "danger")
            return redirect(request.url)
        try:
            price = float(request.form.get("base_price", "0") or 0)
        except ValueError:
            flash(translations.tr("err.invalid_price"), "danger")
            return redirect(request.url)

        # Variants: collected from repeated form fields.
        colors = request.form.getlist("v_color")
        sizes = request.form.getlist("v_size")
        variants = [(c.strip(), s.strip()) for c, s in zip(colors, sizes)]
        # Deduplicate preserving order.
        seen = set()
        unique = []
        for c, s in variants:
            if (c, s) not in seen:
                seen.add((c, s))
                unique.append((c, s))

        # Optional image upload.
        image_bytes, image_ext, keep = None, None, True
        upload = request.files.get("image")
        remove = request.form.get("remove_image") == "1"
        if upload and upload.filename:
            data = upload.read()
            if data:
                image_bytes, image_ext = _optimise_image(data)
        elif remove:
            keep = False

        if product_id is None:
            new_id = repository.create_product(
                code, name, price, image_bytes, image_ext, unique
            )
            flash(f"Product #{new_id} created.", "success")
        else:
            repository.update_product(
                product_id, code, name, price, image_bytes, image_ext, unique, keep
            )
            # Invalidate the cached thumbnail so the new image shows up.
            _thumb_cache.pop(product_id, None)
            flash("Product updated.", "success")
        return redirect(url_for("inventory"))

    @app.route("/inventory/<int:product_id>")
    @login_required
    def product_detail(product_id: int):
        product = repository.get_product(product_id)
        if not product:
            flash("Product not found.", "danger")
            return redirect(url_for("inventory"))
        return render_template(
            "inventory/detail.html",
            product=product,
            stock_total=repository.product_stock_total(product_id),
            variants=repository.list_variants(product_id),
            stock_in=repository.list_stock_in(product_id),
            stock_out=repository.list_stock_out(product_id),
        )

    @app.route("/inventory/<int:product_id>/stock-in", methods=["POST"])
    @login_required
    def stock_in_add(product_id: int):
        try:
            qty = int(request.form.get("quantity", "0"))
            cost = float(request.form.get("unit_cost", "0") or 0)
        except ValueError:
            flash("Invalid quantity or cost.", "danger")
            return redirect(url_for("product_detail", product_id=product_id))
        repository.add_stock_in(
            product_id,
            request.form.get("color", ""),
            request.form.get("size", ""),
            qty, cost,
            request.form.get("date") or date.today().isoformat(),
            request.form.get("note", ""),
        )
        return redirect(url_for("product_detail", product_id=product_id))

    @app.route("/inventory/<int:product_id>/stock-out", methods=["POST"])
    @login_required
    def stock_out_add(product_id: int):
        try:
            qty = int(request.form.get("quantity", "0"))
        except ValueError:
            flash("Invalid quantity.", "danger")
            return redirect(url_for("product_detail", product_id=product_id))
        repository.add_stock_out(
            product_id,
            request.form.get("color", ""),
            request.form.get("size", ""),
            qty,
            request.form.get("date") or date.today().isoformat(),
            request.form.get("customer_name", ""),
            request.form.get("note", ""),
        )
        return redirect(url_for("product_detail", product_id=product_id))

    @app.route("/inventory/<int:product_id>/delete", methods=["POST"])
    @login_required
    def product_delete(product_id: int):
        try:
            repository.delete_product(product_id)
            _thumb_cache.pop(product_id, None)
            flash("Product deleted.", "success")
        except Exception as exc:
            flash(f"Cannot delete: {exc}", "danger")
        return redirect(url_for("inventory"))

    # ---- Orders (Stage 3 — basic stubs for now) -----------------------
    @app.route("/orders")
    @login_required
    def orders():
        orders = repository.list_orders(
            search=request.args.get("search", "").strip() or None,
            status=request.args.get("status", "").strip() or None,
            date_from=request.args.get("from", "").strip() or None,
            date_to=request.args.get("to", "").strip() or None,
        )
        return render_template("orders/list.html", orders=orders,
                               filters={"search": request.args.get("search", ""),
                                        "status": request.args.get("status", ""),
                                        "from": request.args.get("from", ""),
                                        "to": request.args.get("to", "")})

    @app.route("/orders/new", methods=["GET", "POST"])
    @login_required
    def order_new():
        if request.method == "POST":
            customer = request.form.get("customer_name", "").strip()
            order_date = request.form.get("order_date") or date.today().isoformat()
            product_ids = request.form.getlist("product_id")
            colors = request.form.getlist("color")
            sizes = request.form.getlist("size")
            qtys = request.form.getlist("quantity")
            prices = request.form.getlist("unit_price")
            items = []
            for pid, c, s, q, p in zip(product_ids, colors, sizes, qtys, prices):
                if not pid:
                    continue
                try:
                    items.append({
                        "product_id": int(pid),
                        "color": c, "size": s,
                        "quantity": int(q), "unit_price": float(p),
                    })
                except (ValueError, TypeError):
                    continue
            if not customer or not items:
                flash("Customer and at least one line item are required.", "danger")
                return redirect(url_for("order_new"))
            oid = repository.create_order(customer, order_date, items)
            flash(translations.tr("info.saved_msg", order_id=oid), "success")
            return redirect(url_for("orders"))
        return render_template("orders/form.html", order=None,
                               products=repository.list_products(),
                               today=date.today().isoformat())

    @app.route("/orders/<int:order_id>")
    @login_required
    def order_detail(order_id: int):
        order = repository.get_order(order_id)
        if not order:
            flash("Order not found.", "danger")
            return redirect(url_for("orders"))
        return render_template("orders/form.html", order=order,
                               items=repository.list_order_items(order_id),
                               products=[])

    @app.route("/orders/<int:order_id>/ship", methods=["POST"])
    @login_required
    def order_ship(order_id: int):
        try:
            repository.ship_order(order_id)
            flash(translations.tr("status.shipped"), "success")
        except Exception as exc:
            flash(f"Cannot ship: {exc}", "danger")
        return redirect(url_for("orders"))

    @app.route("/orders/<int:order_id>/unship", methods=["POST"])
    @login_required
    def order_unship(order_id: int):
        try:
            repository.unship_order(order_id)
            flash(translations.tr("status.new"), "success")
        except Exception as exc:
            flash(f"Cannot revert: {exc}", "danger")
        return redirect(url_for("orders"))

    @app.route("/orders/<int:order_id>/delete", methods=["POST"])
    @login_required
    def order_delete(order_id: int):
        try:
            repository.delete_order(order_id)
            flash("Order deleted.", "success")
        except Exception as exc:
            flash(f"Cannot delete: {exc}", "danger")
        return redirect(url_for("orders"))

    # ---- Statistics ----------------------------------------------------
    @app.route("/stats")
    @login_required
    def stats():
        from datetime import date as _date
        today = _date.today()
        start_str = request.args.get("from") or today.replace(day=1).isoformat()
        end_str = request.args.get("to") or today.isoformat()
        product_id = request.args.get("product_id") or None
        if product_id:
            product_id = int(product_id)
        summary = repository.sales_summary(start_str, end_str, product_id=product_id)
        return render_template(
            "stats.html",
            summary=summary,
            top=summary["top_products"],
            products=repository.list_products(),
            start=start_str, end=end_str,
            product_id=product_id,
        )

    @app.route("/api/timeseries")
    @login_required
    def api_timeseries():
        start = request.args.get("from")
        end = request.args.get("to")
        metric = request.args.get("metric", "revenue")
        product_id = request.args.get("product_id") or None
        if product_id:
            product_id = int(product_id)
        if not start or not end:
            return jsonify({"labels": [], "values": []})
        # Pick bucket size from the span.
        from datetime import date as _date
        span = (_date.fromisoformat(end) - _date.fromisoformat(start)).days
        bucket = "day" if span <= 21 else ("week" if span <= 120 else "month")
        series = repository.sales_timeseries(start, end, bucket=bucket, product_id=product_id)
        labels = [s["bucket"] for s in series]
        values = [float(s[metric]) for s in series]
        return jsonify({"labels": labels, "values": values, "metric": metric})

    # ---- CLI commands --------------------------------------------------
    @app.cli.command("init-db")
    def init_db_cmd():
        """Create all database tables (idempotent)."""
        db.init_schema()
        click.echo("Database schema created/verified.")

    @app.cli.command("create-user")
    @click.argument("username")
    @click.argument("password")
    @click.option("--display", default="", help="Display name shown in the UI.")
    def create_user_cmd(username: str, password: str, display: str):
        """Create a login account."""
        uid = create_user(username, password, display)
        click.echo(f"Created user '{username}' (id={uid}).")

    @app.cli.command("recompress-images")
    def recompress_images_cmd():
        """Re-compress every stored product image to the current size/quality.

        Run this once after deploying newer image-optimisation settings, or to
        shrink photos that were uploaded before compression was added.
        """
        rows = db.query("SELECT id FROM products WHERE image IS NOT NULL ORDER BY id")
        if not rows:
            click.echo("No product images to recompress.")
            return
        total_before = 0
        total_after = 0
        count = 0
        for r in rows:
            pid = r["id"]
            raw = db.query_one("SELECT image FROM products WHERE id = %s", (pid,))["image"]
            if not raw:
                continue
            before = len(raw)
            new_bytes, _ = _optimise_image(raw)
            after = len(new_bytes)
            db.execute(
                "UPDATE products SET image = %s, image_ext = '.jpg' WHERE id = %s",
                (new_bytes, pid),
            )
            _thumb_cache.pop(pid, None)
            total_before += before
            total_after += after
            count += 1
            click.echo(f"  product #{pid}: {before:,} -> {after:,} bytes")
        if count:
            ratio = total_before / max(1, total_after)
            click.echo(
                f"\nRecompressed {count} image(s): "
                f"{total_before:,} -> {total_after:,} bytes ({ratio:.1f}x smaller)."
            )

    return app


# 1x1 transparent PNG used as a placeholder when a product has no image.
_PLACEHOLDER_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c63000100000005000100" + "0d0a2db4" + "0000000049454e44ae426082"
)


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
