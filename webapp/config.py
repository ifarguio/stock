"""Application configuration, read from environment variables.

Everything that differs between local dev and production (the database URL,
the secret key) comes from the environment so the same code runs in both
places without changes.
"""

from __future__ import annotations

import os


class Config:
    # The PostgreSQL connection string. Render injects DATABASE_URL
    # automatically for the linked database; locally it comes from a .env
    # file or the shell environment.
    DATABASE_URL = os.environ.get("DATABASE_URL", "")

    # Used to sign session cookies. MUST be set in production.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Upload / session tweaks.
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB max per image upload

    # Default language code ("en" or "zh"). Can be overridden per-user later.
    DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "en")
