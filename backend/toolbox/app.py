"""Creates the native window and points it at the React UI."""

from __future__ import annotations

import argparse
import logging
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

import webview

from . import APP_NAME
from .api import Api
from .paths import is_frozen, user_data_dir, web_dir
from .services.components import Components
from .services.settings import Settings

DEFAULT_DEV_URL = "http://127.0.0.1:5173"

# With private_mode=False pywebview serves every app on the same default port
# (42001) so the origin, and thus localStorage, is stable across launches. Two
# such apps running at once collide, and on Windows the second one silently
# gets the first one's pages. A port of our own keeps storage stable without that.
PREFERRED_HTTP_PORT = 47821

log = logging.getLogger(__name__)


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _pick_http_port() -> int:
    if not _port_in_use(PREFERRED_HTTP_PORT):
        return PREFERRED_HTTP_PORT
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    log.warning("Port %d is taken; using %d (saved UI state won't carry over this session)", PREFERRED_HTTP_PORT, port)
    return port


def _configure_logging() -> None:
    handlers: list[logging.Handler] = [logging.FileHandler(user_data_dir() / "toolbox.log", encoding="utf-8")]
    if sys.stderr is not None:  # windowed PyInstaller builds have no console
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def _resolve_url(dev: bool) -> str:
    if dev:
        return os.environ.get("TOOLBOX_DEV_URL", DEFAULT_DEV_URL)
    index = web_dir() / "index.html"
    if not index.is_file():
        raise SystemExit(
            f"Frontend build not found at {index}.\n"
            "Run `npm run build` in frontend/ or start with --dev."
        )
    return str(index)


# Passes once the UI has connected to Python and the Explorer has listed its
# starting folder, i.e. data went through the bridge and was rendered.
_SELF_TEST_PROBE = (
    "document.documentElement.dataset.bridge === 'connected'"
    " && !!document.querySelector('[data-browser-state=\"ready\"]')"
)


def _pdf_engine_works() -> bool:
    """Render a page with PDFium: packaged builds fail here if its native DLL wasn't bundled."""
    from pypdf import PdfWriter

    from .services.pdf.render import render_pages

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "self-test.pdf"
        writer = PdfWriter()
        writer.add_blank_page(200, 200)
        writer.write(path)
        url = render_pages(str(path), [0], 64)[0]
    return bool(url and url.startswith("data:image/jpeg"))


def _conversion_works() -> bool:
    """Markdown (markdown-it + Pygments) printed by WebView2, an image to PDF, and the
    Office automation modules: everything a packaged build could fail to bundle."""
    from PIL import Image

    from . import html_print
    from .services.convert import images, markdown

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        page = folder / "doc.html"
        page.write_text(markdown.render_markdown("# Self-test\n\n```python\nprint('ok')\n```"), encoding="utf-8")
        printed = html_print.print_to_pdf(page.as_uri(), str(folder / "doc.pdf"), {})
        Image.new("RGB", (20, 20)).save(folder / "dot.png")
        pictured = images.images_to_pdf([{"path": str(folder / "dot.png")}], str(folder / "dot.pdf"), {})
    if sys.platform == "win32":
        import pythoncom  # noqa: F401
        import win32com.client  # noqa: F401
    return printed["page_count"] >= 1 and pictured["page_count"] == 1


def _pdf_tools_work() -> bool:
    """From PDF, editing, security and printing on a small generated PDF: covers the
    libraries a packaged build could fail to bundle (python-docx/-pptx templates, openpyxl,
    pdfplumber, ReportLab fonts, pyHanko, the WinRT OCR projection)."""
    from reportlab.pdfgen import canvas

    from .services import latex
    from .services.editing import watermark
    from .services.frompdf import convert
    from .services.printing import impose
    from .services.security import optimize, protect, sign

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        src = str(d / "src.pdf")
        c = canvas.Canvas(src)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(72, 760, "Self-test")
        c.setFont("Helvetica", 11)
        for r, row in enumerate((("Item", "Qty"), ("Pens", "4"), ("Ink", "2"))):
            y = 700 - r * 20
            c.line(72, y + 14, 272, y + 14)
            c.drawString(78, y, row[0])
            c.drawString(178, y, row[1])
        c.line(72, 646, 272, 646)
        for x in (72, 172, 272):
            c.line(x, 714, x, 646)
        c.save()

        cert = sign.create_certificate(str(d / "self.pfx"), "self-test", "Self Test")
        sign.sign(src, str(d / "signed.pdf"), cert["path"], "self-test")
        checks = {
            "word": convert.to_word(src, str(d / "a.docx"), "basic")["size"] > 0,
            "powerpoint": convert.to_powerpoint(src, str(d / "a.pptx"), 72)["slides"] == 1,
            "excel": convert.to_excel(src, str(d / "a.xlsx"))["size"] > 0,
            "markdown": "Self-test" in convert.markdown_preview(src),
            "watermark": watermark.watermark(src, str(d / "w.pdf"), {"kind": "text", "text": "X"})["page_count"] == 1,
            "protect": protect.protect(src, str(d / "p.pdf"), "pw")["page_count"] == 1,
            "compress": optimize.compress(src, str(d / "c.pdf"))["page_count"] == 1,
            "impose": impose.impose(src, str(d / "i.pdf"), {"layout": "booklet"})["sheets"] == 2,  # padded to 4 pages
            "sign": sign.verify(str(d / "signed.pdf"))[0]["intact"],
        }
    if sys.platform == "win32":
        from winrt.windows.globalization import Language  # noqa: F401
        from winrt.windows.graphics.imaging import SoftwareBitmap  # noqa: F401
        from winrt.windows.media.ocr import OcrEngine  # noqa: F401
        from winrt.windows.storage.streams import DataWriter  # noqa: F401
    latex.find_engines()
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        log.error("Self-test: these PDF tools produced bad output: %s", ", ".join(failed))
    return not failed


