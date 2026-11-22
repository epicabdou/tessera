"""Persistent user settings: pinned folders and file-browser preferences (JSON file)."""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Callable

from .filesystem import display_name, path_key, replace_with_retry, resolve_dir

log = logging.getLogger(__name__)

# Preference name -> validator. Only these can be set from the UI.
PREFERENCES: dict[str, Callable[[Any], bool]] = {
    "show_hidden": lambda v: isinstance(v, bool),
    "browser_root": lambda v: v is None or isinstance(v, str),
    "sidebar_width": lambda v: isinstance(v, int) and not isinstance(v, bool) and 180 <= v <= 800,
    "preview_open": lambda v: isinstance(v, bool),
    "preview_width": lambda v: isinstance(v, int) and not isinstance(v, bool) and 200 <= v <= 900,
}

DEFAULTS: dict[str, Any] = {
    "show_hidden": False,
    "browser_root": None,
    "sidebar_width": 300,
    "preview_open": True,
    "preview_width": 360,
}


class Settings:
    """Thread-safe: pywebview runs each JS call on its own thread."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._pinned: list[str] = []
        self._prefs: dict[str, Any] = dict(DEFAULTS)
        self._load()

    # --- persistence ---------------------------------------------------------

    def _load(self) -> None:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            log.warning("Ignoring unreadable settings file %s: %s", self._path, exc)
            return
        if not isinstance(raw, dict):
            return
        pinned = raw.get("pinned")
        if isinstance(pinned, list):
            self._pinned = [p for p in pinned if isinstance(p, str)]
        for key, valid in PREFERENCES.items():
            if key in raw and valid(raw[key]):
                self._prefs[key] = raw[key]

    def _save(self) -> None:
        # Caller holds the lock. Write-then-rename so a crash never leaves half a file.
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"pinned": self._pinned, **self._prefs}, indent=2), encoding="utf-8")
        try:
            replace_with_retry(tmp, self._path)
        except OSError:
            tmp.unlink(missing_ok=True)
            raise

    # --- reads ---------------------------------------------------------------

    def snapshot(self) -> dict:
        with self._lock:
            prefs = dict(self._prefs)
        return {**prefs, "pinned": self.pinned()}

    def pinned(self) -> list[dict]:
        with self._lock:
            paths = list(self._pinned)
        return _describe(paths)

    # --- writes --------------------------------------------------------------

    def set_preference(self, key: str, value: Any) -> None:
        valid = PREFERENCES.get(key)
        if valid is None:
            raise ValueError(f"Unknown preference: {key!r}")
        if not valid(value):
            raise ValueError(f"Invalid value for {key!r}: {value!r}")
        with self._lock:
            self._prefs[key] = value
            self._save()

    def pin(self, path: str, index: int | None = None) -> list[dict]:
        """Pin a folder, or move an already-pinned folder to ``index``."""
        key = path_key(path)
        with self._lock:
            existing = next((p for p in self._pinned if path_key(p) == key), None)
            if existing is None or index is not None:
                # Only new pins must exist; a pin whose folder went missing can still be moved.
                folder = existing if existing is not None else resolve_dir(path)
                pins = [p for p in self._pinned if path_key(p) != key]
                at = len(pins) if index is None else max(0, min(index, len(pins)))
                pins.insert(at, folder)
                self._pinned = pins
                self._save()
            paths = list(self._pinned)
        return _describe(paths)

    def unpin(self, path: str) -> list[dict]:
        key = path_key(path)
        with self._lock:
            self._pinned = [p for p in self._pinned if path_key(p) != key]
            self._save()
            paths = list(self._pinned)
        return _describe(paths)


def _describe(paths: list[str]) -> list[dict]:
    return [{"path": p, "name": display_name(p), "exists": os.path.isdir(p)} for p in paths]
