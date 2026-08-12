"""Central place for filesystem paths used by the application.

All paths are resolved relative to the project root (the folder that contains
the ``app`` package, or — when the app has been frozen into a standalone exe —
the folder that contains the exe). The ``data`` and ``images`` folders are
created on demand the first time the application starts.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def _compute_project_root() -> Path:
    """Return the project root.

    When running from source, this is the parent of the ``app`` package.
    When running from a PyInstaller-frozen executable, ``__file__`` points
    into a temporary extraction folder, so we fall back to the directory
    that contains the .exe itself — that is where the user's ``data/`` and
    ``images/`` folders should live.
    """

    if getattr(sys, "frozen", False):
        # Frozen by PyInstaller. sys.executable is the path to the .exe.
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


# Project root = parent of the "app" package directory (or the folder holding
# the .exe when frozen).
PROJECT_ROOT = _compute_project_root()

#: Directory that holds the SQLite database file.
DATA_DIR = PROJECT_ROOT / "data"

#: Directory that holds product image files copied from the user's disk.
IMAGES_DIR = PROJECT_ROOT / "images"

#: Full path to the SQLite database file.
DB_PATH = DATA_DIR / "inventory.db"


def ensure_dirs() -> None:
    """Create the ``data`` and ``images`` directories if they do not exist."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def resolve_image_path(filename: str) -> Path:
    """Return the absolute path of an image stored inside the ``images`` folder."""

    return IMAGES_DIR / filename


def resolve_stored_image(value: Optional[str]) -> Optional[str]:
    """Resolve a stored ``image_path`` value to an absolute filesystem path.

    Only the image *filename* is persisted in the database so the project can be
    moved between machines without breaking links. For backward compatibility,
    values that already look like an absolute path (legacy rows written before
    this change) are returned unchanged.
    """

    if not value:
        return None
    if os.path.isabs(value):
        return value
    return str(IMAGES_DIR / value)
