"""Reusable Tkinter widgets and helpers used across the UI."""

from __future__ import annotations

import os
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
from typing import Optional

# Pillow is optional. If it is missing we fall back to the built-in
# PhotoImage (PNG/GIF only) — see load_image below for the workaround that
# scales any format without Pillow on Windows.
try:
    from PIL import Image, ImageTk  # type: ignore
    HAS_PIL = True
except Exception:  # pragma: no cover - depends on environment
    HAS_PIL = False

from app.ui.theme import COLORS

# Lazy import to avoid circular dependency — i18n is only needed at runtime
# when the user actually interacts with the widget, not at import time.
def _tr(key: str) -> str:
    from app.i18n import tr
    return tr(key)

# Module-level keepalive lists so PhotoImage references are not garbage
# collected while displayed inside Treeview cells (which do not own refs).
_THUMB_KEEPALIVE: list[tk.PhotoImage] = []


def clear_image_cache() -> None:
    """Drop all cached PhotoImage references.

    Call this before rebuilding a view (e.g. on language change) so old
    images can be garbage-collected. Treeviews that still reference them
    will reload fresh images on the next ``load()``.
    """

    _THUMB_KEEPALIVE.clear()


# ---------------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------------
def confirm(title: str, message: str, parent: Optional[tk.Misc] = None) -> bool:
    """Show a yes/no confirmation dialog. Returns True if the user clicked Yes."""

    return messagebox.askyesno(title, message, parent=parent)


def show_error(title: str, message: str, parent: Optional[tk.Misc] = None) -> None:
    messagebox.showerror(title, message, parent=parent)


def show_info(title: str, message: str, parent: Optional[tk.Misc] = None) -> None:
    messagebox.showinfo(title, message, parent=parent)


def fit_window_to_content(
    window: tk.Misc,
    *,
    min_width: int = 520,
    min_height: int = 360,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None,
    padding: int = 8,
) -> None:
    """Resize a Toplevel/Top window to fit its content.

    Call this **after** all widgets are created. Measures the size the
    contents actually request (via ``update_idletasks`` + ``winfo_reqwidth``
    / ``winfo_reqheight``) and sets the window geometry so nothing is cut
    off — buttons included. The result is clamped to the screen size and to
    the given ``min_*`` / ``max_*`` bounds so a window never becomes too
    tiny or larger than the display.

    This replaces fixed ``geometry("WxH")`` calls, which are fragile under
    different fonts, DPI settings and translations.

    NOTE: this controls the *initial* size. For the bottom button bar to
    stay visible even when the user later shrinks the window, build dialogs
    with :func:`make_dialog_layout` so the footer is packed last with
    ``side=BOTTOM`` and only the middle area is expandable.
    """

    window.update_idletasks()

    req_w = window.winfo_reqwidth()
    req_h = window.winfo_reqheight()

    # Add a little breathing room so borders / shadows are not tight.
    width = max(min_width, req_w + padding)
    height = max(min_height, req_h + padding)

    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()

    # Default ceiling: leave a margin around the screen.
    if max_width is None:
        max_width = screen_w - 40
    if max_height is None:
        max_height = screen_h - 80

    width = min(width, max_width)
    height = min(height, max_height)

    # Centre the window on the parent (or the screen) so it appears in a
    # predictable spot rather than wherever the window manager defaults.
    parent = window.master if hasattr(window, "master") else None
    try:
        if parent is not None and parent.winfo_exists():
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw - width) // 2
            y = py + (ph - height) // 2
        else:
            raise RuntimeError("no parent")
    except Exception:
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2

    # Keep at least a tiny margin from the top-left of the screen.
    x = max(8, min(x, screen_w - width - 8))
    y = max(8, min(y, screen_h - height - 8))

    window.geometry(f"{width}x{height}+{x}+{y}")
    window.minsize(min_width, min_height)


