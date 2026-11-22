"""Print options and page sources for HTML-to-PDF (the printing itself lives in toolbox/html_print.py)."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

PAGE_SIZES_IN = {  # inches, portrait
    "a4": (8.27, 11.69),
    "letter": (8.5, 11.0),
    "legal": (8.5, 14.0),
    "a3": (11.69, 16.54),
    "a5": (5.83, 8.27),
}
MARGINS_IN = {"none": 0.0, "narrow": 0.25, "normal": 0.5, "wide": 1.0}


def print_settings(options: dict) -> dict:
    """Validate UI options into the values WebView2's print settings take."""
    size = options.get("page_size", "a4")
    if size not in PAGE_SIZES_IN:
        raise ValueError(f"Unknown page size: {size!r}")
    margin = options.get("margin", "normal")
    if margin not in MARGINS_IN:
        raise ValueError(f"Unknown margin: {margin!r}")
    scale = float(options.get("scale", 100)) / 100
    if not 0.1 <= scale <= 2.0:
        raise ValueError("Scale must be between 10% and 200%")
    wait = float(options.get("wait", 0))
    if not 0 <= wait <= 30:
        raise ValueError("Wait must be between 0 and 30 seconds")
    width, height = PAGE_SIZES_IN[size]
    return {
        "width": width,
        "height": height,
        "landscape": options.get("orientation") == "landscape",
        "margin": MARGINS_IN[margin],
        "scale": scale,
        "backgrounds": bool(options.get("backgrounds", True)),
        "header_footer": bool(options.get("header_footer", False)),
        "wait": wait,
        "scroll": bool(options.get("scroll", False)),
    }


def normalize_url(text: str) -> str:
    """Accept what people paste: bare domains get https://; only web pages are allowed."""
    url = (text or "").strip()
    if not url:
        raise ValueError("Enter a web address")
    # "scheme:" (but not "host:8080") means the user gave a scheme; only web ones are allowed.
    scheme = re.match(r"^([a-z][a-z0-9+.-]*):(?!\d)", url, re.I)
    if scheme and scheme.group(1).lower() not in ("http", "https"):
        raise ValueError("Only http:// and https:// addresses can be converted")
    if not scheme:
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Only http:// and https:// addresses can be converted")
    return url


def html_document(code: str) -> str:
    """Wrap an HTML fragment in a full document; leave complete documents alone."""
    if re.search(r"<html[\s>]|<!doctype", code, re.I):
        return code
    return f"<!doctype html><html><head><meta charset='utf-8'></head><body>{code}</body></html>"


def title_hint(source: str) -> str:
    """A file name for the PDF: the page's file name or the site's host."""
    parsed = urlparse(source)
    if parsed.scheme in ("http", "https"):
        tail = Path(parsed.path).stem
        return f"{parsed.netloc}-{tail}" if tail else parsed.netloc
    return Path(source).stem or "document"
