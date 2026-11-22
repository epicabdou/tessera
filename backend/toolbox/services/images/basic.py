"""Format & size (compress, resize, convert) and framing (crop, rotate) for images."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageDraw, ImageSequence

from ..pdf.common import unique_path
from ..progress import Progress
from . import imageio as iio

RESAMPLE = {
    "lanczos": Image.Resampling.LANCZOS,
    "bicubic": Image.Resampling.BICUBIC,
    "bilinear": Image.Resampling.BILINEAR,
    "nearest": Image.Resampling.NEAREST,
}


def _batch(paths: list[str], progress: Progress | None, verb: str, work: Callable[[str], dict]) -> list[dict]:
    if not paths:
        raise ValueError("Add at least one image")
    results = []
    for n, path in enumerate(paths):
        if progress:
            progress(n, len(paths), f"{verb} {Path(path).name}")
        results.append(work(path))
    if progress:
        progress(len(paths), len(paths), "Done")
    return results


def _encode_options(options: dict) -> dict:
    return {
        "quality": int(options.get("quality", 85)),
        "keep_metadata": bool(options.get("keep_metadata", True)),
        "background": options.get("background") or "#ffffff",
    }


# --- compress ---------------------------------------------------------------------------


def _compressed(path: str, options: dict) -> tuple[bytes, str, tuple[int, int]]:
    fmt = iio.resolve_format(path, options.get("format", "keep"))
    im = iio.open_image(path)
    max_side = int(options.get("max_side") or 0)
    if max_side and max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    colors = int(options.get("png_colors") or 0)
    if fmt == "png" and 2 <= colors <= 256:
        # Lossy PNG: a palette of `colors`, with dithering. Usually 60-80% smaller.
        im = im.convert("RGBA").quantize(colors=colors, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.FLOYDSTEINBERG)
    data = iio.encode(im, fmt, **_encode_options({**options, "keep_metadata": options.get("keep_metadata", False)}))
    return data, fmt, im.size


def estimate(path: str, options: dict) -> dict:
    """Size after compression, computed in memory (nothing is written)."""
    before = Path(path).stat().st_size
    data, fmt, size = _compressed(path, options)
    return {"before": before, "after": len(data), "format": fmt, "width": size[0], "height": size[1]}


def compress(paths: list[str], folder: str | None, options: dict, progress: Progress | None = None) -> list[dict]:
    def one(path: str) -> dict:
        before = Path(path).stat().st_size
        data, fmt, _size = _compressed(path, options)
        out = iio.output_path(path, folder, options.get("suffix", "_compressed"), fmt)
        same_format = iio.resolve_format(path, "keep") == fmt
        if len(data) >= before and same_format and not options.get("max_side"):
            # Can't do better than the original: keep its bytes rather than grow the file.
            shutil.copyfile(path, out)
            result = iio.saved(out)
            result["kept_original"] = True
        else:
            result = iio.write_bytes(data, out)
        result.update(before=before, after=result["size"])
        return result

    return _batch(paths, progress, "Compressing", one)


# --- resize -----------------------------------------------------------------------------


def target_size(width: int, height: int, options: dict) -> tuple[tuple[int, int], tuple[int, int] | None]:
    """(scaled size, crop size or None) for the resize options. Crop is for "cover"."""
    mode = options.get("mode", "percent")
    if mode == "percent":
        k = float(options.get("percent", 100)) / 100
        size = (width * k, height * k)
        crop = None
    elif mode == "longest":
        k = float(options.get("longest", max(width, height))) / max(width, height)
        size = (width * k, height * k)
        crop = None
    elif mode == "pixels":
        w = int(options.get("width") or 0)
        h = int(options.get("height") or 0)
        if not w and not h:
            raise ValueError("Enter a width or a height")
        crop = None
        if not options.get("keep_aspect", True) and w and h:
            size = (w, h)
        elif w and h:
            fit = options.get("fit", "contain")
            k = max(w / width, h / height) if fit == "cover" else min(w / width, h / height)
            size = (width * k, height * k)
            if fit == "cover":
                crop = (w, h)
        else:
            k = w / width if w else h / height
            size = (width * k, height * k)
    else:
        raise ValueError(f"Unknown resize mode: {mode!r}")
    scaled = (max(1, round(size[0])), max(1, round(size[1])))
    if options.get("no_enlarge") and (scaled[0] > width or scaled[1] > height):
        return (width, height), None
    if scaled[0] * scaled[1] > 200_000_000:
        raise ValueError("That would be over 200 megapixels; choose a smaller size")
    return scaled, crop


def resize_image(im: Image.Image, options: dict) -> Image.Image:
    (w, h), crop = target_size(im.width, im.height, options)
    if (w, h) != im.size:
        im = im.resize((w, h), RESAMPLE.get(options.get("resample", "lanczos"), Image.Resampling.LANCZOS))
    if crop:
        cw, ch = min(crop[0], w), min(crop[1], h)
        left, top = (w - cw) // 2, (h - ch) // 2
        im = im.crop((left, top, left + cw, top + ch))
    return im


def resize(paths: list[str], folder: str | None, options: dict, progress: Progress | None = None) -> list[dict]:
    def one(path: str) -> dict:
        fmt = iio.resolve_format(path, options.get("format", "keep"))
        im = resize_image(iio.open_image(path), options)
        out = iio.output_path(path, folder, options.get("suffix", "_resized"), fmt)
        return iio.save(im, out, fmt, **_encode_options(options))

    return _batch(paths, progress, "Resizing", one)


# --- convert ----------------------------------------------------------------------------


def convert(paths: list[str], folder: str | None, options: dict, progress: Progress | None = None) -> list[dict]:
    """To `options["format"]`. Multi-frame files (TIFF pages, GIF frames) give one file per
    frame when `all_frames` is set, else the first frame."""
    fmt = options.get("format", "jpg")
    if fmt not in iio.FORMATS:
        raise ValueError(f"Unknown image format: {fmt!r}")
    enc = _encode_options(options)

    def one(path: str) -> list[dict]:
        out = iio.output_path(path, folder, options.get("suffix", ""), fmt)
        frames = []
        if options.get("all_frames"):
            with Image.open(iio.check_input(path)) as im:
                if getattr(im, "n_frames", 1) > 1:
                    frames = [frame.copy() for frame in ImageSequence.Iterator(im)]
        if len(frames) > 1:
            results = []
            for i, frame in enumerate(frames, 1):
                target = unique_path(out.with_name(f"{out.stem}_{i}{out.suffix}"))
                results.append(iio.save(frame, target, fmt, **enc))
            return results
        return [iio.save(iio.open_image(path), out, fmt, **enc)]

    nested = _batch(paths, progress, "Converting", lambda p: {"files": one(p)})
    return [f for item in nested for f in item["files"]]


# --- crop -------------------------------------------------------------------------------


def crop(path: str, output: str, rect: dict, options: dict | None = None) -> dict:
    """rect = {x, y, w, h} in pixels of the upright image. shape "circle" (or "ellipse")
    keeps only the ellipse inside the rectangle, with a transparent outside."""
    options = options or {}
    im = iio.open_image(path)
    x0 = max(0, round(float(rect["x"])))
    y0 = max(0, round(float(rect["y"])))
    x1 = min(im.width, round(float(rect["x"]) + float(rect["w"])))
    y1 = min(im.height, round(float(rect["y"]) + float(rect["h"])))
    if x1 - x0 < 1 or y1 - y0 < 1:
        raise ValueError("The crop area is empty")
    out_im = im.crop((x0, y0, x1, y1))
    fmt = iio.resolve_format(path, options.get("format", "keep"))
    if options.get("shape") in ("circle", "ellipse"):
        mask = Image.new("L", (out_im.width * 4, out_im.height * 4), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, mask.width - 1, mask.height - 1), fill=255)
        rgba = out_im.convert("RGBA")
        alpha = mask.resize(out_im.size, Image.Resampling.LANCZOS)
        if iio.has_alpha(out_im):
            alpha = Image.composite(rgba.getchannel("A"), Image.new("L", out_im.size, 0), alpha)
        rgba.putalpha(alpha)
        out_im = rgba
        if not iio.FORMATS[fmt][2]:
            fmt = "png"  # the corners must stay transparent
    return iio.save(out_im, output, fmt, **_encode_options(options))


# --- rotate / flip ----------------------------------------------------------------------

_TURNS = {1: Image.Transpose.ROTATE_270, 2: Image.Transpose.ROTATE_180, 3: Image.Transpose.ROTATE_90}  # clockwise


def transform(im: Image.Image, turns: int = 0, flip_h: bool = False, flip_v: bool = False) -> Image.Image:
    turns = int(turns) % 4
    if turns:
        im = im.transpose(_TURNS[turns])
    if flip_h:
        im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if flip_v:
        im = im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return im


def rotate(items: list[dict], folder: str | None, options: dict, progress: Progress | None = None) -> list[dict]:
    """items: [{path, turns (clockwise quarter turns), flip_h, flip_v}]."""
    by_path = {item["path"]: item for item in items}

    def one(path: str) -> dict:
        item = by_path[path]
        fmt = iio.resolve_format(path, options.get("format", "keep"))
        im = transform(iio.open_image(path), item.get("turns", 0), item.get("flip_h", False), item.get("flip_v", False))
        out = iio.output_path(path, folder, options.get("suffix", "_rotated"), fmt)
        return iio.save(im, out, fmt, **{**_encode_options(options), "quality": int(options.get("quality", 95))})

    return _batch([item["path"] for item in items], progress, "Rotating", one)
