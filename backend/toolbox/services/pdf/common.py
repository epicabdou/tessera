"""Opening, describing and saving PDFs; page-range parsing shared by the tools."""

from __future__ import annotations

import os
import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import DependencyError, PdfReadError

from ..filesystem import replace_with_retry

POINTS_PER_MM = 72 / 25.4


# --- reading -----------------------------------------------------------------


def open_reader(path: str | Path) -> PdfReader:
    file = Path(path)
    if not file.is_file():
        raise FileNotFoundError(f"Not a file: {file}")
    try:
        reader = PdfReader(file)
    except (PdfReadError, ValueError, OSError) as exc:
        raise ValueError(f"{file.name} isn't a readable PDF ({exc})") from None
    if reader.is_encrypted:
        try:
            unlocked = reader.decrypt("")
        except DependencyError:
            raise ValueError(f"{file.name} uses AES encryption, which needs the 'cryptography' package") from None
        if not unlocked:
            raise ValueError(f"{file.name} is password-protected")
    return reader


def visual_size(page) -> tuple[float, float]:
    """Width and height as displayed, i.e. after the page's /Rotate."""
    box = page.cropbox
    w, h = float(box.width), float(box.height)
    return (h, w) if page.rotation % 180 else (w, h)


def pdf_info(path: str | Path) -> dict:
    file = Path(path)
    reader = open_reader(file)
    pages = []
    for page in reader.pages:
        w, h = visual_size(page)
        pages.append({"width": round(w, 2), "height": round(h, 2), "rotation": page.rotation % 360})
    stat = file.stat()
    title = None
    try:
        title = reader.metadata.title if reader.metadata else None
    except Exception:  # noqa: BLE001 - broken metadata shouldn't block opening the file
        pass
    return {
        "path": str(file),
        "name": file.name,
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "page_count": len(pages),
        "pages": pages,
        "title": title or None,
    }


# --- page ranges ---------------------------------------------------------------

_RANGE_RE = re.compile(r"^(\d*)\s*[-–]\s*(\d*)$")


def parse_ranges(spec: str, page_count: int) -> list[list[int]]:
    """Parse "1-3, 5, 8-" into groups of 0-based indexes, one group per comma part.

    Also accepts "all", "odd", "even", open-ended ranges ("8-", "-4").
    """
    parts = [p.strip() for p in re.split(r"[,;]", spec or "") if p.strip()]
    if not parts:
        raise ValueError("Enter pages, for example 1-3, 5, 8-")
    groups: list[list[int]] = []
    for part in parts:
        low = part.lower()
        if low == "all":
            groups.append(list(range(page_count)))
            continue
        if low in ("odd", "even"):
            groups.append(list(range(0 if low == "odd" else 1, page_count, 2)))
            continue
        if part.isdigit():
            start = end = int(part)
        else:
            m = _RANGE_RE.match(part)
            if not m:
                raise ValueError(f"Can't read “{part}”. Use pages like 1-3, 5, 8-")
            start = int(m.group(1)) if m.group(1) else 1
            end = int(m.group(2)) if m.group(2) else page_count
        if start < 1 or end > page_count:
            raise ValueError(f"“{part}” is outside 1–{page_count}")
        if start > end:
            raise ValueError(f"“{part}” runs backwards")
        groups.append(list(range(start - 1, end)))
    return groups


def parse_selection(spec: str, page_count: int) -> list[int]:
    """Flatten ranges into a sorted, de-duplicated list of page indexes."""
    return sorted({i for group in parse_ranges(spec, page_count) for i in group})


def format_ranges(indexes: list[int]) -> str:
    """[0,1,2,4] -> "1-3, 5" (1-based, compact)."""
    out: list[str] = []
    ordered = sorted(set(indexes))
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1] == ordered[j] + 1:
            j += 1
        a, b = ordered[i] + 1, ordered[j] + 1
        out.append(str(a) if a == b else f"{a}-{b}")
        i = j + 1
    return ", ".join(out)


SPLIT_MODES = ("ranges", "every", "extract", "extract_each")


def split_plan(page_count: int, mode: str, value: str | int) -> list[list[int]]:
    """Which pages go into which output file."""
    if mode == "ranges":
        return parse_ranges(str(value), page_count)
    if mode == "every":
        try:
            n = int(value)
        except (TypeError, ValueError):
            raise ValueError("Enter a number of pages per file") from None
        if n < 1:
            raise ValueError("Pages per file must be at least 1")
        return [list(range(i, min(i + n, page_count))) for i in range(0, page_count, n)]
    if mode == "extract":
        return [parse_selection(str(value), page_count)]
    if mode == "extract_each":
        return [[i] for i in parse_selection(str(value), page_count)]
    raise ValueError(f"Unknown split mode: {mode!r}")


# --- writing -------------------------------------------------------------------


def unique_path(path: str | Path) -> Path:
    """`path`, or "name (2).pdf", "name (3).pdf"… if it already exists."""
    target = Path(path)
    n = 2
    while target.exists():
        target = target.with_name(f"{Path(path).stem} ({n}){Path(path).suffix}")
        n += 1
    return target


def suggest_output(path: str | Path, suffix: str) -> str:
    source = Path(path)
    return str(unique_path(source.with_name(f"{source.stem}_{suffix}.pdf")))


def write_pdf(writer: PdfWriter, output: str | Path) -> dict:
    """Write via a temp file + rename, so a failure never leaves half a PDF (and an
    input file can safely be overwritten by its own output)."""
    out = Path(output)
    if out.suffix.lower() != ".pdf":
        out = out.with_name(out.name + ".pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".{out.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "wb") as fh:
            writer.write(fh)
        replace_with_retry(tmp, out)
    except PermissionError:
        tmp.unlink(missing_ok=True)
        raise PermissionError(f"Couldn't save {out.name}. Is it open in another program?") from None
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return {"path": str(out), "name": out.name, "size": out.stat().st_size, "page_count": len(writer.pages)}
