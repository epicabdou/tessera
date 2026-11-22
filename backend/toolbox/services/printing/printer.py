"""Windows printing: list printers and send a PDF with chosen settings.

The page is drawn by PDFium straight onto the printer's device context (vector
output, not a bitmap), so text stays sharp at any printer resolution. Settings
(copies, duplex, colour, paper, orientation) go to the driver in its DEVMODE.
"""

from __future__ import annotations

import ctypes
import sys
import tempfile
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import wait as futures_wait
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

from ..pdf import render
from ..progress import Progress
from .impose import impose

DUPLEX = {"none": 1, "long": 2, "short": 3}  # DMDUP_SIMPLEX / VERTICAL / HORIZONTAL
_DC_PAPERS, _DC_PAPERNAMES, _DC_PAPERSIZE, _DC_DUPLEX, _DC_COLORDEVICE = 2, 16, 3, 7, 32


def _win32():
    if sys.platform != "win32":
        raise RuntimeError("Printing is only available on Windows")
    import win32con
    import win32gui
    import win32print
    import win32ui

    return win32print, win32ui, win32gui, win32con


# Capabilities come from the printer driver. For a network printer that is off or
# unreachable this can take half a minute, and pywin32 holds the GIL for the whole call
# (freezing every other Python thread). So they are read with ctypes (which releases the
# GIL), in parallel, with a short wait; slow printers are listed at once and their details
# fill in on a later call. Answers are cached for the session.
_CAPS: dict[str, dict] = {}
_PENDING: dict[str, Future] = {}
_CAPS_LOCK = threading.Lock()
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="printer-caps")
_NO_CAPS = {"duplex": False, "color": False, "papers": []}


def _device_capabilities():
    from ctypes import wintypes

    fn = ctypes.WinDLL("winspool.drv").DeviceCapabilitiesW
    fn.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.WORD, ctypes.c_void_p, ctypes.c_void_p]
    fn.restype = ctypes.c_int
    return fn


def _query_caps(name: str, port: str) -> dict:
    from ctypes import wintypes

    caps = _device_capabilities()
    try:
        count = caps(name, port, _DC_PAPERS, None, None)
        papers = []
        if count > 0:
            ids = (wintypes.WORD * count)()
            names = (wintypes.WCHAR * (64 * count))()
            sizes = (wintypes.POINT * count)()
            caps(name, port, _DC_PAPERS, ids, None)
            caps(name, port, _DC_PAPERNAMES, names, None)
            caps(name, port, _DC_PAPERSIZE, sizes, None)
            for i in range(count):
                label = ctypes.wstring_at(ctypes.addressof(names) + i * 128, 64).split("\x00", 1)[0].strip()
                papers.append({"id": int(ids[i]), "name": label, "w_mm": round(sizes[i].x / 10), "h_mm": round(sizes[i].y / 10)})
        result = {
            "duplex": caps(name, port, _DC_DUPLEX, None, None) == 1,
            "color": caps(name, port, _DC_COLORDEVICE, None, None) == 1,
            "papers": papers,
        }
    except Exception:  # noqa: BLE001 - a broken driver: list the printer without capabilities
        result = dict(_NO_CAPS)
    with _CAPS_LOCK:
        _CAPS[name] = result
        _PENDING.pop(name, None)
    return result


def _installed() -> tuple[list[tuple[str, str]], str | None]:
    """(name, port) of every printer, and the default printer's name."""
    win32print, *_ = _win32()
    try:
        default = win32print.GetDefaultPrinter() or None
    except Exception:  # noqa: BLE001 - no default printer set
        default = None
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    return [(p["pPrinterName"], p["pPortName"]) for p in win32print.EnumPrinters(flags, None, 2)], default


def printers(wait: float = 2.5) -> list[dict]:
    """Installed printers, default first. `ready` is False while a slow printer's
    capabilities (duplex, colour, paper sizes) are still being read; ask again later."""
    installed, default = _installed()
    waiting = []
    with _CAPS_LOCK:
        for name, port in installed:
            if name in _CAPS:
                continue
            if name not in _PENDING:
                _PENDING[name] = _POOL.submit(_query_caps, name, port)
            waiting.append(_PENDING[name])
    if waiting:
        futures_wait(waiting, timeout=wait)
    result = []
    with _CAPS_LOCK:
        for name, _port in installed:
            caps = _CAPS.get(name)
            result.append({"name": name, "default": name == default, "ready": caps is not None, **(caps or _NO_CAPS)})
    result.sort(key=lambda p: (not p["default"], p["name"].lower()))
    return result


