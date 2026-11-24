"""Real screenshots of Tilepress for the website (public/screenshots/ and public/og.png).

The website has its own private repository, epicabdou/tilepress-website. Clone it next to this
one (..\\tilepress-website) and the files go straight into it, or pass --site <folder>.

The real UI (frontend/dist) runs against the real Python backend, through a small local
HTTP bridge standing in for pywebview's, and headless Microsoft Edge drives it over the
DevTools protocol. Demo files are generated (fictional documents, procedural photos), so
nothing personal appears, and the app's data folder is a temporary one: your own settings
and history are never touched.

    .venv\\Scripts\\python scripts\\screenshots.py                 # every scene
    .venv\\Scripts\\python scripts\\screenshots.py merge history   # some scenes
    .venv\\Scripts\\python scripts\\screenshots.py --serve         # just the bridge, to explore in a browser

Needs a built frontend (npm run build in frontend/), Microsoft Edge, and websocket-client
(requirements-dev.txt).
"""

from __future__ import annotations

import argparse
import io
import json
import math
import mimetypes
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "frontend" / "dist"
SITE = ROOT.parent / "tilepress-website"  # the website repo's checkout; --site changes it
OUT = SITE / "public" / "screenshots"
# A path without anyone's user name in it: it shows in the Explorer pane.
DEMO = Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Documents" / "Tilepress demo"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
VIEW = (1440, 900)  # CSS pixels; captured at 2x

# The app's data folder (settings, history) goes to a throwaway place: set before importing the app.
DATA = Path(tempfile.mkdtemp(prefix="tilepress-shots-"))
os.environ["LOCALAPPDATA"] = str(DATA)
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

from toolbox.api import Api  # noqa: E402
from toolbox.services.history import History  # noqa: E402
from toolbox.services.settings import Settings  # noqa: E402

# =========================================================================================
# Demo content: fictional documents and procedural "photos"
# =========================================================================================


def _noise1d(n: int, rough: float, rng: np.random.Generator) -> np.ndarray:
    """Midpoint-displacement ridge line, values roughly in [-1, 1]."""
    size = 1
    while size < n:
        size *= 2
    line = np.zeros(size + 1)
    step, amp = size, 1.0
    while step > 1:
        half = step // 2
        for i in range(half, size, step):
            line[i] = (line[i - half] + line[i + half]) / 2 + rng.uniform(-amp, amp)
        step, amp = half, amp * rough
    return np.interp(np.linspace(0, size, n), np.arange(size + 1), line)


def _sky(w: int, h: int, stops: list[tuple[float, tuple[int, int, int]]]) -> np.ndarray:
    t = np.linspace(0, 1, h)[:, None]
    img = np.zeros((h, w, 3))
    for (o0, c0), (o1, c1) in zip(stops, stops[1:]):
        m = ((t >= o0) & (t <= o1))[:, 0]
        f = ((t[m] - o0) / (o1 - o0))
        img[m] = np.array(c0) * (1 - f[..., None]) + np.array(c1) * f[..., None]
    return img


