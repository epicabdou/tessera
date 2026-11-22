import pdfplumber
import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from samples import make_report, make_scan
from toolbox.services.editing import edit, forms, ocr, watermark
from toolbox.services.editing.geometry import visual_rect_to_user


@pytest.fixture
def report(tmp_path):
    return str(make_report(tmp_path / "report.pdf"))


def text(path, page=0):
    return PdfReader(path).pages[page].extract_text()


# --- geometry -----------------------------------------------------------------------


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_visual_rect_to_user_matches_what_is_displayed(tmp_path, rotation):
    """Fill the converted rect in user space, render with PDFium (which applies /Rotate),
    and check the dark box shows up exactly where it was placed on screen."""
    import base64
    import io

    from pypdf.generic import DecodedStreamObject, NameObject
    from toolbox.services.pdf import render

    w = PdfWriter()
    page = w.add_blank_page(600, 400)
    page.rotation = rotation
    llx, lly, urx, ury = visual_rect_to_user(page, 10, 20, 30, 50)
    s = DecodedStreamObject()
    s.set_data(f"0 g {llx} {lly} {urx - llx} {ury - lly} re f".encode())
    page[NameObject("/Contents")] = w._add_object(s)
    src = tmp_path / f"r{rotation}.pdf"
    w.write(src)
    shown = render.render_pages(str(src), [0], 600 if rotation % 180 == 0 else 400)[0]
    im = Image.open(io.BytesIO(base64.b64decode(shown.split(",", 1)[1]))).convert("L")
    x0, y0, x1, y1 = im.point(lambda v: 255 if v < 128 else 0).getbbox()
    assert (x0, y0, x1 - x0, y1 - y0) == pytest.approx((10, 20, 30, 50), abs=2)


# --- edit -------------------------------------------------------------------------


def test_text_lines(report):
    lines = edit.text_lines(report, 0)
    title = next(l for l in lines if l["text"] == "Quarterly Report")
    assert title["size"] == 24 and title["bold"] and title["family"] == "sans"
    # drawn with its baseline 90pt below the top; the line box starts at the cap height above that
    assert title["x"] == pytest.approx(72, abs=1) and title["y"] == pytest.approx(90 - 24 * 0.8, abs=3)


def test_replace_text_and_shapes(report, tmp_path):
    title = next(l for l in edit.text_lines(report, 0) if l["text"] == "Quarterly Report")
    img = tmp_path / "logo.png"
    Image.new("RGBA", (40, 40), (255, 0, 0, 128)).save(img)
    out = tmp_path / "edited.pdf"
    edit.apply_edits(
        report,
        str(out),
        [
            {"type": "whiteout", "page": 0, "x": title["x"] - 1, "y": title["y"] - 1, "w": title["w"] + 2, "h": title["h"] + 2, "remove_text": True},
            {"type": "text", "page": 0, "x": title["x"], "y": title["y"], "w": 300, "h": 30, "text": "Rapport trimestriel – été", "size": 24, "bold": True},
            {"type": "image", "page": 0, "x": 400, "y": 60, "w": 40, "h": 40, "src": str(img)},
            {"type": "rect", "page": 1, "x": 50, "y": 50, "w": 100, "h": 40, "stroke": "#ff0000"},
            {"type": "line", "page": 1, "x1": 50, "y1": 120, "x2": 300, "y2": 120, "stroke": "#0000ff", "width": 2},
            {"type": "highlight", "page": 1, "x": 70, "y": 70, "w": 120, "h": 20},
        ],
    )
    with pdfplumber.open(out) as pdf:
        words = pdf.pages[0].extract_words()
        new = [w for w in words if w["text"] == "Rapport"]
        assert new and new[0]["x0"] == pytest.approx(title["x"], abs=1.5)
        assert pdf.pages[0].images, "image was added"
        assert len(pdf.pages[1].rects) >= 2 and pdf.pages[1].lines
    assert "été" in text(str(out))  # TrueType font handles accents
    assert "Quarterly" not in text(str(out))  # the old line is gone, not just covered
    assert "Summary" in text(str(out))  # …and nothing else was removed
    with pytest.raises(ValueError):
        edit.apply_edits(report, str(out), [])
    with pytest.raises(ValueError):
        edit.apply_edits(report, str(out), [{"type": "sparkles", "page": 0}])


def test_redact_removes_text_for_good(report, tmp_path):
    line = next(l for l in edit.text_lines(report, 0) if l["text"].startswith("Sales grew"))
    out = tmp_path / "redacted.pdf"
    res = edit.apply_edits(report, str(out), [{"type": "redact", "page": 0, "x": line["x"] - 2, "y": line["y"] - 2, "w": line["w"] + 4, "h": line["h"] + 4}])
    assert res["text_removed"] >= 1
    content = text(str(out))
    assert "Sales grew" not in content and "regions, led by" in content  # only the boxed line
    with pdfplumber.open(out) as pdf:
        assert any(r["non_stroking_color"] in ((0,), (0, 0, 0), [0], [0, 0, 0], 0) for r in pdf.pages[0].rects)


def test_edit_rotated_page_lands_where_shown(tmp_path):
    src = tmp_path / "rot.pdf"
    w = PdfWriter()
    w.add_blank_page(600, 400).rotation = 90  # displayed 400 wide x 600 tall
    w.write(src)
    out = tmp_path / "out.pdf"
    edit.apply_edits(str(src), str(out), [{"type": "text", "page": 0, "x": 50, "y": 100, "w": 200, "h": 20, "text": "Upright", "size": 14}])
    with pdfplumber.open(out) as pdf:
        page = pdf.pages[0]
        assert page.width == pytest.approx(400) and page.height == pytest.approx(600)
        word = page.extract_words()[0]
        assert word["text"] == "Upright" and word["x0"] == pytest.approx(50, abs=1.5) and word["top"] == pytest.approx(100, abs=4)


