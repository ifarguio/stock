"""The main application window: a notebook with three tabs."""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk

from app import i18n
from app.ui.inventory_view import InventoryView
from app.ui.orders_view import OrdersView
from app.ui.stats_view import StatsView
from app.ui.theme import COLORS


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(i18n.tr("app.title"))
        self.geometry("1180x740")
        # Keep the window within the screen on smaller displays (e.g. laptops).
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        w = min(1180, screen_w - 40)
        h = min(740, screen_h - 80)
        self.geometry(f"{w}x{h}")
        self.minsize(960, 560)
        self.configure(background=COLORS["bg"])
        self._set_window_icon()

        self._build_appbar()

        # Language switch sits in its own bar above the tabs so it never gets
        # destroyed/recreated when the content below is rebuilt.
        self._lang_bar = ttk.Frame(self, style="TFrame")
        self._lang_bar.pack(fill=tk.X, padx=18, pady=(10, 0))
        self.lang_button = ttk.Button(
            self._lang_bar,
            text=i18n.tr("lang.switch_to"),
            command=self._toggle_language,
        )
        self.lang_button.pack(side=tk.RIGHT)

        # Content container is rebuilt on every language change so widgets pick
        # up the freshly translated strings.
        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True, padx=18, pady=(8, 18))
        self.inventory_view: InventoryView | None = None
        self.orders_view: OrdersView | None = None
        self.stats_view: StatsView | None = None
        self.notebook: ttk.Notebook | None = None
        self._build_content()

        # Rebuild the whole content whenever the language changes.
        i18n.on_change(self._on_language_changed)

    def _build_content(self) -> None:
        self.notebook = ttk.Notebook(self.container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.inventory_view = InventoryView(self.notebook, app=self)
        self.orders_view = OrdersView(self.notebook, app=self)
        self.stats_view = StatsView(self.notebook, app=self)

        self.notebook.add(self.inventory_view, text=i18n.tr("tab.inventory"))
        self.notebook.add(self.orders_view, text=i18n.tr("tab.orders"))
        self.notebook.add(self.stats_view, text=i18n.tr("tab.statistics"))

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.inventory_view.load()

    def _set_window_icon(self) -> None:
        """Set the window/taskbar icon.

        Looks for ``app.ico`` next to the executable (or the source root).
        Falls back silently if the icon is missing — the app still runs.
        """

        import os
        import sys
        from app.paths import PROJECT_ROOT

        candidates = [
            PROJECT_ROOT / "app.ico",
            PROJECT_ROOT / "app.png",
        ]
        # When frozen, the icon may be bundled alongside.
        if getattr(sys, "frozen", False):
            candidates.insert(0, PROJECT_ROOT / "app.ico")

        for path in candidates:
            if path.exists():
                try:
                    if path.suffix.lower() == ".ico":
                        self.iconbitmap(default=str(path))
                    else:
                        # PNG fallback for Tk versions without ico support.
                        from PIL import Image, ImageTk
                        self._icon_photo = ImageTk.PhotoImage(Image.open(str(path)))
                        self.iconphoto(True, self._icon_photo)
                    return
                except Exception:
                    continue

    def _build_appbar(self) -> None:
        self.bar = tk.Frame(self, background=COLORS["appbar"], height=68)
        self.bar.pack(side=tk.TOP, fill=tk.X)
        self.bar.pack_propagate(False)

        # Title + subtitle grouped on the left.
        text_block = tk.Frame(self.bar, background=COLORS["appbar"])
        text_block.pack(side=tk.LEFT, padx=22, pady=10)

        self.appbar_label = tk.Label(
            text_block,
            text=i18n.tr("app.appbar"),
            font=("Segoe UI", 15, "bold"),
            foreground="#ffffff",
            background=COLORS["appbar"],
        )
        self.appbar_label.pack(anchor=tk.W)

        self.appbar_subtitle = tk.Label(
            text_block,
            text=i18n.tr("app.appbar_subtitle"),
            font=("Segoe UI", 9),
            foreground="#c8d0f5",
            background=COLORS["appbar"],
        )
        self.appbar_subtitle.pack(anchor=tk.W)

    def _on_tab_changed(self, _event: tk.Event) -> None:
        for view in (self.inventory_view, self.orders_view, self.stats_view):
            if view and view.winfo_ismapped():
                view.load()
                break

    def refresh_all(self) -> None:
        """Refresh every tab. Used after destructive or wide-ranging actions."""

        if self.inventory_view:
            self.inventory_view.load()
        if self.orders_view:
            self.orders_view.load()
        if self.stats_view:
            self.stats_view.load()

    def _toggle_language(self) -> None:
        i18n.toggle_language()

    def _on_language_changed(self) -> None:
        """Rebuild the window title, appbar label and the whole tab area."""

        self.title(i18n.tr("app.title"))
        self.appbar_label.configure(text=i18n.tr("app.appbar"))
        self.appbar_subtitle.configure(text=i18n.tr("app.appbar_subtitle"))
        # Refresh the language button label to show the new target language.
        self.lang_button.configure(text=i18n.tr("lang.switch_to"))

        # Tear down the existing tabs and rebuild so every label/column header
        # is retranslated.
        if self.notebook is not None:
            self.notebook.destroy()
        for child in self.container.winfo_children():
            child.destroy()
        self._build_content()