def landscape(kind: str, w: int = 2400, h: int = 1600, seed: int = 7) -> Image.Image:
    rng = np.random.default_rng(seed)
    presets = {
        "sunrise": dict(sky=[(0, (40, 52, 120)), (0.45, (238, 132, 120)), (0.62, (255, 196, 140)), (1, (255, 214, 170))],
                        sun=(0.68, 0.46, 0.07, (255, 236, 200)),
                        layers=[(0.48, (122, 96, 150)), (0.58, (88, 70, 122)), (0.69, (58, 48, 92)), (0.8, (34, 30, 62))]),
        "dusk": dict(sky=[(0, (22, 26, 70)), (0.5, (120, 80, 160)), (0.7, (236, 140, 150)), (1, (250, 180, 150))],
                     sun=(0.3, 0.6, 0.05, (255, 210, 190)),
                     layers=[(0.5, (84, 66, 128)), (0.58, (54, 44, 96))], water=0.62),
        "dunes": dict(sky=[(0, (110, 170, 230)), (0.6, (200, 225, 245)), (1, (240, 236, 225))],
                      sun=(0.8, 0.22, 0.05, (255, 250, 235)),
                      layers=[(0.55, (226, 170, 110)), (0.66, (214, 146, 88)), (0.78, (196, 122, 70)), (0.9, (170, 98, 56))], smooth=True),
        "aurora": dict(sky=[(0, (6, 10, 30)), (0.6, (14, 30, 60)), (1, (20, 46, 70))],
                       layers=[(0.72, (12, 22, 36)), (0.82, (6, 12, 22))], stars=True, aurora=True),
    }
    p = presets[kind]
    img = _sky(w, h, p["sky"])
    yy, xx = np.mgrid[0:h, 0:w]
    if p.get("stars"):
        for _ in range(900):
            x, y = rng.integers(0, w), rng.integers(0, int(h * 0.7))
            img[y, x] = np.minimum(255, img[y, x] + rng.uniform(80, 220))
    if p.get("aurora"):
        for band, (cx, color) in enumerate([(0.3, (60, 240, 160)), (0.62, (80, 200, 255)), (0.48, (150, 110, 255))]):
            ridge = _noise1d(w, 0.55, rng) * 0.08 + 0.28 + band * 0.05
            dist = yy / h - ridge[None, :]
            glow = np.exp(-np.clip(dist, 0, None) * 14) * (dist > -0.02) * np.exp(-((xx / w - cx) ** 2) * 6)
            img += glow[..., None] * np.array(color) * 0.55
    if "sun" in p:
        sx, sy, r, color = p["sun"]
        d = np.hypot(xx / w - sx, (yy / h - sy) * h / w)
        img += (np.exp(-np.clip(d - r * 0.6, 0, None) * 9) * 0.55)[..., None] * np.array(color)
        img[d < r * 0.6] = color
    water = p.get("water")
    for i, (base, color) in enumerate(p["layers"]):
        rough = 0.42 if p.get("smooth") else 0.58
        ridge = _noise1d(w, rough, rng) * (0.06 if p.get("smooth") else 0.12) + base
        if p.get("smooth"):
            ridge = np.convolve(np.pad(ridge, 40, mode="edge"), np.ones(81) / 81, mode="valid")
        mask = yy / h > ridge[None, :]
        if water:
            mask &= yy / h < water
        shade = 1 - 0.18 * (yy / h - ridge[None, :]).clip(0, 0.3) / 0.3
        img[mask] = (np.array(color) * shade[..., None])[mask]
    if water:
        top = int(h * water)
        above = img[top - (h - top) : top][::-1].copy()
        ripple = (np.sin(np.arange(h - top) / 3.0)[:, None] * 6).astype(int)
        reflect = np.stack([np.roll(above[i], ripple[i, 0], axis=0) for i in range(len(above))])
        img[top:] = reflect * 0.72 + np.array([20, 26, 60]) * 0.28
    img += rng.normal(0, 2.2, img.shape)  # a little grain
    out = Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGB")
    return out.filter(ImageFilter.GaussianBlur(0.6))


