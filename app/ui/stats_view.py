"""Statistics tab: weekly, monthly, quarterly sales summaries + trend chart.

A period picker (This Week / This Month / This Quarter / Custom Range) chooses
the inclusive date range. The summary is computed from shipped orders only.

Includes:
  * A product filter to narrow every metric to one product.
  * Three metric cards: revenue, orders shipped, units sold.
  * A line chart of the selected metric over time, redrawn whenever the
    period or filter changes.
  * A top-products table.
"""

from __future__ import annotations

import calendar
import tkinter as tk
import tkinter.ttk as ttk
from datetime import date, timedelta
from typing import Optional

from app import i18n, repository
from app.ui.theme import COLORS
from app.ui.widgets import LineChart, make_treeview


# Internal period keys (language-independent). Display labels are produced from
# these via i18n so the comparison logic keeps working after a language switch.
_PERIOD_KEYS = ("week", "month", "quarter", "custom")
# Internal metric keys. Maps to a column in the timeseries data.
_METRIC_KEYS = ("revenue", "orders", "units")


def _period_label(key: str) -> str:
    return {
        "week": i18n.tr("period.this_week"),
        "month": i18n.tr("period.this_month"),
        "quarter": i18n.tr("period.this_quarter"),
        "custom": i18n.tr("period.custom"),
    }[key]


def _metric_label(key: str) -> str:
    return {
        "revenue": i18n.tr("metric.revenue"),
        "orders": i18n.tr("metric.orders_shipped"),
        "units": i18n.tr("metric.units_sold"),
    }[key]


def _metric_color(key: str) -> str:
    return {
        "revenue": COLORS["primary"],
        "orders": COLORS["success"],
        "units": COLORS["warning"],
    }[key]


def _quarter_bounds(d: date) -> tuple[date, date]:
    q = (d.month - 1) // 3 + 1
    start_month = 3 * (q - 1) + 1
    first = date(d.year, start_month, 1)
    last = date(d.year, start_month + 2, calendar.monthrange(d.year, start_month + 2)[1])
    return first, last


def _week_bounds(d: date) -> tuple[date, date]:
    # ISO week: Monday is the first day.
    start = d - timedelta(days=d.weekday())
    end = start + timedelta(days=6)
    return start, end


def _month_bounds(d: date) -> tuple[date, date]:
    first = date(d.year, d.month, 1)
    last = date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])
    return first, last


def _choose_bucket(start: date, end: date) -> str:
    """Pick a reasonable chart bucket size for the date span."""

    span_days = (end - start).days
    if span_days <= 21:
        return "day"
    if span_days <= 120:
        return "week"
    return "month"


