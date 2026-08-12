"""Modal dialog for creating or editing a product.

Captures: code, name, base price, image file, and a set of (color, size)
variants. Colors and sizes are picked from dropdowns populated from the
existing variants in the database, but the dropdowns are editable so the
user can type a brand-new color or size on the spot. Chosen variants are
listed in a small table and can be removed individually.

The image is copied into the ``images`` folder so the original file can
later be moved or deleted.
"""

from __future__ import annotations

import os
import shutil
import tkinter as tk
import tkinter.ttk as ttk
from datetime import datetime
from typing import Optional

from app import i18n, repository
from app.paths import IMAGES_DIR
from app.ui.theme import COLORS
from app.ui.widgets import (
    LabeledEntry,
    fit_window_to_content,
    make_dialog_layout,
    make_treeview,
    pick_image_file,
    show_error,
)


def _save_image_into_project(source_path: str) -> str:
    """Copy the chosen image into ``images/`` with a unique name.

    Returns only the *filename* of the stored copy (not its full path). The
    database stores bare filenames so the project stays portable across
    machines; :func:`resolve_stored_image` turns the name back into a path.
    """

    ext = os.path.splitext(source_path)[1] or ".png"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"product_{timestamp}{ext}"
    dest = IMAGES_DIR / filename
    shutil.copyfile(source_path, str(dest))
    return dest.name