def make_pdfs(folder: Path) -> dict[str, Path]:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    ink, violet, blue, cyan, soft = colors.HexColor("#1d2340"), colors.HexColor("#6a5cff"), colors.HexColor("#4f8bff"), colors.HexColor("#22b5e6"), colors.HexColor("#eef0fb")
    W, H = A4
    files: dict[str, Path] = {}

    def body(c: canvas.Canvas, x: float, y: float, lines: list[str], size: float = 10.5, lead: float = 15) -> float:
        c.setFont("Helvetica", size)
        c.setFillColor(colors.HexColor("#3b4262"))
        for line in lines:
            c.drawString(x, y, line)
            y -= lead
        return y

    # --- report ---
    path = folder / "Quarterly report Q2.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle("Quarterly report Q2 2026")
    for x in range(0, int(W), 4):  # gradient band
        t = x / W
        c.setFillColor(colors.Color(0.42 + 0.0 * t, 0.36 + 0.3 * t, 1.0 - 0.1 * t))
        c.rect(x, H - 120 * mm, 4.5, 120 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 38)
    c.drawString(22 * mm, H - 70 * mm, "Quarterly report")
    c.setFont("Helvetica", 20)
    c.drawString(22 * mm, H - 84 * mm, "Second quarter 2026")
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(22 * mm, H - 140 * mm, "Harbor & Pine Cycles")
    body(c, 22 * mm, H - 150 * mm, ["Prepared for the board, 3 July 2026.", "Figures are unaudited."])
    c.showPage()
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(22 * mm, H - 30 * mm, "Sales by month")
    y = body(c, 22 * mm, H - 42 * mm, ["Online orders grew in every month of the quarter, led by the new city", "bike range. Workshop bookings held steady while repairs per bike rose."])
    vals = [42, 51, 47, 63, 71, 84]
    for i, v in enumerate(vals):
        c.setFillColor([violet, blue, cyan][i % 3])
        c.roundRect(28 * mm + i * 26 * mm, y - 110 * mm, 16 * mm, v * 1.1 * mm, 3, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#6b7290"))
        c.setFont("Helvetica", 9)
        c.drawCentredString(36 * mm + i * 26 * mm, y - 116 * mm, ["Jan", "Feb", "Mar", "Apr", "May", "Jun"][i])
    y -= 135 * mm
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(22 * mm, y, "Highlights")
    body(c, 22 * mm, y - 14, ["• 1,284 bikes sold, up 18% on Q1", "• Average order value: 912", "• Two new workshop partners in the north"])
    c.showPage()
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(22 * mm, H - 30 * mm, "Results by range")
    rows = [("Range", "Units", "Revenue", "Margin"), ("City", "612", "498,300", "31%"), ("Trail", "344", "402,480", "28%"), ("Cargo", "128", "214,400", "24%"), ("Kids", "200", "56,000", "35%")]
    for r, row in enumerate(rows):
        yy = H - 50 * mm - r * 11 * mm
        if r == 0:
            c.setFillColor(soft)
            c.rect(22 * mm, yy - 3.5 * mm, W - 44 * mm, 9 * mm, stroke=0, fill=1)
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold" if r == 0 else "Helvetica", 11)
        for col, cell in enumerate(row):
            c.drawString(26 * mm + col * 42 * mm, yy, cell)
    body(c, 22 * mm, H - 120 * mm, ["Cargo bikes remain the fastest-growing range, though margins are lower", "while the supplier contract is renegotiated in September."])
    c.showPage()
    c.save()
    files["report"] = path

    # --- invoice ---
    path = folder / "Invoice 2026-041.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle("Invoice 2026-041")
    c.setFillColor(violet)
    c.rect(0, H - 8 * mm, W, 8 * mm, stroke=0, fill=1)
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(22 * mm, H - 35 * mm, "Invoice")
    c.setFont("Helvetica", 11)
    c.drawRightString(W - 22 * mm, H - 30 * mm, "No. 2026-041")
    c.drawRightString(W - 22 * mm, H - 36 * mm, "Issued 14 June 2026")
    body(c, 22 * mm, H - 55 * mm, ["Billed to", "Lumen Bakery", "12 Orchard Lane", "Riverton"])
    rows = [("Description", "Qty", "Price", "Amount"), ("Brand identity workshop", "1", "1,200.00", "1,200.00"), ("Logo design, three rounds", "1", "2,400.00", "2,400.00"), ("Menu layout, print-ready", "2", "350.00", "700.00"), ("Photo retouching (per image)", "12", "25.00", "300.00")]
    for r, row in enumerate(rows):
        yy = H - 100 * mm - r * 10 * mm
        if r == 0:
            c.setFillColor(soft)
            c.rect(22 * mm, yy - 3.5 * mm, W - 44 * mm, 9 * mm, stroke=0, fill=1)
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold" if r == 0 else "Helvetica", 10.5)
        c.drawString(26 * mm, yy, row[0])
        for col, cell in enumerate(row[1:]):
            c.drawRightString(W - 22 * mm - (2 - col) * 32 * mm, yy, cell)
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(W - 22 * mm, H - 160 * mm, "Total due  4,600.00")
    body(c, 22 * mm, 40 * mm, ["Payment within 30 days. Thank you for your business!"], size=10)
    c.showPage()
    c.save()
    files["invoice"] = path

    # --- guide with a photo ---
    photo = folder / ".guide-cover.jpg"
    landscape("sunrise", 1800, 1100, seed=3).save(photo, quality=90)
    path = folder / "Field guide - Alpine trails.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle("Field guide: Alpine trails")
    c.drawImage(str(photo), 0, H - 150 * mm, W, 150 * mm)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 34)
    c.drawString(20 * mm, H - 40 * mm, "Alpine trails")
    c.setFont("Helvetica", 16)
    c.drawString(20 * mm, H - 50 * mm, "A field guide for day hikers")
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, H - 170 * mm, "Before you set out")
    body(c, 20 * mm, H - 182 * mm, ["Start early: afternoon storms are common from June to August.", "Carry water, a warm layer and a paper map; phones lose signal above the treeline.", "Each route lists distance, climb and the last safe turning point."])
    c.showPage()
    for n, name in enumerate(["Lake circuit", "Ridge path"]):
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(20 * mm, H - 30 * mm, f"Route {n + 1}: {name}")
        body(c, 20 * mm, H - 42 * mm, ["Distance 11 km · Climb 640 m · 4 to 5 hours", "", "Follow the blue markers from the car park along the stream, then climb", "through the larch wood to the lake. The return crosses two footbridges."])
        c.showPage()
    c.save()
    photo.unlink()
    files["guide"] = path
    return files