def print_pdf(path: str, printer: str, options: dict, progress: Progress | None = None) -> dict:
    """options: everything impose() takes, plus copies, collate, duplex ("none"|"long"|"short"),
    color (bool), paper_id (driver paper id, optional), scale ("fit"|"actual"|percent number),
    auto_rotate (bool), output_file (print-to-file printers such as Microsoft Print to PDF)."""
    win32print, win32ui, win32gui, win32con = _win32()
    if printer not in {name for name, _port in _installed()[0]}:
        raise ValueError(f"Printer not found: {printer}")
    copies = max(1, min(999, int(options.get("copies", 1))))
    duplex = options.get("duplex", "none")
    if duplex not in DUPLEX:
        raise ValueError(f"Unknown duplex mode: {duplex!r}")
    gray = not options.get("color", True)

    with tempfile.TemporaryDirectory(prefix="toolbox-print-") as tmp:
        prepared = Path(tmp) / "prepared.pdf"
        imposed = impose(path, str(prepared), options)

        handle = win32print.OpenPrinter(printer)
        try:
            devmode = win32print.GetPrinter(handle, 2)["pDevMode"]
            devmode.Copies = copies
            devmode.Collate = 1 if options.get("collate", True) else 0
            devmode.Duplex = DUPLEX[duplex]
            devmode.Color = 1 if gray else 2  # DMCOLOR_MONOCHROME / DMCOLOR_COLOR
            if options.get("paper_id"):
                devmode.PaperSize = int(options["paper_id"])
            fields = win32con.DM_COPIES | win32con.DM_COLLATE | win32con.DM_DUPLEX | win32con.DM_COLOR
            if options.get("paper_id"):
                fields |= win32con.DM_PAPERSIZE
            devmode.Fields = devmode.Fields | fields
            win32print.DocumentProperties(0, handle, printer, devmode, devmode, win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER)
        finally:
            win32print.ClosePrinter(handle)

        hdc = win32gui.CreateDC("WINSPOOL", printer, devmode)
        dc = win32ui.CreateDCFromHandle(hdc)
        sent = 0
        try:
            title = Path(path).name
            output_file = options.get("output_file")
            dc.StartDoc(title, output_file) if output_file else dc.StartDoc(title)
            horz, vert = dc.GetDeviceCaps(win32con.HORZRES), dc.GetDeviceCaps(win32con.VERTRES)
            dpi_x, dpi_y = dc.GetDeviceCaps(win32con.LOGPIXELSX), dc.GetDeviceCaps(win32con.LOGPIXELSY)
            flags = pdfium_c.FPDF_ANNOT | pdfium_c.FPDF_PRINTING | (pdfium_c.FPDF_GRAYSCALE if gray else 0)
            scale_opt = options.get("scale", "fit")
            with render._LOCK:
                doc = pdfium.PdfDocument(str(prepared))
                try:
                    total = len(doc)
                    for i in range(total):
                        page = doc[i]
                        try:
                            w_pt, h_pt = page.get_size()
                            # Turn landscape pages to fit portrait paper (and vice versa).
                            turn = bool(options.get("auto_rotate", True)) and (w_pt > h_pt) != (horz > vert)
                            if turn:
                                w_pt, h_pt = h_pt, w_pt
                            natural_w, natural_h = w_pt / 72 * dpi_x, h_pt / 72 * dpi_y
                            if scale_opt == "fit":
                                s = min(horz / natural_w, vert / natural_h)
                            elif scale_opt == "actual":
                                s = 1.0
                            else:
                                s = float(scale_opt) / 100
                            out_w, out_h = int(natural_w * s), int(natural_h * s)
                            x, y = (horz - out_w) // 2, (vert - out_h) // 2
                            dc.StartPage()
                            pdfium_c.FPDF_RenderPage(ctypes.c_void_p(dc.GetSafeHdc()), page.raw, x, y, out_w, out_h, 1 if turn else 0, flags)
                            dc.EndPage()
                            sent += 1
                        finally:
                            page.close()
                        if progress:
                            progress(i + 1, total, f"Sending sheet {i + 1} of {total}")
                finally:
                    doc.close()
            dc.EndDoc()
        except Exception:
            try:
                dc.AbortDoc()
            except Exception:  # noqa: BLE001
                pass
            raise
        finally:
            dc.DeleteDC()
    return {"printer": printer, "sheets": sent, "copies": copies, "source_pages": imposed["source_pages"]}
