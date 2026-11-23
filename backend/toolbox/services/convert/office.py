"""Word, Excel and PowerPoint to PDF.

Microsoft Office (driven through COM) gives the most faithful output and is used
when installed; LibreOffice in headless mode is the fallback.

Safety:
- Macros are force-disabled before a document is opened.
- Office runs as a separate, invisible instance we start ourselves; we never
  quit an instance that already had documents open (PowerPoint is single-instance).
- An instance we started is watched: if it stops to show a prompt nobody can see
  (or runs far too long), it is ended and the job fails with a clear error
  instead of waiting forever.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
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


OFFICE_TIMEOUT = 30 * 60  # seconds for one job: a last resort, PDF import of a long file is slow
PROMPT_GRACE = 8.0  # seconds a prompt may stay up before the job is given up
QUIT_GRACE = 60.0  # seconds Office gets to exit after Quit()


def _office_pid(app) -> int | None:
    """Process id of the Office instance behind `app`."""
    import win32gui
    import win32process

    hwnd = 0
    try:
        hwnd = int(app.Hwnd)  # Excel and PowerPoint
    except Exception:  # noqa: BLE001
        pass
    if not hwnd:  # Word has no Application.Hwnd: find its main window by a unique caption
        token = f"Tessera {uuid.uuid4().hex}"
        try:
            app.Caption = token
            hwnd = win32gui.FindWindow("OpusApp", token)
        except Exception:  # noqa: BLE001
            hwnd = 0
    return (win32process.GetWindowThreadProcessId(hwnd)[1] or None) if hwnd else None


def _is_prompt_class(name: str) -> bool:
    return name in ("#32770", "NUIDialog") or name.startswith("bosa_sdm")


def _prompts(is_ours: Callable[[int], bool]) -> list[tuple[int, int, str]]:
    """Visible dialogs shown by processes `is_ours` accepts, as (hwnd, pid, message). The message
    is "" when it can't be read (Office's own dialogs have no readable child windows)."""
    import win32gui
    import win32process

    found: list[tuple[int, int, str]] = []

    def child(hwnd: int, parts: list[str]) -> bool:
        if win32gui.GetClassName(hwnd) == "Static" and win32gui.GetWindowText(hwnd).strip():
            parts.append(win32gui.GetWindowText(hwnd).strip())
        return True

    def top(hwnd: int, _: None) -> bool:
        if not win32gui.IsWindowVisible(hwnd) or not _is_prompt_class(win32gui.GetClassName(hwnd)):
            return True
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        if not is_ours(pid):
            return True
        parts: list[str] = []
        try:
            win32gui.EnumChildWindows(hwnd, child, parts)
        except Exception:  # noqa: BLE001
            pass
        found.append((hwnd, pid, " ".join(parts)))
        return True

    try:
        win32gui.EnumWindows(top, None)
    except Exception:  # noqa: BLE001
        pass
    return found


def _press_default_button(hwnd: int) -> None:
    """Press Enter in a dialog, i.e. its default button (OK)."""
    import win32api
    import win32con
    import win32gui

    target = hwnd
    if win32gui.GetClassName(hwnd) == "NUIDialog":  # Office's own dialogs take keys in their NetUI pane
        kids: list[int] = []
        try:
            win32gui.EnumChildWindows(hwnd, lambda c, acc: acc.append(c) or True, kids)
        except Exception:  # noqa: BLE001
            pass
        target = next((k for k in kids if win32gui.GetClassName(k) == "NetUIHWND"), hwnd)
    win32api.PostMessage(target, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0x001C0001)
    win32api.PostMessage(target, win32con.WM_KEYUP, win32con.VK_RETURN, 0xC01C0001)


def _process_info(pid: int) -> tuple[str, float] | None:
    """(exe file name in lower case, start time as a Unix timestamp) of process `pid`."""
    import win32api
    import win32con
    import win32process

    try:
        handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid)
    except Exception:  # noqa: BLE001 - gone, or not ours to inspect
        return None
    try:
        exe = os.path.basename(win32process.GetModuleFileNameEx(handle, 0)).lower()
        return exe, win32process.GetProcessTimes(handle)["CreationTime"].timestamp()
    except Exception:  # noqa: BLE001
        return None
    finally:
        win32api.CloseHandle(handle)


def _terminate(pid: int) -> None:
    import win32api
    import win32con

    try:
        handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE, False, pid)
    except Exception:  # noqa: BLE001 - already gone
        return
    try:
        win32api.TerminateProcess(handle, 1)
    except Exception:  # noqa: BLE001
        pass
    finally:
        win32api.CloseHandle(handle)


def _reap_later(pid: int) -> None:
    """End our Office instance if it is still running QUIT_GRACE seconds after Quit(): an
    invisible Office stuck on a prompt at exit would otherwise stay in memory for good."""
    import win32api
    import win32con
    import win32event

    try:  # the handle pins this exact process, so a recycled pid is never hit
        handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE | win32con.SYNCHRONIZE, False, pid)
    except Exception:  # noqa: BLE001 - already gone
        return

    def wait() -> None:
        try:
            if win32event.WaitForSingleObject(handle, int(QUIT_GRACE * 1000)) == win32event.WAIT_TIMEOUT:
                log.warning("Office (pid %s) didn't exit after Quit; ending it", pid)
                win32api.TerminateProcess(handle, 1)
        except Exception:  # noqa: BLE001
            pass
        finally:
            win32api.CloseHandle(handle)

    threading.Thread(target=wait, name="office-reaper", daemon=True).start()


class _Watchdog:
    """Office runs hidden here, so a question it asks (crash recovery, a locked Normal.dotm...)
    would wait forever for a click nobody can make, and the job would never end.

    Prompts from `helpers` (exe names of Office's out-of-process servers started during the job,
    such as PDFREFLOW.EXE, which does Word's PDF import and first shows "Word will now convert
    your PDF...") are answered with their default button, as a user would. If any prompt stays up
    for PROMPT_GRACE seconds anyway, or the job passes OFFICE_TIMEOUT, Office and those helpers
    are ended: the pending COM call then fails, and `reason` says why."""

    def __init__(self, pid: int, helpers: tuple[str, ...] = (), timeout: float = OFFICE_TIMEOUT) -> None:
        self.pid = pid
        self.reason: str | None = None
        self._helpers = {h.lower() for h in helpers}
        self._since = time.time() - 1  # helper processes started after this belong to the job
        self._owners: dict[int, bool] = {pid: True}
        self._timeout = timeout
        self._lock = threading.Lock()
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._watch, name="office-watchdog", daemon=True)
        self._thread.start()

    def _is_helper(self, pid: int) -> bool:
        if pid not in self._owners:
            info = _process_info(pid) if self._helpers else None
            self._owners[pid] = bool(info and info[0] in self._helpers and info[1] >= self._since)
        return self._owners[pid] and pid != self.pid

    def _is_ours(self, pid: int) -> bool:
        return pid == self.pid or self._is_helper(pid)

    def _watch(self) -> None:
        started = time.monotonic()
        seen: dict[int, float] = {}  # prompt hwnd -> when it was first seen
        presses: dict[int, int] = {}
        while not self._stopped.wait(0.5):
            now = time.monotonic()
            prompts = _prompts(self._is_ours)
            seen = {hwnd: seen.get(hwnd, now) for hwnd, _, _ in prompts}
            stuck = None
            for hwnd, pid, message in prompts:
                age = now - seen[hwnd]
                if pid != self.pid and age >= 0.5 and presses.get(hwnd, 0) < 3 and age >= 2 * presses.get(hwnd, 0):
                    log.info("Answering a prompt from Office's helper (pid %s)", pid)
                    try:
                        _press_default_button(hwnd)
                    except Exception:  # noqa: BLE001 - closed meanwhile
                        pass
                    presses[hwnd] = presses.get(hwnd, 0) + 1
                if age >= PROMPT_GRACE:
                    stuck = message
            if stuck is not None:
                said = f" (“{stuck}”)" if stuck else ""
                reason = f"stopped to show a message{said} that can't be answered while it runs in the background"
            elif now - started >= self._timeout:
                reason = f"didn't finish within {int(self._timeout // 60)} minutes"
            else:
                continue
            with self._lock:
                if not self._stopped.is_set():
                    self.reason = reason
                    log.warning("Ending Office (pid %s): %s", self.pid, reason)
                    self._end_all()
            return

    def _end_all(self) -> None:
        """End Office and every helper the job started (an orphaned helper would wait forever)."""
        import win32process

        _terminate(self.pid)
        if self._helpers:
            for pid in win32process.EnumProcesses():
                if pid and self._is_helper(pid):
                    _terminate(pid)

    def stop(self) -> None:
        with self._lock:
            self._stopped.set()
        self._thread.join()


def _run_office(progid: str, collection: str, work: Callable, helpers: tuple[str, ...] = ()) -> None:
    """Start Office on this thread, run `work(app)`, and close what we started. `helpers`: see _Watchdog."""
    import pythoncom
    import pywintypes
    import win32com.client

    pythoncom.CoInitialize()
    try:
        app = win32com.client.DispatchEx(progid)
        owned = getattr(app, collection).Count == 0 and not bool(app.Visible)
        # Only an instance we started ourselves is watched (and ended if it hangs), never the user's.
        pid = _office_pid(app) if owned else None
        watchdog = _Watchdog(pid, helpers) if pid else None
        try:
            app.AutomationSecurity = _FORCE_DISABLE_MACROS
            work(app)
        except pywintypes.com_error as exc:
            if watchdog:
                watchdog.stop()
            if watchdog and watchdog.reason:
                raise RuntimeError(f"it {watchdog.reason}, so it was closed") from None
            raise RuntimeError(_com_message(exc)) from None
        finally:
            if watchdog:
                watchdog.stop()
            if owned and not (watchdog and watchdog.reason):
                try:
                    app.Quit()
                except Exception:  # noqa: BLE001 - Office may be gone (crashed); keep the real error
                    pass
                if pid:
                    _reap_later(pid)
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
