"""Live previews (watermark, print layout) through the Api, as the UI calls them."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pypdf import PdfReader

from tests.samples import make_numbered
from toolbox.api import Api
from toolbox.services.settings import Settings

WATERMARK = {"kind": "text", "text": "DRAFT", "opacity": 0.3, "position": "middle-center", "pages": ""}


def _api(tmp_path: Path) -> Api:
    return Api(Settings(tmp_path / "settings.json"), components=object())


def test_overlapping_previews_never_share_a_file(tmp_path):
    src = make_numbered(tmp_path / "doc.pdf", 4)
    api = _api(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(api.pdf_watermark_preview, str(src), WATERMARK, i % 4) for i in range(4)]
        jobs += [pool.submit(api.print_preview, str(src), {"layout": "nup", "per_sheet": 2}) for _ in range(2)]
        results = [j.result() for j in jobs]
    paths = [r["path"] for r in results]
    assert len(set(paths)) == len(paths)
    for r in results[:4]:
        assert r["page_count"] == 1 and "DRAFT" in PdfReader(r["path"]).pages[0].extract_text()
    assert all(r["sheets"] == 2 for r in results[4:])
    api._previews.clear()
    assert not any(Path(p).exists() for p in paths)


def test_only_the_latest_previews_are_kept(tmp_path):
    src = make_numbered(tmp_path / "doc.pdf", 1)
    api = _api(tmp_path)
    paths = [api.pdf_watermark_preview(str(src), WATERMARK, 0)["path"] for _ in range(7)]
    kept = [p for p in paths if Path(p).exists()]
    assert kept == paths[-api._previews.KEEP :]
    api._previews.clear()


def test_preview_of_an_unselected_page_is_the_plain_page(tmp_path):
    src = make_numbered(tmp_path / "doc.pdf", 3)
    api = _api(tmp_path)
    info = api.pdf_watermark_preview(str(src), {**WATERMARK, "pages": "1"}, 2)
    text = PdfReader(info["path"]).pages[0].extract_text()
    assert "DRAFT" not in text and "3" in text
    api._previews.clear()
