"""Quick previews for the right-hand panel: what a file is and what's inside it."""

from __future__ import annotations

import base64
import codecs
import csv
import io
import os
from collections import Counter
from pathlib import Path

from .filesystem import display_name

MAX_TEXT_BYTES = 256 * 1024
MAX_TABLE_BYTES = 1024 * 1024
MAX_TABLE_ROWS = 300
MAX_TABLE_COLS = 40
MAX_IMAGE_EDGE = 1600
MAX_SVG_BYTES = 5 * 1024 * 1024
MAX_FOLDER_ENTRIES = 20000

IMAGE_EXTS = {"png", "jpg", "jpeg", "jfif", "gif", "bmp", "webp", "tif", "tiff", "ico"}
TABLE_EXTS = {"csv": ",", "tsv": "\t"}
TEXT_EXTS = {
    "txt", "md", "markdown", "rst", "log", "ini", "cfg", "conf", "toml", "yaml", "yml", "json", "jsonc",
    "xml", "html", "htm", "css", "scss", "less", "js", "mjs", "cjs", "jsx", "ts", "tsx", "py", "pyi",
    "ps1", "psm1", "bat", "cmd", "sh", "bash", "c", "h", "cpp", "hpp", "cs", "java", "kt", "go", "rs",
    "rb", "php", "sql", "r", "lua", "swift", "vue", "svelte", "env", "gitignore", "gitattributes",
    "editorconfig", "properties", "srt", "vtt", "tex",
}


def _created(st: os.stat_result) -> float:
    # st_birthtime is the creation time on Windows (3.12+); st_ctime is the old fallback.
    return getattr(st, "st_birthtime", st.st_ctime)


# --- text ---------------------------------------------------------------------


def _read_head(path: Path, limit: int) -> tuple[bytes, bool]:
    with open(path, "rb") as fh:
        data = fh.read(limit + 1)
    return data[:limit], len(data) > limit


def _decode(data: bytes) -> tuple[str, str]:
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16", errors="replace"), "UTF-16"
    if data.startswith(codecs.BOM_UTF8):
        return data[3:].decode("utf-8", errors="replace"), "UTF-8 (BOM)"
    try:
        return data.decode("utf-8"), "UTF-8"
    except UnicodeDecodeError as exc:
        # A multi-byte character cut off by the read limit isn't a reason to give up on UTF-8.
        if exc.start >= len(data) - 3:
            return data[: exc.start].decode("utf-8", errors="replace"), "UTF-8"
        return data.decode("cp1252", errors="replace"), "Windows-1252"


def looks_like_text(path: Path) -> bool:
    sample, _ = _read_head(path, 8192)
    if not sample:
        return True
    if sample.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE, codecs.BOM_UTF8)):
        return True
    if b"\x00" in sample:
        return False
    text, _ = _decode(sample)
    printable = sum(ch.isprintable() or ch in "\r\n\t" for ch in text)
    return printable / max(1, len(text)) > 0.95


def _text(path: Path) -> dict:
    data, truncated = _read_head(path, MAX_TEXT_BYTES)
    content, encoding = _decode(data)
    line_endings = "CRLF" if "\r\n" in content else "LF"
    content = content.replace("\r\n", "\n")
    return {
        "content": content,
        "truncated": truncated,
        "encoding": encoding,
        "line_endings": line_endings,
        "lines": content.count("\n") + 1,
    }


def _table(path: Path, default_delimiter: str) -> dict:
    data, truncated = _read_head(path, MAX_TABLE_BYTES)
    text, encoding = _decode(data)
    delimiter = default_delimiter
    if default_delimiter == ",":
        try:  # many locales use ";" in CSV files
            delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            pass
    rows: list[list[str]] = []
    for row in csv.reader(io.StringIO(text), delimiter=delimiter):
        rows.append(row[:MAX_TABLE_COLS])
        if len(rows) > MAX_TABLE_ROWS:
            break
    more = truncated or len(rows) > MAX_TABLE_ROWS
    rows = rows[:MAX_TABLE_ROWS]
    if truncated and rows:
        rows = rows[:-1]  # the last row may have been cut off mid-way
    return {
        "rows": rows,
        "columns": max((len(r) for r in rows), default=0),
        "truncated": more,
        "delimiter": delimiter,
        "encoding": encoding,
    }


