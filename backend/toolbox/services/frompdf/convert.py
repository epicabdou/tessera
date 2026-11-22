"""PDF to Word, PowerPoint, Excel, images and Markdown."""

from __future__ import annotations

import io
import os
import re
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
from pypdf import PdfReader

from ..filesystem import replace_with_retry
from ..pdf import render
from ..pdf.common import open_reader, unique_path
from ..progress import Progress
from .structure import Block, document_blocks


def _atomic(output: str | Path, ext: str) -> tuple[Path, Path]:
    out = Path(output)
    if out.suffix.lower() != f".{ext}":
        out = out.with_name(out.name + f".{ext}")
    out.parent.mkdir(parents=True, exist_ok=True)
    return out, out.with_name(f".{out.stem}.{os.getpid()}.tmp.{ext}")


def _finish(tmp: Path, out: Path, **extra) -> dict:
    replace_with_retry(tmp, out)
    return {"path": str(out), "name": out.name, "size": out.stat().st_size, **extra}


def _indexes(path: str, pages: list[int] | None) -> list[int]:
    count = len(open_reader(path).pages)
    if pages is None:
        return list(range(count))
    bad = [p for p in pages if not 0 <= p < count]
    if bad:
        raise ValueError(f"Page {bad[0] + 1} doesn't exist")
    return pages


# --- Word ------------------------------------------------------------------------


def to_word(path: str, output: str, engine: str = "auto", fmt: str = "docx", progress: Progress | None = None) -> dict:
    """engine "word" uses Microsoft Word's PDF import (best layout); "basic" rebuilds the
    text structure (headings, lists, tables) with python-docx."""
    from ..convert import office

    open_reader(path)  # clear error for unreadable / protected files
    if fmt not in ("docx", "doc"):
        raise ValueError(f"Unknown format: {fmt!r}")
    word_ok = office.engines()["office"]["word"]
    if engine == "auto":
        engine = "word" if word_ok else "basic"
    if engine == "word" and not word_ok:
        raise RuntimeError("Microsoft Word isn't installed")
    if engine == "basic" and fmt == "doc":
        raise ValueError("The built-in converter writes .docx; .doc needs Microsoft Word")
    out, tmp = _atomic(output, fmt)
    try:
        if engine == "word":
            if progress:
                progress(0, 1, "Microsoft Word is converting the PDF…")

            def work(word):
                word.Visible = False
                word.DisplayAlerts = 0
                doc = word.Documents.Open(
                    FileName=str(Path(path).resolve()),
                    ConfirmConversions=False,
                    ReadOnly=True,
                    AddToRecentFiles=False,
                    Visible=False,
                    NoEncodingDialog=True,
                )
                try:
                    doc.SaveAs2(FileName=str(tmp), FileFormat=16 if fmt == "docx" else 0)
                finally:
                    doc.Close(SaveChanges=0)

            with office._LOCK:
                try:
                    office._run_office("Word.Application", "Documents", work)
                except RuntimeError as exc:
                    raise RuntimeError(f"Microsoft Word couldn't convert the PDF: {exc}") from None
        else:
            _basic_docx(path, tmp, progress)
        return _finish(tmp, out, engine=engine)
    finally:
        tmp.unlink(missing_ok=True)


def _basic_docx(path: str, target: Path, progress: Progress | None) -> None:
    from docx import Document
    from docx.enum.text import WD_BREAK

    doc = Document()
    pages = document_blocks(path, progress=progress)
    for n, blocks in enumerate(pages):
        for b in blocks:
            if b.kind == "heading":
                doc.add_heading(b.text, level=min(b.level, 4))
            elif b.kind == "bullet":
                doc.add_paragraph(b.text, style="List Bullet")
            elif b.kind == "numbered":
                doc.add_paragraph(b.text, style="List Number")
            elif b.kind == "table":
                cols = max(len(r) for r in b.rows)
                table = doc.add_table(rows=len(b.rows), cols=cols)
                table.style = "Table Grid"
                for r, row in enumerate(b.rows):
                    for c, value in enumerate(row):
                        table.cell(r, c).text = value
            else:
                doc.add_paragraph(b.text)
        if n < len(pages) - 1:
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.save(target)


# --- PowerPoint ---------------------------------------------------------------------

EMU_PER_POINT = 12700
MAX_SLIDE_EMU = 51206400  # PowerPoint's limit: 56 inches


