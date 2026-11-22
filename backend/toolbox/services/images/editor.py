"""Photo editor (adjustments, filters, layers) and image watermarks, drawn with Pillow.

Coordinates are pixels of the image as shown in the editor: upright, after the editor's
own rotate/flip. Layers are drawn at full resolution when saving; previews use the same
code on a smaller copy, so what you see is what you get.
"""

from __future__ import annotations

import base64
import io
import math
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from ..progress import Progress
from . import basic
from . import imageio as iio

FONTS_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
# family -> (regular, bold, italic, bold italic)
FONT_FILES = {
    "sans": ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"),
    "serif": ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"),
    "mono": ("cour.ttf", "courbd.ttf", "couri.ttf", "courbi.ttf"),
    "display": ("impact.ttf", "impact.ttf", "impact.ttf", "impact.ttf"),
    "script": ("segoesc.ttf", "segoescb.ttf", "segoesc.ttf", "segoescb.ttf"),
    "hand": ("comic.ttf", "comicbd.ttf", "comici.ttf", "comicz.ttf"),
}
LINE_HEIGHT = 1.2  # matches the editor's CSS line-height

FILTERS = {
    "none": {},
    "vivid": {"saturation": 30, "contrast": 12},
    "warm": {"warmth": 35, "saturation": 8},
    "cool": {"warmth": -35},
    "mono": {"saturation": -100},
    "noir": {"saturation": -100, "contrast": 40, "vignette": 30},
    "sepia": {"sepia": 100},
    "vintage": {"sepia": 45, "fade": 30, "vignette": 30, "contrast": -8},
    "fade": {"fade": 45, "saturation": -15},
    "dramatic": {"contrast": 35, "saturation": -15, "vignette": 35, "shadows": -15},
}
ADJUSTMENTS = ("exposure", "brightness", "contrast", "saturation", "warmth", "tint", "highlights", "shadows", "hue", "sharpness", "vignette", "fade", "sepia")


