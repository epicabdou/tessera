"""Conversion: To PDF.

office.py     Word / Excel / PowerPoint via Microsoft Office (COM) or LibreOffice
images.py     images to PDF pages (JPEGs embedded byte-for-byte)
markdown.py   Markdown to a styled HTML document
web.py        page sizes, print options and HTML sources for the WebView2 printer
"""

from __future__ import annotations

from pathlib import Path

from ..filesystem import known_folder
from ..pdf.common import unique_path


def suggest_pdf_path(source: str | None, hint: str = "document") -> str:
    """Where a new PDF should go: next to its source file, else in Downloads."""
    if source:
        src = Path(source)
        return str(unique_path(src.with_suffix(".pdf")))
    folder = Path(known_folder("downloads") or Path.home())
    safe = "".join(c if c.isalnum() or c in " -_." else "_" for c in hint).strip(" ._") or "document"
    return str(unique_path(folder / f"{safe[:80]}.pdf"))
