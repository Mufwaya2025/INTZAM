# -*- coding: utf-8 -*-
"""
config/config_loader.py
=======================
Loads the correct .env file for the current environment BEFORE Django
(and python-decouple) read any settings.

How it works
------------
1. Reads the APP_ENV environment variable (set in shell or systemd unit).
   Defaults to 'local' if not set.
2. Looks for  backend/.env.<APP_ENV>  (e.g. .env.local, .env.production).
3. Loads that file into os.environ using python-dotenv with override=True.
4. python-decouple (used in settings.py) checks os.environ BEFORE its own
   .env parser, so it will always see the values loaded here.
5. odoo_client.py calls load_dotenv('.env', override=False) — that becomes a
   no-op for any key already in os.environ, so it is safe to leave as-is.

Usage
-----
Call load_env() at the very top of manage.py, wsgi.py, and asgi.py —
before os.environ.setdefault('DJANGO_SETTINGS_MODULE', ...) and before
any Django import.

    from config.config_loader import load_env
    load_env()

Environment variable
--------------------
    APP_ENV=local        → loads backend/.env.local   (default)
    APP_ENV=production   → loads backend/.env.production
    APP_ENV=staging      → loads backend/.env.staging  (create as needed)

If the target file does not exist, falls back to backend/.env with a warning.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Backend directory (one level up from this file's config/ package)
_BACKEND_DIR = Path(__file__).resolve().parent.parent


def load_env(app_env: str | None = None) -> Path:
    """
    Load the environment file that matches APP_ENV into os.environ.

    Args:
        app_env: Override APP_ENV (useful in tests).  When None, reads the
                 APP_ENV environment variable (default: 'local').

    Returns:
        Path: the .env file that was actually loaded.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        print(
            "[config_loader] WARNING: python-dotenv is not installed. "
            "Install it with: pip install python-dotenv>=1.0.0",
            file=sys.stderr,
        )
        return _BACKEND_DIR / '.env'

    env_name  = app_env or os.environ.get('APP_ENV', 'local')
    env_file  = _BACKEND_DIR / f'.env.{env_name}'

    if env_file.exists():
        load_dotenv(env_file, override=True)
        _info(f"Loaded environment: {env_file.name}  (APP_ENV={env_name!r})")
        return env_file

    # ── Fallback to legacy .env ────────────────────────────────────────────────
    fallback = _BACKEND_DIR / '.env'
    if fallback.exists():
        load_dotenv(fallback, override=False)
        _warn(
            f".env.{env_name} not found — fell back to .env. "
            f"Create .env.{env_name} from the template to remove this warning."
        )
        return fallback

    _warn(
        f"No environment file found (.env.{env_name} or .env). "
        f"Settings will rely entirely on shell environment variables."
    )
    return env_file   # path doesn't exist, but return it for logging


def _info(msg: str) -> None:
    print(f"[config_loader] {msg}", file=sys.stderr)


def _warn(msg: str) -> None:
    print(f"[config_loader] WARNING: {msg}", file=sys.stderr)


# ── Convenience: expose the active APP_ENV ────────────────────────────────────

def get_app_env() -> str:
    """Return the active APP_ENV value ('local', 'production', etc.)."""
    return os.environ.get('APP_ENV', 'local')