@lru_cache(maxsize=64)
def font(family: str, size: int, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
    files = FONT_FILES.get(family, FONT_FILES["sans"])
    name = files[(1 if bold else 0) + (2 if italic else 0)]
    for candidate in (name, files[0], "arial.ttf"):
        path = FONTS_DIR / candidate
        if path.is_file():
            return ImageFont.truetype(str(path), max(1, int(size)))
    return ImageFont.load_default(max(1, int(size)))


def _rgba(color: str | None, opacity: float = 1.0) -> tuple[int, int, int, int]:
    r, g, b = ImageColor.getrgb(color or "#000000")[:3]
    return (r, g, b, round(255 * max(0.0, min(1.0, opacity))))


# --- adjustments & filters --------------------------------------------------------------


def _lut(fn) -> list[int]:
    return [max(0, min(255, round(fn(v / 255) * 255))) for v in range(256)]


def adjust(im: Image.Image, values: dict) -> Image.Image:
    """Apply a filter preset (values["filter"]) and then the sliders (-100..100; hue in degrees)."""
    preset = FILTERS.get(values.get("filter", "none"), {})
    v = {key: float(preset.get(key, 0)) + float(values.get(key, 0) or 0) for key in ADJUSTMENTS}
    alpha = im.getchannel("A") if iio.has_alpha(im) else None
    out = im.convert("RGB")

    if v["exposure"] or v["brightness"] or v["highlights"] or v["shadows"] or v["fade"]:
        gain = 2 ** (v["exposure"] / 100)
        lift = v["brightness"] / 100 * 0.35
        hi = v["highlights"] / 100 * 0.35
        lo = v["shadows"] / 100 * 0.35
        fade = v["fade"] / 100 * 0.25

        def curve(x: float) -> float:
            y = x * gain
            y += lift * (1 - abs(2 * y - 1)) if lift else 0
            y += hi * y * y * (1 - y) * 4 if hi else 0
            y += lo * (1 - y) * (1 - y) * y * 4 if lo else 0
            return fade + y * (1 - fade)

        out = out.point(_lut(curve) * 3)
    if v["contrast"]:
        out = ImageEnhance.Contrast(out).enhance(max(0.0, 1 + v["contrast"] / 100))
    if v["saturation"]:
        out = ImageEnhance.Color(out).enhance(max(0.0, 1 + v["saturation"] / 100))
    if v["warmth"] or v["tint"]:
        r, g, b = out.split()
        k = v["warmth"] / 100 * 0.18
        t = v["tint"] / 100 * 0.15
        r = r.point(lambda x: min(255, max(0, round(x * (1 + k)))))
        b = b.point(lambda x: min(255, max(0, round(x * (1 - k)))))
        g = g.point(lambda x: min(255, max(0, round(x * (1 - t)))))
        out = Image.merge("RGB", (r, g, b))
    if v["hue"]:
        hsv = np.asarray(out.convert("HSV")).copy()
        hsv[..., 0] = (hsv[..., 0].astype(np.int16) + round(v["hue"] / 360 * 255)) % 256
        out = Image.fromarray(hsv, "HSV").convert("RGB")
    if v["sepia"]:
        sep = ImageOps.colorize(ImageOps.grayscale(out), black="#2b1d0e", white="#fff4e0", mid="#a88a64")
        out = Image.blend(out, sep, min(1.0, v["sepia"] / 100))
    if v["sharpness"] > 0:
        out = out.filter(ImageFilter.UnsharpMask(radius=max(1.0, max(out.size) / 1200), percent=round(v["sharpness"] * 2), threshold=2))
    elif v["sharpness"] < 0:
        out = out.filter(ImageFilter.GaussianBlur(-v["sharpness"] / 100 * max(out.size) / 300))
    if v["vignette"]:
        out = _vignette(out, v["vignette"] / 100)
    if alpha is not None:
        out = out.convert("RGBA")
        out.putalpha(alpha)
    return out


def _vignette(im: Image.Image, amount: float) -> Image.Image:
    """amount > 0 darkens the corners, < 0 lightens them."""
    w, h = im.size
    y, x = np.ogrid[-1 : 1 : complex(256), -1 : 1 : complex(256)]
    weight = np.clip((np.sqrt(x * x + y * y) / math.sqrt(2) - 0.35) / 0.65, 0, 1) ** 1.6
    m = Image.fromarray((weight * 255).astype(np.uint8)).resize((w, h), Image.Resampling.BILINEAR)
    if amount > 0:
        shade = m.point(lambda v: round(255 - amount * v))
        return ImageChops.multiply(im, Image.merge("RGB", (shade, shade, shade)))
    glow = m.point(lambda v: round(-amount * 0.6 * v))
    return ImageChops.screen(im, Image.merge("RGB", (glow, glow, glow)))


# --- layers -----------------------------------------------------------------------------


def _image_source(src: str) -> Image.Image:
    if src.startswith("data:"):
        return Image.open(io.BytesIO(base64.b64decode(src.split(",", 1)[1]))).convert("RGBA")
    return iio.open_image(src).convert("RGBA")


def _points(layer: dict) -> list[tuple[float, float]]:
    x, y, w, h = (float(layer[k]) for k in ("x", "y", "w", "h"))
    return [(x + float(u) * w, y + float(v) * h) for u, v in layer.get("points", [])]


def draw_layers(im: Image.Image, layers: list[dict], k: float = 1.0) -> Image.Image:
    """Draw layers (in order, last on top). `k` scales coordinates (for previews)."""
    if not layers:
        return im
    base = im.convert("RGBA")
    for layer in layers:
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        opacity = float(layer.get("opacity", 1))
        kind = layer.get("type")
        x, y, w, h = (float(layer.get(key, 0)) * k for key in ("x", "y", "w", "h"))
        stroke = max(1, round(float(layer.get("width", 4)) * k))
        if kind == "text":
            size = max(1, round(float(layer.get("size", 48)) * k))
            f = font(layer.get("family", "sans"), size, bool(layer.get("bold")), bool(layer.get("italic")))
            line_h = size * LINE_HEIGHT
            ascent, descent = f.getmetrics()
            lead = (line_h - ascent - descent) / 2  # CSS centres the glyphs in each line box
            outline = round(float(layer.get("outline", 0)) * k)
            if layer.get("shadow"):
                off = max(1, round(size * 0.06))
                for i, line in enumerate(str(layer.get("text", "")).split("\n")):
                    draw.text((x + off, y + off + i * line_h + lead), line, font=f, fill=(0, 0, 0, round(150 * opacity)))
                overlay = overlay.filter(ImageFilter.GaussianBlur(max(1, size * 0.04)))
                draw = ImageDraw.Draw(overlay)
            for i, line in enumerate(str(layer.get("text", "")).split("\n")):
                lw = draw.textlength(line, font=f)
                align = layer.get("align", "left")
                lx = x + (w - lw if align == "right" else (w - lw) / 2 if align == "center" else 0)
                draw.text(
                    (lx, y + i * line_h + lead),
                    line,
                    font=f,
                    fill=_rgba(layer.get("color"), opacity),
                    stroke_width=outline,
                    stroke_fill=_rgba(layer.get("outline_color", "#000000"), opacity) if outline else None,
                )
        elif kind in ("rect", "ellipse"):
            box = (x, y, x + w, y + h)
            fill = _rgba(layer["fill"], opacity) if layer.get("fill") else None
            outline_c = _rgba(layer["stroke"], opacity) if layer.get("stroke") else None
            if kind == "rect":
                draw.rounded_rectangle(box, radius=float(layer.get("radius", 0)) * k, fill=fill, outline=outline_c, width=stroke if outline_c else 0)
            else:
                draw.ellipse(box, fill=fill, outline=outline_c, width=stroke if outline_c else 0)
        elif kind in ("line", "arrow"):
            (u0, v0), (u1, v1) = layer.get("points", [[0, 0], [1, 1]])[:2]
            p0, p1 = (x + u0 * w, y + v0 * h), (x + u1 * w, y + v1 * h)
            color = _rgba(layer.get("stroke", "#e53935"), opacity)
            draw.line((p0, p1), fill=color, width=stroke)
            if kind == "arrow":
                angle = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
                head = stroke * 3.2
                left = (p1[0] - head * math.cos(angle - 0.45), p1[1] - head * math.sin(angle - 0.45))
                right = (p1[0] - head * math.cos(angle + 0.45), p1[1] - head * math.sin(angle + 0.45))
                draw.polygon((p1, left, right), fill=color)
        elif kind == "draw":
            pts = [(px * k, py * k) for px, py in _points(layer)]
            color = _rgba(layer.get("stroke", "#e53935"), opacity)
            if len(pts) == 1:
                pts = pts * 2
            draw.line(pts, fill=color, width=stroke, joint="curve")
            r = stroke / 2
            for px, py in (pts[0], pts[-1]):
                draw.ellipse((px - r, py - r, px + r, py + r), fill=color)
        elif kind == "image" and layer.get("src"):
            pic = _image_source(layer["src"]).resize((max(1, round(w)), max(1, round(h))), Image.Resampling.LANCZOS)
            if opacity < 1:
                pic.putalpha(pic.getchannel("A").point(lambda a: round(a * opacity)))
            overlay.paste(pic, (round(x), round(y)), pic)
        else:
            continue
        rotation = float(layer.get("rotation", 0))
        if rotation:
            cx, cy = x + w / 2, y + h / 2
            overlay = overlay.rotate(-rotation, resample=Image.Resampling.BICUBIC, center=(cx, cy))
        base = Image.alpha_composite(base, overlay)
    return base if iio.has_alpha(im) else base.convert("RGB")


def render(path: str, edits: dict, max_side: int | None = None) -> Image.Image:
    """edits = {turns, flip_h, flip_v, adjust: {...}, layers: [...]}."""
    im = basic.transform(iio.open_image(path), edits.get("turns", 0), edits.get("flip_h", False), edits.get("flip_v", False))
    k = 1.0
    if max_side and max(im.size) > max_side:
        k = max_side / max(im.size)
        im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.Resampling.LANCZOS)
    im = adjust(im, edits.get("adjust", {}))
    if edits.get("include_layers", True):
        im = draw_layers(im, edits.get("layers", []), k)
    return im


