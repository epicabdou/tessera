"""Read a PDF page's layout as headings, paragraphs, list items and tables.

Shared by PDF→Markdown and the built-in PDF→Word converter. Headings are guessed
from font size (relative to the body text) and boldness; tables come from
pdfplumber's table finder and their text is kept out of the paragraphs.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from statistics import median

import pdfplumber

# Bullet glyphs, including Symbol/Wingdings private-use characters from Word and
# "(cid:N)", which is how unmapped glyphs (often bullets) come out of PDFs.
BULLET_RE = re.compile(r"^\s*([•●▪◦‣∙·\-–*]|o|\(cid:\d+\))\s+")
NUMBERED_RE = re.compile(r"^\s*((\d{1,3}|[a-zA-Z])[.)])\s+")


@dataclass
class Line:
    text: str
    size: float
    bold: bool
    x0: float
    top: float
    bottom: float


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
        lines.append(Line(text, round(median(sizes), 1), bold, row[0]["x0"], min(w["top"] for w in row), max(w["bottom"] for w in row)))
    return lines


def body_size(lines: list[Line]) -> float:
    counts = Counter()
    for line in lines:
        counts[line.size] += len(line.text)
    return counts.most_common(1)[0][0] if counts else 10.0


def _heading_level(line: Line, body: float) -> int:
    ratio = line.size / body if body else 1
    short = len(line.text) <= 120 and not line.text.endswith((".", ",", ";"))
    if ratio >= 1.6:
        return 1
    if ratio >= 1.3:
        return 2
    if ratio >= 1.12 and short:
        return 3
    if line.bold and short and len(line.text.split()) <= 12 and ratio >= 0.98:
        return 4
    return 0


def _inside(word: dict, boxes: list[tuple]) -> bool:
    cx, cy = (word["x0"] + word["x1"]) / 2, (word["top"] + word["bottom"]) / 2
    return any(x0 <= cx <= x1 and top <= cy <= bottom for x0, top, x1, bottom in boxes)


def page_blocks(page: "pdfplumber.page.Page", body: float | None = None) -> list[Block]:
    tables = page.find_tables()
    boxes = [t.bbox for t in tables]
    words = page.extract_words(extra_attrs=["size", "fontname"], use_text_flow=False, keep_blank_chars=False)
    lines = _lines([w for w in words if not _inside(w, boxes)])
    body = body or body_size(lines)

    blocks: list[Block] = []
    for t in tables:
        rows = [[(cell or "").replace("\n", " ").strip() for cell in row] for row in t.extract()]
        rows = [r for r in rows if any(r)]
        if rows:
            blocks.append(Block("table", rows=rows, top=t.bbox[1]))

    prev: Line | None = None
    for line in lines:
        level = _heading_level(line, body)
        bullet = BULLET_RE.match(line.text)
        numbered = NUMBERED_RE.match(line.text)
        if level:
            blocks.append(Block("heading", line.text, level, top=line.top))
        elif bullet:
            blocks.append(Block("bullet", line.text[bullet.end():], top=line.top))
        elif numbered:
            blocks.append(Block("numbered", line.text[numbered.end():], top=line.top))
        else:
            last = blocks[-1] if blocks else None
            continues = (
                last is not None
                and last.kind in ("paragraph", "bullet", "numbered")
                and prev is not None
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
    """Blocks for each page; body text size is measured across the whole document."""
    with pdfplumber.open(path) as pdf:
        indexes = pages if pages is not None else list(range(len(pdf.pages)))
        sample = []
        for i in indexes[:20]:
            sample += _lines(pdf.pages[i].extract_words(extra_attrs=["size", "fontname"]))
        body = body_size(sample)
        result = []
        for n, i in enumerate(indexes):
            result.append(page_blocks(pdf.pages[i], body))
            if progress:
                progress(n + 1, len(indexes), f"Reading page {i + 1}")
        return result
