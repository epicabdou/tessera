"""Directory listing, well-known locations and shell actions for the file browser."""

from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
import time
from pathlib import Path

MAX_ENTRIES = 5000
MAX_TEXT_BYTES = 2 * 1024 * 1024

_HIDDEN_ATTRS = getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 0) | getattr(stat, "FILE_ATTRIBUTE_SYSTEM", 0)

# Windows Known Folder IDs; these follow OneDrive / group-policy redirection.
_KNOWN_FOLDERS = {
    "desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
    "documents": "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}",
    "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
}


# --- paths -------------------------------------------------------------------


def path_key(path: str) -> str:
    """Comparison key: two paths are the same folder if their keys match."""
    return os.path.normcase(os.path.abspath(path))


def display_name(path: str) -> str:
    """Last path component, or the drive (``C:``) / root for top-level paths."""
    p = Path(path)
    return p.name or p.anchor.rstrip("\\/") or str(p)


def breadcrumbs(path: str) -> list[dict]:
    p = Path(path)
    return [{"name": display_name(str(q)), "path": str(q)} for q in [*reversed(p.parents), p]]


def resolve_dir(path: str) -> str:
    """Normalise user input (``~``, ``%VARS%``, ``C:``) to an absolute existing folder."""
    raw = os.path.expandvars(os.path.expanduser(path.strip().strip('"')))
    if not raw:
        raise ValueError("Enter a folder path")
    if re.fullmatch(r"[A-Za-z]:", raw):
        raw += "\\"
    full = os.path.abspath(raw)
    if not os.path.isdir(full):
        raise FileNotFoundError(f"Folder not found: {full}")
    return full


# --- listing -----------------------------------------------------------------


def _natural_key(name: str) -> list:
    # "file2" sorts before "file10". re.split with a capture group alternates
    # str/int/str..., so positions always compare like with like.
    return [int(tok) if tok.isdigit() else tok.casefold() for tok in re.split(r"(\d+)", name)]


def _is_hidden(name: str, st: os.stat_result | None) -> bool:
    if name.startswith("."):
        return True
    return bool(st is not None and getattr(st, "st_file_attributes", 0) & _HIDDEN_ATTRS)


def list_dir(path: str, show_hidden: bool = False) -> dict:
    root = resolve_dir(path)
    entries: list[dict] = []
    truncated = False
    try:
        with os.scandir(root) as it:
            for entry in it:
                try:
                    st = entry.stat(follow_symlinks=False)
                except OSError:
                    st = None
                hidden = _is_hidden(entry.name, st)
                if hidden and not show_hidden:
                    continue
                if len(entries) >= MAX_ENTRIES:
                    truncated = True
                    break
                try:
                    is_dir = entry.is_dir()
                except OSError:
                    is_dir = False
                entries.append(
                    {
                        "name": entry.name,
                        "path": entry.path,
                        "is_dir": is_dir,
                        "size": None if is_dir or st is None else st.st_size,
                        "modified": None if st is None else st.st_mtime,
                        "hidden": hidden,
                        "ext": "" if is_dir else Path(entry.name).suffix.lower().lstrip("."),
                    }
                )
    except PermissionError:
        raise PermissionError(f"Access denied: {root}") from None

    entries.sort(key=lambda e: (not e["is_dir"], _natural_key(e["name"])))
    parent = os.path.dirname(root)
    return {
        "path": root,
        "name": display_name(root),
        "parent": parent if parent and path_key(parent) != path_key(root) else None,
        "crumbs": breadcrumbs(root),
        "entries": entries,
        "truncated": truncated,
    }


# --- locations ---------------------------------------------------------------


def known_folder(key: str) -> str | None:
    if sys.platform != "win32":
        return None
    import ctypes
    import uuid

    guid = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID(_KNOWN_FOLDERS[key]).bytes_le)
    out = ctypes.c_wchar_p()
    if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) != 0:
        return None
    try:
        return out.value
    finally:
        ctypes.windll.ole32.CoTaskMemFree(out)


def _drives() -> list[str]:
    if sys.platform != "win32":
        return ["/"]
    import ctypes
    import string

    # GetLogicalDrives is instant; probing each drive would block on offline network shares.
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    return [f"{letter}:\\" for i, letter in enumerate(string.ascii_uppercase) if mask & (1 << i)]


def quick_locations() -> list[dict]:
    home = str(Path.home())
    candidates = [("home", "Home", home)]
    for kind, label in (("desktop", "Desktop"), ("documents", "Documents"), ("downloads", "Downloads")):
        candidates.append((kind, label, known_folder(kind) or os.path.join(home, label)))

    seen: set[str] = set()
    locations = []
    for kind, label, path in candidates:
        if os.path.isdir(path) and path_key(path) not in seen:
            seen.add(path_key(path))
            locations.append({"kind": kind, "label": label, "path": path})
    for drive in _drives():
        locations.append({"kind": "drive", "label": display_name(drive) or drive, "path": drive})
    return locations


# --- safe writes -------------------------------------------------------------


def replace_with_retry(src: str | Path, dst: str | Path, attempts: int = 20, delay: float = 0.05) -> None:
    """os.replace, retried briefly: on Windows the rename fails while anything
    (an antivirus scan, a backup tool, another reader) has `dst` open."""
    for attempt in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay)


# --- shell actions -----------------------------------------------------------


def _existing(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Not found: {path}")
    return os.path.abspath(path)


def open_path(path: str) -> None:
    """Open a file with its default app, or a folder in the system file manager."""
    target = _existing(path)
    if sys.platform == "win32":
        os.startfile(target)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])


def reveal_path(path: str) -> None:
    """Show the item selected in its parent folder."""
    target = _existing(path)
    if sys.platform == "win32":
        subprocess.Popen(["explorer", f"/select,{target}"])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", target])
    else:
        subprocess.Popen(["xdg-open", os.path.dirname(target)])


def read_text_file(path: str, max_bytes: int = MAX_TEXT_BYTES) -> dict:
    file = Path(path)
    if not file.is_file():
        raise FileNotFoundError(f"Not a file: {file}")
    size = file.stat().st_size
    if size > max_bytes:
        raise ValueError(f"{file.name} is too large to open as text ({size:,} bytes; limit {max_bytes:,})")
    data = file.read_bytes()
    if b"\x00" in data[:8192]:
        raise ValueError(f"{file.name} looks like a binary file")
    return {"path": str(file), "name": file.name, "text": data.decode("utf-8-sig", errors="replace")}
