"""Draw on top of (or under) PDF pages with ReportLab, then merge with pypdf.

Fonts: the Windows TrueType fonts (Arial, Times New Roman, Courier New) are embedded
when available, so accented and non-Latin text works; otherwise the PDF base fonts.
"""

from __future__ import annotations

import base64
import io
import os
import re
from pathlib import Path
from typing import Callable

from PIL import Image
from pypdf import PageObject, PdfReader, Transformation
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .geometry import bake_rotation

FAMILIES = {
    "sans": (("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"), ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique")),
    "serif": (("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"), ("Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic")),
    "mono": (("cour.ttf", "courbd.ttf", "couri.ttf", "courbi.ttf"), ("Courier", "Courier-Bold", "Courier-Oblique", "Courier-BoldOblique")),
}
_registered: dict[str, str] = {}


def font(family: str = "sans", bold: bool = False, italic: bool = False) -> str:
    files, base = FAMILIES.get(family, FAMILIES["sans"])
    index = (2 if italic else 0) + (1 if bold else 0)
    name = f"Tbx-{family}-{index}"
    if name in _registered:
        return _registered[name]
    path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / files[index]
    try:
        pdfmetrics.registerFont(TTFont(name, str(path)))
        _registered[name] = name
    except Exception:  # noqa: BLE001 - no such font file: use the built-in one
        _registered[name] = base[index]
    return _registered[name]


def hex_color(value: str | None) -> tuple[float, float, float] | None:
    if not value:
        return None
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", value)
    if not m:
        raise ValueError(f"Colour must look like #RRGGBB, got {value!r}")
    v = m.group(1)
    return tuple(int(v[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def load_image(source: str) -> Image.Image:
    """A file path or a data: URL (e.g. a signature drawn in the UI)."""
    if source.startswith("data:"):
        _, b64 = source.split(",", 1)
        return Image.open(io.BytesIO(base64.b64decode(b64)))
    return Image.open(source)


def image_reader(img: Image.Image, opacity: float = 1.0) -> ImageReader:
    """ReportLab image, with transparency (and extra opacity) preserved via a soft mask."""
    has_alpha = "A" in img.getbands() or "transparency" in img.info
    if has_alpha or opacity < 1:
        rgba = img.convert("RGBA")
        if opacity < 1:
            alpha = rgba.getchannel("A").point(lambda a: int(a * opacity))
            rgba.putalpha(alpha)
        return ImageReader(rgba)
    return ImageReader(img.convert("RGB"))


def overlay_page(width: float, height: float, draw: Callable[[canvas.Canvas], None]) -> PageObject:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    draw(c)
    c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


def stamp(page: PageObject, draw: Callable[[canvas.Canvas, float, float], None], under: bool = False) -> None:
    """Draw on `page` in its displayed orientation; `draw(c, width, height)` uses PDF coords (origin bottom-left)."""
    bake_rotation(page)
    box = page.cropbox
    w, h = float(box.width), float(box.height)
    layer = overlay_page(w, h, lambda c: draw(c, w, h))
    page.merge_transformed_page(layer, Transformation().translate(float(box.left), float(box.bottom)), over=not under)