# --- images -------------------------------------------------------------------


def _image(path: Path) -> dict:
    from PIL import Image, ImageOps

    with Image.open(path) as im:
        fmt, mode = im.format, im.mode
        width, height = im.size
        frames = getattr(im, "n_frames", 1)
        if im.getexif().get(0x0112, 1) in (5, 6, 7, 8):  # EXIF says the photo is turned 90°
            width, height = height, width
        im.draft("RGB", (MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))  # fast JPEG downscale while decoding
        shown = ImageOps.exif_transpose(im)
        shown.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))
        alpha = "A" in shown.getbands() or "transparency" in shown.info
        buf = io.BytesIO()
        if alpha:
            shown.convert("RGBA").save(buf, "PNG")
            mime = "image/png"
        else:
            shown.convert("RGB").save(buf, "JPEG", quality=85)
            mime = "image/jpeg"
    return {
        "data_url": f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode("ascii"),
        "width": width,
        "height": height,
        "format": fmt,
        "mode": mode,
        "frames": frames,
    }


def _svg(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) > MAX_SVG_BYTES:
        raise ValueError("SVG is too large to preview")
    # Shown through <img>, where SVG scripts never run.
    return {
        "data_url": "data:image/svg+xml;base64," + base64.b64encode(data).decode("ascii"),
        "width": None,
        "height": None,
        "format": "SVG",
        "mode": None,
        "frames": 1,
    }


# --- folders ------------------------------------------------------------------


def _folder(path: Path) -> dict:
    folders = files = total = 0
    kinds: Counter[str] = Counter()
    latest: tuple[float, str] | None = None
    truncated = False
    try:
        with os.scandir(path) as it:
            for n, entry in enumerate(it):
                if n >= MAX_FOLDER_ENTRIES:
                    truncated = True
                    break
                try:
                    st = entry.stat(follow_symlinks=False)
                    is_dir = entry.is_dir()
                except OSError:
                    continue
                if latest is None or st.st_mtime > latest[0]:
                    latest = (st.st_mtime, entry.name)
                if is_dir:
                    folders += 1
                else:
                    files += 1
                    total += st.st_size
                    kinds[Path(entry.name).suffix.lower().lstrip(".") or "(none)"] += 1
    except PermissionError:
        raise PermissionError(f"Access denied: {path}") from None
    return {
        "folders": folders,
        "files": files,
        "total_size": total,
        "types": [{"ext": ext, "count": count} for ext, count in kinds.most_common(8)],
        "latest": {"name": latest[1], "modified": latest[0]} if latest else None,
        "truncated": truncated,
    }


# --- entry point --------------------------------------------------------------


def preview_file(path: str) -> dict:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Not found: {target}")
    st = target.stat()
    is_dir = target.is_dir()
    ext = "" if is_dir else target.suffix.lower().lstrip(".")
    info: dict = {
        "path": str(target),
        "name": display_name(str(target)),
        "is_dir": is_dir,
        "size": None if is_dir else st.st_size,
        "modified": st.st_mtime,
        "created": _created(st),
        "ext": ext,
        "kind": "file",
    }
    if is_dir:
        info.update(kind="folder", folder=_folder(target))
        return info
    try:
        if ext == "pdf":
            from .pdf.common import pdf_info

            info.update(kind="pdf", pdf=pdf_info(target))
        elif ext in IMAGE_EXTS:
            info.update(kind="image", image=_image(target))
        elif ext == "svg":
            info.update(kind="image", image=_svg(target))
        elif ext in TABLE_EXTS:
            info.update(kind="table", table=_table(target, TABLE_EXTS[ext]))
        elif ext in TEXT_EXTS or looks_like_text(target):
            info.update(kind="text", text=_text(target))
    except Exception as exc:  # noqa: BLE001 - a broken file still gets its details shown
        info["kind"] = "file"
        info["error"] = f"Can't preview this file: {exc}"
    return info
