"""Stamp page numbers onto pages using the built-in Helvetica font (no font files needed)."""

from __future__ import annotations

import re

from pypdf import PageObject, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from .common import open_reader, write_pdf

POSITIONS = {f"{v}-{h}" for v in ("top", "bottom") for h in ("left", "center", "right")}
FONT_RESOURCE = "/TbxHelv"
CAP_HEIGHT = 0.718  # Helvetica cap height, in em

# Helvetica advance widths (1/1000 em) for ASCII 32-126, from the standard AFM.
_ASCII_WIDTHS = [
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,  # space - /
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556,                                # 0-9
    278, 278, 584, 584, 584, 556, 1015,                                              # : - @
    667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833,                 # A-M
    722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611,                 # N-Z
    278, 278, 278, 469, 556, 333,                                                    # [ - `
    556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833,                 # a-m
    556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500,                 # n-z
    334, 260, 334, 584,                                                              # { - ~
]


def text_width(text: str, size: float) -> float:
    units = sum(_ASCII_WIDTHS[ord(c) - 32] if 32 <= ord(c) <= 126 else 556 for c in text)
    return units * size / 1000


def _pdf_string(text: str) -> bytes:
    raw = text.encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _rgb(color: str) -> tuple[float, float, float]:
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", color or "")
    if not m:
        raise ValueError(f"Colour must look like #333333, got {color!r}")
    v = m.group(1)
    return tuple(int(v[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def format_number(template: str, number: int, total: int) -> str:
    return template.replace("{n}", str(number)).replace("{total}", str(total))


def _overlay(text: str, x: float, y: float, size: float, rgb: tuple[float, float, float], box) -> PageObject:
    overlay = PageObject.create_blank_page(width=float(box.right), height=float(box.top))
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
        }
    )
    overlay[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject(FONT_RESOURCE): font})}
    )
    r, g, b = rgb
    content = (
        f"q {r:.3f} {g:.3f} {b:.3f} rg BT {FONT_RESOURCE} {size:.2f} Tf {x:.2f} {y:.2f} Td (".encode()
        + _pdf_string(text)
        + b") Tj ET Q"
    )
    stream = DecodedStreamObject()
    stream.set_data(content)
    overlay[NameObject("/Contents")] = stream
    return overlay


def add_page_numbers(path: str, output: str, options: dict) -> dict:
    """options:
    position     "bottom-center" (top|bottom - left|center|right)
    template     "Page {n} of {total}"
    start        first number to print (default 1)
    first_page   1-based page to start numbering on (default 1)
    last_page    1-based last page to number (default: last page)
    font_size    points (default 11)
    margin       distance from the page edge, points (default 28)
    color        "#RRGGBB" (default "#222222")
    mirror       swap left/right on even pages, for double-sided printing
    """
    position = options.get("position", "bottom-center")
    if position not in POSITIONS:
        raise ValueError(f"Unknown position: {position!r}")
    template = options.get("template") or "{n}"
    if "{n}" not in template:
        raise ValueError("The format needs {n} where the number goes")
    size = float(options.get("font_size", 11))
    margin = float(options.get("margin", 28))
    if not 4 <= size <= 96:
        raise ValueError("Font size must be between 4 and 96 pt")
    if margin < 0:
        raise ValueError("Margin can't be negative")
    rgb = _rgb(options.get("color", "#222222"))
    mirror = bool(options.get("mirror", False))

    reader = open_reader(path)
    writer = PdfWriter(clone_from=reader)
    count = len(writer.pages)
    first = int(options.get("first_page") or 1)
    last = int(options.get("last_page") or count)
    if not 1 <= first <= last <= count:
        raise ValueError(f"Pages to number must be within 1–{count}")
    start = int(options.get("start", 1))
    total = start + (last - first)

    vertical, horizontal = position.split("-")
    for i in range(first - 1, last):
        page = writer.pages[i]
        if page.rotation % 360:
            # Bake the rotation into the content so "bottom" means the displayed bottom.
            page.transfer_rotation_to_content()
        box = page.cropbox
        number = start + (i - (first - 1))
        text = format_number(template, number, total)
        width = text_width(text, size)

        side = horizontal
        if mirror and (i + 1) % 2 == 0 and side != "center":
            side = "left" if side == "right" else "right"
        if side == "left":
            x = float(box.left) + margin
        elif side == "right":
            x = float(box.right) - margin - width
        else:
            x = (float(box.left) + float(box.right) - width) / 2
        y = float(box.top) - margin - size * CAP_HEIGHT if vertical == "top" else float(box.bottom) + margin

        page.merge_page(_overlay(text, x, y, size, rgb, box))
    return write_pdf(writer, output)
