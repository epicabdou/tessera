"""Compress (smaller files) and repair (damaged files)."""

from __future__ import annotations

import io
import logging
import os
import re
import shutil
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

from ..filesystem import replace_with_retry
from ..pdf import render
from ..pdf.common import open_reader, write_pdf
from ..progress import Progress

LEVELS = {  # longest image side (px), JPEG quality
    "low": (2400, 85),
    "medium": (1600, 72),
    "high": (1100, 55),
}


def _recompressible(obj) -> bool:
    if obj.get("/SMask") is not None or obj.get("/Mask") is not None or obj.get("/ImageMask"):
        return False
    if int(obj.get("/BitsPerComponent", 8)) < 8:
        return False
    filters = obj.get("/Filter")
    names = [str(f) for f in (filters if isinstance(filters, list) else [filters])] if filters else []
    return not any(f in ("/JBIG2Decode", "/CCITTFaxDecode", "/JPXDecode") for f in names)


def compress(path: str, output: str, level: str = "medium", strip_metadata: bool = False, progress: Progress | None = None) -> dict:
    if level not in LEVELS:
        raise ValueError(f"Unknown level: {level!r}")
    max_side, quality = LEVELS[level]
    before = Path(path).stat().st_size
    writer = PdfWriter(clone_from=open_reader(path))
    seen: set[int] = set()
    images = 0
    for n, page in enumerate(writer.pages):
        for img in page.images:
            ref = img.indirect_reference
            if ref is None or ref.idnum in seen:
                continue
            seen.add(ref.idnum)
            obj = ref.get_object()
            if not _recompressible(obj):
                continue
            try:
                pil = img.image
            except Exception:  # noqa: BLE001 - undecodable image: leave it
                continue
            if pil.mode not in ("RGB", "L"):
                if pil.mode in ("P", "CMYK", "LA", "RGBA"):
                    pil = pil.convert("RGB")
                else:
                    continue
            scale = min(1.0, max_side / max(pil.size))
            if scale < 1:
                pil = pil.resize((max(1, int(pil.width * scale)), max(1, int(pil.height * scale))), Image.LANCZOS)
            trial = io.BytesIO()
            pil.save(trial, "JPEG", quality=quality, optimize=True)
            if trial.tell() < len(obj._data or b"") * 0.9:  # only if it actually gets smaller
                img.replace(pil, quality=quality)
                images += 1
        page.compress_content_streams(level=9)
        for key in ("/Thumb", "/PieceInfo"):
            if key in page:
                del page[key]
        if progress:
            progress(n + 1, len(writer.pages), f"Page {n + 1}")
    writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    if strip_metadata:
        writer._info = None
        if "/Metadata" in writer._root_object:
            del writer._root_object[NameObject("/Metadata")]
    result = write_pdf(writer, output)
    if result["size"] >= before:
        # Already as small as we can make it: keep the original bytes.
        shutil.copyfile(path, result["path"])
        result["size"] = before
        result["already_optimal"] = True
    result.update(before=before, after=result["size"], images_recompressed=images)
    return result


# --- repair ------------------------------------------------------------------------