def to_powerpoint(path: str, output: str, dpi: int = 150, notes: bool = True, progress: Progress | None = None) -> dict:
    """One slide per page, showing the page as a picture; its text goes into the speaker notes."""
    from pptx import Presentation

    if not 72 <= dpi <= 300:
        raise ValueError("Resolution must be 72–300 dpi")
    reader = open_reader(path)
    out, tmp = _atomic(output, "pptx")
    first = reader.pages[0]
    w_pt, h_pt = (float(first.cropbox.height), float(first.cropbox.width)) if first.rotation % 180 else (float(first.cropbox.width), float(first.cropbox.height))
    scale = min(1.0, MAX_SLIDE_EMU / (max(w_pt, h_pt) * EMU_PER_POINT))
    prs = Presentation()
    prs.slide_width = int(w_pt * EMU_PER_POINT * scale)
    prs.slide_height = int(h_pt * EMU_PER_POINT * scale)
    blank = prs.slide_layouts[6]
    total = len(reader.pages)
    try:
        with render._LOCK:
            doc = pdfium.PdfDocument(path)
            try:
                for i in range(total):
                    page = doc[i]
                    try:
                        image = page.render(scale=dpi / 72).to_pil().convert("RGB")
                    finally:
                        page.close()
                    buf = io.BytesIO()
                    image.save(buf, "PNG", optimize=True)
                    buf.seek(0)
                    slide = prs.slides.add_slide(blank)
                    # Fit the page inside the slide, centred (pages may differ in shape).
                    fit = min(prs.slide_width / image.width, prs.slide_height / image.height)
                    width, height = int(image.width * fit), int(image.height * fit)
                    slide.shapes.add_picture(buf, (prs.slide_width - width) // 2, (prs.slide_height - height) // 2, width, height)
                    if notes:
                        text = (reader.pages[i].extract_text() or "").strip()
                        if text:
                            slide.notes_slide.notes_text_frame.text = text
                    if progress:
                        progress(i + 1, total, f"Slide {i + 1} of {total}")
            finally:
                doc.close()
        prs.save(tmp)
        return _finish(tmp, out, slides=total)
    finally:
        tmp.unlink(missing_ok=True)


# --- Excel ----------------------------------------------------------------------------

_NUMBER = re.compile(r"^\(?[-+]?[$€£¥]?\s*\d[\d.,\s']*\)?%?$")


def to_number(text: str):
    """'1,234.50' -> 1234.5, '1.234,5' -> 1234.5, '(12)' -> -12, '15%' -> 0.15; else the text."""
    s = (text or "").strip()
    if not s or not _NUMBER.match(s):
        return text
    negative = s.startswith("(") and s.endswith(")")
    percent = s.endswith("%")
    s = s.strip("()%").replace("$", "").replace("€", "").replace("£", "").replace("¥", "").replace(" ", "").replace("'", "")
    if s.startswith("+"):
        s = s[1:]
    if "," in s and "." in s:
        s = s.replace(",", "") if s.rfind(".") > s.rfind(",") else s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", "") if re.fullmatch(r"-?\d{1,3}(,\d{3})+", s) else s.replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3}){2,}", s):
        s = s.replace(".", "")
    try:
        value = float(s)
    except ValueError:
        return text
    if negative:
        value = -value
    if percent:
        value /= 100
    return int(value) if value.is_integer() and not percent and "." not in s else value


