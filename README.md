# Inventory & Order Management

A small desktop application (Python + Tkinter + SQLite) for tracking product
inventory and customer orders. Ships as a standalone Windows `.exe` (no Python
required) and is bilingual (English / Simplified Chinese).

---

## Features

### Inventory System
- Add / edit / delete products with: **code, name, base price, image,
  variants (color + size)**.
- Colors and sizes picked from dropdowns of existing values, with the option
  to type brand-new ones.
- **Search & filters** in the product list: by code/name, color, size,
  in-stock / out-of-stock.
- Double-click a product (or *View Details*) to open the product window:
  - Big **current stock** indicator.
  - **Stock-In** tab — unit cost is pre-filled with the product's base price
    (editable per shipment).
  - **Stock-Out** tab — record outgoing items / returns.
  - **History** tab — combined, time-sorted movement log.
- Click any product thumbnail to view it full-size.

### Order System
- Create an order: customer name, date, line items
  (product, color, size, quantity, unit price). Total is auto-calculated.
- The line-item editor lives at the bottom of the order window, just above
  the action buttons, so it is always visible.
- Orders start as **New**.
- **Mark as Shipped** sets the order to *Shipped* and **reduces stock
  automatically**.
- **Mark as New** reverts a shipment — stock is **returned** to the warehouse.
- **Search & filters**: by customer / order #, by status, by date range.
- Product photos are shown next to each line item in the order view.

### Statistics
- Summaries for **This Week / This Month / This Quarter** or any custom range.
- **Filter by product** — every metric narrows to a single product.
- Cards: revenue, orders shipped, units sold.
- **Interactive line chart** of revenue / orders / units over time; rebuilds
  whenever the period or filter changes. Pure-Tk Canvas (no matplotlib).
- Top-10 products by revenue table.

### UX details
- Modern flat theme (custom palette + Segoe UI).
- Custom application icon (embedded in the window and the .exe).
- All dialog buttons stay visible at any window size — long forms scroll,
  the action bar is pinned to the bottom.
- Language toggle (EN / 中文) in the top-right.

---

## How stock is calculated

Current stock for any product/variant is always derived, never stored:

```
stock = SUM(stock_in.quantity) − SUM(stock_out.quantity)
```

Stock is reduced **only when an order is shipped** (not when it is created),
so the on-hand count reflects only what has actually left the warehouse.
Reverting a shipment removes the matching `stock_out` rows, so the two sides
of the system stay consistent automatically.

---

## Running from source

Requirements: **Python 3.10+** with Tkinter (ships with the official Windows
installer) and Pillow (for JPG/WEBP/BMP product images; PNG/GIF work without
it).

```bash
pip install -r requirements.txt   # Pillow + dateutil
python main.py
```

On first run the app creates two folders next to `main.py`:

- `data/`     → holds `inventory.db` (the SQLite database)
- `images/`   → copies of the product images you pick

---

## Building the standalone .exe

The app is bundled into a single Windows executable with PyInstaller. The
icon is embedded and also placed next to the `.exe` so the running program
can pick it up for the window/taskbar.

```bash
pip install pyinstaller
py -3.14 -m PyInstaller --clean --noconfirm app.spec
```

Output: `dist/InventoryOrders.exe` (~19 MB, fully self-contained).

### Regenerating the icon

The icon is generated procedurally (no external assets needed):

```bash
python make_icon.py          # writes app.ico + app.png
```

---

## Distributing to another user

The ready-to-share bundle lives in **`Release/`**:

```
Release/
├── InventoryOrders.exe      # the standalone app
├── app.ico                  # icon (optional, cosmetic)
└── README.txt               # end-user instructions (Russian + overview)
```

To share: zip the `Release/` folder and send it. The recipient just
double-clicks `InventoryOrders.exe` — no Python, Pillow, or any other
dependency is needed. Their data will be created automatically next to the
`.exe` (`data/inventory.db` + `images/`).

To move the recipient's data to another machine later, copy `InventoryOrders.exe`
together with the `data/` and `images/` folders.

---

## Project layout

```
main.py                    # entry point
make_icon.py               # generates app.ico / app.png
app.spec                   # PyInstaller build spec
requirements.txt           # Pillow + dateutil
app/
  paths.py                 # data/images folder locations (frozen-aware)
  db.py                    # SQLite connection + schema
  repository.py            # all data access (no SQL in the UI)
  i18n.py                  # EN / ZH translations + language toggle
  ui/
    theme.py               # flat colour palette + ttk styles
    widgets.py             # treeview, image thumbnail, line chart, dialogs
    main_window.py         # appbar + 3 tabs
    inventory_view.py      # product list + search/filters
    product_dialog.py      # add / edit product form (variant dropdowns)
    product_detail.py      # stock-in / stock-out / history per product
    orders_view.py         # order list + ship / unship / delete
    order_dialog.py        # create / view order + line items
    stats_view.py          # summaries + trend chart + product filter
data/                      # created automatically (gitignored)
images/                    # created automatically
Release/                   # distributable bundle for end users
```

---

## Backups

To back up your data, copy the `data/inventory.db` file and the `images/`
folder. The database is a single portable file — restoring it is just a
matter of putting it back in place.
