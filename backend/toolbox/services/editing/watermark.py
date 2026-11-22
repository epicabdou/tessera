"""Text or image watermarks: centred, in a corner, or tiled; over or under the page content."""

from __future__ import annotations

import math

from pypdf import PdfWriter
from reportlab.pdfbase.pdfmetrics import stringWidth

from ..pdf.common import open_reader, parse_selection, write_pdf
from .overlay import font, hex_color, image_reader, load_image, stamp

POSITIONS = {f"{v}-{h}" for v in ("top", "middle", "bottom") for h in ("left", "center", "right")} | {"tile"}
MARGIN = 36.0


def _anchor(position: str, w: float, h: float, item_w: float, item_h: float) -> tuple[float, float]:
    """Centre point for the item at `position` on a w x h page (PDF coords)."""
    v, hz = position.split("-")
    x = {"left": MARGIN + item_w / 2, "center": w / 2, "right": w - MARGIN - item_w / 2}[hz]
    y = {"top": h - MARGIN - item_h / 2, "middle": h / 2, "bottom": MARGIN + item_h / 2}[v]
    return x, y


def watermark(path: str, output: str, options: dict) -> dict:
    """options:
    kind        "text" | "image"
    text, family ("sans"|"serif"|"mono"), bold, size (pt), color "#RRGGBB"
    image       file path or data: URL; scale = width as a fraction of the page width
    opacity     0..1      rotation  degrees (counter-clockwise)
    position    "middle-center", "top-left", … or "tile"
    layer       "over" | "under"     pages  "1-3, 5" (blank = all)
    """
    kind = options.get("kind", "text")
    position = options.get("position", "middle-center")
    if position not in POSITIONS:
        raise ValueError(f"Unknown position: {position!r}")
    opacity = float(options.get("opacity", 0.3))
    if not 0.02 <= opacity <= 1:
        raise ValueError("Opacity must be between 2% and 100%")
    rotation = float(options.get("rotation", 45 if kind == "text" else 0))
    reader = open_reader(path)
    count = len(reader.pages)
    spec = (options.get("pages") or "").strip()
    targets = parse_selection(spec, count) if spec else list(range(count))

    if kind == "text":
        text = str(options.get("text") or "").strip()
        if not text:
            raise ValueError("Enter the watermark text")
        name = font(options.get("family", "sans"), bool(options.get("bold", True)), False)
        size = float(options.get("size", 60))
        rgb = hex_color(options.get("color", "#888888"))
        item_w, item_h = stringWidth(text, name, size), size

        def draw_item(c):
            c.setFont(name, size)
            c.setFillColorRGB(*rgb)
            c.drawCentredString(0, -size * 0.35, text)

        image = None
    elif kind == "image":
        image = load_image(str(options.get("image") or ""))
        reader_img = image_reader(image, opacity)
        scale = float(options.get("scale", 0.4))
        if not 0.02 <= scale <= 1.5:
            raise ValueError("Image size must be 2–150% of the page width")
        item_w = item_h = 0.0  # set per page
    else:
        raise ValueError(f"Unknown watermark kind: {kind!r}")

    writer = PdfWriter(clone_from=reader)
    for index in targets:

        def draw(c, w, h):
            nonlocal item_w, item_h
            if image is not None:
                item_w = w * scale
                item_h = item_w * image.height / image.width

            def one(cx, cy):
                c.saveState()
                c.translate(cx, cy)
                c.rotate(rotation)
                if image is not None:
                    c.drawImage(reader_img, -item_w / 2, -item_h / 2, item_w, item_h, mask="auto")
                else:
                    c.setFillAlpha(opacity)
                    draw_item(c)
                c.restoreState()

            if position == "tile":
                # Rotated bounding box decides the spacing so tiles don't overlap.
                rad = math.radians(rotation)
                bw = abs(item_w * math.cos(rad)) + abs(item_h * math.sin(rad))
                bh = abs(item_w * math.sin(rad)) + abs(item_h * math.cos(rad))
                step_x, step_y = bw + 48, bh + 48
                row = 0
                y = step_y / 2
                while y < h + step_y:
                    x = step_x / 2 + (step_x / 2 if row % 2 else 0)
                    while x < w + step_x:
                        one(x, y)
                        x += step_x
                    y += step_y
                    row += 1
            else:
                one(*_anchor(position, w, h, item_w, item_h))

        stamp(writer.pages[index], draw, under=options.get("layer") == "under")
    result = write_pdf(writer, output)
    result["watermarked_pages"] = len(targets)
    return result
