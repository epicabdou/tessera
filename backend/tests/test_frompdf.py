import os
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from samples import PROSE, make_layout, make_report, make_scan
from toolbox.services import frompdf
from toolbox.services.convert import office
from toolbox.services.frompdf import convert as fp
from toolbox.services.frompdf.structure import document_blocks


@pytest.fixture
def report(tmp_path):
    return str(make_report(tmp_path / "report.pdf", with_image=True))


@pytest.fixture
def layout(tmp_path):
    return str(make_layout(tmp_path / "layout.pdf"))


def test_heading_levels_follow_the_documents_own_sizes(layout):
    (page,) = document_blocks(layout)
    headings = [(b.level, b.text) for b in page if b.kind == "heading"]
    assert headings == [(1, "Annual Review"), (2, "Operations"), (3, "Logistics")]


def test_only_wrapped_lines_join_a_paragraph(layout):
    (page,) = document_blocks(layout)
    paragraphs = [b.text for b in page if b.kind == "paragraph"]
    assert PROSE in paragraphs  # its wrapped lines are one paragraph
    # Short lines stay apart: an address, and the rows of a table without lines.
    assert ["Head office", "12 Rue Larbi Ben M'hidi", "Oran"] == paragraphs[1:4]
    assert "Steel brackets 40 100.00" in paragraphs and "Hex bolts 250 30.00" in paragraphs


def test_bullets_drawn_as_shapes(layout):
    (page,) = document_blocks(layout)
    assert [b.text for b in page if b.kind == "bullet"] == ["Fleet renewed", "Two depots opened"]


def test_excel_finds_a_table_without_lines_and_leaves_prose_alone(layout, tmp_path):
    from openpyxl import load_workbook

    for detection in ("auto", "text"):
        res = fp.to_excel(layout, str(tmp_path / f"{detection}.xlsx"), detection=detection)
        wb = load_workbook(res["path"])
        assert wb.sheetnames == ["Page 1"]
        assert [[c.value for c in row] for row in wb["Page 1"].iter_rows()] == [
            ["Item", "Qty", "Total"],
            ["Steel brackets", 40, 100],
            ["Hex bolts", 250, 30],
            ["Delivery", 1, 25],
        ]
    with pytest.raises(ValueError, match="No tables"):
        fp.to_excel(layout, str(tmp_path / "lines.xlsx"), detection="lines")


def test_a_scan_asks_for_ocr(tmp_path):
    scan = str(make_scan(tmp_path / "scan.pdf"))
    for convert in (
        lambda: fp.to_word(scan, str(tmp_path / "s.docx"), engine="basic"),
        lambda: fp.to_markdown(scan, str(tmp_path / "s.md")),
        lambda: fp.markdown_preview(scan),
        lambda: fp.to_excel(scan, str(tmp_path / "s.xlsx")),
    ):
        with pytest.raises(ValueError, match="OCR PDF"):
            convert()
    assert not list(tmp_path.glob("s.*"))


@pytest.fixture
def fake_word(monkeypatch):
    """Office replaced by enough of Word.Application for to_word; records what it was asked to open."""
    seen: dict = {}

    class Doc:
        def SaveAs2(self, FileName, FileFormat):
            Path(FileName).write_bytes(b"converted")

        def Close(self, SaveChanges):
            pass

    class Documents:
        def Open(self, FileName, **kwargs):
            seen["opened"] = FileName
            seen["encrypted"] = PdfReader(FileName).is_encrypted
            return Doc()

    class Word:
        pass

    def run_office(progid, collection, work, helpers=()):
        seen["helpers"] = helpers
        if seen.get("fail"):
            raise RuntimeError(seen["fail"])
        word = Word()
        word.Documents = Documents()
        work(word)

    monkeypatch.setattr(office, "_run_office", run_office)
    monkeypatch.setattr(office, "engines", lambda: {"office": {"word": True, "excel": True, "powerpoint": True}, "libreoffice": None})
    return seen


