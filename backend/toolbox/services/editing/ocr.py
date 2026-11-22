"""OCR: add an invisible, selectable text layer to scanned pages.

Engines:
- Tesseract (if installed): its own "text-only PDF" output places every word
  exactly; we scale that layer onto the original page.
- Windows OCR (built into Windows 10/11, uses installed language packs): word
  boxes from WinRT, drawn as invisible text with ReportLab.
The page images are left untouched; only text is added.
"""

from __future__ import annotations

import asyncio
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pypdfium2 as pdfium
from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfbase.pdfmetrics import stringWidth

from ..pdf import render
from ..pdf.common import open_reader, write_pdf
from ..progress import Progress
from .geometry import bake_rotation
from .overlay import font, overlay_page

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def tesseract_path() -> str | None:
    candidates = [shutil.which("tesseract")]
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")):
        if base:
            candidates += [os.path.join(base, "Tesseract-OCR", "tesseract.exe"), os.path.join(base, "Programs", "Tesseract-OCR", "tesseract.exe")]
    return next((p for p in candidates if p and os.path.isfile(p)), None)


def _tesseract_languages(exe: str) -> list[str]:
    out = subprocess.run([exe, "--list-langs"], capture_output=True, text=True, creationflags=_NO_WINDOW).stdout
    return [line.strip() for line in out.splitlines()[1:] if line.strip() and line.strip() != "osd"]


def _windows_languages() -> list[str]:
    if sys.platform != "win32":
        return []
    try:
        from winrt.windows.media.ocr import OcrEngine

        return [lang.language_tag for lang in OcrEngine.available_recognizer_languages]
    except Exception:  # noqa: BLE001 - WinRT projection missing or OCR unavailable
        return []


def engines() -> dict:
    exe = tesseract_path()
    return {
        "tesseract": {"path": exe, "languages": _tesseract_languages(exe) if exe else []},
        "windows": {"languages": _windows_languages()},
    }


def has_text(page) -> bool:
    try:
        return len((page.extract_text() or "").strip()) >= 20
    except Exception:  # noqa: BLE001
        return False


# --- engines --------------------------------------------------------------------


def _tesseract_layer(exe: str, image, dpi: int, language: str, workdir: Path) -> tuple[object, int]:
    png = workdir / "page.png"
    image.save(png)
    base = workdir / "layer"
    proc = subprocess.run(
        [exe, str(png), str(base), "-l", language, "--dpi", str(dpi), "-c", "textonly_pdf=1", "pdf", "txt"],
        capture_output=True,
        text=True,
        creationflags=_NO_WINDOW,
    )
    if proc.returncode != 0 or not base.with_suffix(".pdf").is_file():
        raise RuntimeError(f"Tesseract failed: {(proc.stderr or '').strip().splitlines()[-1:] or 'no output'}")
    words = len(base.with_suffix(".txt").read_text(encoding="utf-8", errors="replace").split())
    # Load into memory so the temp file can be overwritten by the next page.
    return PdfReader(io.BytesIO(base.with_suffix(".pdf").read_bytes())).pages[0], words


async def _windows_words(image, language: str) -> list[tuple[str, float, float, float, float]]:
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage.streams import DataWriter

    engine = OcrEngine.try_create_from_language(Language(language)) if language else None
    engine = engine or OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise RuntimeError("Windows OCR has no language installed")
    bgra = image.convert("RGBA").tobytes("raw", "BGRA")
    writer = DataWriter()
    writer.write_bytes(bgra)
    bitmap = SoftwareBitmap.create_copy_from_buffer(writer.detach_buffer(), BitmapPixelFormat.BGRA8, image.width, image.height, BitmapAlphaMode.PREMULTIPLIED)
    result = await engine.recognize_async(bitmap)
    return [(w.text, w.bounding_rect.x, w.bounding_rect.y, w.bounding_rect.width, w.bounding_rect.height) for line in result.lines for w in line.words]


def _windows_layer(image, dpi: int, language: str):
    if image.width > 10000 or image.height > 10000:
        raise ValueError("Page too large for Windows OCR at this resolution")
    words = asyncio.run(_windows_words(image, language))
    k = 72 / dpi
    width, height = image.width * k, image.height * k
    name = font("sans")

    def draw(c):
        for text, x, y, w, h in words:
            size = max(1.0, h * k * 0.9)
            natural = stringWidth(text, name, size) or 1
            t = c.beginText()
            t.setTextRenderMode(3)  # invisible, but selectable and searchable
            t.setFont(name, size)
            t.setHorizScale(100 * (w * k) / natural)
            t.setTextOrigin(x * k, height - (y + h * 0.82) * k)
            t.textOut(text)
            c.drawText(t)

    return overlay_page(width, height, draw), len(words)


# --- entry point -------------------------------------------------------------------


def ocr_pdf(
    path: str,
    output: str,
    engine: str = "auto",
    language: str = "",
    dpi: int = 300,
    skip_text_pages: bool = True,
    pages: list[int] | None = None,
    progress: Progress | None = None,
) -> dict:
    if not 100 <= dpi <= 600:
        raise ValueError("Resolution must be 100–600 dpi")
    available = engines()
    exe = available["tesseract"]["path"]
    if engine == "auto":
        engine = "tesseract" if exe else "windows" if available["windows"]["languages"] else ""
    if engine == "tesseract" and not exe:
        raise RuntimeError("Tesseract OCR isn't installed")
    if engine == "windows" and not available["windows"]["languages"]:
        raise RuntimeError("Windows OCR isn't available (no OCR language installed)")
    if not engine:
        raise RuntimeError("No OCR engine found. Install Tesseract OCR, or add a language with OCR support in Windows Settings.")
    if engine == "tesseract":
        language = language or ("eng" if "eng" in available["tesseract"]["languages"] else available["tesseract"]["languages"][0])
        if language not in available["tesseract"]["languages"]:
            raise ValueError(f"Tesseract has no '{language}' language data installed")
    else:
        language = language or available["windows"]["languages"][0]

    reader = open_reader(path)
    writer = PdfWriter(clone_from=reader)
    indexes = list(range(len(reader.pages))) if pages is None else pages
    done = skipped = words = 0
    with tempfile.TemporaryDirectory(prefix="toolbox-ocr-") as tmp:
        for n, i in enumerate(indexes):
            if progress:
                progress(n, len(indexes), f"Recognising page {i + 1} of {len(reader.pages)}")
            if skip_text_pages and has_text(reader.pages[i]):
                skipped += 1
                continue
            with render._LOCK:
                doc = pdfium.PdfDocument(path)
                try:
                    pg = doc[i]
                    image = pg.render(scale=dpi / 72).to_pil().convert("RGB")
                    pg.close()
                finally:
                    doc.close()
            if engine == "tesseract":
                layer, count = _tesseract_layer(exe, image, dpi, language, Path(tmp))
            else:
                layer, count = _windows_layer(image, dpi, language)
            page = writer.pages[i]
            bake_rotation(page)
            box = page.cropbox
            sx = float(box.width) / float(layer.mediabox.width)
            sy = float(box.height) / float(layer.mediabox.height)
            page.merge_transformed_page(layer, Transformation().scale(sx, sy).translate(float(box.left), float(box.bottom)))
            done += 1
            words += count
        if progress:
            progress(len(indexes), len(indexes), "Saving")
        result = write_pdf(writer, output)
    result.update(engine=engine, language=language, pages_recognised=done, pages_skipped=skipped, words=words)
    return result
