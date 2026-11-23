"""Read a PDF page's layout as headings, paragraphs, list items and tables.

Shared by PDF→Markdown and the built-in PDF→Word converter. Headings are guessed
from font size (relative to the body text) and boldness, and ranked by the
document's own heading sizes; tables come from pdfplumber's table finder and
their text is kept out of the paragraphs. Lines join into one paragraph only
where the line before was full (it wrapped), so short lines such as the rows
of a table without lines, or an address, stay apart.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

import pdfplumber

# Bullet glyphs, including Symbol/Wingdings private-use characters from Word and
# "(cid:N)", which is how unmapped glyphs (often bullets) come out of PDFs.
BULLET_RE = re.compile(r"^\s*([•●▪◦‣∙·\-–*]|o|\(cid:\d+\))\s+")
NUMBERED_RE = re.compile(r"^\s*((\d{1,3}|[a-zA-Z])[.)])\s+")
# A word that is only a list marker: a bullet (Symbol/Wingdings ones are private-use characters) or "1." / "a)".
MARKER_RE = re.compile(r"^([•●▪◦‣∙·\-–*o]|\(cid:\d+\)|[-]|(\d{1,3}|[a-zA-Z])[.)])$")


@dataclass
class Line:
    text: str
    size: float
    bold: bool
    x0: float
    top: float
    bottom: float
    x1: float = 0.0
    first_width: float = 0.0  # width of the first word: would it have fitted on the line above?


@dataclass
class Block:
    kind: str  # "heading" | "paragraph" | "bullet" | "numbered" | "table"
    text: str = ""
    level: int = 0
    rows: list[list[str]] = field(default_factory=list)
    top: float = 0.0


def _lines(words: list[dict]) -> list[Line]:
    rows: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if rows and abs(rows[-1][0]["top"] - w["top"]) <= max(2.0, w.get("size", 10) * 0.3):
            rows[-1].append(w)
        else:
            rows.append([w])
    lines = []
    for row in rows:
        row.sort(key=lambda w: w["x0"])
        text = " ".join(w["text"] for w in row)
        sizes = [w.get("size", 10) for w in row]
        bold = sum("bold" in (w.get("fontname") or "").lower() or "black" in (w.get("fontname") or "").lower() for w in row) > len(row) / 2
        lines.append(
            Line(
                text,
                round(median(sizes), 1),
                bold,
                row[0]["x0"],
                min(w["top"] for w in row),
                max(w["bottom"] for w in row),
                max(w["x1"] for w in row),
                row[0]["x1"] - row[0]["x0"],
            )
        )
    return lines


def body_size(lines: list[Line]) -> float:
    counts = Counter()
    for line in lines:
        counts[line.size] += len(line.text)
    return counts.most_common(1)[0][0] if counts else 10.0


def _sized_heading(line: Line, body: float) -> bool:
    """Set in a larger type than the body text, and shaped like a heading."""
    ratio = line.size / body if body else 1
    short = len(line.text) <= 120 and not line.text.endswith((".", ",", ";"))
    return ratio >= 1.3 or (ratio >= 1.12 and short)


def heading_sizes(lines: list[Line], body: float) -> list[float]:
    """The distinct sizes of the larger-type headings, largest first (sizes within 0.5 pt are one)."""
    sizes: list[float] = []
    for size in sorted({line.size for line in lines if _sized_heading(line, body)}, reverse=True):
        if all(abs(size - kept) > 0.5 for kept in sizes):
            sizes.append(size)
    return sizes


def _heading_level(line: Line, body: float, sizes: list[float]) -> int:
    """1-3 by rank among the document's heading sizes, so a title, its sections and their
    subsections stay apart; 4 (or the next free level) for bold headings in body-size type."""
    if _sized_heading(line, body):
        return min(3, 1 + sum(1 for s in sizes if s > line.size + 0.5))
    ratio = line.size / body if body else 1
    short = len(line.text) <= 120 and not line.text.endswith((".", ",", ";"))
    if line.bold and short and len(line.text.split()) <= 12 and ratio >= 0.98:
        return min(4, len(sizes) + 1)
    return 0


def _bullet_marks(page: "pdfplumber.page.Page", boxes: list[tuple]) -> list[tuple[float, float, float, float]]:
    """Small dots and squares drawn as shapes, which is how browsers (Chrome, Edge) print list bullets."""
    marks = []
    for shape in list(page.curves) + list(page.rects):
        w, h = shape["x1"] - shape["x0"], shape["bottom"] - shape["top"]
        if 1.5 <= w <= 8 and 1.5 <= h <= 8 and 0.6 <= w / h <= 1.6 and shape.get("fill") and not inside(shape, boxes):
            marks.append((shape["x0"], shape["top"], shape["x1"], shape["bottom"]))
    return marks


def _has_mark(line: Line, marks: list[tuple[float, float, float, float]]) -> bool:
    """A bullet shape just left of the line's first word, at its height."""
    for x0, top, x1, bottom in marks:
        middle = (top + bottom) / 2
        if line.x0 - 4 * line.size <= x1 <= line.x0 - 1 and line.top <= middle <= line.bottom:
            return True
    return False


