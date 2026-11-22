"""Merge, split, organize, rotate and crop."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import RectangleObject

from .common import format_ranges, open_reader, parse_ranges, split_plan, unique_path, write_pdf

MIN_PAGE_SIZE = 18.0  # points (1/4 inch); refuse crops smaller than this


def _check_rotation(degrees: int) -> int:
    if degrees % 90:
        raise ValueError(f"Rotation must be a multiple of 90°, got {degrees}")
    return degrees % 360


def _add_rotation(page, degrees: int) -> None:
    # page.rotate() would store e.g. 90 + 270 as 360; keep /Rotate within 0-270.
    page.rotation = (page.rotation + degrees) % 360


# --- merge ---------------------------------------------------------------------


def merge(items: list[dict], output: str, bookmarks: bool = False) -> dict:
    """items: [{"path": ..., "pages": "1-3, 5" | "" (all)}], in output order."""
    if not items:
        raise ValueError("Add at least one PDF to merge")
    writer = PdfWriter()
    for item in items:
        path = Path(item["path"])
        reader = open_reader(path)
        spec = (item.get("pages") or "").strip()
        count = len(reader.pages)
        indexes = [i for group in parse_ranges(spec, count) for i in group] if spec else range(count)
        start = len(writer.pages)
        for i in indexes:
            writer.add_page(reader.pages[i])
        if bookmarks and len(writer.pages) > start:
            writer.add_outline_item(title=path.stem, page_number=start)
    if not writer.pages:
        raise ValueError("The selected pages are empty")
    return write_pdf(writer, output)


# --- split ---------------------------------------------------------------------


def _split_name(stem: str, group: list[int], k: int) -> str:
    contiguous = group == list(range(group[0], group[-1] + 1))
    if len(group) == 1:
        return f"{stem}_p{group[0] + 1}.pdf"
    if contiguous:
        return f"{stem}_p{group[0] + 1}-{group[-1] + 1}.pdf"
    return f"{stem}_part{k}.pdf"


def split(path: str, output_dir: str, mode: str, value: str | int) -> dict:
    source = Path(path)
    reader = open_reader(source)
    groups = [g for g in split_plan(len(reader.pages), mode, value) if g]
    if not groups:
        raise ValueError("No pages selected")
    out_dir = Path(output_dir)
    files = []
    for k, group in enumerate(groups, 1):
        writer = PdfWriter()
        for i in group:
            writer.add_page(reader.pages[i])
        files.append(write_pdf(writer, unique_path(out_dir / _split_name(source.stem, group, k))))
    return {"files": files, "folder": str(out_dir)}


# --- organize ------------------------------------------------------------------


def organize(output: str, sources: dict[str, str], pages: list[dict]) -> dict:
    """Build a PDF from a page list.

    sources: {"doc": "C:/a.pdf", "ins1": "C:/b.pdf"}
    pages:   [{"source": "doc", "index": 2, "rotate": 90}, {"blank": True, "width": 595, "height": 842}, ...]
    """
    if not pages:
        raise ValueError("The document has no pages left")
    readers = {key: open_reader(p) for key, p in sources.items()}
    writer = PdfWriter()
    for n, item in enumerate(pages, 1):
        if item.get("blank"):
            writer.add_blank_page(float(item.get("width") or 595.28), float(item.get("height") or 841.89))
            continue
        reader = readers.get(item.get("source", ""))
        if reader is None:
            raise ValueError(f"Page {n} refers to an unknown file")
        index = int(item["index"])
        if not 0 <= index < len(reader.pages):
            raise ValueError(f"Page {n} refers to a page that doesn't exist")
        page = writer.add_page(reader.pages[index])  # pypdf copies, so duplicates stay independent
        rotate = _check_rotation(int(item.get("rotate", 0)))
        if rotate:
            _add_rotation(page, rotate)
    return write_pdf(writer, output)


# --- rotate --------------------------------------------------------------------


def rotate(path: str, output: str, rotations: list[int]) -> dict:
    """rotations: extra clockwise degrees per page (0 leaves a page alone)."""
    reader = open_reader(path)
    writer = PdfWriter(clone_from=reader)
    if len(rotations) != len(writer.pages):
        raise ValueError("Rotation list doesn't match the page count")
    for page, degrees in zip(writer.pages, rotations):
        degrees = _check_rotation(int(degrees))
        if degrees:
            _add_rotation(page, degrees)
    return write_pdf(writer, output)


# --- crop ----------------------------------------------------------------------


def crop(path: str, output: str, margins: dict, pages: list[int] | None = None) -> dict:
    """Trim margins (points, as the page is displayed) from each page, or from `pages`."""
    visual = [float(margins.get(side, 0) or 0) for side in ("top", "right", "bottom", "left")]
    if any(m < 0 for m in visual):
        raise ValueError("Margins can't be negative")
    reader = open_reader(path)
    writer = PdfWriter(clone_from=reader)
    targets = set(range(len(writer.pages))) if pages is None else set(pages)
    if not targets:
        raise ValueError("No pages selected")

    for i, page in enumerate(writer.pages):
        if i not in targets:
            continue
        # Map displayed sides back to the unrotated box: with /Rotate 90 the
        # displayed top is the page's left edge, and so on round the clock.
        steps = (page.rotation % 360) // 90
        top, right, bottom, left = (visual[(side + steps) % 4] for side in range(4))
        box = page.cropbox
        new = RectangleObject(
            [float(box.left) + left, float(box.bottom) + bottom, float(box.right) - right, float(box.top) - top]
        )
        if new.width < MIN_PAGE_SIZE or new.height < MIN_PAGE_SIZE:
            raise ValueError(f"The margins leave nothing of page {i + 1}")
        page.mediabox = new
        page.cropbox = new
    result = write_pdf(writer, output)
    result["cropped_pages"] = format_ranges(sorted(targets))
    return result
