"""Filesystem locations that differ between running from source and a frozen build."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from . import APP_NAME

# backend/toolbox/paths.py -> project root is two levels above the package.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def is_frozen() -> bool:
    """True when running from a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def web_dir() -> Path:
    """Directory holding the built React app (index.html + assets)."""
    if is_frozen():
        # build.py bundles frontend/dist as "web" inside the PyInstaller archive.
        return Path(sys._MEIPASS) / "web"  # type: ignore[attr-defined]
    return PROJECT_ROOT / "frontend" / "dist"


def user_data_dir() -> Path:
    """Per-user writable directory for logs and WebView storage."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    root = Path(base) if base else Path.home() / ".local" / "share"
    path = root / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path