def make_dialog_layout(window: tk.Misc) -> tuple[ttk.Frame, ttk.Frame]:
    """Build the standard dialog shell: a scrollable body + a sticky footer.

    Returns ``(body, footer)``. The footer is packed **first from the
    bottom** (``side=BOTTOM``) so action buttons are *always* visible no
    matter how small the window becomes — the body shrinks instead. The body
    itself sits inside a Canvas+Scrollbar so tall forms scroll instead of
    being clipped.

    Use this instead of manually ``pack``-ing body and footer frames, which
    is the root cause of "buttons are below the visible area" bugs.
    """

    footer = ttk.Frame(window, style="TFrame")
    footer.pack(side=tk.BOTTOM, fill=tk.X)

    # Scrollable body: Canvas + inner frame, standard Tkinter pattern.
    canvas = tk.Canvas(window, highlightthickness=0, background=COLORS["bg"])
    vsb = ttk.Scrollbar(window, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    body = ttk.Frame(canvas, style="TFrame")
    body_window = canvas.create_window((0, 0), window=body, anchor="nw")

    # Keep the inner body as wide as the canvas so widgets stretch correctly.
    def _on_canvas_configure(event):
        canvas.itemconfigure(body_window, width=event.width)

    # Update scrollregion whenever the inner body changes size.
    def _on_body_configure(_event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    canvas.bind("<Configure>", _on_canvas_configure)
    body.bind("<Configure>", _on_body_configure)

    # Mouse-wheel scrolling for convenience.
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
    canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

    return body, footer


def pick_image_file(parent: tk.Misc) -> Optional[str]:
    """Open a file dialog filtered on common image types."""

    path = filedialog.askopenfilename(
        parent=parent,
        title=_tr("file.select_image_title"),
        filetypes=[
            (_tr("file.images"), "*.png *.jpg *.jpeg *.gif *.bmp"),
            (_tr("file.all_files"), "*.*"),
        ],
    )
    return path or None


# ---------------------------------------------------------------------------
# Image loading
# ---------------------------------------------------------------------------
def load_image(path: Optional[str], size: tuple[int, int]) -> Optional[tk.PhotoImage]:
    """Load an image and scale it to ``size`` (width, height) in pixels.

    Returns a PhotoImage, or None if no image could be produced. The
    returned PhotoImage is registered in a module-level keepalive list so it
    survives when used inside Treeview cells.

    The PhotoImage is created against the current default Tk root — this is
    the behaviour of the original, working implementation and is what
    reliably renders both in the main window and in Toplevel dialogs.

    Strategy (with fallbacks so a single broken step never silently yields
    "No image"):
      1. Pillow present  -> any format, smooth scaling.
      2. If Pillow fails or is absent, and the file is PNG/GIF, fall back to
         the built-in ``tk.PhotoImage``.
      3. Anything else -> None (Tk cannot decode it) and the reason is
         printed to stderr so it is diagnosable.
    """

    if not path:
        return None
    if not os.path.exists(path):
        import sys
        print(f"[load_image] file not found: {path}", file=sys.stderr)
        return None

    width, height = size
    ext = os.path.splitext(path)[1].lower()

    # 1) Preferred path: Pillow (supports every common format).
    if HAS_PIL:
        try:
            img = Image.open(path)
            img = _fit_cover(img, width, height)
            photo = ImageTk.PhotoImage(img)
            _THUMB_KEEPALIVE.append(photo)
            return photo
        except Exception as exc:
            import sys
            print(f"[load_image] Pillow failed on {path}: {exc}", file=sys.stderr)
            # Fall through to the Tk fallback for PNG/GIF.

    # 2) Fallback: Tk's built-in PhotoImage (PNG/GIF only).
    if ext in (".png", ".gif"):
        try:
            photo = tk.PhotoImage(file=path)
            photo = _subsample_photo(photo, width, height)
            _THUMB_KEEPALIVE.append(photo)
            return photo
        except Exception as exc:
            import sys
            print(f"[load_image] Tk PhotoImage failed on {path}: {exc}", file=sys.stderr)

    # 3) Nothing else Tk can decode without Pillow.
    if not HAS_PIL and ext not in (".png", ".gif"):
        import sys
        print(
            f"[load_image] cannot display {ext} without Pillow. "
            "Install it with:  pip install Pillow",
            file=sys.stderr,
        )
    return None


def _fit_cover(img, width: int, height: int):
    """Crop+resize a PIL image to fill ``width x height`` without distortion."""

    from PIL import Image  # type: ignore

    img = img.convert("RGB")
    src_w, src_h = img.size
    scale = max(width / src_w, height / src_h)
    new_w, new_h = max(1, int(src_w * scale)), max(1, int(src_h * scale))
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    return img.crop((left, top, left + width, top + height))


def _subsample_photo(photo: tk.PhotoImage, width: int, height: int) -> tk.PhotoImage:
    """Scale a tk.PhotoImage (no Pillow) to roughly fit ``width x height``."""

    src_w = photo.width()
    src_h = photo.height()
    if src_w <= 0 or src_h <= 0:
        return photo
    # subsample takes an integer step. Pick the largest step that keeps the
    # image within the target box (rounds up so we never oversize).
    import math

    step = max(1, int(math.ceil(max(src_w / width, src_h / height))))
    return photo.subsample(step, step)


# ---------------------------------------------------------------------------
# Treeview factory
# ---------------------------------------------------------------------------
def make_treeview(
    parent: tk.Misc,
    columns: list[tuple[str, str, int]],
    *,
    with_image: bool = False,
    image_size: int = 44,
) -> ttk.Treeview:
    """Create a Treeview with scrollbars and column headings.

    ``columns`` is a list of ``(column_id, header_text, width)`` tuples.

    When ``with_image=True`` the first column in ``columns`` is treated as a
    hidden key column and an ``#image`` icon column is rendered at the start.
    Rows are made taller (see the ``Img.Treeview`` style) so the thumbnail is
    visible. Use :func:`insert_image_row` to add rows.
    """

    column_ids = [c[0] for c in columns]

    if with_image:
        # Tk's Treeview always has a #0 (tree) column.  We render it as the
        # thumbnail by passing show="tree headings" and hiding its heading text.
        tree = ttk.Treeview(
            parent,
            columns=column_ids,
            show="tree headings",
            selectmode="browse",
            style="Img.Treeview",
        )
        tree.heading("#0", text="")
        tree.column("#0", width=image_size + 16, minwidth=image_size + 16,
                    stretch=False, anchor=tk.CENTER)
    else:
        tree = ttk.Treeview(parent, columns=column_ids, show="headings", selectmode="browse")
        tree.heading("#0", text="")

    for col_id, header, width in columns:
        anchor = tk.CENTER if col_id in ("quantity", "qty", "stock", "price",
                                         "subtotal", "revenue", "units",
                                         "unit_cost", "total", "id") else tk.W
        tree.heading(col_id, text=header, command=lambda c=col_id: _sort_by(tree, c))
        tree.column(col_id, width=width, anchor=anchor)

    vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    parent.rowconfigure(0, weight=1)
    parent.columnconfigure(0, weight=1)
    return tree


def insert_image_row(
    tree: ttk.Treeview,
    image: Optional[tk.PhotoImage],
    values: tuple,
    iid: str,
) -> None:
    """Insert a row whose leading cell shows ``image``.

    When ``image`` is None the ``-image`` option is omitted entirely so that
    Tcl/Tk does not choke on a ``None`` value (which would shift subsequent
    positional arguments and produce a confusing error).
    """

    if image is not None:
        tree.insert("", tk.END, iid=iid, image=image, values=values)
    else:
        tree.insert("", tk.END, iid=iid, values=values)


def _sort_by(tree: ttk.Treeview, column: str) -> None:
    """Sort a Treeview by a column, toggling direction on repeat clicks."""

    data = [(tree.set(iid, column), iid) for iid in tree.get_children("")]
    try:
        data.sort(key=lambda x: float(x[0].replace(",", "")) if x[0] not in ("", None) else 0.0)
    except ValueError:
        data.sort()
    if getattr(tree, f"_sort_desc_{column}", False):
        data.reverse()
        setattr(tree, f"_sort_desc_{column}", False)
    else:
        setattr(tree, f"_sort_desc_{column}", True)
    for idx, (_, iid) in enumerate(data):
        tree.move(iid, "", idx)


# ---------------------------------------------------------------------------
# Misc widgets
# ---------------------------------------------------------------------------
class LabeledEntry(ttk.Frame):
    """A label + entry packed horizontally with a fixed label width."""

    def __init__(self, parent: tk.Misc, label: str, value: str = "", width: int = 25):
        super().__init__(parent, style="TFrame")
        ttk.Label(self, text=label, width=14, anchor=tk.W).pack(side=tk.LEFT)
        self.var = tk.StringVar(value=value)
        ttk.Entry(self, textvariable=self.var, width=width).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

    def get(self) -> str:
        return self.var.get().strip()


class ImageThumbnail(ttk.Frame):
    """A square image preview that gracefully handles missing images.

    The image is always scaled to ``size`` and the frame itself is fixed in
    size so a large source image can never push the rest of the layout off
    screen.

    Clicking the thumbnail (when an image is set) opens a full-size viewer
    via :class:`ImageViewer`.
    """

    def __init__(self, parent: tk.Misc, size: int = 140):
        super().__init__(parent, style="Card.TFrame")
        self.size = size
        self._photo = None  # keep a reference so the image is not GC'd
        self._path: Optional[str] = None
        self.label = ttk.Label(self, width=size, anchor=tk.CENTER, style="Card.TLabel")
        self.label.pack(padx=4, pady=4)
        # Make the thumbnail clickable so the user can zoom into the image.
        self.label.bind("<Button-1>", self._on_click)
        # Cursor hint that the image is clickable.
        self.label.configure(cursor="hand2")
        self.set_path(None)

    def set_path(self, path: Optional[str]) -> None:
        self._path = path
        photo = load_image(path, (self.size, self.size))
        if photo is None:
            self.label.configure(text=_tr("widget.no_image"), image="", cursor="arrow")
            self._photo = None
            return
        self.label.configure(image=photo, text="", cursor="hand2")
        self._photo = photo

    def _on_click(self, _event: tk.Event) -> None:
        if self._path:
            ImageViewer(self.winfo_toplevel(), self._path)


class ImageViewer(tk.Toplevel):
    """A modal window showing an image scaled to fit the screen.

    Opens when the user clicks a product thumbnail. Click anywhere or press
    Escape to close. The image is shown as large as possible without
    upscaling beyond its native resolution.
    """

    def __init__(self, parent: tk.Misc, path: str):
        super().__init__(parent)
        self.title(_tr("dlg.image_viewer"))
        self.transient(parent)
        self.grab_set()
        self.configure(background=COLORS["bg"])

        # Compute a target size that fits the screen with a margin.
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        max_w = min(1000, screen_w - 80)
        max_h = min(800, screen_h - 120)

        # Determine the native image size (Pillow) so we never upscale.
        native_w = native_h = None
        if HAS_PIL:
            try:
                from PIL import Image as _PILImage
                with _PILImage.open(path) as im:
                    native_w, native_h = im.size
            except Exception:
                native_w = native_h = None

        target_w, target_h = max_w, max_h
        if native_w and native_h:
            # Don't upscale beyond native resolution.
            target_w = min(max_w, native_w)
            target_h = min(max_h, native_h)

        photo = load_image(path, (target_w, target_h))
        if photo is None:
            ttk.Label(self, text=_tr("widget.no_image")).pack(padx=40, pady=40)
        else:
            label = ttk.Label(self, image=photo, background=COLORS["surface"])
            label.pack(padx=12, pady=12)
            label.bind("<Button-1>", lambda _e: self.destroy())
            self._photo = photo  # keepalive

        hint = ttk.Label(self, text=_tr("dlg.image_viewer_hint"),
                         style="Subtitle.TLabel")
        hint.pack(pady=(0, 10))

        # Close interactions.
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self.destroy())
        self.bind("<Button-1>", lambda _e: self.destroy())

        fit_window_to_content(self, min_width=320, min_height=240)


class MetricCard(ttk.Frame):
    """A bordered card showing a big number with a small caption.

    Used by the statistics tab and the product detail header.
    """

    def __init__(self, parent: tk.Misc, caption: str, value: str = "-", accent: str = ""):
        super().__init__(parent, style="Card.TFrame")
        self._value_label = ttk.Label(
            self, text=value, style="Metric.TLabel", foreground=accent or COLORS["primary"]
        )
        self._value_label.pack(anchor=tk.W, padx=16, pady=(18, 2))
        ttk.Label(self, text=caption, style="Subtitle.TLabel").pack(
            anchor=tk.W, padx=16, pady=(0, 16)
        )
        self.configure(height=110)  # visually a card
        self.pack_propagate(False)  # keep the height even when contents are small


def status_badge(status: str) -> str:
    """Return a display string for an order status."""

    return {
        "new": _tr("status.new"),
        "shipped": _tr("status.shipped"),
    }.get(status, status)


# ---------------------------------------------------------------------------
# Search & filter widgets
# ---------------------------------------------------------------------------
class SearchBar(ttk.Frame):
    """A labelled search entry that fires ``on_change`` after each keystroke.

    A short debounce (``delay`` ms) avoids hammering the database while the
    user is still typing.
    """

    def __init__(
        self,
        parent: tk.Misc,
        placeholder: str,
        on_change,
        delay: int = 250,
    ):
        super().__init__(parent, style="TFrame")
        self._on_change = on_change
        self._delay = delay
        self._after_id: Optional[str] = None

        self.var = tk.StringVar()
        entry = ttk.Entry(self, textvariable=self.var)
        entry.pack(fill=tk.X)
        # Placeholder text is set/removed via focus events.
        self._placeholder = placeholder
        self._set_placeholder()
        entry.bind("<FocusIn>", self._on_focus_in)
        entry.bind("<FocusOut>", self._on_focus_out)
        self.var.trace_add("write", self._schedule)

    def _set_placeholder(self) -> None:
        if not self.var.get():
            self.var.set(self._placeholder)

    def _on_focus_in(self, _event: tk.Event) -> None:
        if self.var.get() == self._placeholder:
            self.var.set("")

    def _on_focus_out(self, _event: tk.Event) -> None:
        if not self.var.get():
            self.var.set(self._placeholder)

    def get(self) -> str:
        """Return the current query, or empty string if it's just the placeholder."""

        value = self.var.get()
        return "" if value == self._placeholder else value.strip()

    def clear(self) -> None:
        self.var.set(self._placeholder)
        self._on_change()

    def _schedule(self, *_args) -> None:
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self._after_id = self.after(self._delay, self._fire)

    def _fire(self) -> None:
        self._after_id = None
        self._on_change()


class FilterDropdown(ttk.Frame):
    """A labelled combobox used as a single-value filter.

    ``values`` is a list of ``(raw_value, display_label)`` tuples; the first
    entry should be the "All" sentinel (raw value ``""``).
    """

    def __init__(
        self,
        parent: tk.Misc,
        label: str,
        values: list[tuple[str, str]],
        on_change,
        width: int = 14,
    ):
        super().__init__(parent, style="TFrame")
        ttk.Label(self, text=label, style="Subtitle.TLabel").pack(anchor=tk.W)
        self._raw_for: dict[str, str] = {display: raw for raw, display in values}
        self._values = values
        self.var = tk.StringVar()
        self.box = ttk.Combobox(
            self,
            textvariable=self.var,
            values=[display for _, display in values],
            state="readonly",
            width=width,
        )
        self.box.current(0)
        self.box.pack()
        self.box.bind("<<ComboboxSelected>>", lambda _e: on_change())

    def get(self) -> str:
        """Return the selected raw value (empty string for "All")."""

        display = self.var.get()
        return self._raw_for.get(display, "")

    def set_values(self, values: list[tuple[str, str]]) -> None:
        """Replace the dropdown options, keeping the current selection if possible."""

        current_display = self.var.get()
        current_raw = self._raw_for.get(current_display, "")
        self._raw_for = {display: raw for raw, display in values}
        self._values = values
        self.box.configure(values=[display for _, display in values])
        # Try to keep the same selection; otherwise fall back to the first.
        new_display = next(
            (display for raw, display in values if raw == current_raw),
            values[0][1] if values else "",
        )
        self.var.set(new_display)


# ---------------------------------------------------------------------------
# Line chart (pure Tk Canvas, no matplotlib dependency)
# ---------------------------------------------------------------------------
class LineChart(ttk.Frame):
    """A simple multi-series line chart drawn on a Tk Canvas.

    Built for the Statistics tab. No external dependencies — it just draws
    axes, grid lines and one polyline per series. Redraws automatically when
    the canvas is resized.

    Usage::

        chart = LineChart(parent)
        chart.set_data(
            labels=["2026-07-01", "2026-07-02", ...],
            series={
                "Revenue":  ([10, 20, 5, ...], "#4f6df5"),
                "Orders":   ([1, 2, 1, ...],   "#10b981"),
            },
        )
    """

    def __init__(self, parent: tk.Misc, height: int = 240):
        super().__init__(parent, style="Card.TFrame", padding=12)
        self._labels: list[str] = []
        self._series: dict[str, tuple[list[float], str]] = {}
        self._legend_label: Optional[ttk.Label] = None

        # Canvas with a subtle background; expandable.
        self.canvas = tk.Canvas(self, height=height, highlightthickness=0,
                                background=COLORS["surface"])
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda _e: self._draw())

        # Legend below the chart.
        self._legend_label = ttk.Label(self, text="", style="Card.TLabel")
        self._legend_label.pack(anchor=tk.W, pady=(6, 0))

    def set_data(
        self,
        labels: list[str],
        series: dict[str, tuple[list[float], str]],
    ) -> None:
        """Replace the chart data and redraw.

        ``series`` maps a series name to ``(values, color_hex)``. All series
        must have the same length as ``labels``.
        """

        self._labels = list(labels)
        self._series = {name: (list(vals), color) for name, (vals, color) in series.items()}
        self._update_legend()
        self._draw()

    def _update_legend(self) -> None:
        parts = []
        for name, (_vals, color) in self._series.items():
            parts.append(f"[{color}] {name}")
        self._legend_label.configure(text="   ".join(parts))

    def _draw(self) -> None:
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w <= 1 or h <= 1:
            return  # not laid out yet

        # Plot area with margins for axis labels.
        margin_left = 56
        margin_right = 16
        margin_top = 12
        margin_bottom = 36
        plot_w = max(10, w - margin_left - margin_right)
        plot_h = max(10, h - margin_top - margin_bottom)

        # Determine the Y-axis range across all series.
        max_val = 0.0
        for _name, (vals, _color) in self._series.items():
            for v in vals:
                if v > max_val:
                    max_val = v
        if max_val <= 0:
            max_val = 1.0
        # Round the ceiling up to a tidy number.
        y_ceiling = _nice_ceil(max_val)

        # Grid lines + Y-axis labels (5 ticks).
        c.create_rectangle(0, 0, w, h, fill=COLORS["surface"], outline="")
        for i in range(5 + 1):
            frac = i / 5
            y = margin_top + plot_h - frac * plot_h
            value = y_ceiling * frac
            c.create_line(margin_left, y, margin_left + plot_w, y,
                          fill=COLORS["border"], dash=(2, 3))
            c.create_text(
                margin_left - 8, y, anchor=tk.E,
                text=_format_number(value),
                fill=COLORS["muted"],
                font=("Segoe UI", 8),
            )

        n = len(self._labels)
        if n == 0:
            c.create_text(w // 2, h // 2, text="—", fill=COLORS["muted"])
            return

        # X coordinates for each data point.
        def x_at(i: int) -> float:
            if n == 1:
                return margin_left + plot_w / 2
            return margin_left + (plot_w * i / (n - 1))

        def y_at(value: float) -> float:
            return margin_top + plot_h - (value / y_ceiling) * plot_h

        # Draw each series as a polyline.
        for _name, (vals, color) in self._series.items():
            points = []
            for i, v in enumerate(vals):
                points.extend([x_at(i), y_at(v)])
            if len(points) >= 4:
                c.create_line(*points, fill=color, width=2, smooth=True,
                              splinesteps=12)
            # Data point markers.
            for i, v in enumerate(vals):
                c.create_oval(x_at(i) - 3, y_at(v) - 3, x_at(i) + 3, y_at(v) + 3,
                              fill=color, outline="")

        # X-axis labels: show ~6 evenly spaced labels to avoid clutter.
        label_count = min(6, n)
        if label_count > 0:
            step = max(1, (n - 1) // max(1, label_count - 1)) if n > 1 else 1
            shown = set()
            for i in range(0, n, step):
                shown.add(i)
            # Always include the last index for a clean end label.
            shown.add(n - 1)
            for i in sorted(shown):
                label = self._labels[i]
                # Compact date labels (strip the year if every label is the same year).
                short = label[5:] if len(label) == 10 else label
                c.create_text(x_at(i), margin_top + plot_h + 16,
                              text=short, fill=COLORS["muted"],
                              font=("Segoe UI", 8), anchor=tk.N)


def _nice_ceil(value: float) -> float:
    """Round ``value`` up to a tidy 1/2/5 × 10^n number for axis ceilings."""

    if value <= 0:
        return 1.0
    import math
    mag = 10 ** math.floor(math.log10(value))
    norm = value / mag
    if norm <= 1:
        nice = 1
    elif norm <= 2:
        nice = 2
    elif norm <= 5:
        nice = 5
    else:
        nice = 10
    return nice * mag


def _format_number(value: float) -> str:
    """Compact number formatting for axis ticks (e.g. 1.2k, 3.4M)."""

    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}"