def make_demo(folder: Path) -> dict[str, Path]:
    if folder.exists():
        shutil.rmtree(folder)
    (folder / "Photos").mkdir(parents=True)
    files = make_pdfs(folder)
    photos = folder / "Photos"
    landscape("sunrise", seed=11).save(photos / "Alpine sunrise.png")
    landscape("dusk", seed=5).save(photos / "Lake at dusk.webp", quality=92)
    landscape("dunes", seed=2).save(photos / "Desert dunes.jpg", quality=92)
    import pillow_heif

    pillow_heif.register_heif_opener()
    landscape("aurora", seed=9).save(photos / "Northern lights.heic", quality=90)
    files.update(sunrise=photos / "Alpine sunrise.png", dusk=photos / "Lake at dusk.webp", dunes=photos / "Desert dunes.jpg", aurora=photos / "Northern lights.heic")
    return files


# =========================================================================================
# The bridge: the real Api over HTTP, standing in for pywebview
# =========================================================================================


class DemoApi(Api):
    """The real Api, minus anything that would reach outside the demo: file dialogs return
    what the current scene chose, and nothing is opened in other apps."""

    picks: list[str] = []
    save_dir: Path = DEMO

    def pick_files(self, label: str, extensions: list[str], multiple: bool = True) -> list[str]:
        return list(self.picks) if multiple else self.picks[:1]

    def pick_pdfs(self, multiple: bool = False) -> list[str]:
        return list(self.picks) if multiple else self.picks[:1]

    def pick_file(self) -> str | None:
        return self.picks[0] if self.picks else None

    def pick_folder(self, directory: str = "") -> str | None:
        return str(self.save_dir)

    def save_pdf_dialog(self, suggested_path: str) -> str | None:
        return str(self.save_dir / Path(suggested_path).name)

    def save_file_dialog(self, suggested_path: str, label: str, extensions: list[str]) -> str | None:
        return str(self.save_dir / Path(suggested_path).name)

    def open_path(self, path: str) -> None:
        pass

    def reveal_path(self, path: str) -> None:
        pass

    # Nothing outside the demo folder may ever show up in a screenshot: browsing and previews
    # are confined to it, whatever a scene clicks.

    def get_locations(self) -> list[dict]:
        return [loc for loc in super().get_locations() if loc["kind"] != "drive" or loc["path"].upper().startswith("C:")]

    def resolve_dir(self, path: str) -> str:
        return super().resolve_dir(_confined(path))

    def list_dir(self, path: str, show_hidden: bool = False) -> dict:
        return super().list_dir(_confined(path), show_hidden)

    def read_text_file(self, path: str) -> dict:
        return super().read_text_file(_confined(path))

    def preview_file(self, path: str) -> dict:
        return super().preview_file(_confined(path))


