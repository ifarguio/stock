# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Inventory & Order Management app.

Build:
    py -3.14 -m PyInstaller --clean --noconfirm app.spec

Output:
    dist/InventoryOrders.exe   (single-file Windows executable)

The app stores its SQLite database under ``data/`` and product images under
``images/`` next to the .exe — these folders are created on first run, so
nothing needs to be bundled inside the executable.

The application icon (``app.ico``) is embedded into the .exe and also placed
next to it so the running program can pick it up for the window/taskbar icon.
"""

from PyInstaller.utils.hooks import collect_submodules

# Pillow sometimes needs its plugin submodules collected explicitly so that
# Image OPEN handlers (JPEG, PNG, ...) are available at runtime.
hiddenimports = [
    "PIL._tkinter_finder",
    "PIL.Image",
    "PIL.ImageTk",
]
hiddenimports += collect_submodules("PIL")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    # Ship the icon next to the exe so the running app can load it for the
    # window title and taskbar (see MainWindow._set_window_icon).
    datas=[
        ("app.ico", "."),
        ("app.png", "."),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim modules we know the app never uses to shrink the bundle.
        "unittest",
        "pydoc",
        "doctest",
        "argparse",
        "xml",
        "email",
        "http",
        "urllib",
        "pdb",
        "profile",
        "pstats",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="InventoryOrders",
    # Embed the icon into the .exe so it shows in Explorer/taskbar.
    icon="app.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,           # GUI app: no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
