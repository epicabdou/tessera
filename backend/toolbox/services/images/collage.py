"""Photo collage: several photos arranged on one canvas.

Layouts:

- ``grid``: rows and columns of equal cells. Photos are cropped to fill their cell, or fitted
  inside it. A last row with fewer photos is spread across the full width.
- ``mosaic``: rows of photos at their own shape (nothing is cropped), each row scaled to the
  full width. The height follows from the photos.
- ``featured``: the first photo large on one side, the others in a grid beside it.

Spacing, the outer margin and the corner radius are fractions of the canvas width, so a small
preview looks exactly like the full-size result.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageOps

from . import imageio as iio

MIN_PHOTOS = 2
MAX_PHOTOS = 40
MAX_WIDTH = 10000
MAX_PIXELS = 80_000_000

# Canvas shapes, as width / height.
ASPECTS = {
    "square": 1.0,
    "portrait": 4 / 5,
    "landscape": 3 / 2,
    "wide": 16 / 9,
    "story": 9 / 16,
    "a4": 210 / 297,
    "a4-landscape": 297 / 210,
}
LAYOUTS = ("grid", "mosaic", "featured")
SIDES = ("left", "right", "top", "bottom")

Progress = Callable[[int, int, str], None]


@dataclass(frozen=True)
class Cell:
    x: float
    y: float
    w: float
    h: float

    def box(self) -> tuple[int, int, int, int]:
        """Whole pixels, rounding each edge (so neighbouring cells keep an even gap)."""
        return round(self.x), round(self.y), round(self.x + self.w), round(self.y + self.h)


def _num(value, default: float, lo: float, hi: float) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(n):
        return default
    return max(lo, min(hi, n))


def normalize(options: dict) -> dict:
    """Options from the UI, checked and with every default filled in."""
    o = options or {}
    layout = o.get("layout", "grid")
    if layout not in LAYOUTS:
        raise ValueError(f"Unknown layout: {layout!r}")
    aspect = o.get("aspect", "square")
    if isinstance(aspect, str):
        if aspect not in ASPECTS:
            raise ValueError(f"Unknown canvas shape: {aspect!r}")
        ratio = ASPECTS[aspect]
    else:
        ratio = _num(aspect, 1.0, 0.2, 5.0)
    side = o.get("side", "left")
    background = o.get("background", "#ffffff") or "#ffffff"
    if background != "transparent":
        ImageColor.getrgb(background)  # raises ValueError for a bad colour
    fmt = o.get("format", "jpg")
    if fmt not in iio.FORMATS:
        raise ValueError(f"Unknown image format: {fmt!r}")
    return {
        "layout": layout,
        "ratio": ratio,
        "width": int(_num(o.get("width"), 2400, 200, MAX_WIDTH)),
        "spacing": _num(o.get("spacing"), 0.01, 0, 0.1),
        "margin": _num(o.get("margin"), 0.02, 0, 0.2),
        "radius": _num(o.get("radius"), 0, 0, 0.1),
        "fit": "fit" if o.get("fit") == "fit" else "fill",
        "columns": int(_num(o.get("columns"), 0, 0, 12)),
        "per_row": _num(o.get("per_row"), 3, 1, 8),
        "side": side if side in SIDES else "left",
        "share": _num(o.get("share"), 0.6, 0.3, 0.85),
        "background": background,
        "format": fmt,
        "quality": int(_num(o.get("quality"), 90, 10, 100)),
    }


# --- layout (pure geometry, in canvas pixels) ---------------------------------------------------


def _grid(n: int, x: float, y: float, w: float, h: float, gap: float, aspects: list[float], columns: int = 0) -> list[Cell]:
    """``n`` cells in rows and columns over the box; a short last row spreads to full width."""
    if n <= 0:
        return []
    shapes = (aspects + [1.0] * n)[:n]
    if columns <= 0:
        # The column count whose cells best match the photos placed in them (least cropping),
        # counting the wider cells of a short last row.
        best = None
        for c in range(1, n + 1):
            r = math.ceil(n / c)
            cell_h = (h - (r - 1) * gap) / r
            last = n - c * (r - 1)
            widths = [(w - (c - 1) * gap) / c] * (n - last) + [(w - (last - 1) * gap) / last] * last
            if cell_h <= 0 or min(widths) <= 0:
                continue
            cost = sum(abs(math.log((cw / cell_h) / a)) for cw, a in zip(widths, shapes)) / n
            if best is None or cost < best[0] - 1e-9:
                best = (cost, c)
        columns = best[1] if best else 1
    columns = min(columns, n)
    rows = math.ceil(n / columns)
    cell_h = (h - (rows - 1) * gap) / rows
    cells = []
    for r in range(rows):
        k = columns if r < rows - 1 else n - columns * (rows - 1)
        cell_w = (w - (k - 1) * gap) / k
        for c in range(k):
            cells.append(Cell(x + c * (cell_w + gap), y + r * (cell_h + gap), cell_w, cell_h))
    return cells


def _mosaic(aspects: list[float], x: float, y: float, w: float, gap: float, per_row: float) -> tuple[list[Cell], float]:
    """Justified rows: (cells, total height). Each full row is exactly ``w`` wide."""
    median = sorted(aspects)[len(aspects) // 2]
    target_h = (w - (per_row - 1) * gap) / (per_row * median)
    rows: list[list[int]] = []
    current: list[int] = []
    for i, a in enumerate(aspects):
        width_with = sum(aspects[j] for j in current + [i]) * target_h + len(current) * gap
        if current and width_with > w:
            width_without = sum(aspects[j] for j in current) * target_h + (len(current) - 1) * gap
            if abs(w - width_without) <= abs(width_with - w):
                rows.append(current)
                current = [i]
                continue
            rows.append(current + [i])
            current = []
            continue
        current.append(i)
    if current:
        rows.append(current)

    cells: list[Cell | None] = [None] * len(aspects)
    top = y
    for n, row in enumerate(rows):
        total = sum(aspects[i] for i in row)
        row_h = (w - (len(row) - 1) * gap) / total
        last = n == len(rows) - 1
        left = x
        if last and row_h > target_h:
            # A short last row isn't blown up: it keeps the usual height and is centred.
            row_h = target_h
            left = x + (w - (total * row_h + (len(row) - 1) * gap)) / 2
        for i in row:
            cell_w = aspects[i] * row_h
            cells[i] = Cell(left, top, cell_w, row_h)
            left += cell_w + gap
        top += row_h + (0 if last else gap)
    return [c for c in cells if c is not None], top - y


def plan(sizes: list[tuple[int, int]], options: dict, width: int | None = None) -> tuple[int, int, list[Cell]]:
    """Canvas size and one cell per photo, in order. ``width`` overrides the option (previews)."""
    o = normalize(options)
    n = len(sizes)
    if n < MIN_PHOTOS:
        raise ValueError(f"Add at least {MIN_PHOTOS} photos")
    if n > MAX_PHOTOS:
        raise ValueError(f"A collage can have up to {MAX_PHOTOS} photos")
    W = int(width or o["width"])
    margin = o["margin"] * W
    gap = o["spacing"] * W
    inner_w = W - 2 * margin
    aspects = [max(0.05, min(20.0, w / h)) for w, h in sizes]

    if o["layout"] == "mosaic":
        cells, inner_h = _mosaic(aspects, margin, margin, inner_w, gap, o["per_row"])
        H = round(inner_h + 2 * margin)
    else:
        H = round(W / o["ratio"])
        inner_h = H - 2 * margin
        if inner_w <= 0 or inner_h <= 0:
            raise ValueError("The margin leaves no room for the photos")
        if o["layout"] == "grid":
            cells = _grid(n, margin, margin, inner_w, inner_h, gap, aspects, o["columns"])
        else:
            share, side = o["share"], o["side"]
            if side in ("left", "right"):
                big_w = (inner_w - gap) * share
                rest_w = inner_w - gap - big_w
                big_x = margin if side == "left" else margin + rest_w + gap
                rest_x = margin + big_w + gap if side == "left" else margin
                big = Cell(big_x, margin, big_w, inner_h)
                rest = _grid(n - 1, rest_x, margin, rest_w, inner_h, gap, aspects[1:])
            else:
                big_h = (inner_h - gap) * share
                rest_h = inner_h - gap - big_h
                big_y = margin if side == "top" else margin + rest_h + gap
                rest_y = margin + big_h + gap if side == "top" else margin
                big = Cell(margin, big_y, inner_w, big_h)
                rest = _grid(n - 1, margin, rest_y, inner_w, rest_h, gap, aspects[1:])
            cells = [big, *rest]
    if W * H > MAX_PIXELS:
        raise ValueError(f"That collage would be {W} × {H} px, too big to make. Choose a smaller width.")
    return W, H, cells


# --- drawing ------------------------------------------------------------------------------------


def _upright_size(path: str) -> tuple[int, int]:
    file = iio.check_input(path)
    with Image.open(file) as im:
        w, h = im.size
        orientation = im.getexif().get(0x0112, 1)
    return (h, w) if orientation in (5, 6, 7, 8) else (w, h)


def _photo(path: str, w: int, h: int, fit: str) -> Image.Image:
    """The photo, upright, cropped to fill (or fitted inside) a w × h cell."""
    with Image.open(iio.check_input(path)) as im:
        im.draft("RGB", (w * 2, h * 2))  # big JPEGs decode at a smaller size, fast
        im.load()
        up = ImageOps.exif_transpose(im)
    up = up.convert("RGBA" if iio.has_alpha(up) else "RGB")
    if fit == "fill":
        return ImageOps.fit(up, (w, h), Image.Resampling.LANCZOS)
    return ImageOps.contain(up, (w, h), Image.Resampling.LANCZOS)


def _rounded(im: Image.Image, radius: int) -> Image.Image:
    if radius <= 0:
        return im
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=radius, fill=255)
    if "A" in im.getbands():
        mask = Image.composite(im.getchannel("A"), Image.new("L", im.size, 0), mask)
    out = im.convert("RGBA")
    out.putalpha(mask)
    return out


def render(paths: list[str], options: dict, width: int | None = None, progress: Progress | None = None) -> Image.Image:
    o = normalize(options)
    sizes = [_upright_size(p) for p in paths]
    W, H, cells = plan(sizes, options, width)
    transparent = o["background"] == "transparent"
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0)) if transparent else Image.new("RGB", (W, H), o["background"])
    radius = round(o["radius"] * W)
    fit = "fill" if o["layout"] == "mosaic" else o["fit"]
    for i, (path, cell) in enumerate(zip(paths, cells)):
        if progress:
            progress(i, len(paths), f"Placing {Path(path).name}")
        x0, y0, x1, y1 = cell.box()
        w, h = max(1, x1 - x0), max(1, y1 - y0)
        pic = _rounded(_photo(path, w, h, fit), radius)
        px, py = x0 + (w - pic.width) // 2, y0 + (h - pic.height) // 2
        if "A" in pic.getbands():
            canvas.paste(pic, (px, py), pic)
        else:
            canvas.paste(pic, (px, py))
    if progress:
        progress(len(paths), len(paths), "Done")
    return canvas


def preview(paths: list[str], options: dict, max_side: int = 1000) -> dict:
    """A small render of the collage, plus the full-size result's pixel size."""
    sizes = [_upright_size(p) for p in paths]
    full_w, full_h, _cells = plan(sizes, options)
    k = min(1.0, max_side / max(full_w, full_h))
    im = render(paths, options, max(50, round(full_w * k)))
    return {"data_url": iio.data_url(im), "width": im.width, "height": im.height, "full_width": full_w, "full_height": full_h}


def save(paths: list[str], output: str, options: dict, progress: Progress | None = None) -> dict:
    o = normalize(options)
    im = render(paths, options, progress=progress)
    fmt = iio.format_for_ext(iio.ext_of(output)) if Path(output).suffix else o["format"]
    background = "#ffffff" if o["background"] == "transparent" else o["background"]
    result = iio.save(im, output, fmt, quality=o["quality"], keep_metadata=False, background=background)
    result["photos"] = len(paths)
    return result
