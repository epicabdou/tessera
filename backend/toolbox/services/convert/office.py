"""Word, Excel and PowerPoint to PDF.

Microsoft Office (driven through COM) gives the most faithful output and is used
when installed; LibreOffice in headless mode is the fallback.

Safety:
- Macros are force-disabled before a document is opened.
- Office runs as a separate, invisible instance we start ourselves; we never
  quit an instance that already had documents open (PowerPoint is single-instance).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Callable

from pypdf import PdfReader

from ..filesystem import replace_with_retry
from ..pdf.common import unique_path

log = logging.getLogger(__name__)

KINDS: dict[str, dict] = {
    "word": {
        "progid": "Word.Application",
        "app": "Microsoft Word",
        "exts": {"doc", "docx", "docm", "dot", "dotx", "dotm", "rtf", "odt"},
    },
    "excel": {
        "progid": "Excel.Application",
        "app": "Microsoft Excel",
        "exts": {"xls", "xlsx", "xlsm", "xlsb", "xltx", "xltm", "ods", "csv"},
    },
    "powerpoint": {
        "progid": "PowerPoint.Application",
        "app": "Microsoft PowerPoint",
        "exts": {"ppt", "pptx", "pptm", "pps", "ppsx", "pot", "potx", "odp"},
    },
}

LIBREOFFICE_TIMEOUT = 300  # seconds per file
_FORCE_DISABLE_MACROS = 3  # msoAutomationSecurityForceDisable
_LOCK = threading.Lock()  # one Office/LibreOffice job at a time


# --- engines -----------------------------------------------------------------


def _progid_installed(progid: str) -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    try:
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{progid}\CLSID").Close()
        return True
    except OSError:
        return False


def find_libreoffice() -> str | None:
    candidates = [shutil.which("soffice")]
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if base:
            candidates.append(os.path.join(base, "LibreOffice", "program", "soffice.exe"))
    for path in candidates:
        if path and os.path.isfile(path):
            # soffice.com is the console launcher: it waits for the conversion and prints errors.
            console = os.path.splitext(path)[0] + ".com"
            return console if os.path.isfile(console) else path
    return None


def engines() -> dict:
    return {
        "office": {kind: _progid_installed(spec["progid"]) for kind, spec in KINDS.items()},
        "libreoffice": find_libreoffice(),
    }


def kind_for(path: str | Path) -> str | None:
    ext = Path(path).suffix.lower().lstrip(".")
    return next((kind for kind, spec in KINDS.items() if ext in spec["exts"]), None)


# --- Microsoft Office (COM) ----------------------------------------------------


def _com_message(exc: Exception) -> str:
    # pywintypes.com_error carries Office's own description in excepinfo[2].
    info = getattr(exc, "excepinfo", None)
    if info and len(info) > 2 and info[2]:
        return str(info[2]).strip()
    return str(exc)


def _run_office(progid: str, collection: str, work: Callable) -> None:
    """Start Office on this thread, run `work(app)`, and close what we started."""
    import pythoncom
    import pywintypes
    import win32com.client

    pythoncom.CoInitialize()
    try:
        app = win32com.client.DispatchEx(progid)
        owned = getattr(app, collection).Count == 0 and not bool(app.Visible)
        try:
            app.AutomationSecurity = _FORCE_DISABLE_MACROS
            work(app)
        except pywintypes.com_error as exc:
            raise RuntimeError(_com_message(exc)) from None
        finally:
            if owned:
                try:
                    app.Quit()
                except pywintypes.com_error:
                    pass
            del app
    finally:
        pythoncom.CoUninitialize()


def _word(src: Path, out: Path, opts: dict) -> None:
    def work(word):
        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone
        doc = word.Documents.Open(
            FileName=str(src),
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False,
            PasswordDocument="",  # a protected file fails instead of prompting
            Visible=False,
            NoEncodingDialog=True,
        )
        try:
            doc.ExportAsFixedFormat(
                OutputFileName=str(out),
                ExportFormat=17,  # wdExportFormatPDF
                OpenAfterExport=False,
                OptimizeFor=1 if opts.get("quality") == "small" else 0,
                Range=0,  # whole document
                Item=7 if opts.get("markup") else 0,  # with / without tracked changes & comments
                IncludeDocProps=True,
                KeepIRM=True,
                CreateBookmarks=1 if opts.get("bookmarks", True) else 0,  # from headings
                DocStructureTags=True,
                BitmapMissingFonts=True,
                UseISO19005_1=bool(opts.get("pdfa")),
            )
        finally:
            doc.Close(SaveChanges=0)

    _run_office("Word.Application", "Documents", work)


def _excel(src: Path, out: Path, opts: dict) -> None:
    def work(excel):
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.ScreenUpdating = False
        excel.AskToUpdateLinks = False
        excel.EnableEvents = False
        wb = excel.Workbooks.Open(
            Filename=str(src),
            UpdateLinks=0,
            ReadOnly=True,
            IgnoreReadOnlyRecommended=True,
            Password="",
            Notify=False,
            AddToMru=False,
        )
        try:
            if opts.get("fit_width") or opts.get("landscape"):
                for ws in wb.Worksheets:
                    try:  # page setup talks to the printer driver and can refuse; skip such sheets
                        setup = ws.PageSetup
                        if opts.get("landscape"):
                            setup.Orientation = 2  # xlLandscape
                        if opts.get("fit_width"):
                            setup.Zoom = False
                            setup.FitToPagesWide = 1
                            setup.FitToPagesTall = False
                    except Exception as exc:  # noqa: BLE001
                        log.warning("Page setup skipped for a sheet: %s", exc)
            target = wb.ActiveSheet if opts.get("scope") == "active" else wb
            target.ExportAsFixedFormat(
                Type=0,  # xlTypePDF
                Filename=str(out),
                Quality=1 if opts.get("quality") == "small" else 0,
                IncludeDocProperties=True,
                IgnorePrintAreas=not opts.get("print_areas", True),
                OpenAfterPublish=False,
            )
        finally:
            wb.Close(SaveChanges=False)

    _run_office("Excel.Application", "Workbooks", work)


POWERPOINT_LAYOUTS = {
    "slides": 1,  # ppPrintOutputSlides
    "notes": 5,  # ppPrintOutputNotesPages
    "handouts2": 2,
    "handouts3": 3,
    "handouts6": 4,
}


def _powerpoint(src: Path, out: Path, opts: dict) -> None:
    layout = POWERPOINT_LAYOUTS.get(opts.get("layout", "slides"))
    if layout is None:
        raise ValueError(f"Unknown slide layout: {opts.get('layout')!r}")

    def work(ppt):
        ppt.DisplayAlerts = 1  # ppAlertsNone
        pres = ppt.Presentations.Open(FileName=str(src), ReadOnly=-1, Untitled=0, WithWindow=0)
        try:
            pres.ExportAsFixedFormat(
                Path=str(out),
                FixedFormatType=2,  # ppFixedFormatTypePDF
                Intent=1 if opts.get("quality") == "small" else 2,  # screen / print
                FrameSlides=-1 if opts.get("frame") else 0,
                HandoutOrder=1,
                OutputType=layout,
                PrintHiddenSlides=-1 if opts.get("hidden_slides") else 0,
                PrintRange=None,  # COM object parameter: must be passed explicitly as null
                RangeType=1,  # all slides
                IncludeDocProperties=True,
                KeepIRMSettings=True,
                DocStructureTags=True,
                BitmapMissingFonts=True,
                UseISO19005_1=bool(opts.get("pdfa")),
            )
        finally:
            pres.Close()

    _run_office("PowerPoint.Application", "Presentations", work)


_OFFICE = {"word": _word, "excel": _excel, "powerpoint": _powerpoint}


# --- LibreOffice ---------------------------------------------------------------


def _libreoffice(soffice: str, src: Path, out: Path) -> None:
    work = Path(tempfile.mkdtemp(prefix="toolbox-lo-"))
    try:
        outdir = work / "out"
        cmd = [
            soffice,
            # A private profile: works even while the user has LibreOffice open.
            f"-env:UserInstallation={(work / 'profile').as_uri()}",
            "--headless",
            "--invisible",
            "--norestore",
            "--nologo",
            "--nodefault",
            "--nolockcheck",
            "--convert-to",
            "pdf",
            "--outdir",
            str(outdir),
            str(src),
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=LIBREOFFICE_TIMEOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"LibreOffice took more than {LIBREOFFICE_TIMEOUT}s and was stopped") from None
        produced = outdir / f"{src.stem}.pdf"
        if not produced.is_file():
            detail = (proc.stderr or proc.stdout or "").strip().splitlines()
            raise RuntimeError(detail[-1] if detail else "LibreOffice produced no PDF")
        shutil.move(str(produced), str(out))
    finally:
        shutil.rmtree(work, ignore_errors=True)


# --- entry point ---------------------------------------------------------------


def convert(kind: str, path: str, output_dir: str | None = None, engine: str = "auto", options: dict | None = None) -> dict:
    """Convert one file; the PDF goes next to it (or into `output_dir`) with a non-clashing name."""
    spec = KINDS.get(kind)
    if spec is None:
        raise ValueError(f"Unknown document type: {kind!r}")
    src = Path(path)
    if not src.is_file():
        raise FileNotFoundError(f"Not a file: {src}")
    if src.suffix.lower().lstrip(".") not in spec["exts"]:
        raise ValueError(f"{src.name} isn't a file {spec['app']} can convert")

    available = engines()
    if engine == "auto":
        engine = "office" if available["office"][kind] else "libreoffice" if available["libreoffice"] else ""
    if not engine:
        raise RuntimeError("Converting needs Microsoft Office or LibreOffice. Install either one and try again.")
    if engine == "office" and not available["office"][kind]:
        raise RuntimeError(f"{spec['app']} isn't installed")
    if engine == "libreoffice" and not available["libreoffice"]:
        raise RuntimeError("LibreOffice isn't installed")
    if engine not in ("office", "libreoffice"):
        raise ValueError(f"Unknown engine: {engine!r}")

    out = unique_path(Path(output_dir or src.parent) / f"{src.stem}.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".{out.stem}.{os.getpid()}.converting.pdf")
    who = spec["app"] if engine == "office" else "LibreOffice"
    with _LOCK:
        try:
            if engine == "office":
                _OFFICE[kind](src, tmp, options or {})
            else:
                _libreoffice(available["libreoffice"], src, tmp)
            replace_with_retry(tmp, out)
        except RuntimeError as exc:
            raise RuntimeError(f"{who} couldn't convert {src.name}: {exc}") from None
        finally:
            tmp.unlink(missing_ok=True)
    return {
        "path": str(out),
        "name": out.name,
        "size": out.stat().st_size,
        "page_count": len(PdfReader(out).pages),
        "engine": engine,
    }