def _confined(path: str) -> str:
    resolved = Path(os.path.expandvars(path.strip().strip('"'))).resolve() if path else DEMO
    if resolved != DEMO.resolve() and DEMO.resolve() not in resolved.parents:
        raise PermissionError("Only the demo folder can be browsed while taking screenshots")
    return str(resolved)


SHIM = b"""
(() => {
  const call = async (name, args) => {
    const r = await fetch('/__api/' + name, { method: 'POST', body: JSON.stringify(args) })
    const j = await r.json()
    if (!j.ok) throw new Error(j.error)
    return j.result
  }
  window.pywebview = { api: new Proxy({}, { get: (_, name) => (name === 'then' || typeof name !== 'string' ? undefined : (...args) => call(name, args)) }) }
})()
"""


def serve(api: DemoApi) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: Any) -> None:
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                pass  # the page navigated away mid-request

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path == "/__shim.js":
                return self._send(200, SHIM, "text/javascript")
            file = (WEB / path.lstrip("/")).resolve() if path != "/" else WEB / "index.html"
            if WEB.resolve() not in file.parents and file != WEB / "index.html" or not file.is_file():
                return self._send(404, b"not found", "text/plain")
            body = file.read_bytes()
            if file.name == "index.html":
                body = body.replace(b"<head>", b'<head><script src="/__shim.js"></script>', 1)
            self._send(200, body, mimetypes.guess_type(file.name)[0] or "application/octet-stream")

        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0)
            if self.path == "/__scene":
                scene = json.loads(body or b"{}")
                api.picks = [str(p) for p in scene.get("picks", [])]
                return self._send(200, b"{}", "application/json")
            name = self.path.removeprefix("/__api/")
            fn = getattr(api, name, None)
            if name.startswith("_") or not callable(fn):
                return self._send(404, json.dumps({"ok": False, "error": f"No method {name}"}).encode(), "application/json")
            try:
                result = {"ok": True, "result": fn(*json.loads(body or b"[]"))}
            except Exception as exc:  # noqa: BLE001 - reported to the page like pywebview does
                result = {"ok": False, "error": str(exc) or type(exc).__name__}
            self._send(200, json.dumps(result).encode(), "application/json")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def make_api() -> DemoApi:
    settings = Settings(DATA / "settings.json")
    api = DemoApi(settings, history=History(DATA / "history.db"))
    settings.set_preference("preview_open", True)
    settings.set_preference("browser_root", str(DEMO))
    api.pin_folder(str(DEMO))
    return api


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenes", nargs="*", help="scene names (default: all)")
    parser.add_argument("--serve", action="store_true", help="only run the bridge and print its URL")
    parser.add_argument("--keep", action="store_true", help="keep the demo folder afterwards")
    parser.add_argument("--site", type=Path, default=SITE, help=f"the website repo's checkout (default: {SITE})")
    args = parser.parse_args()
    if not (WEB / "index.html").is_file():
        raise SystemExit("Build the frontend first: npm run build in frontend/")
    global OUT
    OUT = args.site.resolve() / "public" / "screenshots"
    if not args.serve and not (args.site / ".vitepress").is_dir():
        raise SystemExit(
            f"No website checkout at {args.site}. Clone it there:\n"
            f"  git clone https://github.com/epicabdou/tilepress-website.git {args.site}\n"
            "or pass --site <folder>."
        )

    DEMO_FILES.update(make_demo(DEMO))
    api = make_api()
    server = serve(api)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    try:
        if args.serve:
            print(f"Bridge running at {url}  (demo files in {DEMO}; Ctrl+C to stop)", flush=True)
            while True:
                time.sleep(3600)
        return capture(url, api, args.scenes)
    except KeyboardInterrupt:
        return 0
    finally:
        server.shutdown()
        if not args.keep:
            shutil.rmtree(DEMO, ignore_errors=True)
        shutil.rmtree(DATA, ignore_errors=True)


