"""Orders tab: list of orders with New / View / Ship / Delete actions.

A search box plus status / date-range filters narrow the order list.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
from datetime import date

from app import i18n, repository
from app.ui.order_dialog import OrderDialog
from app.ui.theme import COLORS
from app.ui.widgets import (
    FilterDropdown,
    SearchBar,
    confirm,
    make_treeview,
    show_error,
    show_info,
)

try:
    from dateutil.relativedelta import relativedelta  # type: ignore
    HAS_DATEUTIL = True
except Exception:
    HAS_DATEUTIL = False


def _status_option_pairs() -> list[tuple[str, str]]:
    return [
        ("", i18n.tr("filter.all")),
        ("new", i18n.tr("filter.status_new")),
        ("shipped", i18n.tr("filter.status_shipped")),
    ]


def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)


def _first_day_of_quarter(d: date) -> date:
    return d.replace(month=((d.month - 1) // 3) * 3 + 1, day=1)


def _add_months(d: date, months: int) -> date:
    if HAS_DATEUTIL:
        return d + relativedelta(months=months)
    # Naive fallback: approximate by 30-day months. Good enough for a default
    # range that the user can override in the date entries.
    return date.fromordinal(d.toordinal() + months * 30)


class OrdersView(ttk.Frame):
    def __init__(self, parent: tk.Misc, app: tk.Misc) -> None:
        super().__init__(parent, style="TFrame")
        self.app = app
        self._build_layout()

    def _build_layout(self) -> None:
        header = ttk.Frame(self, style="TFrame")
        header.pack(fill=tk.X, pady=(4, 10))
        ttk.Label(header, text=i18n.tr("ord.title"), style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            header,
            text=i18n.tr("ord.subtitle"),
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))

        # Toolbar
        toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        toolbar.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(toolbar, text=i18n.tr("btn.new_order"), style="Primary.TButton",
                   command=self.new_order).pack(side=tk.LEFT)
        ttk.Button(toolbar, text=i18n.tr("btn.view"), command=self.view_order).pack(side=tk.LEFT, padx=8)
        ttk.Button(toolbar, text=i18n.tr("btn.mark_shipped"), style="Success.TButton",
                   command=self.ship_order).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text=i18n.tr("btn.mark_new"),
                   command=self.unship_order).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text=i18n.tr("btn.delete"), style="Danger.TButton",
                   command=self.delete_order).pack(side=tk.LEFT)
        ttk.Button(toolbar, text=i18n.tr("btn.refresh"), command=self.load).pack(side=tk.RIGHT)

        # Filter bar: search + status + date range + clear
        filter_bar = ttk.Frame(self, style="Card.TFrame", padding=(12, 10))
        filter_bar.pack(fill=tk.X, pady=(0, 10))

        self.search = SearchBar(
            filter_bar,
            i18n.tr("ord.search_placeholder"),
            on_change=self._apply_filters,
        )
        self.search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 16))

        self.status_filter = FilterDropdown(
            filter_bar,
            i18n.tr("ord.filter_status"),
            _status_option_pairs(),
            on_change=self._apply_filters,
            width=12,
        )
        self.status_filter.pack(side=tk.LEFT, padx=8)

        # Date range entries
        range_frame = ttk.Frame(filter_bar, style="Card.TFrame")
        range_frame.pack(side=tk.LEFT, padx=8)
        ttk.Label(range_frame, text=i18n.tr("ord.filter_from"),
                  style="Subtitle.TLabel").pack(anchor=tk.W)
        today = date.today()
        self.from_var = tk.StringVar(
            value=_first_day_of_quarter(today).isoformat()
        )
        ttk.Entry(range_frame, textvariable=self.from_var, width=12).pack()

        ttk.Label(range_frame, text=i18n.tr("ord.filter_to"),
                  style="Subtitle.TLabel").pack(anchor=tk.W, pady=(6, 0))
        self.to_var = tk.StringVar(value=today.isoformat())
        ttk.Entry(range_frame, textvariable=self.to_var, width=12).pack()

        ttk.Button(filter_bar, text=i18n.tr("ord.clear_filters"),
                   command=self._clear_filters).pack(side=tk.LEFT, padx=8)
        ttk.Button(filter_bar, text=i18n.tr("btn.apply"),
                   style="Primary.TButton",
                   command=self._apply_filters).pack(side=tk.LEFT, padx=4)

        # Table card
        table_card = ttk.Frame(self, style="Card.TFrame")
        table_card.pack(fill=tk.BOTH, expand=True)
        tree_frame = ttk.Frame(table_card)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        self.tree = make_treeview(
            tree_frame,
            [
                ("id", i18n.tr("col.order_no"), 90),
                ("customer", i18n.tr("col.customer"), 200),
                ("date", i18n.tr("col.order_date"), 130),
                ("status", i18n.tr("col.status"), 120),
                ("shipped", i18n.tr("col.shipped_date"), 130),
                ("total", i18n.tr("col.total"), 110),
            ],
        )
        self.tree.bind("<Double-1>", lambda _e: self.view_order())

        self.tree.tag_configure("shipped", foreground=COLORS["success"])
        self.tree.tag_configure("new", foreground=COLORS["warning"])

    # ---- Filtering ------------------------------------------------------
    def _apply_filters(self) -> None:
        rows = repository.list_orders(
            search=self.search.get() or None,
            status=self.status_filter.get() or None,
            date_from=self.from_var.get().strip() or None,
            date_to=self.to_var.get().strip() or None,
        )
        self._render_rows(rows)

    def _clear_filters(self) -> None:
        self.search.clear()
        self.status_filter.box.current(0)
        today = date.today()
        self.from_var.set(_first_day_of_quarter(today).isoformat())
        self.to_var.set(today.isoformat())
        self._apply_filters()

    # ---- Rendering ------------------------------------------------------
    def _render_rows(self, rows) -> None:
        for iid in self.tree.get_children(""):
            self.tree.delete(iid)
        for row in rows:
            self.tree.insert(
                "",
                tk.END,
                iid=str(row["id"]),
                values=(
                    row["id"],
                    row["customer_name"],
                    row["order_date"],
                    row["status"].capitalize(),
                    row["shipped_date"] or "-",
                    f"{row['total']:.2f}",
                ),
                tags=(row["status"],),
            )

    def load(self) -> None:
        self._apply_filters()

    def _selected_order_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            show_error(i18n.tr("err.no_selection"), i18n.tr("err.select_order"), parent=self)
            return None
        return int(sel[0])

    def new_order(self) -> None:
        dialog = OrderDialog(self)
        self.wait_window(dialog.top)
        if dialog.result is not None:
            self.load()

    def view_order(self) -> None:
        order_id = self._selected_order_id()
        if order_id is None:
            return
        dialog = OrderDialog(self, order_id=order_id)
        self.wait_window(dialog.top)
        self.load()

    def ship_order(self) -> None:
        order_id = self._selected_order_id()
        if order_id is None:
            return
        order = repository.get_order(order_id)
        if order is None:
            return
        if order["status"] == "shipped":
            show_info(i18n.tr("info.already_shipped_title"),
                      i18n.tr("info.already_shipped_msg"), parent=self)
            return
        if not confirm(
            i18n.tr("confirm.ship_title"),
            i18n.tr("confirm.ship_msg", order_id=order_id),
            parent=self,
        ):
            return
        try:
            repository.ship_order(order_id)
        except Exception as exc:
            show_error(i18n.tr("err.cannot_ship"), str(exc), parent=self)
            return
        self.load()
        self.app.refresh_all()

    def unship_order(self) -> None:
        order_id = self._selected_order_id()
        if order_id is None:
            return
        order = repository.get_order(order_id)
        if order is None:
            return
        if order["status"] != "shipped":
            show_info(i18n.tr("info.not_shipped_title"),
                      i18n.tr("info.not_shipped_msg"), parent=self)
            return
        if not confirm(
            i18n.tr("confirm.unship_title"),
            i18n.tr("confirm.unship_msg", order_id=order_id),
            parent=self,
        ):
            return
        try:
            repository.unship_order(order_id)
        except Exception as exc:
            show_error(i18n.tr("err.cannot_unship"), str(exc), parent=self)
            return
        self.load()
        self.app.refresh_all()

    def delete_order(self) -> None:
        order_id = self._selected_order_id()
        if order_id is None:
            return
        if not confirm(
            i18n.tr("confirm.delete_order_title"),
            i18n.tr("confirm.delete_order_msg"),
            parent=self,
        ):
            return
        try:
            repository.delete_order(order_id)
        except Exception as exc:
            show_error(i18n.tr("err.cannot_delete"), str(exc), parent=self)
            return
        self.load()
