"""Images to PDF.

JPEGs are embedded byte-for-byte (no re-compression); other formats are stored
losslessly (Flate), with transparency kept as a soft mask. EXIF rotation is
honoured; for JPEGs it's applied as a drawing transform so the bytes stay intact.
"""

from __future__ import annotations

import base64
import io
import zlib
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, ImageSequence
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject, StreamObject

from ..pdf.common import POINTS_PER_MM, unique_path, write_pdf

IMAGE_EXTS = {"jpg", "jpeg", "jfif", "png", "gif", "bmp", "tif", "tiff", "webp"}

PAGE_SIZES = {  # points, portrait
    "a4": (595.28, 841.89),
    "letter": (612.0, 792.0),
    "legal": (612.0, 1008.0),
    "a3": (841.89, 1190.55),
    "a5": (419.53, 595.28),
}
MARGINS = {"none": 0.0, "small": 10 * POINTS_PER_MM, "large": 20 * POINTS_PER_MM}
DEFAULT_DPI = 96.0
# EXIF orientation -> clockwise quarter turns needed to show the photo upright.
_EXIF_TURNS = {1: 0, 3: 2, 6: 1, 8: 3}


@dataclass
class _Picture:
    stream: StreamObject
    width: int  # pixels, as stored
    height: int
    dpi: float
    turns: int  # clockwise quarter turns to apply when drawing


def _stream(data: bytes, entries: dict) -> StreamObject:
    obj = StreamObject()
    obj.set_data(data)  # already encoded: written out as-is
    obj.update({NameObject(k): v for k, v in entries.items()})
    return obj


def _image_dict(width: int, height: int, colorspace: str, filter_: str, bits: int = 8) -> dict:
    return {
        "/Type": NameObject("/XObject"),
        "/Subtype": NameObject("/Image"),
        "/Width": NumberObject(width),
        "/Height": NumberObject(height),
        "/ColorSpace": NameObject(colorspace),
        "/BitsPerComponent": NumberObject(bits),
        "/Filter": NameObject(filter_),
    }


def _dpi(im: Image.Image) -> float:
    dpi = im.info.get("dpi")
    try:
        value = float(dpi[0]) if dpi else 0.0
    except (TypeError, ValueError, IndexError):
        value = 0.0
    return value if 30 <= value <= 2400 else DEFAULT_DPI


def _flate_picture(writer: PdfWriter, im: Image.Image, dpi: float) -> _Picture:
    has_alpha = "A" in im.getbands() or "transparency" in im.info
    if im.mode in ("1", "L", "LA"):
        base = im.convert("LA" if has_alpha else "L")
        colorspace = "/DeviceGray"
    elif im.mode == "CMYK" and not has_alpha:
        base = im
        colorspace = "/DeviceCMYK"
    else:
        base = im.convert("RGBA" if has_alpha else "RGB")
        colorspace = "/DeviceRGB"
    entries = _image_dict(base.width, base.height, colorspace, "/FlateDecode")
    if has_alpha:
        alpha = base.getchannel("A")
        base = base.convert("L" if colorspace == "/DeviceGray" else "RGB")
        mask = _stream(zlib.compress(alpha.tobytes(), 6), _image_dict(alpha.width, alpha.height, "/DeviceGray", "/FlateDecode"))
        entries["/SMask"] = writer._add_object(mask)
    stream = _stream(zlib.compress(base.tobytes(), 6), entries)
    return _Picture(stream, base.width, base.height, dpi, 0)


def _pictures(writer: PdfWriter, path: Path, extra_turns: int) -> list[_Picture]:
    """One picture per frame (multi-page TIFFs give several)."""
    pictures: list[_Picture] = []
    with Image.open(path) as im:
        dpi = _dpi(im)
        orientation = im.getexif().get(0x0112, 1)
        frames = getattr(im, "n_frames", 1)
        if im.format == "JPEG" and im.mode in ("RGB", "L", "CMYK") and orientation in _EXIF_TURNS:
            colorspace = {"RGB": "/DeviceRGB", "L": "/DeviceGray", "CMYK": "/DeviceCMYK"}[im.mode]
            entries = _image_dict(im.width, im.height, colorspace, "/DCTDecode")
            if im.mode == "CMYK" and "adobe" in im.info:  # Adobe CMYK JPEGs store inverted values
                entries["/Decode"] = ArrayObject([NumberObject(v) for v in (1, 0) * 4])
            stream = _stream(path.read_bytes(), entries)
            pictures.append(_Picture(stream, im.width, im.height, dpi, _EXIF_TURNS[orientation]))
        elif frames > 1 and im.format == "TIFF":
            for frame in ImageSequence.Iterator(im):
                pictures.append(_flate_picture(writer, frame.copy(), dpi))
        else:
            if im.format == "GIF":
                im.seek(0)
            upright = ImageOps.exif_transpose(im)
            pictures.append(_flate_picture(writer, upright, dpi))
    for p in pictures:
        p.turns = (p.turns + extra_turns) % 4
    return pictures


