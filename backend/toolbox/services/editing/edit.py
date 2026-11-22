"""Edit PDF: add text, images and shapes; cover or replace existing text.

Every object uses displayed-page coordinates: x / y from the top-left, in points.
"Replacing" existing text = a white-out box over the old line plus new text on top.
"""

from __future__ import annotations

from collections import defaultdict

import pdfplumber
from pypdf import PdfWriter
from pypdf.generic import ContentStream
from reportlab.pdfgen import canvas

from ..frompdf.structure import _lines
from ..pdf.common import open_reader, write_pdf
from .geometry import bake_rotation, visual_rect_to_user
from .overlay import font, hex_color, image_reader, load_image, stamp

KINDS = ("text", "image", "rect", "ellipse", "line", "highlight", "whiteout", "redact")


def text_lines(path: str, page: int) -> list[dict]:
    """Lines of existing text on a page (displayed coordinates), for "edit text"."""
    with pdfplumber.open(path) as pdf:
        if not 0 <= page < len(pdf.pages):
            raise ValueError(f"Page {page + 1} doesn't exist")
        p = pdf.pages[page]
        words = p.extract_words(extra_attrs=["size", "fontname"])
        out = []
        for line in _lines(words):
            names = [w.get("fontname", "") for w in words if line.top - 1 <= w["top"] <= line.top + 1]
            serif = any(k in n for n in names for k in ("Times", "Serif", "Roman", "Georgia", "Cambria"))
            mono = any(k in n for n in names for k in ("Courier", "Mono", "Consol"))
            right = max((w["x1"] for w in words if line.top - 1 <= w["top"] <= line.top + 1), default=line.x0)
            out.append(
                {
                    "text": line.text,
                    "x": round(line.x0, 2),
                    "y": round(line.top, 2),
                    "w": round(right - line.x0, 2),
                    "h": round(line.bottom - line.top, 2),
                    "size": line.size,
                    "bold": line.bold,
                    "family": "serif" if serif else "mono" if mono else "sans",
                }
            )
        return out


def _draw(c: canvas.Canvas, obj: dict, page_h: float) -> None:
    kind = obj["type"]
    x, y = float(obj.get("x", 0)), float(obj.get("y", 0))
    w, h = float(obj.get("w", 0)), float(obj.get("h", 0))
    opacity = float(obj.get("opacity", 1))
    c.saveState()
    c.setFillAlpha(opacity)
    c.setStrokeAlpha(opacity)
    bottom = page_h - y - h  # PDF y of the box's bottom edge
    if kind == "text":
        name = font(obj.get("family", "sans"), bool(obj.get("bold")), bool(obj.get("italic")))
        size = float(obj.get("size", 12))
        c.setFillColorRGB(*(hex_color(obj.get("color")) or (0, 0, 0)))
        c.setFont(name, size)
        leading = size * 1.2
        align = obj.get("align", "left")
        for n, line in enumerate(str(obj.get("text", "")).split("\n")):
            baseline = page_h - y - size * 0.88 - n * leading
            if align == "center":
                c.drawCentredString(x + w / 2, baseline, line)
            elif align == "right":
                c.drawRightString(x + w, baseline, line)
            else:
                c.drawString(x, baseline, line)
    elif kind == "image":
        c.drawImage(image_reader(load_image(obj["src"]), opacity), x, bottom, w, h, mask="auto", preserveAspectRatio=False)
    elif kind in ("rect", "ellipse", "highlight", "whiteout", "redact"):
        default_fill = {"highlight": "#ffeb3b", "whiteout": "#ffffff", "redact": "#000000"}.get(kind)
        fill = hex_color(obj.get("fill")) if kind in ("rect", "ellipse") else hex_color(obj.get("fill") or default_fill)
        if kind == "redact":
            c.setFillAlpha(1)
        stroke = hex_color(obj.get("stroke")) if kind in ("rect", "ellipse") else None
        if kind == "highlight":
            c.setFillAlpha(min(opacity, 0.4))
        if fill:
            c.setFillColorRGB(*fill)
        if stroke:
            c.setStrokeColorRGB(*stroke)
            c.setLineWidth(float(obj.get("width", 1.5)))
        if kind == "ellipse":
            c.ellipse(x, bottom, x + w, bottom + h, stroke=1 if stroke else 0, fill=1 if fill else 0)
        else:
            c.rect(x, bottom, w, h, stroke=1 if stroke else 0, fill=1 if fill else 0)
    elif kind == "line":
        c.setStrokeColorRGB(*(hex_color(obj.get("stroke")) or (0, 0, 0)))
        c.setLineWidth(float(obj.get("width", 1.5)))
        c.line(float(obj["x1"]), page_h - float(obj["y1"]), float(obj["x2"]), page_h - float(obj["y2"]))
    else:
        raise ValueError(f"Unknown object type: {kind!r}")
    c.restoreState()


_IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _mul(m1: tuple, m2: tuple) -> tuple:
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + b1 * c2, a1 * b2 + b1 * d2, c1 * a2 + d1 * c2, c1 * b2 + d1 * d2, e1 * a2 + f1 * c2 + e2, e1 * b2 + f1 * d2 + f2)


def remove_text(page, writer: PdfWriter, rects: list[tuple[float, float, float, float]]) -> int:
    """Delete text-showing operators that start inside any user-space rect (llx, lly, urx, ury).

    Tracks the graphics/text matrices to find where each Tj/TJ begins. Good for whole
    lines (what "edit text" and redaction select); text inside form XObjects isn't touched.
    Returns how many text operators were removed.
    """
    contents = page.get_contents()
    if contents is None or not rects:
        return 0
    stream = ContentStream(contents, writer)
    ctm, stack = _IDENTITY, []
    tm = tlm = _IDENTITY
    leading = rise = 0.0
    kept, removed = [], 0
    for operands, op in stream.operations:
        if op == b"q":
            stack.append(ctm)
        elif op == b"Q":
            ctm = stack.pop() if stack else _IDENTITY
        elif op == b"cm":
            ctm = _mul(tuple(float(v) for v in operands), ctm)
        elif op == b"BT":
            tm = tlm = _IDENTITY
        elif op == b"Tm":
            tm = tlm = tuple(float(v) for v in operands)
        elif op in (b"Td", b"TD"):
            tx, ty = (float(v) for v in operands)
            if op == b"TD":
                leading = -ty
            tm = tlm = _mul((1, 0, 0, 1, tx, ty), tlm)
        elif op == b"T*":
            tm = tlm = _mul((1, 0, 0, 1, 0, -leading), tlm)
        elif op == b"TL":
            leading = float(operands[0])
        elif op == b"Ts":
            rise = float(operands[0])
        if op in (b"Tj", b"TJ", b"'", b'"'):
            if op in (b"'", b'"'):
                tm = tlm = _mul((1, 0, 0, 1, 0, -leading), tlm)
            m = _mul(tm, ctm)
            x, y = m[4] + rise * m[2], m[5] + rise * m[3]
            if any(llx - 1 <= x <= urx + 1 and lly - 1 <= y <= ury + 1 for llx, lly, urx, ury in rects):
                removed += 1
                if op == b"'":
                    kept.append(([], b"T*"))  # keep the line move
                elif op == b'"':
                    kept += [([operands[0]], b"Tw"), ([operands[1]], b"Tc"), ([], b"T*")]
                continue
        kept.append((operands, op))
    if removed:
        stream.operations = kept
        page.replace_contents(stream)
    return removed


def apply_edits(path: str, output: str, objects: list[dict]) -> dict:
    """Burn the objects into the pages. Objects are drawn in list order (later = on top).

    White-out and redaction boxes with remove_text=True (and every "redact" box) also
    delete the original text underneath, so it can't be searched or copied any more.
    """
    if not objects:
        raise ValueError("Nothing to save: add or change something first")
    reader = open_reader(path)
    writer = PdfWriter(clone_from=reader)
    by_page: dict[int, list[dict]] = defaultdict(list)
    for obj in objects:
        if obj.get("type") not in KINDS:
            raise ValueError(f"Unknown object type: {obj.get('type')!r}")
        page = int(obj.get("page", 0))
        if not 0 <= page < len(writer.pages):
            raise ValueError(f"Page {page + 1} doesn't exist")
        by_page[page].append(obj)
    removed = 0
    for index, items in by_page.items():
        page = writer.pages[index]
        bake_rotation(page)  # displayed coordinates == user coordinates from here on
        cuts = [
            visual_rect_to_user(page, float(o["x"]), float(o["y"]), float(o["w"]), float(o["h"]))
            for o in items
            if o["type"] == "redact" or (o["type"] == "whiteout" and o.get("remove_text"))
        ]
        removed += remove_text(page, writer, cuts)
        stamp(page, lambda c, _w, h, items=items: [_draw(c, o, h) for o in items])
    result = write_pdf(writer, output)
    result["edited_pages"] = len(by_page)
    result["text_removed"] = removed
    return result
