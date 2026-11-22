"""LaTeX: find an engine, compile, and turn the log into clickable errors."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from .filesystem import replace_with_retry

COMPILE_TIMEOUT = 300  # seconds; the first Tectonic run downloads packages
ENGINES = ("tectonic", "latexmk", "pdflatex", "xelatex", "lualatex")
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _search_dirs() -> list[Path]:
    """Where TeX distributions put their binaries when they aren't on PATH."""
    local = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    dirs = [
        Path(local) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64",
        Path(program_files) / "MiKTeX" / "miktex" / "bin" / "x64",
    ]
    texlive = Path("C:/texlive")
    if texlive.is_dir():
        dirs += sorted(texlive.glob("*/bin/windows"), reverse=True) + sorted(texlive.glob("*/bin/win64"), reverse=True)
    return dirs


def find_engines(tectonic_path: str | None = None) -> dict[str, str | None]:
    found: dict[str, str | None] = {}
    for name in ENGINES:
        path = shutil.which(name)
        if not path:
            for d in _search_dirs():
                candidate = d / f"{name}.exe"
                if candidate.is_file():
                    path = str(candidate)
                    break
        found[name] = path
    if tectonic_path and Path(tectonic_path).is_file():
        found["tectonic"] = tectonic_path
    return found


def pick_engine(engines: dict[str, str | None], preferred: str = "auto") -> tuple[str, str] | None:
    if preferred != "auto":
        path = engines.get(preferred)
        return (preferred, path) if path else None
    for name in ENGINES:
        if engines.get(name):
            return name, engines[name]  # type: ignore[return-value]
    return None


# --- log parsing ---------------------------------------------------------------

_FILE_LINE = re.compile(r"^(?:error: )?(?P<file>[^\s:][^:\n]*\.(?:tex|sty|cls|bib)):(?P<line>\d+): (?P<msg>.+)$", re.M)
_BANG = re.compile(r"^! (?P<msg>.+?)\n(?:.*\n){0,6}?l\.(?P<line>\d+)", re.M)
_WARNING = re.compile(r"^(?:LaTeX|Package \w+) Warning: (?P<msg>.+?)(?: on input line (?P<line>\d+))?\.?$", re.M)


def parse_log(text: str, main_file: str) -> list[dict]:
    """Errors and warnings with line numbers (when TeX gives one)."""
    items: list[dict] = []
    seen: set[tuple] = set()

    def add(kind: str, msg: str, line: str | None, file: str | None = None) -> None:
        key = (kind, msg.strip(), line)
        if key in seen:
            return
        seen.add(key)
        items.append({"kind": kind, "message": msg.strip(), "line": int(line) if line else None, "file": file or main_file})

    for m in _FILE_LINE.finditer(text):
        add("error", m.group("msg"), m.group("line"), Path(m.group("file")).name)
    for m in _BANG.finditer(text):
        add("error", m.group("msg"), m.group("line"))
    for m in _WARNING.finditer(text):
        add("warning", m.group("msg"), m.group("line"))
    # Tectonic's own messages ("error: something failed") without a location
    for m in re.finditer(r"^error: (?!.*\.tex:\d+:)(.+)$", text, re.M):
        add("error", m.group(1), None)
    return items


# --- compiling -----------------------------------------------------------------


def _command(engine: str, exe: str, src: Path, build: Path) -> list[str]:
    if engine == "tectonic":
        return [exe, "--outdir", str(build), "--keep-logs", "--synctex", str(src)]
    if engine == "latexmk":
        return [exe, "-pdf", "-interaction=nonstopmode", "-file-line-error", "-halt-on-error", f"-outdir={build}", str(src)]
    return [exe, "-interaction=nonstopmode", "-file-line-error", "-halt-on-error", f"-output-directory={build}", str(src)]


def compile_tex(
    source: str, engine: str = "auto", tectonic_path: str | None = None, timeout: int = COMPILE_TIMEOUT
) -> dict:
    """Compile `source` (a .tex file) in its own folder; the PDF is written next to it."""
    src = Path(source)
    if not src.is_file() or src.suffix.lower() != ".tex":
        raise ValueError("Choose a .tex file to compile")
    chosen = pick_engine(find_engines(tectonic_path), engine)
    if chosen is None:
        raise RuntimeError("No LaTeX engine is installed yet")
    name, exe = chosen
    build = src.parent / ".toolbox-build"
    build.mkdir(exist_ok=True)

    started = time.monotonic()
    log_text = ""
    runs = 2 if name in ("pdflatex", "xelatex", "lualatex") else 1  # second run resolves references
    for _ in range(runs):
        try:
            proc = subprocess.run(
                _command(name, exe, src, build),
                cwd=src.parent,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=_NO_WINDOW,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"{name} took more than {timeout}s and was stopped") from None
        log_file = build / f"{src.stem}.log"
        file_log = log_file.read_text(encoding="utf-8", errors="replace") if log_file.is_file() else ""
        log_text = "\n".join(part for part in (proc.stdout, proc.stderr, file_log) if part)
        if proc.returncode != 0 or "Rerun to get" not in file_log:
            break

    built = build / f"{src.stem}.pdf"
    messages = parse_log(log_text, src.name)
    ok = proc.returncode == 0 and built.is_file()
    pdf = None
    if built.is_file():
        target = src.with_suffix(".pdf")
        shutil.copyfile(built, build / f".{src.stem}.copy.pdf")
        replace_with_retry(build / f".{src.stem}.copy.pdf", target)
        pdf = str(target)
    if not ok and not any(m["kind"] == "error" for m in messages):
        tail = [line for line in log_text.strip().splitlines() if line.strip()][-3:]
        messages.insert(0, {"kind": "error", "message": " ".join(tail) or "Compilation failed", "line": None, "file": src.name})
    return {
        "ok": ok,
        "pdf": pdf,
        "engine": name,
        "seconds": round(time.monotonic() - started, 1),
        "messages": messages,
        "log": log_text[-200_000:],
    }


TEMPLATES = {
    "article": r"""\documentclass[11pt]{article}
\usepackage{amsmath, amssymb, graphicx, hyperref}
\usepackage[margin=2.5cm]{geometry}

\title{Untitled document}
\author{Your name}
\date{\today}

\begin{document}
\maketitle

\section{Introduction}
Write here. Inline maths like $e^{i\pi} + 1 = 0$, or displayed:
\begin{equation}
  \int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2}
\end{equation}

\end{document}
""",
    "report": r"""\documentclass[11pt]{report}
\usepackage{amsmath, graphicx, hyperref}
\title{Report title}
\author{Your name}
\begin{document}
\maketitle
\tableofcontents
\chapter{Introduction}
Write here.
\chapter{Results}
\end{document}
""",
    "beamer": r"""\documentclass{beamer}
\usetheme{Madrid}
\title{Presentation title}
\author{Your name}
\begin{document}
\frame{\titlepage}
\begin{frame}{First slide}
  \begin{itemize}
    \item One point
    \item Another point
  \end{itemize}
\end{frame}
\end{document}
""",
    "letter": r"""\documentclass{letter}
\signature{Your name}
\address{Street \\ City}
\begin{document}
\begin{letter}{Recipient \\ Their address}
\opening{Dear Sir or Madam,}
Write the letter here.
\closing{Yours faithfully,}
\end{letter}
\end{document}
""",
}
