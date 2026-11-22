import re

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from toolbox.services.pdf import common, numbering, ops, render


def make_pdf(path, count=3, rotations=None, content=None, width0=500, height=700):
    """Page i is (width0 + i) points wide, so tests can tell pages apart by width."""
    writer = PdfWriter()
    for i in range(count):
        page = writer.add_blank_page(width0 + i, height)
        if content and content.get(i):
            stream = DecodedStreamObject()
            stream.set_data(content[i])
            page[NameObject("/Contents")] = writer._add_object(stream)
        if rotations and rotations[i]:
            page.rotate(rotations[i])
    writer.write(path)
    return str(path)


def widths(path):
    return [round(float(p.mediabox.width)) for p in PdfReader(path).pages]


# --- ranges ---------------------------------------------------------------------


def test_parse_ranges():
    assert common.parse_ranges("1-3, 5, 8-", 10) == [[0, 1, 2], [4], [7, 8, 9]]
    assert common.parse_ranges("-2; 4", 5) == [[0, 1], [3]]
    assert common.parse_ranges("odd", 5) == [[0, 2, 4]]
    assert common.parse_ranges("EVEN", 5) == [[1, 3]]
    assert common.parse_ranges("all", 3) == [[0, 1, 2]]


@pytest.mark.parametrize("spec", ["", "0", "11", "5-3", "abc", "1--2"])
def test_parse_ranges_errors(spec):
    with pytest.raises(ValueError):
        common.parse_ranges(spec, 10)


def test_format_ranges():
    assert common.format_ranges([6, 0, 1, 2, 4, 7]) == "1-3, 5, 7-8"
    assert common.format_ranges([]) == ""


def test_split_plan():
    assert common.split_plan(7, "every", 3) == [[0, 1, 2], [3, 4, 5], [6]]
    assert common.split_plan(5, "extract", "3, 1-2, 2") == [[0, 1, 2]]
    assert common.split_plan(5, "extract_each", "4, 2") == [[1], [3]]
    assert common.split_plan(5, "ranges", "1-2, 5") == [[0, 1], [4]]
    with pytest.raises(ValueError):
        common.split_plan(5, "every", 0)
    with pytest.raises(ValueError):
        common.split_plan(5, "nope", "1")


# --- reading / writing -----------------------------------------------------------


def test_pdf_info_reports_displayed_size(tmp_path):
    path = make_pdf(tmp_path / "a.pdf", count=2, rotations=[0, 90])
    info = common.pdf_info(path)
    assert info["page_count"] == 2
    assert info["pages"][0] == {"width": 500, "height": 700, "rotation": 0}
    assert info["pages"][1] == {"width": 700, "height": 501, "rotation": 90}


def test_open_reader_rejects_bad_files(tmp_path):
    junk = tmp_path / "junk.pdf"
    junk.write_bytes(b"not a pdf")
    with pytest.raises(ValueError, match="readable PDF"):
        common.open_reader(junk)

    writer = PdfWriter()
    writer.add_blank_page(100, 100)
    writer.encrypt(user_password="secret", algorithm="RC4-128")
    locked = tmp_path / "locked.pdf"
    writer.write(locked)
    with pytest.raises(ValueError, match="password-protected"):
        common.open_reader(locked)


def test_suggest_output_is_unique(tmp_path):
    src = tmp_path / "doc.pdf"
    assert common.suggest_output(src, "rotated").endswith("doc_rotated.pdf")
    (tmp_path / "doc_rotated.pdf").write_bytes(b"x")
    assert common.suggest_output(src, "rotated").endswith("doc_rotated (2).pdf")


# --- operations ------------------------------------------------------------------


def test_merge_with_ranges_and_bookmarks(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", count=3, width0=500)
    b = make_pdf(tmp_path / "b.pdf", count=2, width0=600)
    out = tmp_path / "out.pdf"
    result = ops.merge([{"path": a, "pages": "3, 1"}, {"path": b, "pages": ""}], str(out), bookmarks=True)
    assert result["page_count"] == 4
    assert widths(out) == [502, 500, 600, 601]
    assert [o.title for o in PdfReader(out).outline] == ["a", "b"]


def test_split_by_ranges_names_files(tmp_path):
    src = make_pdf(tmp_path / "doc.pdf", count=5)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "doc_p1-2.pdf").write_bytes(b"existing")  # must not be overwritten
    result = ops.split(src, str(out_dir), "ranges", "1-2, 4, 5")
    names = [f["name"] for f in result["files"]]
    assert names == ["doc_p1-2 (2).pdf", "doc_p4.pdf", "doc_p5.pdf"]
    assert widths(out_dir / "doc_p1-2 (2).pdf") == [500, 501]
    assert (out_dir / "doc_p1-2.pdf").read_bytes() == b"existing"


def test_split_extract_non_contiguous(tmp_path):
    src = make_pdf(tmp_path / "doc.pdf", count=5)
    result = ops.split(src, str(tmp_path), "extract", "1, 3, 5")
    assert [f["name"] for f in result["files"]] == ["doc_part1.pdf"]
    assert widths(result["files"][0]["path"]) == [500, 502, 504]


def test_organize_reorder_duplicate_blank_and_insert(tmp_path):
    doc = make_pdf(tmp_path / "doc.pdf", count=3, width0=500)
    extra = make_pdf(tmp_path / "extra.pdf", count=2, width0=800)
    out = tmp_path / "out.pdf"
    ops.organize(
        str(out),
        {"doc": doc, "ins": extra},
        [
            {"source": "doc", "index": 2},
            {"source": "doc", "index": 0, "rotate": 90},
            {"source": "doc", "index": 0},  # duplicate stays unrotated
            {"blank": True, "width": 300, "height": 400},
            {"source": "ins", "index": 1, "rotate": -90},
        ],
    )
    pages = PdfReader(out).pages
    assert [round(float(p.mediabox.width)) for p in pages] == [502, 500, 500, 300, 801]
    assert [p.rotation for p in pages] == [0, 90, 0, 0, 270]


