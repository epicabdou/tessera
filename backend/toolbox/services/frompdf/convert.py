"""PDF to Word, PowerPoint, Excel, images and Markdown."""

from __future__ import annotations

import io
import os
import re
import shutil
import tempfile
from pathlib import Path
from statistics import median

import pdfplumber
import pypdfium2 as pdfium
from pypdf import PdfWriter

from ..filesystem import replace_with_retry
from ..pdf import render
from ..pdf.common import open_reader, unique_path
from ..progress import Progress
from .structure import MARKER_RE, NO_TEXT, Block, inside, document_blocks, require_text


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

    reader = open_reader(path)  # clear error for unreadable / protected files
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
            # Word opens a private copy: if a run is ever cut short, Word remembers that path as
            # one that "caused a serious error" and asks about it next time, which would block
            # every later conversion of the user's file.
            work_dir = Path(tempfile.mkdtemp(prefix="tilepress-word-"))
            copy = work_dir / Path(path).name
            if reader.is_encrypted:
                # Opens without a password but restricts editing: Word refuses those ("it may be
                # corrupted"), so it gets the decrypted pages.
                PdfWriter(clone_from=reader).write(copy)
            else:
                shutil.copyfile(path, copy)

            def work(word):
                word.Visible = False
                word.DisplayAlerts = 0
                doc = word.Documents.Open(
                    FileName=str(copy),
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

            try:
                with office._LOCK:
                    # PDFREFLOW.EXE does the import and first asks "Word will now convert your PDF…":
                    # DisplayAlerts doesn't reach it, so the watchdog answers OK.
                    office._run_office("Word.Application", "Documents", work, helpers=("PDFREFLOW.EXE",))
            except RuntimeError as exc:
                raise RuntimeError(f"Microsoft Word couldn't convert the PDF: {exc}. Try again, or choose the built-in converter.") from None
            finally:
                shutil.rmtree(work_dir, ignore_errors=True)
        else:
            _basic_docx(path, tmp, progress)
        return _finish(tmp, out, engine=engine)
    finally:
        tmp.unlink(missing_ok=True)


def _basic_docx(path: str, target: Path, progress: Progress | None) -> None:
    from docx import Document
    from docx.enum.text import WD_BREAK

    doc = Document()
    pages = require_text(path, document_blocks(path, progress=progress))
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
    if re.match(r"^[-+]?0\d", s):
        return text  # a code, not an amount: "007", ZIP codes, phone numbers keep their leading zeros
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


TEXT_TABLES = {"vertical_strategy": "text", "horizontal_strategy": "text", "min_words_vertical": 2}

Rows = list[list[str | None]]


def _text_rows(words: list[dict]) -> list[list[dict]]:
    rows: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and abs(rows[-1][0]["top"] - w["top"]) <= 2:
            rows[-1].append(w)
        else:
            rows.append([w])
    for row in rows:
        row.sort(key=lambda w: w["x0"])
    return rows


def _tabular_regions(words: list[dict]) -> list[tuple[float, float, float, float]]:
    """Where a table without lines may be: runs of two or more consecutive lines that wide gaps
    split into cells. Prose lines only have word spaces, so they're never part of one."""
    regions: list[tuple[float, float, float, float]] = []
    run: list[list[dict]] = []

    def close() -> None:
        if len(run) >= 2:
            ws = [w for row in run for w in row]
            regions.append((min(w["x0"] for w in ws) - 1, min(w["top"] for w in ws) - 1, max(w["x1"] for w in ws) + 1, max(w["bottom"] for w in ws) + 1))
        run.clear()

    for row in _text_rows(words):
        height = median(w["bottom"] - w["top"] for w in row)
        text = row[1:] if len(row) > 1 and MARKER_RE.match(row[0]["text"]) else row  # "•   item" is a list, not 2 cells
        cells = 1 + sum(1 for a, b in zip(text, text[1:]) if b["x0"] - a["x1"] > max(6.0, height))
        close_to_last = bool(run) and min(w["top"] for w in row) - max(w["bottom"] for w in run[-1]) < 2.5 * height
        if cells < 2 or not close_to_last:
            close()
        if cells >= 2:
            run.append(row)
    close()
    return regions


def _usable(rows: Rows) -> bool:
    """At least 2 x 2, with two filled cells in two rows."""
    return len(rows) >= 2 and max(len(r) for r in rows) >= 2 and sum(1 for r in rows if sum(1 for c in r if (c or "").strip()) >= 2) >= 2


def _cuts_words(table, words: list[dict]) -> bool:
    """Whether an edge of `table` (its sides included) runs through a word, as when prose or a
    list is read as a table: then words are split, or partly left out."""
    x0, top, x1, bottom = table.bbox
    edges = {c[0] for c in table.cells} | {c[2] for c in table.cells}
    return any(
        w["x1"] > x0 and w["x0"] < x1 and top <= (w["top"] + w["bottom"]) / 2 <= bottom and any(w["x0"] + 0.5 < e < w["x1"] - 0.5 for e in edges)
        for w in words
    )


def _text_tables(page: "pdfplumber.page.Page", ruled: list[tuple], strict: bool) -> list[tuple[float, Rows]]:
    """(top, rows) of the tables without lines on `page`, outside the `ruled` table boxes.

    pdfplumber's text-alignment finder, run over a whole page, reads prose into a "table" too and
    cuts words in two, so it only looks inside the likely regions. `strict` (automatic mode) also
    drops any table whose edges cut words; the user's explicit "aligned text" choice keeps them."""
    words = [w for w in page.extract_words() if not inside(w, ruled)]
    found: list[tuple[float, Rows]] = []
    for bbox in _tabular_regions(words):
        x0, top, x1, bottom = page.bbox
        region = page.within_bbox((max(bbox[0], x0), max(bbox[1], top), min(bbox[2], x1), min(bbox[3], bottom)))
        region_words = region.extract_words()
        for table in region.find_tables(TEXT_TABLES):
            rows = table.extract()
            if _usable(rows) and not (strict and _cuts_words(table, region_words)):
                found.append((table.bbox[1], rows))
    return found


def to_excel(path: str, output: str, pages: list[int] | None = None, detection: str = "auto", progress: Progress | None = None) -> dict:
    """Tables to sheets (one per table). detection: "lines" (ruled tables), "text" (aligned columns),
    "auto" (ruled tables, plus clear-cut tables without lines)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    if detection not in ("auto", "lines", "text"):
        raise ValueError(f"Unknown detection mode: {detection!r}")
    indexes = _indexes(path, pages)
    wb = Workbook()
    wb.remove(wb.active)
    tables_found = 0
    has_text = False
    with pdfplumber.open(path) as pdf:
        for n, i in enumerate(indexes):
            page = pdf.pages[i]
            has_text = has_text or bool(page.chars)
            ruled = [] if detection == "text" else page.find_tables()
            found = [(t.bbox[1], t.extract()) for t in ruled]
            if detection in ("auto", "text"):
                found += _text_tables(page, [t.bbox for t in ruled], strict=detection == "auto")
            tables = [rows for _, rows in sorted(found, key=lambda f: f[0])]
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
        if not has_text:
            raise ValueError(NO_TEXT.format(name=Path(path).name))
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
        reader = open_reader(path)
        skipped = 0
        for n, i in enumerate(indexes):
            try:
                images = reader.pages[i].images
                count = len(images)
            except Exception:  # noqa: BLE001 - a page whose image list pypdf can't read
                images, count, skipped = None, 0, skipped + 1
            for k in range(count):
                # pypdf decodes each image as it's fetched: one in an encoding it can't decode
                # mustn't cost the others.
                try:
                    img = images[k]
                    data, ext = img.data, Path(img.name).suffix or ".png"
                except Exception:  # noqa: BLE001
                    skipped += 1
                    continue
                target = unique_path(folder / f"{src.stem}_p{i + 1}_{k + 1}{ext}")
                target.write_bytes(data)
                files.append({"path": str(target), "name": target.name, "size": target.stat().st_size})
            if progress:
                progress(n + 1, len(indexes), f"Page {i + 1}")
        if not files:
            if skipped:
                raise ValueError(f"The images on the selected pages use an encoding that can't be extracted ({skipped} skipped). Save the pages as images instead.")
            raise ValueError("The selected pages contain no embedded images")
        return {"files": files, "folder": str(folder), "skipped": skipped}

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
    text = blocks_to_markdown(require_text(path, document_blocks(path, indexes, progress)), page_breaks)
    out, tmp = _atomic(output, "md")
    try:
        tmp.write_text(text, encoding="utf-8")
        return _finish(tmp, out, characters=len(text))
    finally:
        tmp.unlink(missing_ok=True)


def markdown_preview(path: str, pages: list[int] | None = None) -> str:
    return blocks_to_markdown(require_text(path, document_blocks(path, _indexes(path, pages))))