def editor_preview(path: str, edits: dict, max_side: int = 1400) -> dict:
    """Adjusted image without layers (the editor draws those itself while you work)."""
    out = render(path, {**edits, "include_layers": False}, max_side)
    return {"data_url": iio.data_url(out), "width": out.width, "height": out.height}


def editor_save(path: str, output: str, edits: dict, options: dict) -> dict:
    out = render(path, edits)
    fmt = iio.format_for_ext(iio.ext_of(output)) if Path(output).suffix else iio.resolve_format(path, options.get("format", "keep"))
    if iio.has_alpha(out) and not iio.FORMATS[fmt][2] and options.get("format") == "keep":
        fmt = "png"
    return iio.save(out, output, fmt, quality=int(options.get("quality", 92)), keep_metadata=bool(options.get("keep_metadata", True)))


# --- watermark --------------------------------------------------------------------------

_POSITIONS = {
    "top-left": (0, 0),
    "top-center": (0.5, 0),
    "top-right": (1, 0),
    "middle-left": (0, 0.5),
    "middle-center": (0.5, 0.5),
    "middle-right": (1, 0.5),
    "bottom-left": (0, 1),
    "bottom-center": (0.5, 1),
    "bottom-right": (1, 1),
}


def _mark(im_size: tuple[int, int], options: dict) -> Image.Image:
    """The watermark itself (RGBA, already rotated and faded)."""
    w, h = im_size
    opacity = max(0.0, min(1.0, float(options.get("opacity", 0.4))))
    if options.get("kind", "text") == "image":
        if not options.get("image"):
            raise ValueError("Choose an image for the watermark")
        pic = _image_source(options["image"])
        target_w = max(1, round(w * float(options.get("scale", 0.25))))
        mark = pic.resize((target_w, max(1, round(pic.height * target_w / pic.width))), Image.Resampling.LANCZOS)
    else:
        text = str(options.get("text", "")).strip()
        if not text:
            raise ValueError("Enter the watermark text")
        size = max(6, round(min(w, h) * float(options.get("size", 8)) / 100))
        f = font(options.get("family", "sans"), size, bool(options.get("bold", True)), bool(options.get("italic", False)))
        lines = text.split("\n")
        tw = max(round(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(line, font=f)) for line in lines)
        th = round(size * LINE_HEIGHT * len(lines))
        outline = max(1, round(size * 0.04)) if options.get("outline") else 0
        mark = Image.new("RGBA", (tw + 2 * outline + 4, th + 2 * outline + 4), (0, 0, 0, 0))
        draw = ImageDraw.Draw(mark)
        for i, line in enumerate(lines):
            draw.text(
                (outline + 2, outline + 2 + i * size * LINE_HEIGHT + size * (LINE_HEIGHT - 1) / 2),
                line,
                font=f,
                fill=_rgba(options.get("color", "#ffffff")),
                stroke_width=outline,
                stroke_fill=_rgba("#000000") if outline else None,
            )
    rotation = float(options.get("rotation", 0))
    if rotation:
        mark = mark.rotate(rotation, resample=Image.Resampling.BICUBIC, expand=True)
    if opacity < 1:
        mark.putalpha(mark.getchannel("A").point(lambda a: round(a * opacity)))
    return mark