def to_excel(path: str, output: str, pages: list[int] | None = None, detection: str = "auto", progress: Progress | None = None) -> dict:
    """Tables to sheets (one per table). detection: "lines" (ruled tables), "text" (aligned columns), "auto"."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    if detection not in ("auto", "lines", "text"):
        raise ValueError(f"Unknown detection mode: {detection!r}")
    indexes = _indexes(path, pages)
    wb = Workbook()
    wb.remove(wb.active)
    tables_found = 0
    text_settings = {"vertical_strategy": "text", "horizontal_strategy": "text"}
    with pdfplumber.open(path) as pdf:
        for n, i in enumerate(indexes):
            page = pdf.pages[i]
            tables = [] if detection == "text" else page.extract_tables()
            if not tables and detection in ("auto", "text"):
                tables = page.extract_tables(text_settings)
            for k, table in enumerate(tables):
                rows = [[(c or "").strip() for c in row] for row in table if any((c or "").strip() for c in row)]
                if not rows:
                    continue
                tables_found += 1
                ws = wb.create_sheet(f"Page {i + 1}" + (f" ({k + 1})" if len(tables) > 1 else ""))
                for row in rows:
                    ws.append([to_number(c) for c in row])
                for cell in ws[1]:
                    cell.font = Font(bold=True)
                ws.freeze_panes = "A2"
                for c in range(1, ws.max_column + 1):
                    width = max(len(str(ws.cell(r, c).value or "")) for r in range(1, ws.max_row + 1))
                    ws.column_dimensions[get_column_letter(c)].width = min(60, max(8, width + 2))
            if progress:
                progress(n + 1, len(indexes), f"Page {i + 1}")
    if not tables_found:
        raise ValueError("No tables were found on the selected pages")
    out, tmp = _atomic(output, "xlsx")
    try:
        wb.save(tmp)
        return _finish(tmp, out, tables=tables_found)
    finally:
        tmp.unlink(missing_ok=True)


# --- images ---------------------------------------------------------------------------


def to_images(
    path: str,
    output_dir: str | None,
    pages: list[int] | None = None,
    fmt: str = "jpg",
    dpi: int = 150,
    quality: int = 90,
    mode: str = "pages",
    progress: Progress | None = None,
) -> dict:
    """mode "pages": render each page; "extract": save the images embedded in the pages as they are."""
    if fmt not in ("jpg", "png"):
        raise ValueError(f"Unknown image format: {fmt!r}")
    if not 36 <= dpi <= 600:
        raise ValueError("Resolution must be 36–600 dpi")
    src = Path(path)
    folder = Path(output_dir or src.parent)
    folder.mkdir(parents=True, exist_ok=True)
    indexes = _indexes(path, pages)
    files: list[dict] = []
    if mode == "extract":
        reader = PdfReader(path)
        for n, i in enumerate(indexes):
            for k, img in enumerate(reader.pages[i].images, 1):
                ext = Path(img.name).suffix or ".png"
                target = unique_path(folder / f"{src.stem}_p{i + 1}_{k}{ext}")
                target.write_bytes(img.data)
                files.append({"path": str(target), "name": target.name, "size": target.stat().st_size})
            if progress:
                progress(n + 1, len(indexes), f"Page {i + 1}")
        if not files:
            raise ValueError("The selected pages contain no embedded images")
        return {"files": files, "folder": str(folder)}

    with render._LOCK:
        doc = pdfium.PdfDocument(path)
        try:
            for n, i in enumerate(indexes):
                page = doc[i]
                try:
                    image = page.render(scale=dpi / 72).to_pil()
                finally:
                    page.close()
                target = unique_path(folder / f"{src.stem}_p{i + 1}.{fmt}")
                if fmt == "jpg":
                    image.convert("RGB").save(target, "JPEG", quality=quality, dpi=(dpi, dpi), optimize=True)
                else:
                    image.save(target, "PNG", dpi=(dpi, dpi), optimize=True)
                files.append({"path": str(target), "name": target.name, "size": target.stat().st_size})
                if progress:
                    progress(n + 1, len(indexes), f"Page {i + 1} of {len(indexes)}")
        finally:
            doc.close()
    return {"files": files, "folder": str(folder)}


# --- Markdown -------------------------------------------------------------------------


def _md_escape_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _md_table(rows: list[list[str]]) -> str:
    cols = max(len(r) for r in rows)
    rows = [r + [""] * (cols - len(r)) for r in rows]
    lines = ["| " + " | ".join(_md_escape_cell(c) for c in rows[0]) + " |", "|" + "---|" * cols]
    lines += ["| " + " | ".join(_md_escape_cell(c) for c in r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def blocks_to_markdown(pages: list[list[Block]], page_breaks: bool = False) -> str:
    parts: list[str] = []
    for n, blocks in enumerate(pages):
        if page_breaks and n:
            parts.append(f"<!-- page {n + 1} -->")
        number = 0
        for b in blocks:
            if b.kind != "numbered":
                number = 0
            if b.kind == "heading":
                parts.append("#" * b.level + " " + b.text)
            elif b.kind == "bullet":
                parts.append("- " + b.text)
            elif b.kind == "numbered":
                number += 1
                parts.append(f"{number}. {b.text}")
            elif b.kind == "table":
                parts.append(_md_table(b.rows))
            else:
                parts.append(b.text)
    # Keep list items together; separate everything else with a blank line.
    out: list[str] = []
    for part in parts:
        is_item = part.startswith("- ") or re.match(r"^\d+\. ", part)
        if out and not (is_item and (out[-1].startswith("- ") or re.match(r"^\d+\. ", out[-1]))):
            out.append("")
        out.append(part)
    return "\n".join(out).strip() + "\n"


def to_markdown(path: str, output: str, pages: list[int] | None = None, page_breaks: bool = False, progress: Progress | None = None) -> dict:
    indexes = _indexes(path, pages)
    text = blocks_to_markdown(document_blocks(path, indexes, progress), page_breaks)
    out, tmp = _atomic(output, "md")
    try:
        tmp.write_text(text, encoding="utf-8")
        return _finish(tmp, out, characters=len(text))
    finally:
        tmp.unlink(missing_ok=True)


def markdown_preview(path: str, pages: list[int] | None = None) -> str:
    return blocks_to_markdown(document_blocks(path, _indexes(path, pages)))
