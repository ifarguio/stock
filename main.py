"""Application entry point.

Run with::

    python main.py
"""

from __future__ import annotations

from app.db import init_db
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def main() -> None:
    # Initialise the database (creates tables if missing) before the UI starts.
    init_db()

    app = MainWindow()
    # Apply the modern flat theme once the window exists so styles attach to
    # the correct Tk root.
    apply_theme(app)
    app.mainloop()


if __name__ == "__main__":
    main()