def test_organize_rejects_bad_input(tmp_path):
    doc = make_pdf(tmp_path / "doc.pdf", count=1)
    with pytest.raises(ValueError):
        ops.organize(str(tmp_path / "o.pdf"), {"doc": doc}, [])
    with pytest.raises(ValueError):
        ops.organize(str(tmp_path / "o.pdf"), {"doc": doc}, [{"source": "doc", "index": 5}])
    with pytest.raises(ValueError):
        ops.organize(str(tmp_path / "o.pdf"), {"doc": doc}, [{"source": "doc", "index": 0, "rotate": 45}])


def test_rotate_in_place(tmp_path):
    path = make_pdf(tmp_path / "doc.pdf", count=3, rotations=[0, 90, 0])
    ops.rotate(path, path, [90, 270, 0])  # output may be the input file
    assert [p.rotation for p in PdfReader(path).pages] == [90, 0, 0]
    with pytest.raises(ValueError):
        ops.rotate(path, path, [90])


def test_crop_margins_follow_displayed_orientation(tmp_path):
    path = make_pdf(tmp_path / "doc.pdf", count=2, rotations=[0, 90], width0=600, height=800)
    out = tmp_path / "out.pdf"
    ops.crop(path, str(out), {"top": 10, "right": 20, "bottom": 30, "left": 40})
    p0, p1 = PdfReader(out).pages
    assert [float(v) for v in p0.cropbox] == [40, 30, 580, 790]
    # Page 1 is shown rotated 90° clockwise: displayed top = its left edge,
    # displayed right = its top, displayed bottom = its right, displayed left = its bottom.
    assert [float(v) for v in p1.cropbox] == [10, 40, 601 - 30, 800 - 20]
    assert [float(v) for v in p1.mediabox] == [float(v) for v in p1.cropbox]


def test_crop_selected_pages_and_limits(tmp_path):
    path = make_pdf(tmp_path / "doc.pdf", count=3)
    out = tmp_path / "out.pdf"
    result = ops.crop(path, str(out), {"top": 50}, pages=[1])
    assert result["cropped_pages"] == "2"
    assert [round(float(p.cropbox.height)) for p in PdfReader(out).pages] == [700, 650, 700]
    with pytest.raises(ValueError, match="nothing"):
        ops.crop(path, str(out), {"top": 400, "bottom": 400})


# --- page numbers ----------------------------------------------------------------


def _number_x(page) -> float:
    match = re.search(rb"([\d.]+) ([\d.]+) Td\s*\(", page.get_contents().get_data())
    return float(match.group(1))


def test_page_numbers_text_and_range(tmp_path):
    path = make_pdf(tmp_path / "doc.pdf", count=4, rotations=[0, 0, 90, 0])
    out = tmp_path / "out.pdf"
    numbering.add_page_numbers(
        path, str(out), {"template": "Page {n} of {total}", "first_page": 2, "start": 1}
    )
    pages = PdfReader(out).pages
    texts = [p.extract_text() for p in pages]
    assert "Page" not in texts[0]
    assert texts[1].strip() == "Page 1 of 3"
    assert texts[3].strip() == "Page 3 of 3"
    assert "Page 2 of 3" in texts[2]
    assert pages[2].rotation == 0  # rotation was baked in so the number is upright


def test_page_numbers_mirror_and_validation(tmp_path):
    path = make_pdf(tmp_path / "doc.pdf", count=2, width0=600)
    out = tmp_path / "out.pdf"
    numbering.add_page_numbers(path, str(out), {"position": "bottom-right", "mirror": True, "margin": 30})
    odd, even = PdfReader(out).pages
    assert _number_x(odd) > 500  # right side
    assert _number_x(even) == pytest.approx(30)  # mirrored to the left
    with pytest.raises(ValueError):
        numbering.add_page_numbers(path, str(out), {"template": "no placeholder"})
    with pytest.raises(ValueError):
        numbering.add_page_numbers(path, str(out), {"position": "middle"})
    with pytest.raises(ValueError):
        numbering.add_page_numbers(path, str(out), {"first_page": 3})


def test_text_width_uses_helvetica_metrics():
    assert numbering.text_width("11", 10) == pytest.approx(11.12)
    assert numbering.text_width("Page", 10) > numbering.text_width("1111", 10) - 1


# --- rendering -------------------------------------------------------------------


def test_render_pages(tmp_path):
    path = make_pdf(tmp_path / "doc.pdf", count=2, rotations=[0, 90])
    urls = render.render_pages(path, [0, 1, 9], 120)
    assert urls[0].startswith("data:image/jpeg;base64,")
    assert urls[1].startswith("data:image/jpeg;base64,")
    assert urls[2] is None
    assert render.render_pages(path, [0], 120) == urls[:1]  # cached


def test_detect_margins_finds_content(tmp_path):
    # Black box from x=100..400, y=200..600 on a 595x842 page.
    path = make_pdf(
        tmp_path / "doc.pdf", count=1, width0=595, height=842, content={0: b"0 g 100 200 300 400 re f"}
    )
    m = render.detect_margins(path, 0, padding=0)
    assert m["left"] == pytest.approx(100, abs=2)
    assert m["right"] == pytest.approx(195, abs=2)
    assert m["top"] == pytest.approx(242, abs=2)
    assert m["bottom"] == pytest.approx(200, abs=2)
