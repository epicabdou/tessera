"""Markdown to a styled, self-contained HTML document (printed to PDF by WebView2)."""

from __future__ import annotations

import base64
import html
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

MAX_EMBED_BYTES = 15 * 1024 * 1024

_BASE_CSS = """
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;background:#fff;color:#1f2328}
article{max-width:860px;margin:0 auto;padding:24px}
@media print{article{max-width:none;padding:0}}
img{max-width:100%}
table{border-collapse:collapse;margin:1em 0;display:block;overflow:auto;width:max-content;max-width:100%}
th,td{border:1px solid #d0d7de;padding:6px 12px}
th{background:#f6f8fa;font-weight:600}
tr:nth-child(2n) td{background:#fafbfc}
pre{padding:12px 14px;border-radius:6px;overflow:auto;white-space:pre-wrap;word-break:break-word;break-inside:avoid}
code{font-family:"Cascadia Mono",Consolas,ui-monospace,monospace;font-size:.88em}
:not(pre)>code{padding:.15em .35em;border-radius:4px;background:rgba(175,184,193,.25)}
blockquote{margin:1em 0;padding:0 1em;color:#59636e;border-left:4px solid #d0d7de}
hr{border:0;border-top:1px solid #d0d7de;margin:1.6em 0}
h1,h2,h3,h4{break-after:avoid;line-height:1.25}
a{color:#0969da;text-decoration:none}
"""

THEMES = {
    "github": _BASE_CSS
    + """
body{font:15px/1.6 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
h1,h2{padding-bottom:.3em;border-bottom:1px solid #d8dee4}
h1{font-size:2em}h2{font-size:1.5em}h3{font-size:1.25em}
pre{background:#f6f8fa}
""",
    "document": _BASE_CSS
    + """
body{font:12pt/1.55 Cambria,Georgia,"Times New Roman",serif;color:#111}
h1,h2,h3,h4{font-family:Cambria,Georgia,serif;font-weight:700}
h1{font-size:2em;text-align:center;margin-bottom:.8em}
h2{font-size:1.45em;margin-top:1.6em}h3{font-size:1.2em}
p{text-align:justify;hyphens:auto}
pre{background:#f4f4f4;border:1px solid #e1e1e1}
blockquote{font-style:italic}
""",
    "compact": _BASE_CSS
    + """
body{font:12.5px/1.45 "Segoe UI",Arial,sans-serif}
h1{font-size:1.7em}h2{font-size:1.35em}h3{font-size:1.15em}
h1,h2,h3{margin:.9em 0 .4em}p,ul,ol{margin:.45em 0}
pre{background:#f6f8fa;padding:8px 10px}
th,td{padding:3px 8px}
""",
}

_FORMATTER = HtmlFormatter(nowrap=True)
_PYGMENTS_CSS = HtmlFormatter(style="default").get_style_defs(".hl")


def _highlight(code: str, lang: str, _attrs: str) -> str:
    try:
        lexer = get_lexer_by_name(lang.strip()) if lang.strip() else None
    except ClassNotFound:
        lexer = None
    if lexer is None:
        return ""  # markdown-it falls back to plain escaped code
    return f'<pre class="hl"><code>{highlight(code, lexer, _FORMATTER)}</code></pre>'


def _embed(src: str, base_dir: Path | None, root: Path | None = None) -> str:
    """Turn a local image path into a data: URL so it shows in previews and PDFs alike.

    With ``root``, only files inside that folder are embedded (a server rendering a user's
    Markdown must not read anyone else's files); others are left as they are."""
    parsed = urlparse(src)
    if parsed.scheme in ("http", "https", "data"):
        return src
    if parsed.scheme == "file":
        candidate = Path(unquote(parsed.path.lstrip("/")))
    elif parsed.scheme and len(parsed.scheme) > 1:
        return src  # some other scheme; leave it alone
    else:
        raw = Path(unquote(src))
        candidate = raw if raw.is_absolute() else (base_dir / raw if base_dir else raw)
    try:
        if root is not None and not candidate.resolve().is_relative_to(root.resolve()):
            return src
        if candidate.is_file() and candidate.stat().st_size <= MAX_EMBED_BYTES:
            mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            return f"data:{mime};base64," + base64.b64encode(candidate.read_bytes()).decode("ascii")
    except OSError:
        pass
    return src


def render_markdown(
    text: str, base_dir: str | None = None, theme: str = "github", title: str = "Document", root: str | None = None
) -> str:
    """``root``: embed only local images inside this folder (see _embed)."""
    if theme not in THEMES:
        raise ValueError(f"Unknown theme: {theme!r}")
    md = MarkdownIt("commonmark", {"html": True, "typographer": True, "highlight": _highlight}).enable(
        ["table", "strikethrough"]
    )
    base = Path(base_dir) if base_dir else None
    limit = Path(root) if root else None
    default_image = md.renderer.rules.get("image")

    def image(_renderer, tokens, idx, options, env):
        token = tokens[idx]
        token.attrSet("src", _embed(token.attrGet("src") or "", base, limit))
        return default_image(tokens, idx, options, env)

    md.add_render_rule("image", image)
    body = md.render(text)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        f"<style>{THEMES[theme]}{_PYGMENTS_CSS}</style>"
        f"</head><body><article class='markdown-body'>{body}</article></body></html>"
    )
