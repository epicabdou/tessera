"""Generate the Tessera logo files from one definition.

    .venv\\Scripts\\python scripts\\make_brand.py

Writes:
    frontend/public/favicon.svg        the mark: app header, About box, browser tab
    assets/icon.ico                    the Windows icon (16 to 256 px), used by build.py
    assets/installer/dialog.bmp        MSI welcome/finish side panel (493 x 312)
    assets/installer/banner.bmp        MSI top banner on the inner pages (493 x 58)

The mark is a "T" laid from five tesserae (mosaic tiles) on the aurora gradient tile;
at 32 px and up the rest of the 3 x 3 grid shows as faint empty tiles.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent

# --- the design, on a 32-unit canvas ----------------------------------------------------

APP_WORDMARK = "Tessera"
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
  <title>{APP_WORDMARK}</title>
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


def gradient(w: int, h: int) -> Image.Image:
    """The aurora gradient, same direction as the SVG (0 at top-left, 1 at bottom-right)."""
    yy, xx = np.mgrid[0:h, 0:w]
    t = (xx / max(w - 1, 1) + yy / max(h - 1, 1)) / 2
    rgb = np.zeros((h, w, 3))
    for (o0, c0), (o1, c1) in zip(GRADIENT, GRADIENT[1:]):
        m = (t >= o0) & (t <= o1)
        f = ((t - o0) / (o1 - o0))[m][:, None]
        rgb[m] = _hex(c0) * (1 - f) + _hex(c1) * f
    return Image.fromarray(np.dstack([rgb, np.full((h, w), 255.0)]).astype(np.uint8), "RGBA")


def draw_tiles(img: Image.Image, left: float, top: float, k: float, size_px: int) -> Image.Image:
    """Lay the tiles over img; (left, top) is the canvas origin in pixels, k pixels per canvas unit."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for x, y, a in cells(size_px):
        x0, y0 = left + x * k, top + y * k
        draw.rounded_rectangle((x0, y0, x0 + TILE * k - 1, y0 + TILE * k - 1), radius=TILE_RADIUS * k, fill=(255, 255, 255, round(255 * a)))
    return Image.alpha_composite(img, layer)


def render(size_px: int, supersample: int = 8) -> Image.Image:
    """The full mark (gradient tile + tesserae) at one size."""
    n = size_px * supersample
    img = gradient(n, n)
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, n - 1, n - 1), radius=RADIUS * n / UNIT, fill=255)
    img.putalpha(mask)
    img = draw_tiles(img, 0, 0, n / UNIT, size_px)
    return img.resize((size_px, size_px), Image.Resampling.LANCZOS)


# --- installer artwork (Windows Installer dialogs are always light: black text on white) ----

FONT = Path("C:/Windows/Fonts/seguisb.ttf")  # Segoe UI Semibold


def _font(px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.truetype(str(FONT), px) if FONT.is_file() else ImageFont.load_default(px)


def installer_dialog(w: int = 493, h: int = 312, panel: int = 164, ss: int = 4) -> Image.Image:
    """Welcome / finish background: the gradient panel on the left, white where the text goes."""
    img = Image.new("RGBA", (w * ss, h * ss), (255, 255, 255, 255))
    img.paste(gradient(panel * ss, h * ss), (0, 0))
    k = 3.0 * ss  # 3 px per canvas unit: the grid is ~58 px wide
    grid = (3 * TILE + 2 * GAP) * k
    img = draw_tiles(img, (panel * ss - grid) / 2 - ORIGIN * k, 92 * ss - ORIGIN * k, k, 256)
    draw = ImageDraw.Draw(img)
    draw.text((panel * ss / 2, (92 + 14) * ss + grid), APP_WORDMARK, font=_font(22 * ss), fill="white", anchor="mt")
    return img.resize((w, h), Image.Resampling.LANCZOS).convert("RGB")


def installer_banner(w: int = 493, h: int = 58, ss: int = 4) -> Image.Image:
    """Inner pages: white (the page title sits on the left), the mark on the right."""
    img = Image.new("RGBA", (w * ss, h * ss), (255, 255, 255, 255))
    mark = render(40, supersample=ss * 4).resize((40 * ss, 40 * ss), Image.Resampling.LANCZOS)
    img.alpha_composite(mark, ((w - 40 - 14) * ss, (h - 40) // 2 * ss))
    return img.resize((w, h), Image.Resampling.LANCZOS).convert("RGB")


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

    out = ROOT / "assets" / "installer"
    out.mkdir(exist_ok=True)
    for name, img in (("dialog.bmp", installer_dialog()), ("banner.bmp", installer_banner())):
        img.save(out / name, format="BMP")
        print(f"wrote {(out / name).relative_to(ROOT)} ({img.width} x {img.height})")


if __name__ == "__main__":
    main()