def watermark_image(im: Image.Image, options: dict) -> Image.Image:
    base = im.convert("RGBA")
    mark = _mark(base.size, options)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    position = options.get("position", "bottom-right")
    if position == "tile":
        gap = float(options.get("spacing", 60)) / 100
        sx, sy = round(mark.width * (1 + gap)), round(mark.height * (1 + gap))
        for row, top in enumerate(range(-mark.height, base.height + mark.height, max(1, sy))):
            shift = (sx // 2) if row % 2 else 0
            for left in range(-mark.width + shift, base.width + mark.width, max(1, sx)):
                layer.paste(mark, (left, top), mark)
    else:
        fx, fy = _POSITIONS.get(position, (1, 1))
        margin = round(min(base.size) * float(options.get("margin", 3)) / 100)
        left = round(margin + fx * (base.width - mark.width - 2 * margin))
        top = round(margin + fy * (base.height - mark.height - 2 * margin))
        layer.paste(mark, (left, top), mark)
    out = Image.alpha_composite(base, layer)
    return out if iio.has_alpha(im) else out.convert("RGB")


def watermark_preview(path: str, options: dict, max_side: int = 1400) -> dict:
    im = iio.open_image(path)
    if max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    out = watermark_image(im, options)
    return {"data_url": iio.data_url(out), "width": out.width, "height": out.height}


def watermark(paths: list[str], folder: str | None, options: dict, progress: Progress | None = None) -> list[dict]:
    def one(path: str) -> dict:
        fmt = iio.resolve_format(path, options.get("format", "keep"))
        out = watermark_image(iio.open_image(path), options)
        return iio.save(out, iio.output_path(path, folder, options.get("suffix", "_watermarked"), fmt), fmt, quality=int(options.get("quality", 92)), keep_metadata=bool(options.get("keep_metadata", True)))

    return basic._batch(paths, progress, "Watermarking", one)
