"""Conversion: From PDF (Word, PowerPoint, Excel, images, Markdown)."""

from __future__ import annotations

from pathlib import Path

from ..pdf.common import unique_path


def suggest_path(source: str, ext: str, folder: str | None = None) -> str:
    """`report.pdf` -> `report.docx` next to it (or in `folder`), never clashing."""
    src = Path(source)
    return str(unique_path(Path(folder or src.parent) / f"{src.stem}.{ext.lstrip('.')}"))
