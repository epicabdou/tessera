"""Reading, previewing and writing images for the image tools.

Images are always handled upright (EXIF orientation applied). Saving keeps the ICC
colour profile and, unless asked not to, the EXIF metadata (with orientation reset,
since the pixels are now upright). Writes go through a temp file and a rename.
"""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path

from PIL import Image, ImageOps

from ..filesystem import replace_with_retry
from ..pdf.common import unique_path

try:  # HEIC/HEIF photos (iPhone); optional so the rest works without it
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIF = True
except Exception:  # noqa: BLE001
    HEIF = False

Image.MAX_IMAGE_PIXELS = 400_000_000  # well above any photo; still stops decompression bombs

INPUT_EXTS = {"jpg", "jpeg", "jfif", "png", "gif", "bmp", "tif", "tiff", "webp", "avif", "ico"} | ({"heic", "heif"} if HEIF else set())
JPEG_EXTS = {"jpg", "jpeg", "jfif"}

# Output formats: Pillow format name, extension, can keep transparency, lossy (has quality).
FORMATS = {
    "jpg": ("JPEG", "jpg", False, True),
    "png": ("PNG", "png", True, False),
    "webp": ("WEBP", "webp", True, True),
    "avif": ("AVIF", "avif", True, True),
    "gif": ("GIF", "gif", True, False),
    "bmp": ("BMP", "bmp", False, False),
    "tiff": ("TIFF", "tif", True, False),
}
_FORMAT_BY_PIL = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "AVIF": "avif", "GIF": "gif", "BMP": "bmp", "TIFF": "tiff", "MPO": "jpg"}


def ext_of(path: str | Path) -> str:
    return Path(path).suffix.lower().lstrip(".")


def check_input(path: str | Path) -> Path:
    file = Path(path)
    if not file.is_file():
        raise FileNotFoundError(f"Not a file: {file}")
    if ext_of(file) not in INPUT_EXTS:
        raise ValueError(f"{file.name} isn't a supported image")
    return file


def open_image(path: str | Path) -> Image.Image:
    """The image, upright, fully loaded (the file is closed afterwards)."""
    file = check_input(path)
    try:
        with Image.open(file) as im:
            im.load()
            upright = ImageOps.exif_transpose(im)
            upright.info.update({k: v for k, v in im.info.items() if k in ("icc_profile", "dpi", "exif", "transparency")})
            return upright
    except (OSError, SyntaxError) as exc:
        raise ValueError(f"{file.name} isn't a readable image ({exc})") from None


def source_format(path: str | Path) -> str:
    """Output-format key matching the file's own format (for "keep format")."""
    with Image.open(check_input(path)) as im:
        return _FORMAT_BY_PIL.get(im.format or "", "png")


def has_alpha(im: Image.Image) -> bool:
    return im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info)


def info(path: str | Path) -> dict:
    file = check_input(path)
    with Image.open(file) as im:
        width, height = im.size
        if im.getexif().get(0x0112, 1) in (5, 6, 7, 8):
            width, height = height, width
        frames = getattr(im, "n_frames", 1)
        st = file.stat()
        return {
            "path": str(file),
            "name": file.name,
            "size": st.st_size,
            "mtime": st.st_mtime,
            "width": width,
            "height": height,
            "format": im.format or ext_of(file).upper(),
            "mode": im.mode,
            "alpha": has_alpha(im),
            "frames": frames,
        }


def data_url(im: Image.Image, max_side: int | None = None, fmt: str = "auto") -> str:
    """A preview: JPEG, or PNG when the image has transparency (so it shows as such)."""
    shown = im
    if max_side and max(im.size) > max_side:
        shown = im.copy()
        shown.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    if fmt == "png" or (fmt == "auto" and has_alpha(shown)):
        shown.convert("RGBA").save(buf, "PNG", compress_level=1)
        mime = "image/png"
    else:
        shown.convert("RGB").save(buf, "JPEG", quality=88)
        mime = "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def preview(path: str | Path, max_side: int = 1600) -> dict:
    """Upright preview of the file plus its real pixel size."""
    file = check_input(path)
    with Image.open(file) as im:
        im.draft("RGB", (max_side, max_side))  # fast path for big JPEGs
        im.load()
        upright = ImageOps.exif_transpose(im)
    full = info(file)
    return {**full, "data_url": data_url(upright, max_side)}


def flatten(im: Image.Image, background: str = "#ffffff") -> Image.Image:
    """RGB image; transparent areas become `background`."""
    if not has_alpha(im):
        return im.convert("RGB")
    rgba = im.convert("RGBA")
    base = Image.new("RGB", rgba.size, background)
    base.paste(rgba, mask=rgba.getchannel("A"))
    return base


