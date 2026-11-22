"""Find faces with the face detector built into Windows, and blur, pixelate or cover them.

Detection gives a starting point; the UI lets the user add, move or remove boxes, so the
blur is applied to exactly the boxes passed in (in pixels of the upright image).
"""

from __future__ import annotations

import asyncio
import sys

from PIL import Image, ImageDraw, ImageFilter

from . import imageio as iio

_DETECT_MAX = 2048  # the detector works on this size; bigger photos are also scanned in tiles


async def _detect_gray(gray: Image.Image) -> list[tuple[float, float, float, float]]:
    from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
    from winrt.windows.media.faceanalysis import FaceDetector
    from winrt.windows.storage.streams import DataWriter

    detector = await FaceDetector.create_async()
    writer = DataWriter()
    writer.write_bytes(gray.tobytes())
    bitmap = SoftwareBitmap.create_copy_from_buffer(writer.detach_buffer(), BitmapPixelFormat.GRAY8, gray.width, gray.height)
    faces = await detector.detect_faces_async(bitmap)
    return [(f.face_box.x, f.face_box.y, f.face_box.width, f.face_box.height) for f in faces]


def _iou(a: tuple, b: tuple) -> float:
    ax1, ay1, ax2, ay2 = a[0], a[1], a[0] + a[2], a[1] + a[3]
    bx1, by1, bx2, by2 = b[0], b[1], b[0] + b[2], b[1] + b[3]
    iw, ih = max(0, min(ax2, bx2) - max(ax1, bx1)), max(0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union else 0.0


def _merge(boxes: list[tuple]) -> list[tuple]:
    """Drop duplicates found by overlapping passes (keep the larger box)."""
    kept: list[tuple] = []
    for box in sorted(boxes, key=lambda b: b[2] * b[3], reverse=True):
        if all(_iou(box, k) < 0.3 for k in kept):
            kept.append(box)
    return kept


def detect(path: str) -> list[dict]:
    if sys.platform != "win32":
        raise RuntimeError("Face detection uses Windows and isn't available here")
    im = iio.open_image(path)
    gray = im.convert("L")
    found: list[tuple] = []
    k = min(1.0, _DETECT_MAX / max(gray.size))
    small = gray if k == 1 else gray.resize((round(gray.width * k), round(gray.height * k)), Image.Resampling.LANCZOS)
    found += [(x / k, y / k, w / k, h / k) for x, y, w, h in asyncio.run(_detect_gray(small))]
    if k < 1:
        # Small faces in big group photos: also look at full-resolution tiles.
        step = int(_DETECT_MAX * 0.75)
        for top in range(0, max(1, gray.height - _DETECT_MAX // 4), step):
            for left in range(0, max(1, gray.width - _DETECT_MAX // 4), step):
                tile = gray.crop((left, top, min(gray.width, left + _DETECT_MAX), min(gray.height, top + _DETECT_MAX)))
                found += [(x + left, y + top, w, h) for x, y, w, h in asyncio.run(_detect_gray(tile))]
    faces = _merge(found)
    faces.sort(key=lambda b: (b[1], b[0]))
    return [{"x": round(x, 1), "y": round(y, 1), "w": round(w, 1), "h": round(h, 1)} for x, y, w, h in faces]


def obscure(im: Image.Image, faces: list[dict], options: dict) -> Image.Image:
    """style: "blur" | "pixelate" | "solid"; strength 1-100; shape "ellipse" | "rect";
    padding: % to grow each box (faces are usually a bit bigger than the detected box)."""
    style = options.get("style", "blur")
    strength = max(1.0, min(100.0, float(options.get("strength", 60))))
    pad = float(options.get("padding", 15)) / 100
    shape = options.get("shape", "ellipse")
    out = im.convert("RGBA") if iio.has_alpha(im) else im.convert("RGB")
    for face in faces:
        w, h = float(face["w"]), float(face["h"])
        x0 = max(0, round(float(face["x"]) - w * pad / 2))
        y0 = max(0, round(float(face["y"]) - h * pad / 2))
        x1 = min(out.width, round(float(face["x"]) + w * (1 + pad / 2)))
        y1 = min(out.height, round(float(face["y"]) + h * (1 + pad / 2)))
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        region = out.crop((x0, y0, x1, y1))
        size = max(x1 - x0, y1 - y0)
        if style == "pixelate":
            block = max(3, round(size * strength / 100 * 0.14))
            small = region.resize((max(1, region.width // block), max(1, region.height // block)), Image.Resampling.BILINEAR)
            effect = small.resize(region.size, Image.Resampling.NEAREST)
        elif style == "solid":
            effect = Image.new(region.mode, region.size, options.get("color") or "#000000")
        else:
            # Blur a margin around the box too, so the edge isn't a sharp ring.
            effect = region.filter(ImageFilter.GaussianBlur(max(2.0, size * strength / 100 * 0.18)))
        mask = Image.new("L", region.size, 0)
        draw = ImageDraw.Draw(mask)
        if shape == "rect":
            draw.rectangle((0, 0, region.width - 1, region.height - 1), fill=255)
        else:
            draw.ellipse((0, 0, region.width - 1, region.height - 1), fill=255)
        if style != "solid":
            mask = mask.filter(ImageFilter.GaussianBlur(max(1.0, size * 0.02)))
        out.paste(effect, (x0, y0), mask)
    return out


def preview(path: str, faces: list[dict], options: dict, max_side: int = 1400) -> dict:
    im = iio.open_image(path)
    k = min(1.0, max_side / max(im.size))
    if k < 1:
        im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.Resampling.LANCZOS)
    scaled = [{key: float(face[key]) * k for key in ("x", "y", "w", "h")} for face in faces]
    out = obscure(im, scaled, options)
    return {"data_url": iio.data_url(out), "width": out.width, "height": out.height}


def blur_faces(path: str, output: str, faces: list[dict], options: dict) -> dict:
    if not faces:
        raise ValueError("No faces to blur: run detection or draw boxes on the photo")
    out = obscure(iio.open_image(path), faces, options)
    fmt = iio.resolve_format(path, options.get("format", "keep"))
    result = iio.save(out, output, fmt, quality=int(options.get("quality", 92)), keep_metadata=bool(options.get("keep_metadata", False)))
    result["faces"] = len(faces)
    return result
