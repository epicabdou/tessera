"""Page previews and content detection with PDFium.

PDFium is not thread-safe and pywebview runs every JS call on its own thread,
so every PDFium call goes through one lock.
"""

from __future__ import annotations

import base64
import io
import os
import threading
from collections import OrderedDict
from pathlib import Path

import pypdfium2 as pdfium

_LOCK = threading.Lock()
_CACHE: OrderedDict[tuple, str] = OrderedDict()
_CACHE_MAX = 600

MIN_WIDTH, MAX_WIDTH = 32, 1600


def _open(path: Path) -> pdfium.PdfDocument:
    try:
        return pdfium.PdfDocument(str(path))
    except pdfium.PdfiumError as exc:
        raise ValueError(f"Can't render {path.name}: {exc}") from None


def _data_url(image) -> str:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, "JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def render_pages(path: str, indexes: list[int], width: int) -> list[str | None]:
    """JPEG data URLs of the given pages, `width` pixels wide (None for bad indexes)."""
    file = Path(path)
    width = max(MIN_WIDTH, min(MAX_WIDTH, int(width)))
    stat = os.stat(file)
    stamp = (str(file), stat.st_mtime_ns, stat.st_size, width)

    results: dict[int, str | None] = {}
    with _LOCK:
        missing = []
        for i in indexes:
            cached = _CACHE.get((*stamp, i))
            if cached is not None:
                _CACHE.move_to_end((*stamp, i))
                results[i] = cached
            else:
                missing.append(i)
        if missing:
            doc = _open(file)
            try:
                for i in missing:
                    if not 0 <= i < len(doc):
                        results[i] = None
                        continue
                    page = doc[i]
                    try:
                        page_w, _ = page.get_size()  # already accounts for /Rotate
                        url = _data_url(page.render(scale=width / page_w).to_pil())
                    finally:
                        page.close()
                    results[i] = url
                    _CACHE[(*stamp, i)] = url
                    while len(_CACHE) > _CACHE_MAX:
                        _CACHE.popitem(last=False)
            finally:
                doc.close()
    return [results[i] for i in indexes]


def detect_margins(path: str, index: int, threshold: int = 242, padding: float = 6.0) -> dict:
    """Margins (points, as displayed) around the page's visible content, for auto-crop."""
    file = Path(path)
    with _LOCK:
        doc = _open(file)
        try:
            if not 0 <= index < len(doc):
                raise ValueError(f"Page {index + 1} doesn't exist")
            page = doc[index]
            try:
                w_pt, h_pt = page.get_size()
                scale = min(2.0, 900 / max(w_pt, h_pt))
                image = page.render(scale=scale).to_pil().convert("L")
            finally:
                page.close()
        finally:
            doc.close()

    bbox = image.point(lambda v: 255 if v < threshold else 0).getbbox()
    if not bbox:
        return {"top": 0.0, "right": 0.0, "bottom": 0.0, "left": 0.0}
    x0, y0, x1, y1 = bbox
    px = 1 / scale
    return {
        "top": round(max(0.0, y0 * px - padding), 2),
        "right": round(max(0.0, (image.width - x1) * px - padding), 2),
        "bottom": round(max(0.0, (image.height - y1) * px - padding), 2),
        "left": round(max(0.0, x0 * px - padding), 2),
    }