# --- watermark -----------------------------------------------------------------------


def test_text_watermark_tile_and_pages(report, tmp_path):
    out = tmp_path / "wm.pdf"
    res = watermark.watermark(report, str(out), {"kind": "text", "text": "CONFIDENTIAL", "position": "tile", "size": 30, "pages": "1"})
    assert res["watermarked_pages"] == 1
    assert text(str(out), 0).count("CONFIDENTIAL") > 3
    assert "CONFIDENTIAL" not in text(str(out), 1)


def test_image_watermark_under(report, tmp_path):
    img = tmp_path / "logo.png"
    Image.new("RGB", (100, 50), (0, 0, 200)).save(img)
    out = tmp_path / "wm.pdf"
    watermark.watermark(report, str(out), {"kind": "image", "image": str(img), "scale": 0.5, "position": "bottom-right", "layer": "under"})
    with pdfplumber.open(out) as pdf:
        (im,) = pdf.pages[0].images
        assert im["x1"] == pytest.approx(595.28 - 36, abs=1) and im["width"] == pytest.approx(595.28 * 0.5, abs=1)
    with pytest.raises(ValueError):
        watermark.watermark(report, str(out), {"kind": "text", "text": ""})


# --- forms -----------------------------------------------------------------------------


def test_create_list_fill_flatten(report, tmp_path):
    designed = tmp_path / "form.pdf"
    forms.add_fields(
        report,
        str(designed),
        [
            {"page": 0, "type": "text", "name": "full_name", "x": 300, "y": 120, "w": 200, "h": 20, "required": True},
            {"page": 0, "type": "multiline", "name": "notes", "x": 300, "y": 150, "w": 200, "h": 60},
            {"page": 0, "type": "checkbox", "name": "agree", "x": 300, "y": 220, "w": 14, "h": 14},
            {"page": 1, "type": "dropdown", "name": "region", "x": 72, "y": 140, "w": 120, "h": 20, "options": ["North", "South"]},
        ],
    )
    fields = {f["name"]: f for f in forms.list_fields(str(designed))}
    assert {n: f["type"] for n, f in fields.items()} == {"full_name": "text", "notes": "multiline", "agree": "checkbox", "region": "dropdown"}
    assert fields["full_name"]["required"] and fields["region"]["options"] == ["North", "South"]
    assert fields["full_name"]["widgets"][0] == {"page": 0, "x": 300, "y": 120, "w": 200, "h": 20, "state": None}
    with pytest.raises(ValueError, match="already a field"):
        forms.add_fields(str(designed), str(tmp_path / "x.pdf"), [{"page": 0, "type": "text", "name": "agree", "x": 0, "y": 0, "w": 10, "h": 10}])

    filled = tmp_path / "filled.pdf"
    forms.fill(str(designed), str(filled), {"full_name": "Amina Benali", "agree": True, "region": "South"})
    values = {f["name"]: f["value"] for f in forms.list_fields(str(filled))}
    assert values["full_name"] == "Amina Benali" and values["agree"] == "Yes" and values["region"] == "South"

    flat = tmp_path / "flat.pdf"
    forms.fill(str(designed), str(flat), {"full_name": "Amina Benali"}, flatten=True)
    assert "Amina Benali" in text(str(flat))
    with pytest.raises(ValueError, match="No field"):
        forms.fill(str(designed), str(flat), {"nope": "x"})


# --- OCR -----------------------------------------------------------------------------------


@pytest.mark.parametrize("engine", ["tesseract", "windows"])
def test_ocr_makes_scans_searchable(tmp_path, engine):
    available = ocr.engines()
    if engine == "tesseract" and not available["tesseract"]["path"]:
        pytest.skip("Tesseract not installed")
    if engine == "windows" and not available["windows"]["languages"]:
        pytest.skip("Windows OCR not available")
    scan = make_scan(tmp_path / "scan.pdf")
    assert not text(str(scan)).strip()
    out = tmp_path / "searchable.pdf"
    res = ocr.ocr_pdf(str(scan), str(out), engine=engine, dpi=200)
    found = " ".join(text(str(out)).split())
    assert res["pages_recognised"] == 1 and res["words"] >= 5
    assert "invoice 4711" in found.lower() and "128" in found
    # the words sit where they are on the image (top-left area of the page)
    with pdfplumber.open(out) as pdf:
        w = next(w for w in pdf.pages[0].extract_words() if "4711" in w["text"])
        assert w["top"] < 200 and w["x0"] > 100


def test_ocr_skips_pages_that_already_have_text(report, tmp_path):
    if not ocr.engines()["tesseract"]["path"]:
        pytest.skip("Tesseract not installed")
    mixed = tmp_path / "mixed.pdf"
    w = PdfWriter()
    w.append(report, pages=[0])
    w.append(str(make_scan(tmp_path / "scan.pdf")))
    w.write(mixed)
    res = ocr.ocr_pdf(str(mixed), str(tmp_path / "o.pdf"), engine="tesseract", dpi=150)
    assert (res["pages_skipped"], res["pages_recognised"]) == (1, 1)
    assert "invoice" in text(str(tmp_path / "o.pdf"), 1).lower()