def test_word_engine_opens_a_private_decrypted_copy(report, tmp_path, fake_word):
    locked = tmp_path / "locked.pdf"
    writer = PdfWriter(clone_from=report)
    writer.encrypt(user_password="", owner_password="owner", algorithm="AES-256")  # opens without a password
    writer.write(locked)
    res = fp.to_word(str(locked), str(tmp_path / "out.docx"))
    assert res["engine"] == "word" and Path(res["path"]).read_bytes() == b"converted"
    opened = Path(fake_word["opened"])
    # Never the user's own path (Word would remember it if a run were cut short), and decrypted (Word refuses those).
    assert opened.name == "locked.pdf" and opened.parent != tmp_path and not fake_word["encrypted"]
    assert not opened.parent.exists()  # the copy is cleaned up
    # PDFREFLOW.EXE asks "Word will now convert your PDF…": the watchdog must look at it.
    assert fake_word["helpers"] == ("PDFREFLOW.EXE",)


def test_word_engine_failure_points_to_the_builtin_converter(report, tmp_path, fake_word):
    fake_word["fail"] = "it stopped to show a message that can't be answered while it runs in the background, so it was closed"
    with pytest.raises(RuntimeError, match="Microsoft Word couldn't convert the PDF: it stopped.*built-in converter"):
        fp.to_word(report, str(tmp_path / "out.docx"))
    assert not list(tmp_path.glob("*.docx")) and not list(tmp_path.glob(".*.tmp.docx"))


def test_extract_skips_images_it_cant_decode(report, tmp_path, monkeypatch):
    good = PdfReader(report).pages[0].images[0]

    class Images:
        def __len__(self):
            return 2

        def __getitem__(self, k):
            if k == 0:
                raise NotImplementedError("unsupported filter /JBIG2Decode")
            return good

    class Page:
        images = Images()

    class Reader:
        pages = [Page(), Page()]

    monkeypatch.setattr(fp, "open_reader", lambda path: Reader())
    res = fp.to_images(report, str(tmp_path / "img"), pages=[0], mode="extract")
    assert [f["name"] for f in res["files"]] == ["report_p1_2.png"] and res["skipped"] == 1


def test_structure(report):
    page1, page2 = document_blocks(report)
    kinds = [(b.kind, b.level, b.text) for b in page1 if b.kind != "table"]
    assert ("heading", 1, "Quarterly Report") in kinds
    assert ("heading", 3, "Summary") in kinds or ("heading", 2, "Summary") in kinds
    assert ("paragraph", 0, "Sales grew strongly this quarter across all regions, led by the north.") in kinds
    assert [t for k, _, t in kinds if k == "bullet"] == ["Revenue up 12%", "Costs down 3%"]
    assert [t for k, _, t in kinds if k == "numbered"] == ["Hire two engineers", "Open the Oran office"]
    (table,) = [b for b in page1 if b.kind == "table"]
    assert table.rows == [["Region", "Units", "Price"], ["North", "1,200", "3.50"], ["South", "950", "4.25"]]
    assert page2[0].kind == "heading" and page2[0].text == "Outlook"


def test_markdown(report, tmp_path):
    res = fp.to_markdown(report, str(tmp_path / "out.md"), page_breaks=True)
    md = (tmp_path / "out.md").read_text(encoding="utf-8")
    assert res["name"] == "out.md"
    assert md.startswith("# Quarterly Report\n")
    assert "- Revenue up 12%\n- Costs down 3%" in md
    assert "1. Hire two engineers\n2. Open the Oran office" in md
    assert "| Region | Units | Price |\n|---|---|---|\n| North | 1,200 | 3.50 |" in md
    assert "<!-- page 2 -->" in md and "Outlook" in md


