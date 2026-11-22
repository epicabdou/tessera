"""Lay pages out on sheets before printing: page selection, n-up, booklets, crop marks."""

from __future__ import annotations

from pypdf import PageObject, PdfWriter, Transformation
from pypdf.generic import DecodedStreamObject, NameObject

from ..editing.geometry import bake_rotation
from ..pdf.common import POINTS_PER_MM, open_reader, parse_ranges, write_pdf

SHEETS = {  # points, portrait
    "a4": (595.28, 841.89),
    "a3": (841.89, 1190.55),
    "a5": (419.53, 595.28),
    "letter": (612.0, 792.0),
    "legal": (612.0, 1008.0),
    "tabloid": (792.0, 1224.0),
}
GRIDS = {1: (1, 1), 2: (2, 1), 4: (2, 2), 6: (2, 3), 9: (3, 3), 16: (4, 4)}
MARK_LEN, MARK_GAP = 14.0, 4.0  # crop mark length and gap from the trim, points


def _select(count: int, spec: str) -> list[int]:
    spec = (spec or "").strip()
    return [i for group in parse_ranges(spec, count) for i in group] if spec else list(range(count))


def _upright(reader, index: int) -> PageObject:
    """A copy of the page with its rotation baked in (so layout math is simple)."""
    tmp = PdfWriter()
    page = tmp.add_page(reader.pages[index])
    bake_rotation(page)
    return page


def _place(sheet: PageObject, page: PageObject, x: float, y: float, w: float, h: float) -> None:
    """Scale `page` to fit the w x h cell at (x, y), centred."""
    box = page.cropbox
    pw, ph = float(box.width), float(box.height)
    s = min(w / pw, h / ph)
    ox, oy = x + (w - pw * s) / 2, y + (h - ph * s) / 2
    t = Transformation().translate(-float(box.left), -float(box.bottom)).scale(s).translate(ox, oy)
    sheet.merge_transformed_page(page, t)


def _marks(sheet: PageObject, x: float, y: float, w: float, h: float, bleed: float) -> None:
    """Crop marks just outside the trim box (x, y, w, h), clear of the bleed."""
    g = MARK_GAP + bleed
    ops = ["q 0.25 w 0 G"]
    for cx, cy, dx, dy in ((x, y, -1, -1), (x + w, y, 1, -1), (x, y + h, -1, 1), (x + w, y + h, 1, 1)):
        ops.append(f"{cx + dx * g:.2f} {cy:.2f} m {cx + dx * (g + MARK_LEN):.2f} {cy:.2f} l S")
        ops.append(f"{cx:.2f} {cy + dy * g:.2f} m {cx:.2f} {cy + dy * (g + MARK_LEN):.2f} l S")
    ops.append("Q")
    stream = DecodedStreamObject()
    stream.set_data(" ".join(ops).encode())
    existing = sheet.get_contents()
    data = (existing.get_data() if existing is not None else b"") + b"\n" + stream.get_data()
    merged = DecodedStreamObject()
    merged.set_data(data)
    sheet[NameObject("/Contents")] = merged