def _image_tools_work() -> bool:
    """Image tools on generated pictures: HEIC (pillow-heif), WebP/AVIF, resize, the
    editor's fonts and filters, watermark, the Windows face detector, and ONNX Runtime's
    native libraries (the AI models themselves are downloaded on first use)."""
    from PIL import Image

    from .services.images import basic, editor, faces
    from .services.images import imageio as iio

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        Image.new("RGB", (320, 200), "#3366cc").save(d / "p.png")
        Image.open(d / "p.png").save(d / "p.heic")
        checks = {
            "heic": iio.info(d / "p.heic")["width"] == 320,
            "webp+avif": [f["name"] for f in basic.convert([str(d / "p.png")], None, {"format": "webp"}) + basic.convert([str(d / "p.png")], None, {"format": "avif"})] == ["p.webp", "p.avif"],
            "resize": basic.resize([str(d / "p.png")], None, {"mode": "percent", "percent": 50})[0]["width"] == 160,
            "editor": editor.editor_save(str(d / "p.png"), str(d / "e.png"), {"adjust": {"filter": "vintage"}, "layers": [{"type": "text", "x": 5, "y": 5, "w": 100, "h": 30, "text": "Hi", "size": 24}]}, {})["width"] == 320,
            "watermark": editor.watermark([str(d / "p.png")], None, {"text": "©"})[0]["width"] == 320,
        }
        if sys.platform == "win32":
            checks["faces"] = faces.detect(str(d / "p.png")) == []
    import onnxruntime

    checks["onnxruntime"] = "CPUExecutionProvider" in onnxruntime.get_available_providers()
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        log.error("Self-test: these image tools produced bad output: %s", ", ".join(failed))
    return not failed


def _self_test(window: webview.Window, outcome: dict) -> None:
    """Runs on pywebview's worker thread: waits for the UI to show Python data, then closes."""
    try:
        try:
            if not _pdf_engine_works():
                log.error("Self-test failed: PDF rendering returned no image")
                return
        except Exception:
            log.exception("Self-test failed: PDF engine error")
            return
        if not window.events.loaded.wait(30):
            log.error("Self-test: page never loaded")
            return
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if window.evaluate_js(_SELF_TEST_PROBE):
                try:
                    if not _conversion_works():
                        log.error("Self-test failed: a conversion produced no pages")
                        return
                    if not _pdf_tools_work() or not _image_tools_work():
                        return
                except Exception:
                    log.exception("Self-test failed: conversion or PDF tool error")
                    return
                outcome["ok"] = True
                log.info("Self-test passed: UI rendered data from the Python bridge; PDF engine, converters, PDF and image tools OK")
                return
            time.sleep(0.25)
        log.error("Self-test failed: bridge data never appeared in the UI")
    finally:
        window.destroy()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog=APP_NAME)
    parser.add_argument("--dev", action="store_true", help="load the UI from the Vite dev server")
    parser.add_argument("--debug", action="store_true", help="enable WebView devtools")
    parser.add_argument("--self-test", action="store_true", help="open, verify the UI-to-Python bridge, exit 0/1")
    args = parser.parse_args(argv)

    _configure_logging()
    url = _resolve_url(args.dev)
    log.info("Starting %s (frozen=%s) at %s", APP_NAME, is_frozen(), url)

    # pywebview lets file:// pages read other local files by default. The UI is served
    # over HTTP and doesn't need that, and HTML/Markdown being converted to PDF must not
    # be able to read the user's files.
    webview.settings["ALLOW_FILE_URLS"] = False

    components = Components(user_data_dir())
    api = Api(Settings(user_data_dir() / "settings.json"), components)
    if not args.self_test:
        # First run (or after a failed attempt): install the LaTeX engine in the background.
        threading.Thread(target=components.ensure_latex, name="components", daemon=True).start()
    window = webview.create_window(
        APP_NAME,
        url,
        js_api=api,
        width=1320,
        height=820,
        min_size=(980, 600),
        background_color="#0f1115",
        text_select=True,
    )
    api._bind_window(window)

    outcome = {"ok": False}
    webview.start(
        func=_self_test if args.self_test else None,
        args=(window, outcome) if args.self_test else None,
        debug=args.debug or (args.dev and not args.self_test),
        # Serve the built files over a local HTTP server: Vite's ES module output
        # doesn't load from file:// in Chromium-based WebViews.
        http_server=not args.dev,
        http_port=None if args.dev else _pick_http_port(),
        private_mode=False,
        storage_path=str(user_data_dir() / "webview"),
    )
    if args.self_test:
        sys.exit(0 if outcome["ok"] else 1)