def test_word_basic(report, tmp_path):
    from docx import Document

    res = fp.to_word(report, str(tmp_path / "out.docx"), engine="basic")
    assert res["engine"] == "basic"
    doc = Document(res["path"])
    styles = {(p.style.name, p.text) for p in doc.paragraphs}
    assert ("Heading 1", "Quarterly Report") in styles
    assert ("List Bullet", "Revenue up 12%") in styles
    assert ("List Number", "Open the Oran office") in styles
    assert doc.tables[0].cell(1, 0).text == "North"
    with pytest.raises(ValueError):
        fp.to_word(report, str(tmp_path / "x.doc"), engine="basic", fmt="doc")


def test_powerpoint(report, tmp_path):
    from pptx import Presentation

    res = fp.to_powerpoint(report, str(tmp_path / "out.pptx"), dpi=96)
    prs = Presentation(res["path"])
    assert res["slides"] == 2 and len(prs.slides) == 2
    assert round(prs.slide_width / prs.slide_height, 2) == round(595.28 / 841.89, 2)  # A4 portrait
    assert "Quarterly Report" in prs.slides[0].notes_slide.notes_text_frame.text


def test_excel(report, tmp_path):
    from openpyxl import load_workbook

    res = fp.to_excel(report, str(tmp_path / "out.xlsx"))
    wb = load_workbook(res["path"])
    ws = wb["Page 1"]
    assert [c.value for c in ws[1]] == ["Region", "Units", "Price"]
    assert [c.value for c in ws[2]] == ["North", 1200, 3.5]
    assert res["tables"] >= 1
    with pytest.raises(ValueError, match="No tables"):
        fp.to_excel(report, str(tmp_path / "none.xlsx"), pages=[1], detection="lines")


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("1,234.50", 1234.5),
        ("1.234,5", 1234.5),
        ("950", 950),
        ("3.50", 3.5),
        ("(12)", -12),
        ("15%", 0.15),
        ("12,5", 12.5),
        ("abc", "abc"),
        ("1.234.567", 1234567),
        # codes keep their leading zeros; amounts below one still become numbers
        ("007", "007"),
        ("0555 12 34 56", "0555 12 34 56"),
        ("0.5", 0.5),
        ("0,25", 0.25),
        ("0", 0),
    ],
)
def test_to_number(text, value):
    assert fp.to_number(text) == value


def test_images(report, tmp_path):
    res = fp.to_images(report, str(tmp_path / "pages"), fmt="png", dpi=72)
    assert [f["name"] for f in res["files"]] == ["report_p1.png", "report_p2.png"]
    w, h = Image.open(res["files"][0]["path"]).size
    assert abs(w - 595) <= 1 and abs(h - 842) <= 1  # A4 at 72 dpi (PDFium rounds 595.28 up)
    jpg = fp.to_images(report, str(tmp_path / "pages"), pages=[0], fmt="jpg", dpi=50)
    assert jpg["files"][0]["name"] == "report_p1.jpg"
    extracted = fp.to_images(report, str(tmp_path / "img"), mode="extract")
    assert len(extracted["files"]) == 1 and Image.open(extracted["files"][0]["path"]).size == (120, 80)
    with pytest.raises(ValueError, match="no embedded images"):
        fp.to_images(report, str(tmp_path / "img"), pages=[1], mode="extract")


def test_suggest_path(tmp_path):
    src = tmp_path / "a.pdf"
    assert frompdf.suggest_path(str(src), "docx") == str(tmp_path / "a.docx")
    (tmp_path / "a.docx").write_text("x")
    assert frompdf.suggest_path(str(src), ".docx").endswith("a (2).docx")


@pytest.mark.skipif(os.environ.get("TOOLBOX_OFFICE_TESTS") != "1", reason="set TOOLBOX_OFFICE_TESTS=1")
def test_word_engine(report, tmp_path):
    from docx import Document

    res = fp.to_word(report, str(tmp_path / "out.docx"), engine="word")
    text = "\n".join(p.text for p in Document(res["path"]).paragraphs)
    assert res["engine"] == "word" and "Quarterly Report" in text