def booklet_order(count: int) -> list[tuple[int | None, int | None]]:
    """Saddle-stitch order: (left, right) page pairs, front and back of each sheet in turn.
    None = blank padding (booklets need a multiple of 4 pages)."""
    total = (count + 3) // 4 * 4
    idx = lambda n: n if n < count else None  # noqa: E731
    pairs = []
    for s in range(total // 4):
        pairs.append((idx(total - 1 - 2 * s), idx(2 * s)))  # front
        pairs.append((idx(2 * s + 1), idx(total - 2 - 2 * s)))  # back
    return pairs


def impose(path: str, output: str, options: dict) -> dict:
    """options:
    pages "1-4, 7" (blank = all)   reverse bool
    layout "normal" | "nup" | "booklet"     per_sheet 2|4|6|9|16 (nup)
    sheet "auto" | "a4" | "letter" | …      orientation "auto" | "portrait" | "landscape"
    marks bool   bleed_mm float   frame bool (n-up cell borders)
    """
    reader = open_reader(path)
    indexes = _select(len(reader.pages), options.get("pages", ""))
    if options.get("reverse"):
        indexes.reverse()
    layout = options.get("layout", "normal")
    sheet_name = options.get("sheet", "auto")
    if sheet_name != "auto" and sheet_name not in SHEETS:
        raise ValueError(f"Unknown paper size: {sheet_name!r}")
    bleed = float(options.get("bleed_mm", 0)) * POINTS_PER_MM
    marks = bool(options.get("marks"))
    margin = (MARK_GAP + MARK_LEN + bleed + 6) if marks else 0.0
    writer = PdfWriter()

    if layout == "normal":
        for i in indexes:
            page = _upright(reader, i)
            if not marks and sheet_name == "auto":
                writer.add_page(page)
                continue
            box = page.cropbox
            w, h = float(box.width), float(box.height)
            if sheet_name == "auto":
                sw, sh = w + 2 * margin, h + 2 * margin
            else:
                sw, sh = SHEETS[sheet_name]
                if (w > h) != (sw > sh):
                    sw, sh = sh, sw
            sheet = PageObject.create_blank_page(width=sw, height=sh)
            avail_w, avail_h = sw - 2 * margin, sh - 2 * margin
            s = 1.0 if sheet_name == "auto" else min(avail_w / w, avail_h / h)
            x, y = (sw - w * s) / 2, (sh - h * s) / 2
            _place(sheet, page, x, y, w * s, h * s)
            if marks:
                _marks(sheet, x, y, w * s, h * s, bleed)
            writer.add_page(sheet)

    elif layout == "nup":
        per = int(options.get("per_sheet", 2))
        if per not in GRIDS:
            raise ValueError(f"Pages per sheet must be one of {sorted(GRIDS)}")
        cols, rows = GRIDS[per]
        first = _upright(reader, indexes[0])
        pw, ph = float(first.cropbox.width), float(first.cropbox.height)
        sw, sh = SHEETS[sheet_name] if sheet_name != "auto" else (pw, ph) if pw < ph else (ph, pw)
        sw, sh = min(sw, sh), max(sw, sh)  # portrait base
        orientation = options.get("orientation", "auto")
        # 2 and 6 per sheet suit landscape sheets for portrait pages; pick what wastes least.
        landscape = orientation == "landscape" or (orientation == "auto" and (cols > rows) == (ph >= pw))
        if landscape:
            sw, sh = sh, sw
            if cols < rows:
                cols, rows = rows, cols
        elif cols > rows:
            cols, rows = rows, cols
        gap = 12.0
        cw, ch = (sw - gap * (cols + 1)) / cols, (sh - gap * (rows + 1)) / rows
        for start in range(0, len(indexes), per):
            sheet = PageObject.create_blank_page(width=sw, height=sh)
            for k, i in enumerate(indexes[start : start + per]):
                col, row = k % cols, k // cols
                x = gap + col * (cw + gap)
                y = sh - gap - (row + 1) * ch - row * gap
                _place(sheet, _upright(reader, i), x, y, cw, ch)
                if options.get("frame"):
                    _marks_frame(sheet, x, y, cw, ch)
            writer.add_page(sheet)

    elif layout == "booklet":
        first = _upright(reader, indexes[0])
        pw, ph = float(first.cropbox.width), float(first.cropbox.height)
        if sheet_name == "auto":
            sw, sh = 2 * pw, ph  # two pages side by side at full size
        else:
            short, long_ = sorted(SHEETS[sheet_name])
            sw, sh = long_, short  # landscape sheet, folded in half
        half = sw / 2
        for left, right in booklet_order(len(indexes)):
            sheet = PageObject.create_blank_page(width=sw, height=sh)
            for slot, n in ((0, left), (1, right)):
                if n is not None:
                    _place(sheet, _upright(reader, indexes[n]), slot * half, 0, half, sh)
            writer.add_page(sheet)
    else:
        raise ValueError(f"Unknown layout: {layout!r}")

    result = write_pdf(writer, output)
    result["sheets"] = len(writer.pages)
    result["source_pages"] = len(indexes)
    return result


def _marks_frame(sheet: PageObject, x: float, y: float, w: float, h: float) -> None:
    stream_ops = f"q 0.4 w 0.6 G {x:.2f} {y:.2f} {w:.2f} {h:.2f} re S Q"
    existing = sheet.get_contents()
    merged = DecodedStreamObject()
    merged.set_data((existing.get_data() if existing is not None else b"") + b"\n" + stream_ops.encode())
    sheet[NameObject("/Contents")] = merged