class _Collect(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        if msg not in self.messages:
            self.messages.append(msg)


def analyze(path: str) -> dict:
    """What's wrong with a PDF, without changing it."""
    file = Path(path)
    data = file.read_bytes()
    issues: list[str] = []
    if not data.lstrip()[:5] == b"%PDF-":
        issues.append("The file doesn't start with a PDF header")
    if b"%%EOF" not in data[-2048:]:
        issues.append("The end-of-file marker is missing (the file may be cut short)")
    handler = _Collect()
    logger = logging.getLogger("pypdf")
    logger.addHandler(handler)
    pages_pypdf = None
    strict_ok = False
    try:
        try:
            len(PdfReader(io.BytesIO(data), strict=True).pages)
            strict_ok = True
        except Exception as exc:  # noqa: BLE001
            issues.append(f"Strict reading failed: {exc}")
        try:
            pages_pypdf = len(PdfReader(io.BytesIO(data), strict=False).pages)
        except Exception as exc:  # noqa: BLE001
            issues.append(f"Lenient reading failed: {exc}")
    finally:
        logger.removeHandler(handler)
    pages_pdfium = None
    with render._LOCK:
        try:
            doc = pdfium.PdfDocument(data)
            pages_pdfium = len(doc)
            doc.close()
        except Exception as exc:  # noqa: BLE001
            issues.append(f"PDFium couldn't open it: {exc}")
    issues += [f"Warning: {m}" for m in handler.messages[:20]]
    return {
        "path": str(file),
        "name": file.name,
        "size": len(data),
        "healthy": strict_ok and not handler.messages and pages_pypdf is not None,
        "pages": max(p or 0 for p in (pages_pypdf, pages_pdfium)) or None,
        "issues": issues,
    }


_OBJ = re.compile(rb"(?<![\d])(\d+)\s+(\d+)\s+obj\b")


def _salvage(data: bytes) -> list[tuple[str, bytes]]:
    """For files that lost their end (index + trailer): keep every complete object and
    append a fresh index and trailer. Two variants: one trusting the document's own page
    tree, one with a new page tree built from every page object found."""
    last_end = data.rfind(b"endobj")
    if last_end == -1:
        return []
    body = data[: last_end + len(b"endobj")] + b"\n"
    offsets: dict[int, int] = {}
    page_objs: list[int] = []
    catalog = None
    for m in _OBJ.finditer(body):
        num = int(m.group(1))
        end = body.find(b"endobj", m.end())
        if end == -1:
            continue
        offsets[num] = m.start()
        chunk = body[m.end() : end]
        if re.search(rb"/Type\s*/Catalog\b", chunk):
            catalog = num
        elif re.search(rb"/Type\s*/Page(?![A-Za-z])", chunk):
            page_objs.append(num)

    def finish(extra: dict[int, bytes], root: int) -> bytes:
        out = bytearray(body)
        objs = dict(offsets)
        for num, content in extra.items():
            objs[num] = len(out)
            out += b"%d 0 obj\n" % num + content + b"\nendobj\n"
        size = max(objs) + 1
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % size
        for num in range(1, size):
            out += (b"%010d 00000 n \n" % objs[num]) if num in objs else b"0000000000 65535 f \n"
        out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, root, xref)
        return bytes(out)

    variants = []
    if catalog is not None:
        variants.append(("salvaged", finish({}, catalog)))
    if page_objs:
        top = max(offsets) + 1
        kids = b" ".join(b"%d 0 R" % n for n in page_objs)
        extra = {
            top: b"<< /Type /Pages /Kids [" + kids + b"] /Count %d >>" % len(page_objs),
            top + 1: b"<< /Type /Catalog /Pages %d 0 R >>" % top,
        }
        variants.append(("rebuilt", finish(extra, top + 1)))
    return variants


def _try_pypdf(data: bytes, target: Path) -> int:
    reader = PdfReader(io.BytesIO(data), strict=False)
    writer = PdfWriter()
    for page in reader.pages:
        try:
            writer.add_page(page)
        except Exception:  # noqa: BLE001 - a broken page: skip it, keep the rest
            pass
    if not writer.pages:
        return 0
    with open(target, "wb") as fh:
        writer.write(fh)
    return len(writer.pages)


def _try_pdfium(data: bytes, target: Path) -> int:
    with render._LOCK:
        doc = pdfium.PdfDocument(data)
        try:
            if not len(doc):
                return 0
            doc.save(str(target), flags=pdfium_c.FPDF_NO_INCREMENTAL)
            return len(doc)
        finally:
            doc.close()


def repair(path: str, output: str) -> dict:
    """Rebuild the file. Tries pypdf (lenient) and PDFium on the file as it is, then on
    salvaged versions; keeps whichever recovers the most pages."""
    data = Path(path).read_bytes()
    out = Path(output)
    if out.suffix.lower() != ".pdf":
        out = out.with_name(out.name + ".pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    candidates: list[tuple[int, str, Path]] = []
    sources = [("original", data)]
    if b"%%EOF" not in data[-2048:] or b"trailer" not in data[-4096:]:
        sources += _salvage(data)
    for n, (label, source) in enumerate(sources):
        for engine, attempt in (("pypdf", _try_pypdf), ("pdfium", _try_pdfium)):
            tmp = out.with_name(f".{out.stem}.{os.getpid()}.{n}.{engine}.pdf")
            try:
                pages = attempt(source, tmp)
            except Exception:  # noqa: BLE001 - this route failed; try the others
                pages = 0
            if pages:
                candidates.append((pages, engine if label == "original" else f"{engine} ({label})", tmp))
            else:
                tmp.unlink(missing_ok=True)

    try:
        if not candidates:
            raise ValueError("The file is too damaged to recover any pages")
        pages, method, best = max(candidates, key=lambda c: (c[0], c[1].startswith("pypdf")))
        PdfReader(best, strict=False).pages[0]  # sanity check: the result opens
        replace_with_retry(best, out)
    finally:
        for _, _, tmp in candidates:
            tmp.unlink(missing_ok=True)
    return {"path": str(out), "name": out.name, "size": out.stat().st_size, "page_count": pages, "method": method}