def _matrix(turns: int, x: float, y: float, w: float, h: float) -> list[float]:
    """cm operands drawing the unit-square image into (x, y, w, h), turned clockwise."""
    return {
        0: [w, 0, 0, h, x, y],
        1: [0, -h, w, 0, x, y + h],
        2: [-w, 0, 0, -h, x + w, y + h],
        3: [0, h, -w, 0, x + w, y],
    }[turns]


def _layout(pic: _Picture, options: dict) -> tuple[tuple[float, float], tuple[float, float, float, float], tuple[float, float, float, float] | None]:
    """Page size, image rectangle and (for 'fill') the clip rectangle."""
    w_px, h_px = (pic.height, pic.width) if pic.turns % 2 else (pic.width, pic.height)
    img_w, img_h = w_px * 72 / pic.dpi, h_px * 72 / pic.dpi
    margin = MARGINS.get(options.get("margin", "small"))
    if margin is None:
        raise ValueError(f"Unknown margin: {options.get('margin')!r}")
    size = options.get("page_size", "a4")
    if size == "fit":
        return (img_w + 2 * margin, img_h + 2 * margin), (margin, margin, img_w, img_h), None
    if size not in PAGE_SIZES:
        raise ValueError(f"Unknown page size: {size!r}")
    pw, ph = PAGE_SIZES[size]
    orientation = options.get("orientation", "auto")
    landscape = img_w > img_h if orientation == "auto" else orientation == "landscape"
    if landscape:
        pw, ph = ph, pw
    box_w, box_h = pw - 2 * margin, ph - 2 * margin
    fill = options.get("fit", "contain") == "fill"
    scale = (max if fill else min)(box_w / img_w, box_h / img_h)
    w, h = img_w * scale, img_h * scale
    x, y = margin + (box_w - w) / 2, margin + (box_h - h) / 2
    return (pw, ph), (x, y, w, h), (margin, margin, box_w, box_h) if fill else None


def _add_page(writer: PdfWriter, pic: _Picture, options: dict) -> None:
    (pw, ph), rect, clip = _layout(pic, options)
    page = writer.add_blank_page(pw, ph)
    ref = writer._add_object(pic.stream)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): ref})}
    )
    ops = ["q"]
    if clip:
        ops.append("{:.3f} {:.3f} {:.3f} {:.3f} re W n".format(*clip))
    ops.append("{:.4f} {:.4f} {:.4f} {:.4f} {:.3f} {:.3f} cm /Im0 Do Q".format(*_matrix(pic.turns, *rect)))
    content = DecodedStreamObject()
    content.set_data(" ".join(ops).encode())
    page[NameObject("/Contents")] = writer._add_object(content)


def _check(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Not a file: {path}")
    if path.suffix.lower().lstrip(".") not in IMAGE_EXTS:
        raise ValueError(f"{path.name} isn't a supported image")


def images_to_pdf(items: list[dict], output: str, options: dict) -> dict:
    """All images into one PDF. items: [{"path": ..., "rotate": 0|90|180|270}]."""
    if not items:
        raise ValueError("Add at least one image")
    writer = PdfWriter()
    for item in items:
        path = Path(item["path"])
        _check(path)
        try:
            for pic in _pictures(writer, path, int(item.get("rotate", 0)) // 90):
                _add_page(writer, pic, options)
        except (OSError, Image.DecompressionBombError) as exc:
            raise ValueError(f"Can't read {path.name}: {exc}") from None
    return write_pdf(writer, output)


def images_to_pdfs(items: list[dict], output_dir: str | None, options: dict) -> list[dict]:
    """One PDF per image, next to each image or in `output_dir`."""
    results = []
    for item in items:
        path = Path(item["path"])
        target = unique_path(Path(output_dir or path.parent) / f"{path.stem}.pdf")
        results.append(images_to_pdf([item], str(target), options))
    return results


def thumbnail(path: str, size: int = 160) -> dict:
    """Small JPEG preview plus the displayed (EXIF-upright) pixel size (any format the
    image tools read, HEIC included)."""
    from ..images import imageio

    file = imageio.check_input(path)
    with Image.open(file) as im:
        width, height = im.size
        if im.getexif().get(0x0112, 1) in (5, 6, 7, 8):
            width, height = height, width
        im.draft("RGB", (size * 2, size * 2))
        shown = ImageOps.exif_transpose(im)
        shown.thumbnail((size, size))
        buf = io.BytesIO()
        shown.convert("RGB").save(buf, "JPEG", quality=80)
        frames = getattr(im, "n_frames", 1) if im.format == "TIFF" else 1
    return {
        "path": str(file),
        "name": file.name,
        "data_url": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii"),
        "width": width,
        "height": height,
        "pages": frames,
        "size": file.stat().st_size,
    }