# =========================================================================================
# Headless Edge over the DevTools protocol
# =========================================================================================

HELPERS = r"""
window.T = {
  sleep: (ms) => new Promise((r) => setTimeout(r, ms)),
  shown: (el) => !!el && el.offsetParent !== null,
  find(text, sel = 'button, [role=tab], [role=treeitem], a, label') {
    return [...document.querySelectorAll(sel)].find((e) => this.shown(e) &&
      (e.textContent.trim() === text || e.getAttribute('title') === text || e.getAttribute('aria-label') === text))
  },
  async wait(fn, what, ms = 30000) {
    const t0 = Date.now()
    for (;;) {
      const v = fn()
      if (v) return v
      if (Date.now() - t0 > ms) throw new Error('Timed out waiting for ' + what)
      await this.sleep(100)
    }
  },
  async click(text, sel) {
    const el = await this.wait(() => this.find(text, sel), JSON.stringify(text))
    el.click()
    await this.sleep(350)
    return el
  },
  async picks(paths) {
    await fetch('/__scene', { method: 'POST', body: JSON.stringify({ picks: paths }) })
  },
  // Scoped: the Explorer pane has items with the same names as sections ("Documents").
  async open(section, category, tool) {
    await this.click(section, '.section-tab')
    await this.click(category, '.tabs [role=tab]')
    if (tool) await this.click(tool, '.tool-pill')
  },
  async explore(name) {
    await this.click(name, '.browser [role=treeitem], .browser li, .browser button')
  },
  async preview(open) {
    const btn = this.find(open ? 'Show preview' : 'Hide preview')
    if (btn) { btn.click(); await this.sleep(400) }
  },
  async settle() {
    await this.wait(() => [...document.images].every((i) => i.complete), 'images')
    await this.wait(() => !document.querySelector('.spinner'), 'spinners')
    await this.sleep(900)
  },
}
"""


