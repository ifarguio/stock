"""Modern flat theme for the Tkinter UI.

Built on top of the *clam* theme, the most customisable of ttk's built-in
themes. Defines a single colour palette and styles every widget used in the
application (buttons, treeviews, notebook, entries, cards, ...) so the whole
app looks consistent.

Apply once at startup via :func:`apply_theme`.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk

#: Central colour palette. UI code can import this directly.
COLORS = {
    "bg": "#f4f6fa",            # app background (soft, easy on the eyes)
    "surface": "#ffffff",       # cards / tables
    "surface_alt": "#f0f3f9",   # table header, hover
    "primary": "#5b6cf2",       # accent / primary actions
    "primary_hover": "#4754d6",
    "primary_soft": "#e9ecff",  # selected row, soft highlight
    "text": "#1f2937",
    "muted": "#6b7280",
    "border": "#e6eaf2",
    "border_dark": "#c8d0de",
    "row_selected": "#e9ecff",
    "row_hover": "#f5f7fc",     # subtle hover stripe for tables
    "success": "#16a37b",       # shipped
    "warning": "#e08a00",       # pending
    "danger": "#e25b5b",        # delete / destructive
    "appbar": "#3d4eb3",        # slightly deeper appbar for depth
}

# Default font family used across the UI. Segoe UI is present on every Windows
# install; falls back gracefully on other platforms.
FONT_FAMILY = "Segoe UI"


def apply_theme(root: tk.Misc) -> ttk.Style:
    """Configure ``root`` with the modern theme. Returns the ttk Style."""

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass  # fall back to the platform default if clam is unavailable

    root.configure(background=COLORS["bg"])
    _configure_styles(style)
    return style


def _configure_styles(style: ttk.Style) -> None:
    c = COLORS
    f = FONT_FAMILY

    # ---- Base -----------------------------------------------------------
    style.configure(".", background=c["bg"], foreground=c["text"],
                    fieldbackground=c["surface"], font=(f, 10),
                    bordercolor=c["border"])
    style.configure("TFrame", background=c["bg"])
    style.configure("Card.TFrame", background=c["surface"])
    style.configure("Toolbar.TFrame", background=c["bg"])

    # ---- Labels ---------------------------------------------------------
    style.configure("TLabel", background=c["bg"], foreground=c["text"])
    style.configure("Card.TLabel", background=c["surface"], foreground=c["text"])
    style.configure("Title.TLabel", font=(f, 16, "bold"), foreground=c["text"])
    style.configure("Section.TLabel", font=(f, 11, "bold"), foreground=c["text"])
    style.configure("Subtitle.TLabel", font=(f, 10), foreground=c["muted"])
    style.configure("Muted.TLabel", foreground=c["muted"])
    style.configure("Metric.TLabel", font=(f, 26, "bold"), foreground=c["primary"])
    style.configure("Success.TLabel", foreground=c["success"])
    style.configure("Danger.TLabel", foreground=c["danger"])

    # ---- Buttons --------------------------------------------------------
    # Default outline button
    style.configure("TButton", padding=(14, 8), font=(f, 10),
                    background=c["surface"], foreground=c["text"],
                    borderwidth=0, relief="flat", focusthickness=0,
                    highlightthickness=0)
    style.map("TButton",
              background=[("active", c["surface_alt"]), ("disabled", c["surface_alt"])],
              foreground=[("disabled", c["muted"])])

    # Primary filled button
    style.configure("Primary.TButton", padding=(18, 9), font=(f, 10, "bold"),
                    background=c["primary"], foreground="#ffffff",
                    borderwidth=0, relief="flat", focusthickness=0)
    style.map("Primary.TButton",
              background=[("active", c["primary_hover"]), ("disabled", "#c7d0e9")],
              foreground=[("disabled", "#ffffff")])

    # Success (ship order, stock-in)
    style.configure("Success.TButton", padding=(18, 9), font=(f, 10, "bold"),
                    background=c["success"], foreground="#ffffff",
                    borderwidth=0, relief="flat", focusthickness=0)
    style.map("Success.TButton",
              background=[("active", "#059669")],
              foreground=[("disabled", "#ffffff")])

    # Danger (delete)
    style.configure("Danger.TButton", padding=(14, 8), font=(f, 10),
                    background=c["danger"], foreground="#ffffff",
                    borderwidth=0, relief="flat", focusthickness=0)
    style.map("Danger.TButton",
              background=[("active", "#dc2626")],
              foreground=[("disabled", "#ffffff")])

    # ---- Inputs ---------------------------------------------------------
    style.configure("TEntry", fieldbackground=c["surface"], foreground=c["text"],
                    bordercolor=c["border_dark"], lightcolor=c["border_dark"],
                    darkcolor=c["border_dark"], padding=8,
                    borderwidth=1, relief="solid")
    style.map("TEntry",
              bordercolor=[("focus", c["primary"])],
              lightcolor=[("focus", c["primary"])],
              darkcolor=[("focus", c["primary"])])

    style.configure("TCombobox", fieldbackground=c["surface"], foreground=c["text"],
                    background=c["surface"], padding=7,
                    borderwidth=1, relief="solid",
                    arrowcolor=c["muted"])
    style.map("TCombobox",
              fieldbackground=[("readonly", c["surface"])],
              bordercolor=[("focus", c["primary"])])

    # ---- Treeview (compact, default for data tables) --------------------
    style.configure("Treeview", background=c["surface"], foreground=c["text"],
                    fieldbackground=c["surface"], rowheight=28, borderwidth=0,
                    font=(f, 10))
    style.configure("Treeview.Heading", font=(f, 10, "bold"),
                    background=c["surface_alt"], foreground=c["muted"],
                    borderwidth=0, padding=(10, 10), relief="flat")
    style.map("Treeview",
              background=[("selected", c["row_selected"])],
              foreground=[("selected", c["text"])])
    style.map("Treeview.Heading", background=[("active", c["surface_alt"])])

    # Treeview with leading image column: taller rows + zero indent so the
    # thumbnail sits flush at the left edge of the cell.
    style.configure("Img.Treeview", rowheight=60, indent=0)
    style.configure("Img.Treeview.Heading", font=(f, 10, "bold"),
                    background=c["surface_alt"], foreground=c["muted"],
                    borderwidth=0, padding=(10, 10), relief="flat")

    # ---- Notebook (flat tabs) -------------------------------------------
    style.configure("TNotebook", background=c["bg"], borderwidth=0,
                    tabmargins=(16, 10, 16, 0))
    style.configure("TNotebook.Tab", padding=(24, 12), font=(f, 11, "bold"),
                    background=c["bg"], foreground=c["muted"], borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", c["surface"])],
              foreground=[("selected", c["primary"])])

    # ---- Labeled frame (card with title) --------------------------------
    style.configure("Card.TLabelframe", background=c["surface"],
                    bordercolor=c["border"], relief="solid", borderwidth=1)
    style.configure("Card.TLabelframe.Label", background=c["surface"],
                    foreground=c["text"], font=(f, 10, "bold"))

    # ---- Scrollbar ------------------------------------------------------
    style.configure("TScrollbar", background=c["surface"], borderwidth=0,
                    troughcolor=c["surface_alt"], arrowcolor=c["muted"],
                    relief="flat")
    style.map("TScrollbar", background=[("active", c["border_dark"])])

    # ---- Separator ------------------------------------------------------
    style.configure("TSeparator", background=c["border"])
