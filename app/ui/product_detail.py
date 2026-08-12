"""Product detail window: header, current stock, and Stock-In/Out/History tabs.

The window is a non-modal Toplevel so the user can keep several product windows
open at once. The parent inventory list refreshes when this window closes.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
from datetime import date

from app import i18n, repository
from app.paths import resolve_stored_image
from app.ui.theme import COLORS
from app.ui.widgets import ImageThumbnail, fit_window_to_content, make_treeview, show_error


class StockForm(ttk.Frame):
    """A small form used for both stock-in and stock-out entry."""

    def __init__(
        self,
        parent: tk.Misc,
        product_id: int,
        mode: str,
        on_saved=None,
        default_cost: float = 0.0,
    ) -> None:
        super().__init__(parent, style="Card.TFrame", padding=14)
        self.product_id = product_id
        self.mode = mode  # "in" or "out"
        self.on_saved = on_saved

        variants = repository.list_variants(product_id)
        color_values = sorted({v["color"] for v in variants}) or [""]
        size_values = sorted({v["size"] for v in variants}) or [""]

        ttk.Label(self, text=i18n.tr("lbl.color")).grid(row=0, column=0, sticky=tk.W, padx=4, pady=6)
        self.color_var = tk.StringVar()
        self.color_box = ttk.Combobox(
            self, textvariable=self.color_var, values=color_values, width=18
        )
        self.color_box.grid(row=0, column=1, sticky=tk.W, padx=4)

        ttk.Label(self, text=i18n.tr("lbl.size")).grid(row=0, column=2, sticky=tk.W, padx=4, pady=6)
        self.size_var = tk.StringVar()
        self.size_box = ttk.Combobox(
            self, textvariable=self.size_var, values=size_values, width=12
        )
        self.size_box.grid(row=0, column=3, sticky=tk.W, padx=4)

        ttk.Label(self, text=i18n.tr("lbl.quantity")).grid(row=1, column=0, sticky=tk.W, padx=4, pady=6)
        self.qty_var = tk.StringVar(value="1")
        ttk.Entry(self, textvariable=self.qty_var, width=10).grid(
            row=1, column=1, sticky=tk.W, padx=4
        )

        if mode == "in":
            ttk.Label(self, text=i18n.tr("lbl.unit_cost")).grid(row=1, column=2, sticky=tk.W, padx=4)
            # Pre-fill the unit cost with the product's base price — the user
            # can still overwrite it for this particular shipment.
            self.cost_var = tk.StringVar(value=f"{default_cost:.2f}")
            ttk.Entry(self, textvariable=self.cost_var, width=10).grid(
                row=1, column=3, sticky=tk.W, padx=4
            )
        else:
            ttk.Label(self, text=i18n.tr("lbl.customer")).grid(row=1, column=2, sticky=tk.W, padx=4)
            self.customer_var = tk.StringVar()
            ttk.Entry(self, textvariable=self.customer_var, width=18).grid(
                row=1, column=3, sticky=tk.W, padx=4
            )

        ttk.Label(self, text=i18n.tr("lbl.date")).grid(row=2, column=0, sticky=tk.W, padx=4, pady=6)
        self.date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(self, textvariable=self.date_var, width=12).grid(
            row=2, column=1, sticky=tk.W, padx=4
        )

        ttk.Label(self, text=i18n.tr("lbl.note")).grid(row=3, column=0, sticky=tk.W, padx=4, pady=6)
        self.note_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.note_var, width=40).grid(
            row=3, column=1, columnspan=3, sticky=tk.W + tk.E, padx=4
        )

        ttk.Button(
            self,
            text=i18n.tr("btn.add") if mode == "in" else i18n.tr("btn.remove_stock"),
            style="Primary.TButton" if mode == "in" else "Success.TButton",
            command=self.submit,
        ).grid(row=4, column=3, sticky=tk.E, pady=(10, 0), padx=4)

    def submit(self) -> None:
        try:
            qty = int(self.qty_var.get())
        except ValueError:
            show_error(i18n.tr("err.invalid_qty_title"),
                       i18n.tr("err.invalid_qty_int_msg"), parent=self)
            return
        if qty <= 0:
            show_error(i18n.tr("err.invalid_qty_title"),
                       i18n.tr("err.invalid_qty_pos_msg"), parent=self)
            return

        color = self.color_var.get().strip()
        size = self.size_var.get().strip()
        move_date = self.date_var.get().strip() or date.today().isoformat()
        note = self.note_var.get().strip()

        if self.mode == "in":
            try:
                cost = float(self.cost_var.get() or 0)
            except ValueError:
                show_error(i18n.tr("err.invalid_cost_title"),
                           i18n.tr("err.invalid_cost_msg"), parent=self)
                return
            repository.add_stock_in(
                self.product_id, color, size, qty, cost, move_date, note
            )
        else:
            repository.add_stock_out(
                self.product_id,
                color,
                size,
                qty,
                move_date,
                self.customer_var.get().strip(),
                note,
            )

        # Reset the quantity so several movements can be added in a row.
        self.qty_var.set("1")
        self.note_var.set("")
        if self.on_saved:
            self.on_saved()


class ProductDetailWindow:
    """Top-level window showing a single product with movement management."""

    def __init__(self, parent: tk.Misc, product_id: int) -> None:
        self.product_id = product_id
        self.top = tk.Toplevel(parent)
        self.top.title(i18n.tr("detail.title"))
        self.top.configure(background=COLORS["bg"])
        self.top.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_header()

        self.notebook = ttk.Notebook(self.top)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))

        self._build_stock_in_tab()
        self._build_stock_out_tab()
        self._build_history_tab()

        self._refresh_all()

        # Fit the window to its real content height so buttons are never cut
        # off (matters under non-default fonts, DPI scaling and translations).
        fit_window_to_content(
            self.top, min_width=860, min_height=600, max_width=1200, max_height=920
        )

    def _build_header(self) -> None:
        product = repository.get_product(self.product_id)
        if product is None:
            self.top.destroy()
            return

        header = ttk.Frame(self.top, style="Card.TFrame")
        header.pack(fill=tk.X, padx=18, pady=18)

        # Left: fixed-size image (capped so a large photo never hides info).
        thumb_holder = ttk.Frame(header, style="Card.TFrame")
        thumb_holder.pack(side=tk.LEFT, padx=16, pady=16)
        thumb_holder.configure(width=128, height=128)
        thumb_holder.pack_propagate(False)
        self.thumbnail = ImageThumbnail(thumb_holder, size=120)
        self.thumbnail.set_path(resolve_stored_image(product["image_path"]))
        self.thumbnail.pack(anchor=tk.CENTER)

        # Right: product info + stock metric
        info = ttk.Frame(header, style="Card.TFrame")
        info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 16), pady=16)

        ttk.Label(
            info,
            text=product["name"],
            style="Card.TLabel",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            info,
            text=i18n.tr("detail.code", code=product["code"]),
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))
        ttk.Label(
            info,
            text=i18n.tr("detail.base_price", price=f"{product['base_price']:.2f}"),
            style="Card.TLabel",
        ).pack(anchor=tk.W, pady=(8, 0))

        # Current stock metric
        metric = ttk.Frame(info, style="Card.TFrame")
        metric.pack(anchor=tk.W, pady=(14, 0))
        self.stock_label = ttk.Label(
            metric,
            text="0",
            style="Card.TLabel",
            font=("Segoe UI", 28, "bold"),
            foreground=COLORS["primary"],
        )
        self.stock_label.pack(side=tk.LEFT)
        ttk.Label(
            metric,
            text=i18n.tr("detail.units_in_stock"),
            style="Subtitle.TLabel",
        ).pack(side=tk.LEFT, padx=(10, 0))

    def _build_stock_in_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=i18n.tr("tab.stock_in"))
        # Pre-fill unit cost with the product's base price.
        product = repository.get_product(self.product_id) or {}
        base_price = float(product.get("base_price") or 0.0)
        self.stock_in_form = StockForm(
            tab, self.product_id, "in",
            on_saved=self._refresh_all,
            default_cost=base_price,
        )
        self.stock_in_form.pack(fill=tk.X, padx=12, pady=12)

        # Current stock table: one row per (color, size) variant, showing the
        # live derived quantity rather than a raw log of incoming movements.
        tree_label = ttk.Frame(tab)
        tree_label.pack(fill=tk.X, padx=12)
        ttk.Label(tree_label, text=i18n.tr("sect.current_stock"),
                  style="Section.TLabel").pack(anchor=tk.W)

        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))
        self.stock_in_tree = make_treeview(
            tree_frame,
            [
                ("color", i18n.tr("col.color"), 140),
                ("size", i18n.tr("col.size"), 120),
                ("stock", i18n.tr("col.stock"), 120),
            ],
        )

    def _build_stock_out_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=i18n.tr("tab.stock_out"))
        self.stock_out_form = StockForm(tab, self.product_id, "out", on_saved=self._refresh_all)
        self.stock_out_form.pack(fill=tk.X, padx=12, pady=12)

        tree_label = ttk.Frame(tab)
        tree_label.pack(fill=tk.X, padx=12)
        ttk.Label(tree_label, text=i18n.tr("sect.recent_stock_out"),
                  style="Section.TLabel").pack(anchor=tk.W)

        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))
        self.stock_out_tree = make_treeview(
            tree_frame,
            [
                ("date", i18n.tr("col.date"), 120),
                ("color", i18n.tr("col.color"), 110),
                ("size", i18n.tr("col.size"), 90),
                ("quantity", i18n.tr("col.qty"), 70),
                ("customer", i18n.tr("col.customer"), 180),
                ("note", i18n.tr("col.note"), 200),
            ],
        )

    def _build_history_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=i18n.tr("tab.history"))
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.history_tree = make_treeview(
            tree_frame,
            [
                ("type", i18n.tr("col.type"), 90),
                ("date", i18n.tr("col.date"), 120),
                ("color", i18n.tr("col.color"), 110),
                ("size", i18n.tr("col.size"), 90),
                ("quantity", i18n.tr("col.qty"), 70),
                ("info", i18n.tr("col.info"), 280),
            ],
        )

    def _refresh_all(self) -> None:
        # Stock total
        total = repository.product_stock_total(self.product_id)
        self.stock_label.configure(text=str(total))

        # Current stock per variant (color/size → live stock) in the Stock-In tab.
        for iid in self.stock_in_tree.get_children(""):
            self.stock_in_tree.delete(iid)
        for variant in repository.list_variants(self.product_id):
            self.stock_in_tree.insert(
                "",
                tk.END,
                values=(variant["color"], variant["size"], variant["stock"]),
            )

        # Stock-out table (recent movements log)
        for iid in self.stock_out_tree.get_children(""):
            self.stock_out_tree.delete(iid)
        columns = ("date", "color", "size", "quantity", "customer", "note")
        for row in repository.list_stock_out(self.product_id):
            values = []
            for col in columns:
                if col == "customer":
                    values.append(row.get("customer_name", ""))
                else:
                    values.append(row.get(col, ""))
            self.stock_out_tree.insert("", tk.END, values=values)

        # History = combined movements, newest first
        for iid in self.history_tree.get_children(""):
            self.history_tree.delete(iid)
        history = []
        for row in repository.list_stock_in(self.product_id):
            history.append(("IN", row["date"], row["color"], row["size"],
                            row["quantity"], f"cost {row['unit_cost']:.2f}  {row['note']}"))
        for row in repository.list_stock_out(self.product_id):
            history.append(("OUT", row["date"], row["color"], row["size"],
                            row["quantity"], f"{row['customer_name']}  {row['note']}"))
        history.sort(key=lambda x: (x[1], x[0]), reverse=True)
        for item in history:
            self.history_tree.insert("", tk.END, values=item)

    def _on_close(self) -> None:
        self.top.destroy()