def _clean_exif(im: Image.Image) -> bytes | None:
    try:
        exif = im.getexif()
    except Exception:  # noqa: BLE001
        return None
    if not exif:
        return None
    exif[0x0112] = 1  # pixels are upright now
    return exif.tobytes()


def encode(im: Image.Image, fmt: str, quality: int = 85, keep_metadata: bool = True, background: str = "#ffffff", optimize: bool = True) -> bytes:
    """Encode `im` as `fmt` (a FORMATS key) and return the bytes."""
    if fmt not in FORMATS:
        raise ValueError(f"Unknown image format: {fmt!r}")
    pil_name, _ext, alpha_ok, lossy = FORMATS[fmt]
    quality = max(1, min(100, int(quality)))
    if fmt in ("webp", "avif"):
        img = im.convert("RGBA" if has_alpha(im) else "RGB")
    elif alpha_ok:
        img = im if im.mode in ("RGB", "RGBA", "L", "LA", "P", "1") else im.convert("RGBA" if has_alpha(im) else "RGB")
    else:
        img = flatten(im, background)
    params: dict = {}
    if keep_metadata:
        if im.info.get("icc_profile"):
            params["icc_profile"] = im.info["icc_profile"]
        if fmt in ("jpg", "webp", "png", "avif", "tiff"):
            exif = _clean_exif(im)
            if exif:
                params["exif"] = exif
        if im.info.get("dpi") and fmt in ("jpg", "png", "tiff", "bmp"):
            params["dpi"] = im.info["dpi"]
    if fmt == "jpg":
        params.update(quality=quality, optimize=optimize, progressive=True, subsampling=0 if quality >= 90 else 2)
    elif fmt == "webp":
        params.update(quality=quality, method=5 if optimize else 3)
    elif fmt == "avif":
        params.update(quality=quality, speed=6)
    elif fmt == "png":
        params.update(optimize=optimize, compress_level=9 if optimize else 6)
    elif fmt == "tiff":
        params.update(compression="tiff_lzw")
    elif fmt == "gif":
        if img.mode not in ("P", "L"):
            img = img.convert("RGBA").quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.FLOYDSTEINBERG)
    if not lossy:
        params.pop("quality", None)
    buf = io.BytesIO()
    img.save(buf, pil_name, **params)
    return buf.getvalue()


def write_bytes(data: bytes, output: str | Path) -> dict:
    """Atomic write; returns the SavedFile description."""
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".{out.stem}.{os.getpid()}.tmp{out.suffix}")
    try:
        tmp.write_bytes(data)
        replace_with_retry(tmp, out)
    finally:
        tmp.unlink(missing_ok=True)
    return saved(out)


def saved(out: Path) -> dict:
    result = {"path": str(out), "name": out.name, "size": out.stat().st_size}
    try:
        with Image.open(out) as im:
            result.update(width=im.width, height=im.height)
    except Exception:  # noqa: BLE001 - a PDF, say
        pass
    return result


def save(im: Image.Image, output: str | Path, fmt: str | None = None, **options) -> dict:
    """Encode and write. `fmt` defaults to the output's extension."""
    out = Path(output)
    fmt = fmt or format_for_ext(ext_of(out))
    ext = FORMATS[fmt][1]
    if ext_of(out) not in ({ext} | ({"jpeg", "jfif"} if fmt == "jpg" else set()) | ({"tiff"} if fmt == "tiff" else set())):
        out = out.with_name(f"{out.name}.{ext}")
    return write_bytes(encode(im, fmt, **options), out)


def format_for_ext(ext: str) -> str:
    ext = ext.lower()
    if ext in JPEG_EXTS:
        return "jpg"
    if ext in ("tif", "tiff"):
        return "tiff"
    if ext in FORMATS:
        return ext
    raise ValueError(f"Can't save .{ext} images; choose JPG, PNG, WebP, AVIF, GIF, BMP or TIFF")


def output_path(source: str | Path, folder: str | None, suffix: str, fmt: str) -> Path:
    """A non-clashing "<name><suffix>.<ext>" next to the source or in `folder`."""
    src = Path(source)
    ext = FORMATS[fmt][1]
    return unique_path(Path(folder or src.parent) / f"{src.stem}{suffix}.{ext}")


def resolve_format(source: str | Path, fmt: str) -> str:
    """"keep" -> the source's own format (HEIC/ICO, which we don't write, become JPG/PNG)."""
    if fmt != "keep":
        if fmt not in FORMATS:
            raise ValueError(f"Unknown image format: {fmt!r}")
        return fmt
    ext = ext_of(source)
    if ext in ("heic", "heif"):
        return "jpg"
    if ext == "ico":
        return "png"
    return format_for_ext(ext)