class StatsView(ttk.Frame):
    def __init__(self, parent: tk.Misc, app: tk.Misc) -> None:
        super().__init__(parent, style="TFrame")
        self.app = app
        # Internal keys — display labels are derived from these so the logic
        # survives a language change.
        self.period_key = "month"
        self.metric_key = "revenue"

        # ---- Page header ------------------------------------------------
        header = ttk.Frame(self, style="TFrame")
        header.pack(fill=tk.X, pady=(4, 10))
        ttk.Label(header, text=i18n.tr("stats.title"), style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(header, text=i18n.tr("stats.subtitle"),
                  style="Subtitle.TLabel").pack(anchor=tk.W, pady=(2, 0))

        # ---- Filter bar -------------------------------------------------
        bar = ttk.Frame(self, style="Toolbar.TFrame")
        bar.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(bar, text=i18n.tr("lbl.period")).pack(side=tk.LEFT, padx=(0, 4))
        self.period_box = ttk.Combobox(
            bar, values=[_period_label(k) for k in _PERIOD_KEYS],
            state="readonly", width=16,
        )
        self.period_box.set(_period_label(self.period_key))
        self.period_box.pack(side=tk.LEFT)
        self.period_box.bind("<<ComboboxSelected>>", self._on_period_change)

        ttk.Label(bar, text=i18n.tr("lbl.from")).pack(side=tk.LEFT, padx=(16, 2))
        self.from_var = tk.StringVar()
        ttk.Entry(bar, textvariable=self.from_var, width=12).pack(side=tk.LEFT)
        ttk.Label(bar, text=i18n.tr("lbl.to")).pack(side=tk.LEFT, padx=(8, 2))
        self.to_var = tk.StringVar()
        ttk.Entry(bar, textvariable=self.to_var, width=12).pack(side=tk.LEFT)

        # Product filter (All / specific product).
        ttk.Label(bar, text=i18n.tr("lbl.product")).pack(side=tk.LEFT, padx=(16, 2))
        self._product_options: list[tuple[Optional[int], str]] = [(None, i18n.tr("filter.all"))]
        for p in repository.list_products():
            self._product_options.append((p["id"], f"{p['code']} - {p['name']}"))
        self.product_box = ttk.Combobox(
            bar, values=[label for _, label in self._product_options],
            state="readonly", width=24,
        )
        self.product_box.current(0)
        self.product_box.pack(side=tk.LEFT)
        self.product_box.bind("<<ComboboxSelected>>", lambda _e: self.load())

        ttk.Button(bar, text=i18n.tr("btn.apply"), style="Primary.TButton",
                   command=self.load).pack(side=tk.LEFT, padx=10)

        # ---- Metric cards ----------------------------------------------
        cards = ttk.Frame(self, style="TFrame")
        cards.pack(fill=tk.X, pady=(0, 12))
        for col in range(3):
            cards.columnconfigure(col, weight=1)
        self.revenue_card = self._card(cards, i18n.tr("metric.revenue"), COLORS["primary"], 0)
        self.orders_card = self._card(cards, i18n.tr("metric.orders_shipped"), COLORS["success"], 1)
        self.units_card = self._card(cards, i18n.tr("metric.units_sold"), COLORS["warning"], 2)

        # ---- Chart section ---------------------------------------------
        chart_card = ttk.Frame(self, style="Card.TFrame", padding=12)
        chart_card.pack(fill=tk.BOTH, expand=False, pady=(0, 12))

        chart_header = ttk.Frame(chart_card, style="Card.TFrame")
        chart_header.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(chart_header, text=i18n.tr("sect.trend"),
                  style="Section.TLabel").pack(side=tk.LEFT)

        # Metric selector for the chart.
        self.metric_box = ttk.Combobox(
            chart_header, values=[_metric_label(k) for k in _METRIC_KEYS],
            state="readonly", width=16,
        )
        self.metric_box.set(_metric_label(self.metric_key))
        self.metric_box.pack(side=tk.RIGHT)
        self.metric_box.bind("<<ComboboxSelected>>", self._on_metric_change)

        self.chart = LineChart(chart_card, height=220)
        self.chart.pack(fill=tk.BOTH, expand=True)

        # ---- Top products table ----------------------------------------
        ttk.Label(self, text=i18n.tr("sect.top_products"),
                  style="Section.TLabel").pack(anchor=tk.W, pady=(0, 6))
        table_card = ttk.Frame(self, style="Card.TFrame")
        table_card.pack(fill=tk.BOTH, expand=True)
        tree_frame = ttk.Frame(table_card)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.tree = make_treeview(
            tree_frame,
            [
                ("code", i18n.tr("col.code"), 130),
                ("name", i18n.tr("col.product"), 260),
                ("units", i18n.tr("col.units"), 110),
                ("revenue", i18n.tr("col.revenue"), 140),
            ],
        )

        self._on_period_change()

    # ---- Layout helpers -----------------------------------------------
    def _card(self, parent: tk.Misc, title: str, accent: str, col: int) -> ttk.Label:
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid(row=0, column=col, sticky="nsew", padx=6)
        frame.configure(height=110)
        frame.pack_propagate(False)

        inner = ttk.Frame(frame, style="Card.TFrame")
        inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        value_label = ttk.Label(inner, text="-",
                                font=("Segoe UI", 26, "bold"), foreground=accent)
        value_label.pack(anchor=tk.W)
        ttk.Label(inner, text=title, style="Subtitle.TLabel").pack(anchor=tk.W, pady=(4, 0))
        return value_label

    # ---- Event handlers -----------------------------------------------
    def _on_period_change(self, _event: object = None) -> None:
        # Translate the selected display label back into an internal key so the
        # period logic is language-independent.
        selected = self.period_box.get()
        for key in _PERIOD_KEYS:
            if _period_label(key) == selected:
                self.period_key = key
                break

        today = date.today()
        if self.period_key == "week":
            start, end = _week_bounds(today)
        elif self.period_key == "month":
            start, end = _month_bounds(today)
        elif self.period_key == "quarter":
            start, end = _quarter_bounds(today)
        else:
            # Default custom range to this month until the user types values.
            start, end = _month_bounds(today)
        self.from_var.set(start.isoformat())
        self.to_var.set(end.isoformat())

    def _on_metric_change(self, _event: object = None) -> None:
        selected = self.metric_box.get()
        for key in _METRIC_KEYS:
            if _metric_label(key) == selected:
                self.metric_key = key
                break
        self.load()

    # ---- Data ---------------------------------------------------------
    def _selected_product_id(self) -> Optional[int]:
        """Resolve the currently selected product filter to a product id.

        We match by the displayed text rather than by ``Combobox.current()``
        because ``current()`` relies on positional indexing and can return
        the wrong value (or -1) after the dropdown is repopulated or the
        window is rebuilt on a language switch.
        """

        selected_text = self.product_box.get()
        for pid, label in self._product_options:
            if label == selected_text:
                return pid
        return None

    def load(self) -> None:
        start = self.from_var.get().strip()
        end = self.to_var.get().strip()
        if not start or not end:
            self._on_period_change()
            start = self.from_var.get().strip()
            end = self.to_var.get().strip()

        product_id = self._selected_product_id()
        summary = repository.sales_summary(start, end, product_id=product_id)

        self.revenue_card.configure(text=f"{summary['revenue']:.2f}")
        self.orders_card.configure(text=str(summary["order_count"]))
        self.units_card.configure(text=str(summary["units"]))

        # Top products (when filtering by a single product, this still works
        # — it will just show that one product).
        for iid in self.tree.get_children(""):
            self.tree.delete(iid)
        for row in summary["top_products"]:
            self.tree.insert(
                "", tk.END,
                values=(row["code"], row["name"], row["units"], f"{row['revenue']:.2f}"),
            )

        # Chart: pull the timeseries and plot the selected metric.
        try:
            start_d = date.fromisoformat(start)
            end_d = date.fromisoformat(end)
        except ValueError:
            return
        bucket = _choose_bucket(start_d, end_d)
        series_data = repository.sales_timeseries(start, end, bucket=bucket, product_id=product_id)
        labels = [item["bucket"] for item in series_data]
        values = [float(item[self.metric_key]) for item in series_data]
        self.chart.set_data(
            labels=labels,
            series={_metric_label(self.metric_key): (values, _metric_color(self.metric_key))},
        )
