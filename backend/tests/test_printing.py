import sys

import pdfplumber
import pytest
from pypdf import PdfReader

from samples import make_numbered
from toolbox.services.printing import impose as imp


def page_words(path, sheet):
    with pdfplumber.open(path) as pdf:
        p = pdf.pages[sheet]
        return p.width, p.height, [(w["text"], w["x0"], w["top"]) for w in p.extract_words() if w["text"] != "Page"]


def test_booklet_order():
    assert imp.booklet_order(8) == [(7, 0), (1, 6), (5, 2), (3, 4)]
    assert imp.booklet_order(5) == [(None, 0), (1, None), (None, 2), (3, 4)]


def test_nup_four_per_sheet(tmp_path):
    src = make_numbered(tmp_path / "doc.pdf", 6)
    res = imp.impose(str(src), str(tmp_path / "out.pdf"), {"layout": "nup", "per_sheet": 4, "sheet": "a4"})
    assert res["sheets"] == 2 and res["source_pages"] == 6
    w, h, words = page_words(res["path"], 0)
    assert (round(w), round(h)) == (595, 842)
    pos = {t: (x, y) for t, x, y in words}
    # reading order: 1 top-left, 2 top-right, 3 bottom-left, 4 bottom-right
    assert pos["1"][0] < w / 2 and pos["1"][1] < h / 2
    assert pos["2"][0] > w / 2 and pos["2"][1] < h / 2
    assert pos["3"][0] < w / 2 and pos["3"][1] > h / 2
    assert pos["4"][0] > w / 2 and pos["4"][1] > h / 2


def test_two_up_turns_sheet_landscape(tmp_path):
    src = make_numbered(tmp_path / "doc.pdf", 2)
    res = imp.impose(str(src), str(tmp_path / "out.pdf"), {"layout": "nup", "per_sheet": 2, "sheet": "a4"})
    w, h, words = page_words(res["path"], 0)
    assert w > h and [t for t, _, _ in sorted(words, key=lambda x: x[1])] == ["1", "2"]


def test_booklet(tmp_path):
    src = make_numbered(tmp_path / "doc.pdf", 4)
    res = imp.impose(str(src), str(tmp_path / "out.pdf"), {"layout": "booklet"})
    assert res["sheets"] == 2
    w, h, front = page_words(res["path"], 0)
    assert w == pytest.approx(2 * 595.28, abs=1) and h == pytest.approx(841.89, abs=1)
    assert [t for t, _, _ in sorted(front, key=lambda x: x[1])] == ["4", "1"]
    _, _, back = page_words(res["path"], 1)
    assert [t for t, _, _ in sorted(back, key=lambda x: x[1])] == ["2", "3"]


def test_selection_reverse_and_marks(tmp_path):
    src = make_numbered(tmp_path / "doc.pdf", 5)
    res = imp.impose(str(src), str(tmp_path / "out.pdf"), {"pages": "2-4", "reverse": True, "marks": True, "bleed_mm": 3})
    assert res["sheets"] == 3
    reader = PdfReader(res["path"])
    assert [p.extract_text().split()[-1] for p in reader.pages] == ["4", "3", "2"]
    assert float(reader.pages[0].mediabox.width) > 595.28 + 40  # room for bleed + marks
    with pdfplumber.open(res["path"]) as pdf:
        assert len(pdf.pages[0].lines) == 8  # two strokes at each corner


def test_layout_errors(tmp_path):
    src = make_numbered(tmp_path / "doc.pdf", 2)
    for bad in ({"layout": "nup", "per_sheet": 3}, {"layout": "spiral"}, {"sheet": "b5"}):
        with pytest.raises(ValueError):
            imp.impose(str(src), str(tmp_path / "x.pdf"), bad)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows printing")
def test_print_to_microsoft_print_to_pdf(tmp_path):
    from toolbox.services.printing import printer

    names = [p["name"] for p in printer.printers()]
    if "Microsoft Print to PDF" not in names:
        pytest.skip("Microsoft Print to PDF not installed")
    src = make_numbered(tmp_path / "doc.pdf", 4)
    target = tmp_path / "printed.pdf"
    res = printer.print_pdf(str(src), "Microsoft Print to PDF", {"layout": "nup", "per_sheet": 2, "sheet": "a4", "output_file": str(target), "color": False})
    assert res["sheets"] == 2
    import time

    for _ in range(50):  # the spooler finishes the file asynchronously
        if target.is_file() and target.stat().st_size:
            break
        time.sleep(0.2)
    assert len(PdfReader(target).pages) == 2


@pytest.mark.skipif(sys.platform != "win32", reason="Windows printing")
def test_slow_printer_is_listed_at_once_and_filled_in_later(monkeypatch):
    """A network printer that takes ages to answer mustn't hold up the list (or the GIL)."""
    import threading
    import time

    from toolbox.services.printing import printer

    release = threading.Event()

    def fake_caps(name, port):
        if name == "Slow WSD printer":
            release.wait(5)
        caps = {"duplex": name != "Fast", "color": True, "papers": [{"id": 9, "name": "A4", "w_mm": 210, "h_mm": 297}]}
        with printer._CAPS_LOCK:
            printer._CAPS[name] = caps
            printer._PENDING.pop(name, None)
        return caps

    monkeypatch.setattr(printer, "_installed", lambda: ([("Fast", "LPT1:"), ("Slow WSD printer", "WSD-1")], "Fast"))
    monkeypatch.setattr(printer, "_query_caps", fake_caps)
    monkeypatch.setattr(printer, "_CAPS", {})
    monkeypatch.setattr(printer, "_PENDING", {})

    start = time.monotonic()
    first = printer.printers(wait=0.3)
    assert time.monotonic() - start < 2
    assert [(p["name"], p["ready"]) for p in first] == [("Fast", True), ("Slow WSD printer", False)]
    assert first[1]["papers"] == [] and not first[1]["duplex"]

    release.set()
    for _ in range(50):
        later = printer.printers(wait=0.1)
        if all(p["ready"] for p in later):
            break
        time.sleep(0.05)
    assert later[1]["ready"] and later[1]["duplex"] and later[1]["papers"][0]["name"] == "A4"