def inside(word: dict, boxes: list[tuple]) -> bool:
    cx, cy = (word["x0"] + word["x1"]) / 2, (word["top"] + word["bottom"]) / 2
    return any(x0 <= cx <= x1 and top <= cy <= bottom for x0, top, x1, bottom in boxes)


def page_blocks(page: "pdfplumber.page.Page", body: float | None = None, sizes: list[float] | None = None) -> list[Block]:
    tables = page.find_tables()
    boxes = [t.bbox for t in tables]
    words = page.extract_words(extra_attrs=["size", "fontname"], use_text_flow=False, keep_blank_chars=False)
    lines = _lines([w for w in words if not inside(w, boxes)])
    body = body or body_size(lines)
    sizes = heading_sizes(lines, body) if sizes is None else sizes
    marks = _bullet_marks(page, boxes)
    right = max((line.x1 for line in lines), default=0.0)  # where full lines end

    blocks: list[Block] = []
    for t in tables:
        rows = [[(cell or "").replace("\n", " ").strip() for cell in row] for row in t.extract()]
        rows = [r for r in rows if any(r)]
        if rows:
            blocks.append(Block("table", rows=rows, top=t.bbox[1]))

    prev: Line | None = None
    for line in lines:
        level = _heading_level(line, body, sizes)
        bullet = BULLET_RE.match(line.text)
        numbered = NUMBERED_RE.match(line.text)
        if level:
            blocks.append(Block("heading", line.text, level, top=line.top))
        elif bullet:
            blocks.append(Block("bullet", line.text[bullet.end():], top=line.top))
        elif numbered:
            blocks.append(Block("numbered", line.text[numbered.end():], top=line.top))
        elif marks and _has_mark(line, marks):
            blocks.append(Block("bullet", line.text, top=line.top))
        else:
            last = blocks[-1] if blocks else None
            # The line above wrapped if this line's first word wouldn't have fitted after it.
            wrapped = prev is not None and (prev.text.endswith("-") or prev.x1 + 0.25 * line.size + line.first_width > right)
            continues = (
                last is not None
                and last.kind in ("paragraph", "bullet", "numbered")
                and prev is not None
                and wrapped
                and line.top - prev.bottom < line.size * 0.9
                and abs(line.size - prev.size) < 0.6
                and (last.kind == "paragraph" or line.x0 > prev.x0 + 2)
            )
            if continues:
                joiner = "" if last.text.endswith("-") and line.text[:1].islower() else " "
                last.text = (last.text[:-1] if joiner == "" else last.text) + joiner + line.text
            else:
                blocks.append(Block("paragraph", line.text, top=line.top))
        prev = line
    blocks.sort(key=lambda b: b.top)
    return blocks


def document_blocks(path: str, pages: list[int] | None = None, progress=None) -> list[list[Block]]:
    """Blocks for each page; body text size and heading sizes are measured across the document."""
    with pdfplumber.open(path) as pdf:
        indexes = pages if pages is not None else list(range(len(pdf.pages)))
        sample = []
        for i in indexes[:20]:
            sample += _lines(pdf.pages[i].extract_words(extra_attrs=["size", "fontname"]))
        body = body_size(sample)
        sizes = heading_sizes(sample, body)
        result = []
        for n, i in enumerate(indexes):
            result.append(page_blocks(pdf.pages[i], body, sizes))
            if progress:
                progress(n + 1, len(indexes), f"Reading page {i + 1}")
        return result


NO_TEXT = "{name} has no text to convert: its pages are pictures, as in a scan. Use OCR PDF first to recognise the text, then convert the result."


def require_text(path: str, pages: list[list[Block]]) -> list[list[Block]]:
    """`pages`, or a clear error when there's nothing in them (an image-only PDF)."""
    if not any(pages):
        raise ValueError(NO_TEXT.format(name=Path(path).name))
    return pages
