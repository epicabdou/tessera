"""HTML to PDF with WebView2 (the engine that draws the app's UI), in a hidden window.

This is UI-layer code: it needs pywebview's native window, so it lives outside services/.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

import webview

from .services.convert.web import print_settings
from .services.filesystem import replace_with_retry

log = logging.getLogger(__name__)

LOAD_TIMEOUT = 60  # seconds
SETTLE_TIMEOUT = 15
_LOCK = threading.Lock()  # one hidden render window at a time

# Ready when the document, its web fonts and its images have loaded.
_READY_JS = """(() => document.readyState === 'complete'
  && (!document.fonts || document.fonts.status === 'loaded')
  && [...document.images].every((i) => i.complete))()"""

# Scroll through the page so lazy-loaded images and sections render, then go back up.
_SCROLL_JS = """new Promise((resolve) => {
  let y = 0
  const step = () => {
    window.scrollTo(0, y)
    y += Math.max(400, innerHeight * 0.8)
    if (y < document.documentElement.scrollHeight && y < 300000) setTimeout(step, 120)
    else { window.scrollTo(0, 0); setTimeout(() => resolve(true), 400) }
  }
  step()
})"""


def print_to_pdf(url: str, output: str, options: dict, header_title: str | None = None, footer_uri: str | None = None) -> dict:
    """Load `url` (http(s) or file://) in a hidden WebView2 window and print it to `output`.

    header_title / footer_uri replace the page title and address in the optional
    header and footer (useful when printing a temporary file).
    """
    settings = print_settings(options)
    settings["header_title"] = header_title
    settings["footer_uri"] = footer_uri
    out = Path(output)
    if out.suffix.lower() != ".pdf":
        out = out.with_name(out.name + ".pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".{out.stem}.{os.getpid()}.printing.pdf")

    with _LOCK:
        window = webview.create_window("Toolbox PDF renderer", url, hidden=True, width=1280, height=1000, focus=False)
        try:
            if not window.events.loaded.wait(LOAD_TIMEOUT):
                raise TimeoutError(f"The page didn't load within {LOAD_TIMEOUT} seconds")
            if str(window.evaluate_js("location.href")).startswith("chrome-error://"):
                raise RuntimeError("The page couldn't be loaded. Check the address and your internet connection.")
            deadline = time.monotonic() + SETTLE_TIMEOUT
            while time.monotonic() < deadline and not window.evaluate_js(_READY_JS):
                time.sleep(0.2)
            if settings["scroll"]:
                window.evaluate_js(_SCROLL_JS)
            if settings["wait"]:
                time.sleep(settings["wait"])
            _print(window, tmp, settings)
            replace_with_retry(tmp, out)
        finally:
            tmp.unlink(missing_ok=True)
            window.destroy()

    from pypdf import PdfReader

    return {"path": str(out), "name": out.name, "size": out.stat().st_size, "page_count": len(PdfReader(out).pages)}


PRINT_TIMEOUT = 120  # seconds


def _print(window: webview.Window, path: Path, s: dict) -> None:
    """Print on the UI thread and wait for the result on this one.

    Never block in a .NET call here (e.g. Task.Result): that holds Python's GIL while
    the UI thread needs it to finish the print, and both threads freeze. Instead a .NET
    continuation sets a Python Event, and waiting on that releases the GIL.
    """
    from Microsoft.Web.WebView2.Core import CoreWebView2PrintOrientation
    from System import Action, Boolean
    from System.Threading.Tasks import Task

    form = window.native
    view = form.browser.webview
    done = threading.Event()
    started: dict = {}

    def finished(task) -> None:
        started["ok"] = (not task.IsFaulted) and bool(task.Result)
        if task.IsFaulted:
            started["error"] = task.Exception
        done.set()

    def start() -> None:
        try:
            core = view.CoreWebView2
            ps = core.Environment.CreatePrintSettings()
            ps.Orientation = CoreWebView2PrintOrientation.Landscape if s["landscape"] else CoreWebView2PrintOrientation.Portrait
            ps.PageWidth = s["width"]
            ps.PageHeight = s["height"]
            ps.MarginTop = ps.MarginBottom = ps.MarginLeft = ps.MarginRight = s["margin"]
            ps.ScaleFactor = s["scale"]
            ps.ShouldPrintBackgrounds = s["backgrounds"]
            ps.ShouldPrintHeaderAndFooter = s["header_footer"]
            if s["header_footer"] and s["header_title"] is not None:
                ps.HeaderTitle = s["header_title"]
            if s["header_footer"] and s["footer_uri"] is not None:
                ps.FooterUri = s["footer_uri"]
            core.PrintToPdfAsync(str(path), ps).ContinueWith(Action[Task[Boolean]](finished))
        except Exception as exc:  # noqa: BLE001 - surfaced on the calling thread below
            started["error"] = exc
            done.set()

    form.Invoke(Action(start))
    if not done.wait(PRINT_TIMEOUT):
        raise TimeoutError(f"Printing took longer than {PRINT_TIMEOUT} seconds")
    if "error" in started:
        raise RuntimeError(f"Printing failed: {started['error']}")
    if not started.get("ok") or not path.is_file():
        raise RuntimeError("WebView2 couldn't create the PDF")


# --- HTML to image ------------------------------------------------------------------------

CAPTURE_MAX_HEIGHT = 16000  # CSS px; Chromium can't capture taller surfaces reliably


def _cdp(window: webview.Window, method: str, params: dict, timeout: float = 60) -> dict:
    """Call a Chrome DevTools Protocol method on the window's WebView2 and return its result.
    Same rule as _print: never block in .NET; a continuation sets a Python Event."""
    import json

    from System import Action, String
    from System.Threading.Tasks import Task

    form = window.native
    view = form.browser.webview
    done = threading.Event()
    box: dict = {}

    def finished(task) -> None:
        if task.IsFaulted:
            box["error"] = task.Exception
        else:
            box["result"] = str(task.Result)
        done.set()

    def start() -> None:
        try:
            view.CoreWebView2.CallDevToolsProtocolMethodAsync(method, json.dumps(params)).ContinueWith(Action[Task[String]](finished))
        except Exception as exc:  # noqa: BLE001 - surfaced below
            box["error"] = exc
            done.set()

    form.Invoke(Action(start))
    if not done.wait(timeout):
        raise TimeoutError(f"{method} took longer than {timeout} seconds")
    if "error" in box:
        raise RuntimeError(f"{method} failed: {box['error']}")
    return json.loads(box["result"] or "{}")


def _show_offscreen(window: webview.Window) -> None:
    """Show the render window far off-screen. A window that has never been shown draws
    no frames, and a screenshot waits for one (indefinitely); an off-screen tool window
    renders normally while staying out of sight, the taskbar and Alt+Tab. Focus is
    handed straight back to whichever window had it."""
    import ctypes

    from System import Action
    from System.Drawing import Point
    from System.Windows.Forms import FormBorderStyle, FormStartPosition

    user32 = ctypes.windll.user32
    previous = user32.GetForegroundWindow()
    form = window.native
    failed: dict = {}

    def show() -> None:
        try:
            form.ShowInTaskbar = False
            form.FormBorderStyle = FormBorderStyle.FixedToolWindow
            form.StartPosition = FormStartPosition.Manual
            form.Location = Point(-32000, -32000)
            form.Show()
        except Exception as exc:  # noqa: BLE001 - surfaced below
            failed["error"] = exc

    form.Invoke(Action(show))
    if previous:
        user32.SetForegroundWindow(previous)
    if "error" in failed:
        raise RuntimeError(f"Couldn't prepare the page renderer: {failed['error']}")


def capture_image(url: str, output: str, options: dict) -> dict:
    """Render `url` in a hidden WebView2 window and save a screenshot.

    options: width (CSS px viewport, 320-3840), height (viewport height), full_page,
    scale (1-3, device pixel ratio), format (png/jpg/webp), quality, transparent (no
    page background, for PNG/WebP), wait (s), scroll.
    """
    import base64
    import io

    from PIL import Image

    from .services.images import imageio as iio

    width = max(320, min(3840, int(options.get("width", 1280))))
    height = max(200, min(4000, int(options.get("height", 800))))
    scale = max(1.0, min(3.0, float(options.get("scale", 1))))
    full = bool(options.get("full_page", True))
    fmt = options.get("format", "png")
    transparent = bool(options.get("transparent")) and iio.FORMATS.get(fmt, ("", "", False))[2]

    with _LOCK:
        window = webview.create_window("Toolbox image renderer", url, hidden=True, width=width, height=height, focus=False)
        try:
            if not window.events.loaded.wait(LOAD_TIMEOUT):
                raise TimeoutError(f"The page didn't load within {LOAD_TIMEOUT} seconds")
            if str(window.evaluate_js("location.href")).startswith("chrome-error://"):
                raise RuntimeError("The page couldn't be loaded. Check the address and your internet connection.")
            _show_offscreen(window)
            _cdp(window, "Emulation.setDeviceMetricsOverride", {"width": width, "height": height, "deviceScaleFactor": scale, "mobile": width < 600})
            _cdp(window, "Emulation.setScrollbarsHidden", {"hidden": True})
            if transparent:
                _cdp(window, "Emulation.setDefaultBackgroundColorOverride", {"color": {"r": 0, "g": 0, "b": 0, "a": 0}})
            deadline = time.monotonic() + SETTLE_TIMEOUT
            while time.monotonic() < deadline and not window.evaluate_js(_READY_JS):
                time.sleep(0.2)
            if options.get("scroll", True) and full:
                window.evaluate_js(_SCROLL_JS)
            time.sleep(max(0.3, float(options.get("wait", 0) or 0)))
            metrics = _cdp(window, "Page.getLayoutMetrics", {})
            content = metrics.get("cssContentSize") or metrics.get("contentSize") or {}
            shot_h = min(CAPTURE_MAX_HEIGHT, max(1, round(content.get("height", height)))) if full else height
            shot = _cdp(
                window,
                "Page.captureScreenshot",
                {"format": "png", "captureBeyondViewport": full, "fromSurface": True, "clip": {"x": 0, "y": 0, "width": width, "height": shot_h, "scale": 1}},
                timeout=60,
            )
        finally:
            window.destroy()

    im = Image.open(io.BytesIO(base64.b64decode(shot["data"])))
    im.load()
    result = iio.save(im, output, fmt, quality=int(options.get("quality", 90)), keep_metadata=False)
    result["truncated"] = full and content.get("height", 0) > CAPTURE_MAX_HEIGHT
    return result
