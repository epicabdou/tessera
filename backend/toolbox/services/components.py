"""Optional components the app installs itself on first run (today: the Tectonic LaTeX engine).

On every start the app calls ensure_latex(): if no LaTeX engine is installed it
downloads the pinned Tectonic release, checks its SHA-256, unpacks it into the
user's data folder and compiles a tiny document once so Tectonic fetches its
core TeX files. Progress is readable at any time through status().
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

from .. import APP_NAME
from . import latex
from .filesystem import replace_with_retry

log = logging.getLogger(__name__)

TECTONIC_VERSION = "0.15.0"
TECTONIC_URL = (
    "https://github.com/tectonic-typesetting/tectonic/releases/download/"
    f"tectonic%40{TECTONIC_VERSION}/tectonic-{TECTONIC_VERSION}-x86_64-pc-windows-msvc.zip"
)
TECTONIC_SHA256 = "1d6bb76f049c8a3774f6e9d66e4b04e1a8c3dcb37527b6b41b7e894328e7bf29"
# Compiled once after install, so what most documents need (text and math fonts, amsmath,
# graphicx, hyperref) is already cached the first time the user compiles.
WARM_UP = r"""\documentclass{article}
\usepackage{amsmath,amssymb,graphicx,hyperref}
\begin{document}
\section{Ready}
\textbf{Bold} \textit{italic} \texttt{mono} $x^2 + \sqrt{y}$
\[ \sum_{i=1}^{n} \frac{1}{i^2} = \int_0^1 f(x)\,dx \]
\begin{itemize}\item one\end{itemize}
\end{document}"""


class Components:
    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir / "tectonic"
        self._lock = threading.Lock()
        self._state = {"state": "unknown", "progress": 0.0, "error": None}

    # --- status ------------------------------------------------------------------

    @property
    def tectonic_path(self) -> str:
        return str(self._dir / "tectonic.exe")

    def latex_engines(self) -> dict:
        return latex.find_engines(self.tectonic_path)

    def status(self) -> dict:
        engines = self.latex_engines()
        chosen = latex.pick_engine(engines)
        with self._lock:
            state = dict(self._state)
        if chosen and state["state"] in ("unknown", "missing", "error"):
            state = {"state": "ready", "progress": 1.0, "error": None}
        return {"latex": {**state, "engine": chosen[0] if chosen else None, "engines": engines}}

    def _set(self, **changes) -> None:
        with self._lock:
            self._state.update(changes)

    # --- install -------------------------------------------------------------------

    def ensure_latex(self) -> None:
        """Install and warm up Tectonic unless some LaTeX engine is already usable. Safe to call twice."""
        with self._lock:
            if self._state["state"] in ("downloading", "installing", "warming"):
                return
        chosen = latex.pick_engine(self.latex_engines())
        if chosen and (chosen[0] != "tectonic" or (self._dir / ".warmed").is_file()):
            self._set(state="ready", progress=1.0, error=None)
            return
        try:
            started = time.monotonic()
            if not Path(self.tectonic_path).is_file():
                log.info("No LaTeX engine found: downloading Tectonic %s", TECTONIC_VERSION)
                self._download()
            self._warm_up()
            self._set(state="ready", progress=1.0, error=None)
            log.info("LaTeX engine ready (Tectonic %s, set up in %.0f s)", TECTONIC_VERSION, time.monotonic() - started)
        except Exception as exc:  # noqa: BLE001 - reported to the UI, retried next start
            log.exception("LaTeX engine setup failed")
            self._set(state="error", error=str(exc))

    def _download(self) -> None:
        self._set(state="downloading", progress=0.0, error=None)
        self._dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="toolbox-tectonic-") as tmp:
            archive = Path(tmp) / "tectonic.zip"
            digest = hashlib.sha256()
            request = urllib.request.Request(TECTONIC_URL, headers={"User-Agent": f"{APP_NAME}-desktop"})
            with urllib.request.urlopen(request, timeout=60) as response, open(archive, "wb") as out:
                total = int(response.headers.get("Content-Length") or 0)
                done = 0
                while chunk := response.read(256 * 1024):
                    out.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
                    if total:
                        self._set(progress=round(done / total, 3))
            if digest.hexdigest() != TECTONIC_SHA256:
                raise RuntimeError("The downloaded LaTeX engine didn't match its checksum and was discarded")
            self._set(state="installing")
            with zipfile.ZipFile(archive) as zf:
                member = next((n for n in zf.namelist() if n.lower().endswith("tectonic.exe")), None)
                if member is None:
                    raise RuntimeError("The download didn't contain tectonic.exe")
                staged = Path(tmp) / "tectonic.exe"
                with zf.open(member) as src, open(staged, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            replace_with_retry(staged, self.tectonic_path)

    def _warm_up(self) -> None:
        """First compile fetches Tectonic's core TeX files, so the user's first compile is quick."""
        if (self._dir / ".warmed").is_file():
            return
        self._set(state="warming", progress=1.0)
        with tempfile.TemporaryDirectory(prefix="toolbox-latex-warm-") as tmp:
            doc = Path(tmp) / "warmup.tex"
            doc.write_text(WARM_UP, encoding="utf-8")
            result = latex.compile_tex(str(doc), "tectonic", self.tectonic_path, timeout=900)
        if not result["ok"]:
            first = next((m["message"] for m in result["messages"] if m["kind"] == "error"), "unknown error")
            raise RuntimeError(f"LaTeX engine test compile failed: {first}")
        (self._dir / ".warmed").write_text(TECTONIC_VERSION)
