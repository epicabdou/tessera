import base64
import codecs
import io

import pytest
from PIL import Image
from pypdf import PdfWriter

from toolbox.services import preview


def test_folder_summary(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "x.txt").write_bytes(b"12345")
    (tmp_path / "y.txt").write_bytes(b"123")
    (tmp_path / "z.pdf").write_bytes(b"1")
    p = preview.preview_file(str(tmp_path))
    assert p["kind"] == "folder" and p["size"] is None
    f = p["folder"]
    assert (f["folders"], f["files"], f["total_size"]) == (2, 3, 9)
    assert f["types"][0] == {"ext": "txt", "count": 2}
    assert f["latest"]["name"] in {"a", "b", "x.txt", "y.txt", "z.pdf"}


def test_text_preview_and_truncation(tmp_path, monkeypatch):
    src = tmp_path / "notes.md"
    src.write_bytes(b"line 1\r\nline 2\r\nline 3")
    p = preview.preview_file(str(src))
    assert p["kind"] == "text"
    assert p["text"] == {
        "content": "line 1\nline 2\nline 3",
        "truncated": False,
        "encoding": "UTF-8",
        "line_endings": "CRLF",
        "lines": 3,
    }

    monkeypatch.setattr(preview, "MAX_TEXT_BYTES", 8)
    assert preview.preview_file(str(src))["text"]["truncated"] is True


def test_text_encodings(tmp_path):
    utf16 = tmp_path / "u16.txt"
    utf16.write_bytes(codecs.BOM_UTF16_LE + "héllo".encode("utf-16-le"))
    assert preview.preview_file(str(utf16))["text"]["content"] == "héllo"

    latin = tmp_path / "latin.txt"
    latin.write_bytes("café crème".encode("cp1252"))
    t = preview.preview_file(str(latin))["text"]
    assert t["content"] == "café crème" and t["encoding"] == "Windows-1252"


def test_cut_multibyte_char_stays_utf8(tmp_path, monkeypatch):
    src = tmp_path / "e.txt"
    src.write_text("aé", encoding="utf-8")  # é is 2 bytes; a 2-byte limit cuts it
    monkeypatch.setattr(preview, "MAX_TEXT_BYTES", 2)
    t = preview.preview_file(str(src))["text"]
    assert t["encoding"] == "UTF-8" and t["content"] == "a"


def test_unknown_extension_is_sniffed(tmp_path):
    (tmp_path / "LICENSE").write_text("MIT License\n\nPermission is hereby granted")
    assert preview.preview_file(str(tmp_path / "LICENSE"))["kind"] == "text"
    (tmp_path / "blob.bin").write_bytes(bytes(range(256)) * 4)
    assert preview.preview_file(str(tmp_path / "blob.bin"))["kind"] == "file"


def test_csv_with_semicolons(tmp_path):
    src = tmp_path / "data.csv"
    src.write_text("name;qty;price\napple;3;1,20\npear;5;0,80\n", encoding="utf-8")
    t = preview.preview_file(str(src))["table"]
    assert t["delimiter"] == ";"
    assert t["rows"] == [["name", "qty", "price"], ["apple", "3", "1,20"], ["pear", "5", "0,80"]]
    assert t["columns"] == 3 and t["truncated"] is False


def test_tsv_and_row_limit(tmp_path, monkeypatch):
    src = tmp_path / "data.tsv"
    src.write_text("".join(f"{i}\tx\n" for i in range(10)))
    monkeypatch.setattr(preview, "MAX_TABLE_ROWS", 4)
    t = preview.preview_file(str(src))["table"]
    assert len(t["rows"]) == 4 and t["truncated"] is True and t["rows"][0] == ["0", "x"]


def _decode_data_url(url):
    header, b64 = url.split(",", 1)
    return header, Image.open(io.BytesIO(base64.b64decode(b64)))


def test_png_with_alpha_stays_png(tmp_path):
    src = tmp_path / "logo.png"
    Image.new("RGBA", (300, 200), (255, 0, 0, 128)).save(src)
    img = preview.preview_file(str(src))["image"]
    assert (img["width"], img["height"], img["format"], img["mode"]) == (300, 200, "PNG", "RGBA")
    header, decoded = _decode_data_url(img["data_url"])
    assert header == "data:image/png;base64" and decoded.size == (300, 200)


def test_large_photo_is_downscaled_but_reports_real_size(tmp_path):
    src = tmp_path / "photo.jpg"
    Image.new("RGB", (4000, 2000), (10, 120, 200)).save(src, quality=90)
    img = preview.preview_file(str(src))["image"]
    assert (img["width"], img["height"]) == (4000, 2000)
    header, decoded = _decode_data_url(img["data_url"])
    assert header == "data:image/jpeg;base64" and max(decoded.size) <= preview.MAX_IMAGE_EDGE


def test_exif_rotated_photo_reports_upright_size(tmp_path):
    src = tmp_path / "turned.jpg"
    im = Image.new("RGB", (400, 200))
    exif = im.getexif()
    exif[0x0112] = 6  # rotate 90° CW when displayed
    im.save(src, exif=exif)
    img = preview.preview_file(str(src))["image"]
    assert (img["width"], img["height"]) == (200, 400)
    _, decoded = _decode_data_url(img["data_url"])
    assert decoded.size == (200, 400)


def test_svg_and_pdf(tmp_path):
    svg = tmp_path / "icon.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>')
    assert preview.preview_file(str(svg))["image"]["data_url"].startswith("data:image/svg+xml;base64,")

    pdf = tmp_path / "doc.pdf"
    w = PdfWriter()
    w.add_blank_page(300, 400)
    w.add_blank_page(300, 400)
    w.write(pdf)
    p = preview.preview_file(str(pdf))
    assert p["kind"] == "pdf" and p["pdf"]["page_count"] == 2


def test_broken_file_falls_back_to_details(tmp_path):
    src = tmp_path / "fake.png"
    src.write_bytes(b"definitely not an image")
    p = preview.preview_file(str(src))
    assert p["kind"] == "file" and p["error"].startswith("Can't preview this file")
    assert p["size"] == len(b"definitely not an image")


def test_missing_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        preview.preview_file(str(tmp_path / "gone.txt"))
