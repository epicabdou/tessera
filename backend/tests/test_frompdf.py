import os

import pytest
from PIL import Image

from samples import make_report
from toolbox.services import frompdf
from toolbox.services.frompdf import convert as fp
from toolbox.services.frompdf.structure import document_blocks


@pytest.fixture
def report(tmp_path):
    return str(make_report(tmp_path / "report.pdf", with_image=True))


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
    [("1,234.50", 1234.5), ("1.234,5", 1234.5), ("950", 950), ("3.50", 3.5), ("(12)", -12), ("15%", 0.15), ("12,5", 12.5), ("abc", "abc"), ("1.234.567", 1234567)],
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
