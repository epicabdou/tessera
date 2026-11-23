import os
import re
import time
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from toolbox.services import convert
from toolbox.services.convert import images, markdown, office, web
from toolbox.services.pdf import render


def _xobjects(page):
    res = page["/Resources"]["/XObject"]
    return {name: res[name].get_object() for name in res}


def _content(page) -> bytes:
    return page.get_contents().get_data()


# --- images -----------------------------------------------------------------------


def test_jpeg_is_embedded_byte_for_byte(tmp_path):
    src = tmp_path / "photo.jpg"
    Image.new("RGB", (800, 400), (200, 30, 30)).save(src, quality=90)
    out = tmp_path / "out.pdf"
    images.images_to_pdf([{"path": str(src)}], str(out), {"page_size": "a4", "orientation": "auto", "margin": "small"})
    page = PdfReader(out).pages[0]
    (img,) = _xobjects(page).values()
    assert img["/Filter"] == "/DCTDecode"
    assert img._data == src.read_bytes()
    # landscape image + auto orientation -> landscape A4
    assert (round(float(page.mediabox.width)), round(float(page.mediabox.height))) == (842, 595)


def test_png_alpha_becomes_soft_mask(tmp_path):
    src = tmp_path / "logo.png"
    Image.new("RGBA", (50, 40), (0, 0, 255, 120)).save(src)
    out = tmp_path / "out.pdf"
    images.images_to_pdf([{"path": str(src)}], str(out), {"page_size": "fit", "margin": "none"})
    page = PdfReader(out).pages[0]
    (img,) = _xobjects(page).values()
    assert img["/Filter"] == "/FlateDecode" and "/SMask" in img
    # "fit" page = image size at 96 dpi
    assert round(float(page.mediabox.width)) == round(50 * 72 / 96)


