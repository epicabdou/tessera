"""Generate the Tessera logo files from one definition.

    .venv\\Scripts\\python scripts\\make_brand.py

Writes:
    frontend/public/favicon.svg   the mark: app header, About box, browser tab
    assets/icon.ico               the Windows icon (16 to 256 px), used by build.py

The mark is a "T" laid from five tesserae (mosaic tiles) on the aurora gradient tile;
at 32 px and up the rest of the 3 x 3 grid shows as faint empty tiles.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent

# --- the design, on a 32-unit canvas ----------------------------------------------------

UNIT = 32
RADIUS = 8  # corner radius of the app tile
# Violet -> blue -> cyan, top-left to bottom-right: the same stops as --accent-grad in frontend/src/index.css.
GRADIENT = [(0.0, "#7c6cff"), (0.55, "#4f8bff"), (1.0, "#36c5ef")]

TILE = 5.6  # one tessera
GAP = 1.2
TILE_RADIUS = 1.3
ORIGIN = (UNIT - (3 * TILE + 2 * GAP)) / 2  # centres the 3 x 3 grid

# (column, row) -> opacity. The "T"; slight variation makes it read as a mosaic.
T_TILES = {(0, 0): 1.0, (1, 0): 1.0, (2, 0): 0.82, (1, 1): 0.94, (1, 2): 0.74}
GHOST_OPACITY = 0.16  # the empty cells of the grid, shown at 32 px and up
GHOST_MIN_SIZE = 32


def cells(size_px: int) -> list[tuple[float, float, float]]:
    """(x, y, opacity) of every tile to draw, in canvas units."""
    out = []
    for row in range(3):
        for col in range(3):
            alpha = T_TILES.get((col, row))
            if alpha is None:
                if size_px < GHOST_MIN_SIZE:
                    continue
                alpha = GHOST_OPACITY
            out.append((ORIGIN + col * (TILE + GAP), ORIGIN + row * (TILE + GAP), alpha))
    return out


# --- SVG ------------------------------------------------------------------------------------


def svg() -> str:
    stops = "\n".join(f'      <stop offset="{o:g}" stop-color="{c}"/>' for o, c in GRADIENT)
    tiles = "\n".join(
        f'  <rect x="{x:.2f}" y="{y:.2f}" width="{TILE}" height="{TILE}" rx="{TILE_RADIUS}" fill="#fff"'
        + (f' fill-opacity="{a:g}"' if a < 1 else "")
        + "/>"
        for x, y, a in cells(GHOST_MIN_SIZE)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {UNIT} {UNIT}" fill="none">
  <title>Tessera</title>
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="{UNIT}" y2="{UNIT}" gradientUnits="userSpaceOnUse">
{stops}
    </linearGradient>
  </defs>
  <rect width="{UNIT}" height="{UNIT}" rx="{RADIUS}" fill="url(#g)"/>
{tiles}
</svg>
"""


# --- raster -----------------------------------------------------------------------------


def _hex(c: str) -> np.ndarray:
    return np.array([int(c[i : i + 2], 16) for i in (1, 3, 5)], dtype=np.float64)


def render(size_px: int, supersample: int = 8) -> Image.Image:
    n = size_px * supersample
    k = n / UNIT  # pixels per canvas unit

    # Diagonal gradient, same direction as the SVG (0 at top-left, 1 at bottom-right).
    yy, xx = np.mgrid[0:n, 0:n]
    t = (xx + yy) / (2 * (n - 1))
    rgb = np.zeros((n, n, 3))
    for (o0, c0), (o1, c1) in zip(GRADIENT, GRADIENT[1:]):
        m = (t >= o0) & (t <= o1)
        f = ((t - o0) / (o1 - o0))[m][:, None]
        rgb[m] = _hex(c0) * (1 - f) + _hex(c1) * f
    img = Image.fromarray(np.dstack([rgb, np.full((n, n), 255.0)]).astype(np.uint8), "RGBA")

    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, n - 1, n - 1), radius=RADIUS * k, fill=255)
    img.putalpha(mask)

    layer = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for x, y, a in cells(size_px):
        draw.rounded_rectangle((x * k, y * k, (x + TILE) * k - 1, (y + TILE) * k - 1), radius=TILE_RADIUS * k, fill=(255, 255, 255, round(255 * a)))
    img = Image.alpha_composite(img, layer)
    return img.resize((size_px, size_px), Image.Resampling.LANCZOS)


ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]


def main() -> None:
    favicon = ROOT / "frontend" / "public" / "favicon.svg"
    favicon.write_text(svg(), encoding="utf-8")
    print(f"wrote {favicon.relative_to(ROOT)}")

    icon = ROOT / "assets" / "icon.ico"
    icon.parent.mkdir(exist_ok=True)
    images = [render(s) for s in ICO_SIZES]
    images[-1].save(icon, format="ICO", sizes=[(s, s) for s in ICO_SIZES], append_images=images[:-1])
    print(f"wrote {icon.relative_to(ROOT)} ({', '.join(map(str, ICO_SIZES))} px)")


if __name__ == "__main__":
    main()