class ProductDialog:
    """A modal toplevel wrapping a form. Sets ``self.result`` on success."""

    def __init__(
        self,
        parent: tk.Misc,
        product: Optional[dict] = None,
    ) -> None:
        self.result: Optional[int] = None
        self.product = product
        self.image_path: Optional[str] = product["image_path"] if product else None

        # Variants being edited: list of (color, size) tuples, order-preserving
        # with no duplicates.
        self._variants: list[tuple[str, str]] = []
        # Pre-populate existing variant catalog (colors / sizes seen so far in
        # the whole database) so the dropdowns offer sensible suggestions.
        self._known_colors = repository.list_all_colors()
        self._known_sizes = repository.list_all_sizes()

        self.top = tk.Toplevel(parent)
        self.top.title(
            i18n.tr("dlg.edit_product") if product else i18n.tr("dlg.add_product")
        )
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(background=COLORS["bg"])

        body, footer = make_dialog_layout(self.top)
        body.configure(padding=20)

        ttk.Label(
            body,
            text=i18n.tr("dlg.edit_product") if product else i18n.tr("dlg.add_product"),
            style="Title.TLabel",
        ).pack(anchor=tk.W)
        ttk.Label(
            body,
            text=i18n.tr("dlg.product_subtitle"),
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(2, 14))

        form_card = ttk.Frame(body, style="Card.TFrame", padding=16)
        form_card.pack(fill=tk.X)

        self.code = LabeledEntry(form_card, i18n.tr("lbl.code"), product["code"] if product else "")
        self.code.pack(fill=tk.X, pady=2)
        self.name = LabeledEntry(form_card, i18n.tr("lbl.name"), product["name"] if product else "")
        self.name.pack(fill=tk.X, pady=2)

        price_frame = ttk.Frame(form_card, style="Card.TFrame")
        price_frame.pack(fill=tk.X, pady=2)
        ttk.Label(price_frame, text=i18n.tr("lbl.base_price"), style="Card.TLabel",
                  width=14, anchor=tk.W).pack(side=tk.LEFT)
        self.price_var = tk.StringVar(
            value=str(product["base_price"]) if product else "0"
        )
        ttk.Entry(price_frame, textvariable=self.price_var, width=12).pack(side=tk.LEFT)

        # Image picker
        img_frame = ttk.Frame(form_card, style="Card.TFrame")
        img_frame.pack(fill=tk.X, pady=6)
        ttk.Label(img_frame, text=i18n.tr("lbl.image"), style="Card.TLabel",
                  width=14, anchor=tk.W).pack(side=tk.LEFT)
        self.img_label = ttk.Label(img_frame, text=i18n.tr("lbl.no_image"),
                                   style="Card.TLabel", anchor=tk.W)
        self.img_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(img_frame, text=i18n.tr("btn.browse"),
                   command=self.browse_image).pack(side=tk.LEFT)
        if self.image_path:
            self.img_label.configure(text=os.path.basename(self.image_path))

        # ---- Variants editor ----
        variants_card = ttk.Frame(body, style="Card.TFrame", padding=16)
        variants_card.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        ttk.Label(variants_card, text=i18n.tr("sect.add_variant"),
                  style="Section.TLabel").pack(anchor=tk.W)

        add_row = ttk.Frame(variants_card, style="Card.TFrame")
        add_row.pack(fill=tk.X, pady=(6, 4))

        ttk.Label(add_row, text=i18n.tr("lbl.pick_color"),
                  style="Card.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(0, 4))
        # Editable combobox: the user can either pick an existing color or
        # type a new one.
        self.color_var = tk.StringVar()
        self.color_box = ttk.Combobox(
            add_row, textvariable=self.color_var,
            values=self._known_colors, width=14,
        )
        self.color_box.grid(row=0, column=1, padx=2)
        ttk.Label(add_row, text=i18n.tr("hint.color_new"),
                  style="Subtitle.TLabel").grid(row=1, column=1, sticky=tk.W, padx=2)

        ttk.Label(add_row, text=i18n.tr("lbl.pick_size"),
                  style="Card.TLabel").grid(row=0, column=2, sticky=tk.W, padx=(12, 4))
        self.size_var = tk.StringVar()
        self.size_box = ttk.Combobox(
            add_row, textvariable=self.size_var,
            values=self._known_sizes, width=10,
        )
        self.size_box.grid(row=0, column=3, padx=2)
        ttk.Label(add_row, text=i18n.tr("hint.size_new"),
                  style="Subtitle.TLabel").grid(row=1, column=3, sticky=tk.W, padx=2)

        ttk.Button(add_row, text=i18n.tr("btn.add_variant"),
                   style="Primary.TButton",
                   command=self.add_variant).grid(row=0, column=4, padx=(12, 0))

        # Existing variants list
        ttk.Label(variants_card, text=i18n.tr("sect.existing_variants"),
                  style="Card.TLabel").pack(anchor=tk.W, pady=(12, 4))

        list_frame = ttk.Frame(variants_card, style="Card.TFrame")
        list_frame.pack(fill=tk.BOTH, expand=True)
        self.variants_tree = make_treeview(
            list_frame,
            [
                ("color", i18n.tr("lbl.color").rstrip(":"), 180),
                ("size", i18n.tr("lbl.size").rstrip(":"), 140),
            ],
        )
        ttk.Button(variants_card, text=i18n.tr("btn.remove_variant"),
                   command=self.remove_variant).pack(anchor=tk.W, pady=(6, 0))

        self._empty_label = ttk.Label(
            variants_card, text=i18n.tr("info.no_variants"),
            style="Subtitle.TLabel",
        )

        # Load existing variants when editing.
        if product:
            for v in repository.list_variants(product["id"]):
                self._variants.append((v["color"], v["size"]))
        self._render_variants()

        # Footer buttons — packed into the sticky footer so they stay visible.
        footer.configure(style="TFrame", padding=(20, 12, 20, 12))
        ttk.Button(footer, text=i18n.tr("btn.cancel"),
                   command=self.top.destroy).pack(side=tk.RIGHT)
        ttk.Button(footer, text=i18n.tr("btn.save"), style="Primary.TButton",
                   command=self.save).pack(side=tk.RIGHT, padx=4)

        # Fit the window to its real content height so buttons are never cut
        # off (matters under non-default fonts, DPI scaling and translations).
        fit_window_to_content(
            self.top, min_width=540, min_height=560, max_width=900, max_height=920
        )

    # ---- Variant management --------------------------------------------
    def add_variant(self) -> None:
        color = self.color_var.get().strip()
        size = self.size_var.get().strip()
        if not color or not size:
            show_error(i18n.tr("err.variant_empty_title"),
                       i18n.tr("err.variant_empty_msg"), parent=self.top)
            return
        pair = (color, size)
        if pair in self._variants:
            show_error(i18n.tr("err.duplicate_variant_title"),
                       i18n.tr("err.duplicate_variant_msg"), parent=self.top)
            return

        self._variants.append(pair)
        # If the user typed a brand-new color/size, remember it for the
        # dropdown so it appears next time within this dialog session.
        if color not in self._known_colors:
            self._known_colors.append(color)
            self.color_box.configure(values=self._known_colors)
        if size not in self._known_sizes:
            self._known_sizes.append(size)
            self.size_box.configure(values=self._known_sizes)

        self.color_var.set("")
        self.size_var.set("")
        self._render_variants()

    def remove_variant(self) -> None:
        sel = self.variants_tree.selection()
        if not sel:
            return
        idx = self.variants_tree.index(sel[0])
        if 0 <= idx < len(self._variants):
            self._variants.pop(idx)
        self._render_variants()

    def _render_variants(self) -> None:
        for iid in self.variants_tree.get_children(""):
            self.variants_tree.delete(iid)
        for color, size in self._variants:
            self.variants_tree.insert(
                "", tk.END,
                values=(color, size),
                iid=f"{color}__{size}",
            )
        # Show/hide the empty-state hint.
        if self._variants:
            self._empty_label.pack_forget()
        else:
            self._empty_label.pack(anchor=tk.W, pady=(4, 0))

    # ---- Image / save ---------------------------------------------------
    def browse_image(self) -> None:
        path = pick_image_file(self.top)
        if path:
            self.image_path = path
            self.img_label.configure(text=os.path.basename(path))

    def save(self) -> None:
        code = self.code.get()
        name = self.name.get()
        if not code or not name:
            show_error(i18n.tr("err.missing_data_title"),
                       i18n.tr("err.missing_data_msg"), parent=self.top)
            return
        try:
            price = float(self.price_var.get() or 0)
        except ValueError:
            show_error(i18n.tr("err.invalid_price_title"),
                       i18n.tr("err.invalid_price_msg"), parent=self.top)
            return

        variants = list(self._variants)

        stored_image_filename = self.image_path
        # If the chosen path is absolute (i.e. the user just browsed to a file
        # outside the images/ folder), copy it in and store only the filename.
        if self.image_path and os.path.isabs(self.image_path):
            try:
                stored_image_filename = _save_image_into_project(self.image_path)
            except Exception as exc:
                show_error(i18n.tr("err.image_error_title"), str(exc), parent=self.top)
                return

        try:
            if self.product is None:
                self.result = repository.create_product(
                    code, name, price, stored_image_filename, variants
                )
            else:
                repository.update_product(
                    self.product["id"], code, name, price, stored_image_filename, variants
                )
                self.result = self.product["id"]
        except Exception as exc:
            show_error(i18n.tr("err.could_not_save_title"), str(exc), parent=self.top)
            return

        self.top.destroy()
