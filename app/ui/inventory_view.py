"""Inventory tab: lists products with thumbnails and their current stock.

Double-clicking a product (or the *View Details* button) opens the product
detail window where stock-in and stock-out operations are performed.

A search box plus colour / size / stock filters let the user narrow the list.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk

from app import i18n, repository
from app.paths import resolve_stored_image
from app.ui.product_detail import ProductDetailWindow
from app.ui.product_dialog import ProductDialog
from app.ui.theme import COLORS
from app.ui.widgets import (
    FilterDropdown,
    SearchBar,
    confirm,
    insert_image_row,
    load_image,
    make_treeview,
    show_error,
)


def _filter_option_pairs(values: list[str]) -> list[tuple[str, str]]:
    """Build (raw, display) pairs for a filter dropdown, with an "All" entry first."""

    all_label = i18n.tr("filter.all")
    pairs: list[tuple[str, str]] = [("", all_label)]
    for value in values:
        display = value if value else "-"
        pairs.append((value, display))
    return pairs


def _stock_option_pairs() -> list[tuple[str, str]]:
    return [
        ("", i18n.tr("filter.all")),
        ("in_stock", i18n.tr("filter.in_stock")),
        ("out_of_stock", i18n.tr("filter.out_of_stock")),
    ]


class InventoryView(ttk.Frame):
    def __init__(self, parent: tk.Misc, app: tk.Misc) -> None:
        super().__init__(parent, style="TFrame")

        self.app = app
        self._build_layout()

    def _build_layout(self) -> None:
        header = ttk.Frame(self, style="TFrame")
        header.pack(fill=tk.X, pady=(4, 10))
        ttk.Label(header, text=i18n.tr("inv.title"), style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            header,
            text=i18n.tr("inv.subtitle"),
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))

        # Toolbar
        toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        toolbar.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(toolbar, text=i18n.tr("btn.add_product"), style="Primary.TButton",
                   command=self.add_product).pack(side=tk.LEFT)
        ttk.Button(toolbar, text=i18n.tr("btn.view_details"),
                   command=self.open_details).pack(side=tk.LEFT, padx=8)
        ttk.Button(toolbar, text=i18n.tr("btn.edit"), command=self.edit_product).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text=i18n.tr("btn.delete"), style="Danger.TButton",
                   command=self.delete_product).pack(side=tk.LEFT)
        ttk.Button(toolbar, text=i18n.tr("btn.refresh"), command=self.load).pack(side=tk.RIGHT)

        # Filter bar: search + colour + size + stock dropdowns + clear button
        filter_bar = ttk.Frame(self, style="Card.TFrame", padding=(12, 10))
        filter_bar.pack(fill=tk.X, pady=(0, 10))

        self.search = SearchBar(
            filter_bar,
            i18n.tr("inv.search_placeholder"),
            on_change=self._apply_filters,
        )
        self.search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 16))

        self.color_filter = FilterDropdown(
            filter_bar,
            i18n.tr("inv.filter_color"),
            _filter_option_pairs(repository.list_all_colors()),
            on_change=self._apply_filters,
        )
        self.color_filter.pack(side=tk.LEFT, padx=8)

        self.size_filter = FilterDropdown(
            filter_bar,
            i18n.tr("inv.filter_size"),
            _filter_option_pairs(repository.list_all_sizes()),
            on_change=self._apply_filters,
        )
        self.size_filter.pack(side=tk.LEFT, padx=8)

        self.stock_filter = FilterDropdown(
            filter_bar,
            i18n.tr("inv.filter_stock"),
            _stock_option_pairs(),
            on_change=self._apply_filters,
        )
        self.stock_filter.pack(side=tk.LEFT, padx=8)

        ttk.Button(filter_bar, text=i18n.tr("inv.clear_filters"),
                   command=self._clear_filters).pack(side=tk.LEFT, padx=8)

        # Table card
        table_card = ttk.Frame(self, style="Card.TFrame")
        table_card.pack(fill=tk.BOTH, expand=True)
        tree_frame = ttk.Frame(table_card)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        self.tree = make_treeview(
            tree_frame,
            [
                ("code", i18n.tr("col.code"), 120),
                ("name", i18n.tr("col.name"), 240),
                ("price", i18n.tr("col.price"), 100),
                ("stock", i18n.tr("col.stock"), 100),
            ],
            with_image=True,
            image_size=44,
        )
        self.tree.bind("<Double-1>", lambda _e: self.open_details())

    # ---- Filtering ------------------------------------------------------
    def _refresh_filter_options(self) -> None:
        """Update the dropdown options to match the current data set."""

        self.color_filter.set_values(_filter_option_pairs(repository.list_all_colors()))
        self.size_filter.set_values(_filter_option_pairs(repository.list_all_sizes()))

    def _apply_filters(self) -> None:
        rows = repository.list_products(
            search=self.search.get() or None,
            color=self.color_filter.get() or None,
            size=self.size_filter.get() or None,
            stock_filter=self.stock_filter.get() or None,
        )
        self._render_rows(rows)

    def _clear_filters(self) -> None:
        self.search.clear()
        self.color_filter.box.current(0)
        self.size_filter.box.current(0)
        self.stock_filter.box.current(0)
        self._apply_filters()

    # ---- Rendering ------------------------------------------------------
    def _render_rows(self, rows) -> None:
        for iid in self.tree.get_children(""):
            self.tree.delete(iid)
        for row in rows:
            image = load_image(resolve_stored_image(row["image_path"]), (44, 44))
            insert_image_row(
                self.tree,
                image,
                values=(
                    row["code"],
                    row["name"],
                    f"{row['base_price']:.2f}",
                    row["stock"],
                ),
                iid=str(row["id"]),
            )

    def load(self) -> None:
        self._refresh_filter_options()
        self._apply_filters()

    def _selected_product_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            show_error(i18n.tr("err.no_selection"), i18n.tr("err.select_product"), parent=self)
            return None
        return int(sel[0])

    def add_product(self) -> None:
        dialog = ProductDialog(self)
        self.wait_window(dialog.top)
        if dialog.result is not None:
            self.load()

    def edit_product(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            return
        product = repository.get_product(product_id)
        if product is None:
            return
        dialog = ProductDialog(self, product=product)
        self.wait_window(dialog.top)
        if dialog.result is not None:
            self.load()

    def delete_product(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            return
        if not confirm(
            i18n.tr("confirm.delete_product_title"),
            i18n.tr("confirm.delete_product_msg"),
            parent=self,
        ):
            return
        try:
            repository.delete_product(product_id)
        except Exception as exc:
            show_error(i18n.tr("err.cannot_delete"), str(exc), parent=self)
            return
        self.load()

    def open_details(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            return
        window = ProductDetailWindow(self, product_id)
        self.wait_window(window.top)
        self.load()
