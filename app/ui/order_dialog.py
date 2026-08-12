"""Dialog to create or view an order and its line items."""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
from datetime import date
from typing import Optional

from app import i18n, repository
from app.paths import resolve_stored_image
from app.ui.theme import COLORS
from app.ui.widgets import (
    fit_window_to_content,
    insert_image_row,
    load_image,
    make_dialog_layout,
    make_treeview,
    show_error,
    show_info,
)


class OrderDialog:
    """Modal dialog for creating or inspecting an order."""

    def __init__(self, parent: tk.Misc, order_id: Optional[int] = None) -> None:
        self.result: Optional[int] = None
        self.order_id = order_id
        self.is_readonly = order_id is not None

        self.top = tk.Toplevel(parent)
        self.top.title(
            f"Order #{order_id}" if order_id else i18n.tr("dlg.order_title_new")
        )
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(background=COLORS["bg"])

        body, footer = make_dialog_layout(self.top)
        # Add inner padding via a wrapper so the scrollable body breathes.
        body.configure(padding=20)

        # Title
        ttk.Label(
            body,
            text=f"Order #{order_id}" if order_id else i18n.tr("dlg.order_title_new"),
            style="Title.TLabel",
        ).pack(anchor=tk.W)
        ttk.Label(
            body,
            text=i18n.tr("dlg.order_subtitle"),
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(2, 12))

        # Header card
        header_card = ttk.Frame(body, style="Card.TFrame", padding=16)
        header_card.pack(fill=tk.X)

        ttk.Label(header_card, text=i18n.tr("lbl.customer"), style="Card.TLabel").grid(
            row=0, column=0, sticky=tk.W, padx=4, pady=6
        )
        self.customer_var = tk.StringVar()
        self.customer_entry = ttk.Entry(header_card, textvariable=self.customer_var, width=30)
        self.customer_entry.grid(row=0, column=1, sticky=tk.W, padx=4)

        ttk.Label(header_card, text=i18n.tr("lbl.order_date"), style="Card.TLabel").grid(
            row=0, column=2, sticky=tk.W, padx=(20, 4), pady=6
        )
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.date_entry = ttk.Entry(header_card, textvariable=self.date_var, width=14)
        self.date_entry.grid(row=0, column=3, sticky=tk.W, padx=4)

        # Status line (view mode only)
        self.status_label = ttk.Label(body, text="", style="Subtitle.TLabel")
        self.status_label.pack(anchor=tk.W, pady=(10, 0))

        # Items section
        ttk.Label(body, text=i18n.tr("sect.line_items"), style="Section.TLabel").pack(
            anchor=tk.W, pady=(14, 6)
        )
        items_card = ttk.Frame(body, style="Card.TFrame")
        items_card.pack(fill=tk.BOTH, expand=True)
        items_inner = ttk.Frame(items_card, style="Card.TFrame")
        items_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        self.items_tree = make_treeview(
            items_inner,
            [
                ("code", i18n.tr("col.code"), 100),
                ("name", i18n.tr("col.product"), 180),
                ("color", i18n.tr("col.color"), 100),
                ("size", i18n.tr("col.size"), 80),
                ("qty", i18n.tr("col.qty"), 60),
                ("price", i18n.tr("col.price"), 80),
                ("subtotal", i18n.tr("col.subtotal"), 100),
            ],
            with_image=True,
            image_size=44,
        )

        # Line editor for new orders — placed inside the sticky footer so the
        # whole row (Product / Color / Size / Qty / Price + Add/Remove) stays
        # pinned to the bottom of the window, just above the action buttons,
        # and is always visible regardless of window size.
        editor = ttk.Frame(self.top, style="TFrame")

        ttk.Label(editor, text=i18n.tr("lbl.product")).grid(row=0, column=0, sticky=tk.W, padx=2)
        self.products = []
        self.variants_by_product: dict[int, list[tuple[str, str]]] = {}
        for p in repository.list_products():
            p = dict(p)
            p["_variants"] = [
                (v["color"], v["size"]) for v in repository.list_variants(p["id"])
            ]
            self.variants_by_product[p["id"]] = p["_variants"]
            self.products.append(p)
        self.product_box = ttk.Combobox(
            editor,
            values=[f"{p['code']} - {p['name']}" for p in self.products],
            width=30,
            state="readonly" if self.products else "disabled",
        )
        self.product_box.grid(row=0, column=1, padx=2)
        self.product_box.bind("<<ComboboxSelected>>", self._on_product_changed)

        ttk.Label(editor, text=i18n.tr("lbl.color")).grid(row=0, column=2, sticky=tk.W, padx=2)
        self.color_var = tk.StringVar()
        self.color_box = ttk.Combobox(
            editor, textvariable=self.color_var, width=12, state="readonly"
        )
        self.color_box.grid(row=0, column=3, padx=2)
        self.color_box.bind("<<ComboboxSelected>>", self._on_color_changed)

        ttk.Label(editor, text=i18n.tr("lbl.size")).grid(row=0, column=4, sticky=tk.W, padx=2)
        self.size_var = tk.StringVar()
        self.size_box = ttk.Combobox(
            editor, textvariable=self.size_var, width=8, state="readonly"
        )
        self.size_box.grid(row=0, column=5, padx=2)

        ttk.Label(editor, text=i18n.tr("lbl.qty")).grid(row=0, column=6, sticky=tk.W, padx=2)
        self.qty_var = tk.StringVar(value="1")
        self.qty_entry = ttk.Entry(editor, textvariable=self.qty_var, width=5)
        self.qty_entry.grid(row=0, column=7, padx=2)

        ttk.Label(editor, text=i18n.tr("lbl.price")).grid(row=0, column=8, sticky=tk.W, padx=2)
        self.price_var = tk.StringVar(value="0")
        self.price_entry = ttk.Entry(editor, textvariable=self.price_var, width=7)
        self.price_entry.grid(row=0, column=9, padx=2)

        ttk.Button(editor, text=i18n.tr("btn.add_line"), style="Primary.TButton",
                   command=self.add_line).grid(row=0, column=10, padx=4)
        ttk.Button(editor, text=i18n.tr("btn.remove"),
                   command=self.remove_line).grid(row=0, column=11, padx=2)

        # ---- Footer (sticky bottom area) --------------------------------
        # Structure inside the footer (top to bottom):
        #   1. separator + "Add line" editor row   <- pinned just above buttons
        #   2. actions row: total | Save / Close    <- the very bottom
        footer.configure(style="TFrame", padding=(20, 10, 20, 12))

        ttk.Separator(footer, orient="horizontal").pack(fill=tk.X, pady=(0, 8))
        editor.pack(fill=tk.X, pady=(0, 10))

        actions = ttk.Frame(footer, style="TFrame")
        actions.pack(fill=tk.X)
        self.total_label = ttk.Label(
            actions, text=i18n.tr("total.label", total="0.00"),
            font=("Segoe UI", 12, "bold"), foreground=COLORS["primary"]
        )
        self.total_label.pack(side=tk.LEFT)

        ttk.Button(actions, text=i18n.tr("btn.close"),
                   command=self.top.destroy).pack(side=tk.RIGHT)
        if self.is_readonly:
            self._load_existing()
            self._set_readonly()
        else:
            self.save_btn = ttk.Button(
                actions, text=i18n.tr("btn.save_order"),
                style="Primary.TButton", command=self.save
            )
            self.save_btn.pack(side=tk.RIGHT, padx=4)

        self.pending_items: list[dict] = []

        # Fit the window to its real content height so buttons are never cut
        # off. The width is bumped to accommodate the wide line-editor row
        # (7 fields + 2 buttons), which no longer overlaps the items table.
        fit_window_to_content(
            self.top, min_width=980, min_height=580, max_width=1280, max_height=940
        )

    def _load_existing(self) -> None:
        order = repository.get_order(self.order_id)
        if order is None:
            return
        self.customer_var.set(order["customer_name"])
        self.date_var.set(order["order_date"])
        status_text = i18n.tr("status.label", status=order["status"].upper())
        if order["shipped_date"]:
            status_text += i18n.tr("status.shipped_on", date=order["shipped_date"])
        self.status_label.configure(text=status_text)
        for iid in self.items_tree.get_children(""):
            self.items_tree.delete(iid)
        for item in repository.list_order_items(self.order_id):
            image = load_image(resolve_stored_image(item.get("image_path")), (44, 44))
            insert_image_row(
                self.items_tree,
                image,
                values=(
                    item["product_code"],
                    item["product_name"],
                    item["color"],
                    item.get("size", ""),
                    item["quantity"],
                    f"{item['unit_price']:.2f}",
                    f"{item['quantity'] * item['unit_price']:.2f}",
                ),
                iid=str(item["id"]),
            )

    def _set_readonly(self) -> None:
        for widget in (
            self.customer_entry,
            self.date_entry,
            self.product_box,
            self.color_box,
            self.size_box,
            self.qty_entry,
            self.price_entry,
        ):
            widget.configure(state="disabled")

    _EMPTY = "—"

    def _display(self, value: str) -> str:
        return self._EMPTY if value == "" else value

    def _raw(self, display_value: str) -> str:
        return "" if display_value == self._EMPTY else display_value

    def _selected_product(self):
        idx = self.product_box.current()
        if idx < 0:
            return None
        return self.products[idx]

    def _on_product_changed(self, _event: tk.Event) -> None:
        """Rebuild the color list and auto-fill base price for the newly selected product."""

        product = self._selected_product()
        colors: list[str] = []
        if product:
            seen = set()
            for color, _size in self.variants_by_product.get(product["id"], []):
                if color not in seen:
                    seen.add(color)
                    colors.append(color)
            self.price_var.set(f"{product['base_price']:.2f}")
        self.color_box.configure(values=[self._display(c) for c in colors] or [self._EMPTY])
        self.color_var.set(colors[0] if colors else "")
        self._on_color_changed()

    def _on_color_changed(self, _event: tk.Event | None = None) -> None:
        """Filter the size list by the currently selected color."""

        product = self._selected_product()
        color = self.color_var.get()
        sizes: list[str] = []
        if product:
            seen = set()
            for c, size in self.variants_by_product.get(product["id"], []):
                if c == color and size not in seen:
                    seen.add(size)
                    sizes.append(size)
        self.size_box.configure(values=[self._display(s) for s in sizes] or [self._EMPTY])
        self.size_var.set(sizes[0] if sizes else "")

    def add_line(self) -> None:
        if self.is_readonly:
            return
        if not self.products:
            show_error(i18n.tr("err.no_products_title"),
                       i18n.tr("err.no_products_msg"), parent=self.top)
            return
        product = self._selected_product()
        if product is None:
            show_error(i18n.tr("err.pick_product_title"),
                       i18n.tr("err.pick_product_msg"), parent=self.top)
            return
        try:
            qty = int(self.qty_var.get())
        except ValueError:
            show_error(i18n.tr("err.bad_qty_title"),
                       i18n.tr("err.bad_qty_msg"), parent=self.top)
            return
        try:
            price = float(self.price_var.get())
        except ValueError:
            show_error(i18n.tr("err.bad_price_title"),
                       i18n.tr("err.bad_price_msg"), parent=self.top)
            return

        color = self.color_var.get().strip()
        size = self.size_var.get().strip()
        subtotal = qty * price
        image = load_image(resolve_stored_image(product.get("image_path")), (44, 44))
        insert_image_row(
            self.items_tree,
            image,
            values=(
                product["code"],
                product["name"],
                color,
                size,
                qty,
                f"{price:.2f}",
                f"{subtotal:.2f}",
            ),
            iid=f"pending_{len(self.pending_items)}",
        )
        self.pending_items.append(
            {
                "product_id": product["id"],
                "color": color,
                "size": size,
                "quantity": qty,
                "unit_price": price,
            }
        )
        self._recalc_total()
        self.qty_var.set("1")

    def remove_line(self) -> None:
        if self.is_readonly:
            return
        sel = self.items_tree.selection()
        if not sel:
            return
        idx = self.items_tree.index(sel[0])
        self.items_tree.delete(sel[0])
        if 0 <= idx < len(self.pending_items):
            self.pending_items.pop(idx)
        self._recalc_total()

    def _recalc_total(self) -> None:
        total = sum(i["quantity"] * i["unit_price"] for i in self.pending_items)
        self.total_label.configure(text=i18n.tr("total.label", total=f"{total:.2f}"))

    def save(self) -> None:
        customer = self.customer_var.get().strip()
        if not customer:
            show_error(i18n.tr("err.missing_customer_title"),
                       i18n.tr("err.missing_customer_msg"), parent=self.top)
            return
        if not self.pending_items:
            show_error(i18n.tr("err.no_items_title"),
                       i18n.tr("err.no_items_msg"), parent=self.top)
            return
        order_date = self.date_var.get().strip() or date.today().isoformat()
        self.result = repository.create_order(customer, order_date, self.pending_items)
        show_info(
            i18n.tr("info.saved_title"),
            i18n.tr("info.saved_msg", order_id=self.result),
            parent=self.top,
        )
        self.top.destroy()