class Cdp:
    def __init__(self, ws_url: str) -> None:
        import websocket

        self.ws = websocket.create_connection(ws_url, timeout=120, suppress_origin=True)
        self.n = 0
        self.errors: list[str] = []

    def __call__(self, method: str, **params: Any) -> dict:
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            if msg.get("method") == "Runtime.exceptionThrown":
                self.errors.append(msg["params"]["exceptionDetails"].get("exception", {}).get("description", "error"))

    def js(self, source: str) -> Any:
        result = self("Runtime.evaluate", expression=f"(async () => {{ {source} }})()", awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in result:
            details = result["exceptionDetails"]
            raise RuntimeError(details.get("exception", {}).get("description") or details.get("text"))
        return result.get("result", {}).get("value")


def launch_edge(profile: Path) -> tuple[subprocess.Popen, Cdp]:
    proc = subprocess.Popen(
        [str(EDGE), "--headless=new", "--remote-debugging-port=0", "--remote-allow-origins=*", f"--user-data-dir={profile}",
         "--no-first-run", "--no-default-browser-check", "--hide-scrollbars", "--force-color-profile=srgb",
         f"--window-size={VIEW[0]},{VIEW[1]}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    port_file = profile / "DevToolsActivePort"
    for _ in range(100):
        if port_file.is_file() and port_file.read_text().strip():
            break
        time.sleep(0.1)
    port = int(port_file.read_text().splitlines()[0])
    pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list"))
    cdp = Cdp(next(p for p in pages if p["type"] == "page")["webSocketDebuggerUrl"])
    cdp("Runtime.enable")
    cdp("Page.enable")
    cdp("Emulation.setDeviceMetricsOverride", width=VIEW[0], height=VIEW[1], deviceScaleFactor=2, mobile=False)
    return proc, cdp


def load(cdp: Cdp, url: str, theme: str) -> None:
    cdp("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": theme}])
    cdp("Page.navigate", url=url)
    time.sleep(0.5)
    cdp.js(HELPERS + "await T.wait(() => document.querySelector('.bridge-connected'), 'the app'); await T.explore('Tilepress demo'); await T.sleep(600)")


def shot(cdp: Cdp, name: str) -> Path:
    import base64

    png = base64.b64decode(cdp("Page.captureScreenshot", format="png")["data"])
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{name}.webp"
    Image.open(io.BytesIO(png)).save(out, "WEBP", quality=86, method=6)
    return out


def make_og(screenshot: Path) -> Path:
    """1200 x 630 social-sharing card: the brand on the left, the real app on the right."""
    from PIL import ImageFont

    w, h, ss = 1200, 630, 2
    card = Image.new("RGB", (w * ss, h * ss), (11, 14, 28))
    yy, xx = np.mgrid[0 : h * ss, 0 : w * ss]
    glow = np.exp(-(((xx / (w * ss) - 0.15) ** 2) / 0.08 + ((yy / (h * ss) - 0.2) ** 2) / 0.1))
    base = np.array(card, dtype=np.float64) + glow[..., None] * np.array([90, 70, 200]) * 0.5
    card = Image.fromarray(base.clip(0, 255).astype(np.uint8))
    app = Image.open(screenshot).convert("RGB")
    app = app.resize((int(app.width * 0.36), int(app.height * 0.36)), Image.Resampling.LANCZOS)
    mask = Image.new("L", app.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, app.width - 1, app.height - 1), radius=28, fill=255)
    card.paste(app, (int(w * ss * 0.47), int(h * ss * 0.16)), mask)
    sys.path.insert(0, str(ROOT / "scripts"))
    from make_brand import render

    logo = render(96, supersample=8).resize((96 * ss // 1, 96 * ss // 1), Image.Resampling.LANCZOS)
    card.paste(logo, (64 * ss, 120 * ss), logo)
    draw = ImageDraw.Draw(card)
    font = lambda name, px: ImageFont.truetype(f"C:/Windows/Fonts/{name}", px * ss)  # noqa: E731
    draw.text((64 * ss, 240 * ss), "Tilepress", font=font("seguisb.ttf", 64), fill="white")
    for i, line in enumerate(["Free PDF and image tools", "that run on your own computer."]):
        draw.text((64 * ss, (330 + i * 40) * ss), line, font=font("segoeui.ttf", 28), fill=(214, 218, 240))
    draw.text((64 * ss, 450 * ss), "Open source · Windows · Nothing uploaded", font=font("segoeui.ttf", 20), fill=(150, 158, 190))
    out = screenshot.parent.parent / "og.png"
    card.resize((w, h), Image.Resampling.LANCZOS).save(out, optimize=True)
    return out


# =========================================================================================
# Scenes
# =========================================================================================


def scenes(files: dict[str, Path]) -> dict[str, dict]:
    q = lambda *keys: json.dumps([str(files[k]) for k in keys])  # noqa: E731
    return {
        "merge": dict(js=f"""
            await T.preview(true)
            await T.open('Documents', 'Combine, Split & Page Management', 'Merge PDF')
            await T.picks({q('report', 'guide', 'invoice')})
            await T.click('Add PDFs…')
            await T.wait(() => document.querySelectorAll('.merge-row, .merge-list li').length >= 3 || T.find('Merge and save…'), 'the files')
            await T.explore('Quarterly report Q2.pdf')
            await T.settle()
        """),
        "convert-jpg": dict(js=f"""
            await T.preview(false)
            await T.open('Images', 'Format & Size Optimization', 'Convert to JPG')
            await T.picks({q('aurora', 'sunrise', 'dusk')})
            await T.click('Add images…')
            await T.click('Convert 3 images')
            await T.wait(() => document.querySelector('.result-card'), 'the Saved card', 120000)
            document.querySelector('.content').scrollTop = 1e6  // the Saved card, above the docked bar
            await T.settle()
        """),
        "photo-editor": dict(js=f"""
            await T.preview(false)
            await T.open('Images', 'Editing & Branding', 'Photo editor')
            await T.picks({q('dusk')})
            await T.click('Open image…')
            await T.wait(() => document.querySelector('.tool:not([hidden]) canvas, .image-stage img'), 'the photo')
            await T.settle()
        """),
        "watermark": dict(js=f"""
            await T.preview(false)
            await T.open('Documents', 'Editing, Forms & Text Recognition', 'Watermark')
            await T.picks({q('invoice')})
            await T.click('Open PDF…')
            await T.sleep(2500)
            await T.settle()
        """),
        "organize": dict(js=f"""
            await T.preview(false)
            await T.open('Documents', 'Combine, Split & Page Management', 'Organize PDF')
            await T.picks({q('report')})
            await T.click('Open PDF…')
            await T.sleep(2500)
            await T.settle()
        """),
        "history": dict(before="history", js="""
            await T.preview(true)
            await T.open('Documents', 'Combine, Split & Page Management', 'Merge PDF')
            await T.click('History')
            await T.wait(() => document.querySelectorAll('.history-entry').length >= 4, 'history entries')
            await T.settle()
        """),
        "merge-light": dict(theme="light", js=f"""
            await T.preview(true)
            await T.open('Documents', 'Combine, Split & Page Management', 'Merge PDF')
            await T.picks({q('report', 'guide', 'invoice')})
            await T.click('Add PDFs…')
            await T.explore('Field guide - Alpine trails.pdf')
            await T.settle()
        """),
    }


def fill_history(api: DemoApi, files: dict[str, Path]) -> None:
    """Real tool runs, so the History scene shows genuine entries."""
    out = DEMO / "Output"
    out.mkdir(exist_ok=True)
    api.pdf_merge([{"path": str(files["report"])}, {"path": str(files["invoice"])}], str(out / "Board pack.pdf"))
    api.pdf_compress(str(files["guide"]), str(out / "Field guide - Alpine trails_compressed.pdf"))
    api.image_resize([str(files["sunrise"]), str(files["dunes"])], str(out), {"mode": "percent", "percent": 50})
    api.pdf_split(str(files["report"]), str(out), "every", "1")
    try:
        api.pdf_unlock(str(files["invoice"]), str(out / "x.pdf"), "wrong")
    except Exception:  # noqa: BLE001 - a failed run is part of the story
        pass


def capture(url: str, api: DemoApi, names: list[str]) -> int:
    if not EDGE.is_file():
        raise SystemExit(f"Microsoft Edge not found at {EDGE}")
    files = {k: v for k, v in DEMO_FILES.items()}
    plan = scenes(files)
    unknown = set(names) - set(plan)
    if unknown:
        raise SystemExit(f"Unknown scene(s): {', '.join(sorted(unknown))}. Scenes: {', '.join(plan)}")
    profile = DATA / "edge"
    proc, cdp = launch_edge(profile)
    failed = 0
    try:
        for name, scene in plan.items():
            if names and name not in names:
                continue
            if scene.get("before") == "history":
                fill_history(api, files)
            try:
                load(cdp, url, scene.get("theme", "dark"))
                cdp.js(scene["js"])
                print(f"  {name}: {shot(cdp, name)}", flush=True)
                if name == "merge":
                    print(f"  og image: {make_og(OUT / 'merge.webp')}", flush=True)
            except Exception as exc:  # noqa: BLE001 - keep going, report at the end
                failed += 1
                debug = shot(cdp, f"_failed-{name}")
                print(f"  {name}: FAILED: {exc}  (page as it was: {debug})", flush=True)
            if cdp.errors:
                print(f"    page errors: {cdp.errors[-3:]}", flush=True)
                cdp.errors.clear()
    finally:
        try:
            cdp("Browser.close")
        except Exception:  # noqa: BLE001
            proc.kill()
        proc.wait(10)
    return 1 if failed else 0


DEMO_FILES: dict[str, Path] = {}


if __name__ == "__main__":
    sys.exit(main())