def test_exif_rotated_jpeg_is_drawn_upright(tmp_path):
    # Left half red, right half blue; EXIF 6 = turn 90° clockwise to view,
    # so upright the red half is on top.
    im = Image.new("RGB", (400, 200), (220, 0, 0))
    im.paste((0, 0, 220), (200, 0, 400, 200))
    exif = im.getexif()
    exif[0x0112] = 6
    src = tmp_path / "turned.jpg"
    im.save(src, exif=exif, quality=95)
    out = tmp_path / "out.pdf"
    images.images_to_pdf([{"path": str(src)}], str(out), {"page_size": "fit", "margin": "none"})
    page = PdfReader(out).pages[0]
    assert float(page.mediabox.height) > float(page.mediabox.width)  # portrait
    assert _xobjects(page)["/Im0"]._data == src.read_bytes()  # still untouched

    import base64
    import io

    url = render.render_pages(str(out), [0], 100)[0]
    shown = Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGB")
    top = shown.getpixel((shown.width // 2, shown.height // 4))
    bottom = shown.getpixel((shown.width // 2, shown.height * 3 // 4))
    assert top[0] > 150 and top[2] < 80  # red
    assert bottom[2] > 150 and bottom[0] < 80  # blue


def test_rotation_layout_fill_and_multipage_tiff(tmp_path):
    jpg = tmp_path / "a.jpg"
    Image.new("RGB", (300, 200), "white").save(jpg)
    tif = tmp_path / "scan.tiff"
    frames = [Image.new("L", (100, 140), 255), Image.new("L", (100, 140), 0)]
    frames[0].save(tif, save_all=True, append_images=frames[1:])
    out = tmp_path / "out.pdf"
    images.images_to_pdf(
        [{"path": str(jpg), "rotate": 90}, {"path": str(tif)}],
        str(out),
        {"page_size": "letter", "orientation": "portrait", "margin": "large", "fit": "fill"},
    )
    pages = PdfReader(out).pages
    assert len(pages) == 3  # 1 jpeg + 2 tiff frames
    assert all((round(float(p.mediabox.width)), round(float(p.mediabox.height))) == (612, 792) for p in pages)
    first = _content(pages[0])
    assert b"re W n" in first  # "fill" clips to the margin box
    assert re.search(rb"0\.0000 -[\d.]+ [\d.]+ 0\.0000 [\d.]+ [\d.]+ cm", first)  # turned 90°


def test_one_pdf_per_image(tmp_path):
    for name in ("a", "b"):
        Image.new("RGB", (10, 10)).save(tmp_path / f"{name}.png")
    (tmp_path / "a.pdf").write_bytes(b"existing")
    results = images.images_to_pdfs([{"path": str(tmp_path / "a.png")}, {"path": str(tmp_path / "b.png")}], None, {})
    assert [r["name"] for r in results] == ["a (2).pdf", "b.pdf"]


def test_image_errors(tmp_path):
    (tmp_path / "x.txt").write_text("hi")
    with pytest.raises(ValueError, match="supported image"):
        images.images_to_pdf([{"path": str(tmp_path / "x.txt")}], str(tmp_path / "o.pdf"), {})
    (tmp_path / "bad.png").write_bytes(b"nope")
    with pytest.raises(ValueError, match="Can't read"):
        images.images_to_pdf([{"path": str(tmp_path / "bad.png")}], str(tmp_path / "o.pdf"), {})
    with pytest.raises(ValueError):
        images.images_to_pdf([], str(tmp_path / "o.pdf"), {})


def test_thumbnail(tmp_path):
    src = tmp_path / "big.png"
    Image.new("RGB", (1000, 500)).save(src)
    t = images.thumbnail(str(src), 100)
    assert (t["width"], t["height"]) == (1000, 500) and t["data_url"].startswith("data:image/jpeg")


# --- markdown & web ---------------------------------------------------------------


def test_markdown_render(tmp_path):
    Image.new("RGB", (4, 4)).save(tmp_path / "pic.png")
    text = "# Title\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n```python\ndef f(): pass\n```\n\n![p](pic.png) ~~gone~~"
    out = markdown.render_markdown(text, str(tmp_path), "document", "My <Doc>")
    assert "<title>My &lt;Doc&gt;</title>" in out
    assert "<table>" in out and "<s>gone</s>" in out
    assert 'class="hl"' in out and '<span class="k">def</span>' in out  # highlighted
    assert 'src="data:image/png;base64,' in out  # local image embedded
    with pytest.raises(ValueError):
        markdown.render_markdown("x", theme="nope")


def test_print_settings_and_urls():
    s = web.print_settings({"page_size": "letter", "orientation": "landscape", "margin": "narrow", "scale": 90})
    assert (s["width"], s["height"], s["landscape"], s["margin"], s["scale"]) == (8.5, 11.0, True, 0.25, 0.9)
    for bad in ({"page_size": "b5"}, {"margin": "huge"}, {"scale": 500}, {"wait": 99}):
        with pytest.raises(ValueError):
            web.print_settings(bad)
    assert web.normalize_url(" example.com/x ") == "https://example.com/x"
    assert web.normalize_url("http://a.b") == "http://a.b"
    assert web.normalize_url("localhost:8000/page") == "https://localhost:8000/page"
    for bad in ("", "javascript:alert(1)", "data:text/html,hi", "file:///C:/x.html", "ftp://x"):
        with pytest.raises(ValueError):
            web.normalize_url(bad)
    assert web.html_document("<p>hi</p>").startswith("<!doctype html>")
    assert web.html_document("<!DOCTYPE html><html></html>") == "<!DOCTYPE html><html></html>"
    assert web.title_hint("https://example.com/docs/page.html") == "example.com-page"


def test_suggest_pdf_path(tmp_path):
    src = tmp_path / "report.docx"
    assert convert.suggest_pdf_path(str(src)) == str(tmp_path / "report.pdf")
    (tmp_path / "report.pdf").write_bytes(b"x")
    assert convert.suggest_pdf_path(str(src)).endswith("report (2).pdf")
    assert convert.suggest_pdf_path(None, "exa/mple:site").endswith("exa_mple_site.pdf")


def test_suggest_output_path_uses_the_real_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(convert, "known_folder", lambda name: str(tmp_path))
    # A web address is never a folder: the image goes to Downloads, named after the page.
    assert convert.suggest_output_path(None, "example.com-docs", "png") == str(tmp_path / "example.com-docs.png")
    # The clash check looks for the image's own name, not a .pdf.
    (tmp_path / "example.com-docs.png").write_bytes(b"x")
    (tmp_path / "page.pdf").write_bytes(b"x")
    assert convert.suggest_output_path(None, "example.com-docs", "png").endswith("example.com-docs (2).png")
    assert convert.suggest_output_path(None, "page", ".jpg") == str(tmp_path / "page.jpg")
    src = tmp_path / "card.html"
    assert convert.suggest_output_path(str(src), "", "webp") == str(tmp_path / "card.webp")


# --- office -----------------------------------------------------------------------


def test_office_kind_and_validation(tmp_path):
    assert office.kind_for("a.DOCX") == "word"
    assert office.kind_for("b.xlsm") == "excel"
    assert office.kind_for("c.ppsx") == "powerpoint"
    assert office.kind_for("d.pdf") is None
    e = office.engines()
    assert set(e["office"]) == {"word", "excel", "powerpoint"}
    with pytest.raises(ValueError):
        office.convert("visio", str(tmp_path / "x.vsd"))
    with pytest.raises(FileNotFoundError):
        office.convert("word", str(tmp_path / "missing.docx"))
    (tmp_path / "x.txt").write_text("hi")
    with pytest.raises(ValueError, match="can convert"):
        office.convert("word", str(tmp_path / "x.txt"))


# --- the watchdog that keeps a hidden Office from waiting forever on a prompt ---


def _until(condition, seconds: float = 5.0) -> None:
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.05)


@pytest.fixture
def desktop(monkeypatch):
    """The Win32 side of the watchdog, faked: `shown` maps a prompt's hwnd to its process."""
    state = {"shown": {}, "pressed": [], "ended": [], "processes": {}}

    def prompts(is_ours):
        return [(hwnd, pid, "") for hwnd, pid in list(state["shown"].items()) if is_ours(pid)]

    def press(hwnd):
        state["pressed"].append(hwnd)
        state["shown"].pop(hwnd, None)  # OK closes it

    monkeypatch.setattr(office, "PROMPT_GRACE", 0.8)
    monkeypatch.setattr(office, "_prompts", prompts)
    monkeypatch.setattr(office, "_press_default_button", press)
    monkeypatch.setattr(office, "_terminate", state["ended"].append)
    monkeypatch.setattr(office, "_process_info", lambda pid: state["processes"].get(pid))
    return state


def test_watchdog_ends_office_stuck_on_its_own_prompt(desktop):
    desktop["shown"][11] = 4242  # e.g. "The last time you opened X, it caused a serious error..."
    dog = office._Watchdog(4242)
    _until(lambda: dog.reason)
    dog.stop()
    assert desktop["ended"] == [4242] and desktop["pressed"] == []
    assert "can't be answered" in dog.reason


def test_watchdog_answers_the_pdf_import_notice(desktop):
    # PDFREFLOW.EXE, started for this job, shows "Word will now convert your PDF..."
    desktop["processes"][777] = ("pdfreflow.exe", time.time())
    desktop["shown"][22] = 777
    dog = office._Watchdog(4242, helpers=("PDFREFLOW.EXE",))
    _until(lambda: desktop["pressed"])
    time.sleep(1.2)
    dog.stop()
    assert desktop["pressed"] == [22] and desktop["ended"] == [] and dog.reason is None


def test_watchdog_leaves_other_processes_alone(desktop):
    desktop["processes"][777] = ("pdfreflow.exe", time.time() - 600)  # the user's own Word, started earlier
    desktop["processes"][888] = ("notepad.exe", time.time())
    desktop["shown"].update({22: 777, 33: 888})
    dog = office._Watchdog(4242, helpers=("PDFREFLOW.EXE",))
    time.sleep(1.5)
    dog.stop()
    assert desktop["pressed"] == [] and desktop["ended"] == [] and dog.reason is None


def test_watchdog_time_limit(desktop):
    dog = office._Watchdog(4242, timeout=0.6)
    _until(lambda: dog.reason)
    dog.stop()
    assert desktop["ended"] == [4242] and "didn't finish" in dog.reason


def test_stopped_watchdog_never_ends_office(desktop):
    desktop["shown"][11] = 4242
    dog = office._Watchdog(4242)
    dog.stop()  # the job finished first
    time.sleep(1.2)
    assert desktop["ended"] == [] and dog.reason is None


# Real conversions start Office / LibreOffice (slow): opt in with TOOLBOX_OFFICE_TESTS=1.
needs_apps = pytest.mark.skipif(os.environ.get("TOOLBOX_OFFICE_TESTS") != "1", reason="set TOOLBOX_OFFICE_TESTS=1")
RTF = r"{\rtf1\ansi{\fonttbl\f0 Arial;}\f0\fs28 Hello from Toolbox\par Second line\par}"


def _engine(kind, engine):
    e = office.engines()
    if engine == "office" and not e["office"][kind]:
        pytest.skip(f"Microsoft Office {kind} not installed")
    if engine == "libreoffice" and not e["libreoffice"]:
        pytest.skip("LibreOffice not installed")


@needs_apps
@pytest.mark.parametrize("engine", ["office", "libreoffice"])
def test_word_and_excel_conversions(tmp_path, engine):
    _engine("word", engine)
    doc = tmp_path / "letter.rtf"
    doc.write_text(RTF)
    res = office.convert("word", str(doc), engine=engine)
    assert res["engine"] == engine and Path(res["path"]).name == "letter.pdf"
    assert "Hello from Toolbox" in PdfReader(res["path"]).pages[0].extract_text()

    sheet = tmp_path / "numbers.csv"
    sheet.write_text("city,pop\nOran,1500000\n")
    res = office.convert("excel", str(sheet), engine=engine, options={"fit_width": True, "landscape": True})
    text = PdfReader(res["path"]).pages[0].extract_text()
    assert "Oran" in text and "1500000" in text


@needs_apps
def test_powerpoint_conversion(tmp_path):
    _engine("powerpoint", "office")
    import pythoncom
    import win32com.client

    deck = tmp_path / "deck.pptx"
    pythoncom.CoInitialize()
    try:
        ppt = win32com.client.DispatchEx("PowerPoint.Application")
        pres = ppt.Presentations.Add(WithWindow=0)
        slide = pres.Slides.Add(1, 1)  # ppLayoutTitle
        slide.Shapes(1).TextFrame.TextRange.Text = "Quarterly review"
        pres.Slides.Add(2, 1)
        pres.SaveAs(str(deck))
        pres.Close()
        if ppt.Presentations.Count == 0:
            ppt.Quit()
        del slide, pres, ppt
    finally:
        pythoncom.CoUninitialize()

    res = office.convert("powerpoint", str(deck), engine="office")
    reader = PdfReader(res["path"])
    assert len(reader.pages) == 2 and "Quarterly review" in reader.pages[0].extract_text()
    notes = office.convert("powerpoint", str(deck), engine="office", options={"layout": "handouts6"})
    assert len(PdfReader(notes["path"]).pages) == 1  # six slides per page
