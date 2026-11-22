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


# The app was called "Toolbox" before it became Tessera; its data folder moves across on first start.
LEGACY_DATA_DIRS = ("Toolbox",)
# Files that show a legacy folder is ours, not another app's that happens to share the generic name.
_DATA_MARKERS = ("settings.json", "toolbox.log")


def user_data_dir() -> Path:
    """Per-user writable directory for settings, logs, downloaded components and WebView storage."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    root = Path(base) if base else Path.home() / ".local" / "share"
    path = root / APP_NAME
    if not path.exists():
        for name in LEGACY_DATA_DIRS:
            legacy = root / name
            if legacy.is_dir() and any((legacy / m).is_file() for m in _DATA_MARKERS):
                try:
                    legacy.rename(path)
                except OSError:
                    # Still open (an old copy running?): keep using it rather than start empty.
                    return legacy
                break
    path.mkdir(parents=True, exist_ok=True)
    return path
