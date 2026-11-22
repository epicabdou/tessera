"""The surface exposed to JavaScript as ``window.pywebview.api``.

Every public method here becomes an async function in the React app. Keep this
layer thin: validate input, call into ``services``, return JSON-serialisable
data. Raised exceptions reject the JS promise with the exception message.

Attributes and methods starting with ``_`` are not exposed to JavaScript.
"""

from __future__ import annotations

import atexit
import functools
import inspect
import logging
import os
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import webview

from . import html_print
from .services import convert, filesystem, frompdf, latex, preview, progress, system_info
from .services.editing import edit as ed_edit
from .services.images import ai as img_ai
from .services.images import basic as img_basic
from .services.images import editor as img_editor
from .services.images import faces as img_faces
from .services.images import imageio as img_io
from .services.editing import forms as ed_forms
from .services.editing import ocr as ed_ocr
from .services.editing import watermark as ed_watermark
from .services.frompdf import convert as fp_convert
from .services.printing import impose as pr_impose
from .services.printing import printer as pr_printer
from .services.security import optimize as sec_optimize
from .services.security import protect as sec_protect
from .services.security import sign as sec_sign
from .services.convert import images as convert_images
from .services.convert import markdown as convert_markdown
from .services.convert import office as convert_office
from .services.convert import web as convert_web
from .services.pdf import common as pdf_common
from .services.pdf import numbering as pdf_numbering
from .services.pdf import ops as pdf_ops
from .services.pdf import render as pdf_render
from .services.history import History
from .services.settings import Settings

log = logging.getLogger(__name__)

PDF_TYPES = ("PDF files (*.pdf)", "All files (*.*)")


# --- activity history ------------------------------------------------------------------

Label = str | Callable[[dict[str, Any]], str]


def _records(label: Label) -> Callable:
    """Record each call of a tool method in the activity history: its input and output files,
    timing, and the error if it failed. ``label`` is the tool's name in the UI, or a function
    of the call's arguments for methods that serve several tools."""

    def wrap(func: Callable) -> Callable:
        signature = inspect.signature(func)

        @functools.wraps(func)
        def recorded(self: Api, *args: Any, **kwargs: Any) -> Any:
            try:
                bound = signature.bind(self, *args, **kwargs)
                bound.apply_defaults()
                values = {k: v for k, v in bound.arguments.items() if k != "self"}
            except TypeError:
                values = {}  # wrong arguments: let the call itself raise
            started, clock = time.time(), time.perf_counter()
            try:
                result = func(self, *args, **kwargs)
            except Exception as exc:
                self._record(func.__name__, label, values, started, clock, None, exc)
                raise
            self._record(func.__name__, label, values, started, clock, result, None)
            return result

        # pywebview names the JS function's parameters with getfullargspec, which doesn't
        # follow functools.wraps; an explicit signature keeps them.
        recorded.__signature__ = signature  # type: ignore[attr-defined]
        return recorded

    return wrap


def _history_inputs(values: dict[str, Any]) -> list[str]:
    """Source files of a call, from the argument names the tool methods use."""
    found: list[str] = []
    if isinstance(values.get("path"), str):
        found.append(values["path"])
    found += [p for p in values.get("paths") or [] if isinstance(p, str)]
    found += [i["path"] for i in values.get("items") or [] if isinstance(i, dict) and isinstance(i.get("path"), str)]
    sources = values.get("sources")
    if isinstance(sources, dict):
        found += [p for p in sources.values() if isinstance(p, str)]
    if values.get("kind") in ("url", "file") and isinstance(values.get("value"), str):
        found.append(values["value"])  # HTML to PDF / image: a web address or an .html file
    return list(dict.fromkeys(found))


def _history_outputs(result: Any) -> list[dict]:
    """Files a call wrote: one file ({path, ...}), several ({files: [...]}) or a list of them."""
    if isinstance(result, dict):
        items = result["files"] if isinstance(result.get("files"), list) else [result]
    elif isinstance(result, list):
        items = result
    else:
        items = []
    return [{"path": i["path"], "size": i.get("size")} for i in items if isinstance(i, dict) and isinstance(i.get("path"), str)]


_OFFICE_LABELS = {"word": "Word to PDF", "excel": "Excel to PDF", "powerpoint": "PowerPoint to PDF"}


def _pages(path: str, spec: str | None) -> list[int] | None:
    """"1-3, 5" -> [0, 1, 2, 4]; blank -> None (all pages)."""
    spec = (spec or "").strip()
    if not spec:
        return None
    return pdf_common.parse_selection(spec, len(pdf_common.open_reader(path).pages))


class _PreviewFiles:
    """Temporary PDFs behind live previews. Every call writes a new file, so a page that is
    still being rendered is never overwritten by the next preview. Once a preview is done,
    only the last few of each kind are kept; the rest go now, or when the app exits."""

    KEEP = 4

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq = 0
        self._done: dict[str, list[Path]] = {}
        self._leftovers: list[Path] = []  # couldn't be deleted yet (still open)
        atexit.register(self.clear)

    @contextmanager
    def new(self, kind: str) -> Iterator[Path]:
        with self._lock:
            self._seq += 1
            path = Path(tempfile.gettempdir()) / f"toolbox-{kind}-{os.getpid()}-{self._seq}.pdf"
        try:
            yield path
        except BaseException:
            self._remove(path)
            raise
        with self._lock:
            done = self._done.setdefault(kind, [])
            done.append(path)
            stale = done[: -self.KEEP]
            del done[: -self.KEEP]
        for old in stale:
            self._remove(old)

    def clear(self) -> None:
        with self._lock:
            files = [f for group in self._done.values() for f in group] + self._leftovers
            self._done.clear()
            self._leftovers = []
        for f in files:
            self._remove(f)

    def _remove(self, path: Path) -> None:
        if not _remove_quietly(path):
            with self._lock:
                self._leftovers.append(path)


def _remove_quietly(path: Path) -> bool:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return False  # still open by a page render
    return True


class Api:
    def __init__(self, settings: Settings, components: Any = None, history: History | None = None) -> None:
        from .paths import user_data_dir
        from .services.components import Components

        self._window: webview.Window | None = None
        self._settings = settings
        self._components = components or Components(user_data_dir())
        self._previews = _PreviewFiles()
        self._models = img_ai.Models(user_data_dir() / "models")
        # Opened on first use, so nothing is created until a tool runs or the history is viewed.
        self._history = history or History(user_data_dir() / "history.db")
        atexit.register(self._history.close)  # a clean close folds the WAL back into the database

    def _record(
        self, action: str, label: Label, values: dict[str, Any], started: float, clock: float, result: Any, exc: BaseException | None
    ) -> None:
        """Called by @_records. Never raises: a history problem must not fail the tool."""
        try:
            if not self._settings.preference("history_enabled"):
                return
            name = label(values) if callable(label) else label
            error = None if exc is None else (str(exc) or type(exc).__name__)[:1000]
            duration = round((time.perf_counter() - clock) * 1000)
            self._history.add(action, name, started, duration, _history_inputs(values), _history_outputs(result), error)
        except Exception:  # noqa: BLE001
            log.exception("Couldn't record %s in the history", action)

    def _bind_window(self, window: webview.Window) -> None:
        self._window = window

    def _dialog(self, kind: webview.FileDialog, **kwargs: Any) -> list[str]:
        if self._window is None:
            raise RuntimeError("Window not ready")
        result = self._window.create_file_dialog(kind, **kwargs)
        if not result:
            return []
        return [result] if isinstance(result, str) else list(result)

    # --- app ---------------------------------------------------------------

    def ping(self) -> str:
        return "pong"

    def get_system_info(self) -> dict:
        return system_info.get_system_info()

    # --- settings & pinned folders -----------------------------------------

    def get_settings(self) -> dict:
        return self._settings.snapshot()

    def set_preference(self, key: str, value: Any) -> None:
        self._settings.set_preference(key, value)

    # --- activity history ------------------------------------------------------

    def history_list(self, query: str = "", limit: int = 50, before_id: int | None = None) -> dict:
        """Newest first; pass the last entry's id as ``before_id`` for the next page."""
        return {**self._history.list(query, limit, before_id), "enabled": bool(self._settings.preference("history_enabled"))}

    def history_delete(self, ids: list[int]) -> None:
        self._history.delete(ids)

    def history_clear(self) -> None:
        self._history.clear()

    def pin_folder(self, path: str, index: int | None = None) -> list[dict]:
        """Pin a folder; if it's already pinned and ``index`` is given, move it there."""
        return self._settings.pin(path, index)

    def unpin_folder(self, path: str) -> list[dict]:
        return self._settings.unpin(path)

    # --- file browser ------------------------------------------------------

    def get_locations(self) -> list[dict]:
        return filesystem.quick_locations()

    def resolve_dir(self, path: str) -> str:
        return filesystem.resolve_dir(path)

    def list_dir(self, path: str, show_hidden: bool = False) -> dict:
        return filesystem.list_dir(path, show_hidden)

    def open_path(self, path: str) -> None:
        filesystem.open_path(path)

    def open_link(self, name: str) -> None:
        """Open one of the project's pages (website, source, license…) in the default browser.
        Only names from LINKS: the page can't make the app open arbitrary addresses."""
        import webbrowser

        from . import LINKS

        if name not in LINKS:
            raise ValueError(f"Unknown link: {name!r}")
        webbrowser.open(LINKS[name])

    def reveal_path(self, path: str) -> None:
        filesystem.reveal_path(path)

    def read_text_file(self, path: str) -> dict:
        return filesystem.read_text_file(path)

    def preview_file(self, path: str) -> dict:
        """Everything the Preview panel shows for a file or folder."""
        return preview.preview_file(path)

    def pick_file(self) -> str | None:
        """Open a native file dialog; returns the chosen path or None."""
        return next(iter(self._dialog(webview.FileDialog.OPEN)), None)

    def pick_folder(self, directory: str = "") -> str | None:
        return next(iter(self._dialog(webview.FileDialog.FOLDER, directory=directory or "")), None)

    def pick_pdfs(self, multiple: bool = False) -> list[str]:
        return self._dialog(webview.FileDialog.OPEN, allow_multiple=multiple, file_types=PDF_TYPES)

    def pick_files(self, label: str, extensions: list[str], multiple: bool = True) -> list[str]:
        """Open dialog filtered to `extensions`, e.g. ("Word documents", ["doc", "docx"])."""
        safe_label = "".join(c for c in label if c.isalnum() or c == " ").strip() or "Files"
        patterns = ";".join(f"*.{ext.strip('.').lower()}" for ext in extensions if ext.strip(".").isalnum())
        return self._dialog(
            webview.FileDialog.OPEN,
            allow_multiple=multiple,
            file_types=(f"{safe_label} ({patterns})", "All files (*.*)"),
        )

    def save_pdf_dialog(self, suggested_path: str) -> str | None:
        """Native Save dialog, starting at `suggested_path`; returns the chosen path (always .pdf)."""
        suggested = Path(suggested_path)
        chosen = next(
            iter(
                self._dialog(
                    webview.FileDialog.SAVE,
                    directory=str(suggested.parent),
                    save_filename=suggested.name,
                    file_types=PDF_TYPES,
                )
            ),
            None,
        )
        if chosen and not chosen.lower().endswith(".pdf"):
            chosen += ".pdf"
        return chosen

    # --- PDF: combine, split & page management ------------------------------

    def pdf_info(self, path: str) -> dict:
        return pdf_common.pdf_info(path)

    def pdf_thumbnails(self, path: str, indexes: list[int], width: int) -> list[str | None]:
        return pdf_render.render_pages(path, indexes, width)

    def pdf_detect_margins(self, path: str, index: int) -> dict:
        return pdf_render.detect_margins(path, index)

    def pdf_split_plan(self, page_count: int, mode: str, value: str) -> list[list[int]]:
        return pdf_common.split_plan(page_count, mode, value)

    def pdf_suggest_output(self, path: str, suffix: str) -> str:
        return pdf_common.suggest_output(path, suffix)

    @_records("Merge PDF")
    def pdf_merge(self, items: list[dict], output: str, bookmarks: bool = False) -> dict:
        return pdf_ops.merge(items, output, bookmarks)

    @_records("Split PDF")
    def pdf_split(self, path: str, output_dir: str, mode: str, value: str) -> dict:
        return pdf_ops.split(path, output_dir, mode, value)

    @_records("Organize PDF")
    def pdf_organize(self, output: str, sources: dict[str, str], pages: list[dict]) -> dict:
        return pdf_ops.organize(output, sources, pages)

    @_records("Rotate PDF")
    def pdf_rotate(self, path: str, output: str, rotations: list[int]) -> dict:
        return pdf_ops.rotate(path, output, rotations)

    @_records("Crop PDF")
    def pdf_crop(self, path: str, output: str, margins: dict, pages: list[int] | None = None) -> dict:
        return pdf_ops.crop(path, output, margins, pages)

    @_records("Page numbers")
    def pdf_number_pages(self, path: str, output: str, options: dict) -> dict:
        return pdf_numbering.add_page_numbers(path, output, options)

    # --- Conversion: To PDF ---------------------------------------------------

    def conversion_engines(self) -> dict:
        """Which of Microsoft Office / LibreOffice can convert Word, Excel and PowerPoint files."""
        return convert_office.engines()

    @_records(lambda a: _OFFICE_LABELS.get(a.get("kind"), "Office to PDF"))
    def convert_office(
        self, kind: str, path: str, output_dir: str | None = None, engine: str = "auto", options: dict | None = None
    ) -> dict:
        return convert_office.convert(kind, path, output_dir, engine, options or {})

    def suggest_pdf_path(self, source: str | None, hint: str = "document") -> str:
        return convert.suggest_pdf_path(source, hint)

    def image_thumbnails(self, paths: list[str], size: int = 160) -> list[dict]:
        results = []
        for path in paths:
            try:
                results.append(convert_images.thumbnail(path, size))
            except Exception as exc:  # noqa: BLE001 - one bad file shouldn't hide the rest
                results.append({"path": path, "name": Path(path).name, "error": str(exc)})
        return results

    @_records("JPG to PDF")
    def images_to_pdf(self, items: list[dict], output: str, options: dict) -> dict:
        return convert_images.images_to_pdf(items, output, options)

    @_records("JPG to PDF")
    def images_to_pdfs(self, items: list[dict], output_dir: str | None, options: dict) -> list[dict]:
        return convert_images.images_to_pdfs(items, output_dir, options)

    def markdown_html(self, text: str, base_dir: str | None, theme: str, title: str) -> str:
        """Rendered Markdown, for the live preview."""
        return convert_markdown.render_markdown(text, base_dir, theme, title)

    @_records("Markdown to PDF")
    def markdown_to_pdf(self, text: str, base_dir: str | None, theme: str, title: str, output: str, options: dict) -> dict:
        document = convert_markdown.render_markdown(text, base_dir, theme, title)
        return self._print_html_document(document, output, options, title)

    # --- Images: format & size -------------------------------------------------------

    def image_info(self, path: str) -> dict:
        return img_io.info(path)

    def image_preview(self, path: str, max_side: int = 1600) -> dict:
        return img_io.preview(path, int(max_side))

    def image_formats(self) -> dict:
        return {
            "inputs": sorted(img_io.INPUT_EXTS),
            "outputs": {key: {"ext": ext, "alpha": alpha, "lossy": lossy} for key, (_pil, ext, alpha, lossy) in img_io.FORMATS.items()},
            "heif": img_io.HEIF,
        }

    def image_suggest(self, path: str, suffix: str, fmt: str = "keep") -> str:
        return str(img_io.output_path(path, None, suffix, img_io.resolve_format(path, fmt)))

    @_records("Compress Image")
    def image_compress(self, paths: list[str], folder: str | None, options: dict, job_id: str = "") -> list[dict]:
        return img_basic.compress(paths, folder, options, progress.reporter(job_id))

    def image_compress_estimate(self, path: str, options: dict) -> dict:
        return img_basic.estimate(path, options)

    @_records("Resize Image")
    def image_resize(self, paths: list[str], folder: str | None, options: dict, job_id: str = "") -> list[dict]:
        return img_basic.resize(paths, folder, options, progress.reporter(job_id))

    @_records(lambda a: "Convert to JPG" if (a.get("options") or {}).get("format") == "jpg" else "Convert from JPG")
    def image_convert(self, paths: list[str], folder: str | None, options: dict, job_id: str = "") -> list[dict]:
        return img_basic.convert(paths, folder, options, progress.reporter(job_id))

    # --- Images: framing, layout & generation -----------------------------------------

    @_records("Crop Image")
    def image_crop(self, path: str, output: str, rect: dict, options: dict) -> dict:
        return img_basic.crop(path, output, rect, options)

    @_records("Rotate Image")
    def image_rotate(self, items: list[dict], folder: str | None, options: dict, job_id: str = "") -> list[dict]:
        return img_basic.rotate(items, folder, options, progress.reporter(job_id))

    @_records("HTML to Image")
    def html_to_image(self, kind: str, value: str, output: str, options: dict) -> dict:
        """kind: "url", "file" (a local .html file) or "code" (HTML source)."""
        if kind == "url":
            return html_print.capture_image(convert_web.normalize_url(value), output, options)
        if kind == "file":
            source = Path(value)
            if not source.is_file() or source.suffix.lower() not in (".html", ".htm", ".xhtml", ".svg"):
                raise ValueError("Choose an .html file")
            return html_print.capture_image(source.resolve().as_uri(), output, options)
        if kind == "code":
            if not value.strip():
                raise ValueError("Enter some HTML")
            with tempfile.TemporaryDirectory(prefix="toolbox-html-") as tmp:
                page = Path(tmp) / "document.html"
                page.write_text(convert_web.html_document(value), encoding="utf-8")
                return html_print.capture_image(page.as_uri(), output, options)
        raise ValueError(f"Unknown HTML source: {kind!r}")

    # --- Images: AI -------------------------------------------------------------------

    def ai_models(self) -> dict:
        return self._models.status()

    @_records("Upscale Image")
    def ai_upscale(self, path: str, output: str, scale: int, options: dict, job_id: str = "") -> dict:
        return img_ai.upscale(self._models, path, output, int(scale), options, progress.reporter(job_id))

    def ai_upscale_limit(self, scale: int) -> int:
        return img_ai.upscale_limit(int(scale))

    def ai_remove_bg_preview(self, path: str, options: dict, job_id: str = "") -> dict:
        return img_ai.remove_background_preview(self._models, path, options, progress=progress.reporter(job_id))

    @_records("Remove background")
    def ai_remove_bg(self, path: str, output: str, options: dict, job_id: str = "") -> dict:
        return img_ai.remove_background(self._models, path, output, options, progress.reporter(job_id))

    def faces_detect(self, path: str) -> list[dict]:
        return img_faces.detect(path)

    def faces_preview(self, path: str, faces: list[dict], options: dict) -> dict:
        return img_faces.preview(path, faces, options)

    @_records("Blur face")
    def faces_blur(self, path: str, output: str, faces: list[dict], options: dict) -> dict:
        return img_faces.blur_faces(path, output, faces, options)

    # --- Images: editing & branding ----------------------------------------------------

    def photo_preview(self, path: str, edits: dict, max_side: int = 1400) -> dict:
        return img_editor.editor_preview(path, edits, int(max_side))

    @_records("Photo editor")
    def photo_save(self, path: str, output: str, edits: dict, options: dict) -> dict:
        return img_editor.editor_save(path, output, edits, options)

    def image_watermark_preview(self, path: str, options: dict, max_side: int = 1400) -> dict:
        return img_editor.watermark_preview(path, options, int(max_side))

    @_records("Watermark Image")
    def image_watermark(self, paths: list[str], folder: str | None, options: dict, job_id: str = "") -> list[dict]:
        return img_editor.watermark(paths, folder, options, progress.reporter(job_id))

    @_records("HTML to PDF")
    def html_to_pdf(self, kind: str, value: str, output: str, options: dict) -> dict:
        """kind: "url" (a web address), "file" (a local .html file) or "code" (HTML source)."""
        if kind == "url":
            return html_print.print_to_pdf(convert_web.normalize_url(value), output, options)
        if kind == "file":
            source = Path(value)
            if not source.is_file() or source.suffix.lower() not in (".html", ".htm", ".xhtml", ".svg"):
                raise ValueError("Choose an .html file")
            return html_print.print_to_pdf(source.resolve().as_uri(), output, options)
        if kind == "code":
            if not value.strip():
                raise ValueError("Enter some HTML")
            return self._print_html_document(convert_web.html_document(value), output, options, Path(output).stem)
        raise ValueError(f"Unknown HTML source: {kind!r}")

    # --- shared: dialogs, progress, components ----------------------------------

    def save_file_dialog(self, suggested_path: str, label: str, extensions: list[str]) -> str | None:
        """Save dialog for any file type; the first extension is added if the name has none."""
        suggested = Path(suggested_path)
        safe_label = "".join(c for c in label if c.isalnum() or c == " ").strip() or "Files"
        patterns = ";".join(f"*.{e.strip('.').lower()}" for e in extensions)
        chosen = next(
            iter(
                self._dialog(
                    webview.FileDialog.SAVE,
                    directory=str(suggested.parent),
                    save_filename=suggested.name,
                    file_types=(f"{safe_label} ({patterns})", "All files (*.*)"),
                )
            ),
            None,
        )
        if chosen and extensions and not any(chosen.lower().endswith(f".{e.strip('.').lower()}") for e in extensions):
            chosen += f".{extensions[0].strip('.')}"
        return chosen

    def job_progress(self, job_id: str) -> dict | None:
        return progress.get(job_id)

    def components_status(self) -> dict:
        return self._components.status()

    def components_retry(self) -> None:
        threading.Thread(target=self._components.ensure_latex, daemon=True).start()

    # --- Conversion: From PDF --------------------------------------------------------

    def frompdf_suggest(self, path: str, ext: str) -> str:
        return frompdf.suggest_path(path, ext)

    @_records("PDF to Word")
    def pdf_to_word(self, path: str, output: str, engine: str = "auto", fmt: str = "docx", job_id: str = "") -> dict:
        return fp_convert.to_word(path, output, engine, fmt, progress.reporter(job_id))

    @_records("PDF to PowerPoint")
    def pdf_to_powerpoint(self, path: str, output: str, dpi: int = 150, notes: bool = True, job_id: str = "") -> dict:
        return fp_convert.to_powerpoint(path, output, int(dpi), bool(notes), progress.reporter(job_id))

    @_records("PDF to Excel")
    def pdf_to_excel(self, path: str, output: str, pages: str = "", detection: str = "auto", job_id: str = "") -> dict:
        return fp_convert.to_excel(path, output, _pages(path, pages), detection, progress.reporter(job_id))

    @_records(lambda a: f"PDF to {str(a.get('fmt') or 'jpg').upper()}")
    def pdf_to_images(
        self, path: str, output_dir: str | None, pages: str = "", fmt: str = "jpg", dpi: int = 150, quality: int = 90, mode: str = "pages", job_id: str = ""
    ) -> dict:
        return fp_convert.to_images(path, output_dir, _pages(path, pages), fmt, int(dpi), int(quality), mode, progress.reporter(job_id))

    @_records("PDF to Markdown")
    def pdf_to_markdown(self, path: str, output: str, pages: str = "", page_breaks: bool = False, job_id: str = "") -> dict:
        return fp_convert.to_markdown(path, output, _pages(path, pages), bool(page_breaks), progress.reporter(job_id))

    def pdf_markdown_preview(self, path: str, pages: str = "") -> str:
        indexes = _pages(path, pages)
        return fp_convert.markdown_preview(path, indexes[:5] if indexes else list(range(min(5, len(pdf_common.open_reader(path).pages)))))

    # --- Editing, Forms & Text Recognition ---------------------------------------------

    def pdf_text_lines(self, path: str, page: int) -> list[dict]:
        return ed_edit.text_lines(path, int(page))

    @_records("Edit PDF")
    def pdf_apply_edits(self, path: str, output: str, objects: list[dict]) -> dict:
        return ed_edit.apply_edits(path, output, objects)

    def ocr_engines(self) -> dict:
        return ed_ocr.engines()

    @_records("OCR PDF")
    def ocr_pdf(
        self, path: str, output: str, engine: str = "auto", language: str = "", dpi: int = 300, skip_text: bool = True, pages: str = "", job_id: str = ""
    ) -> dict:
        return ed_ocr.ocr_pdf(path, output, engine, language, int(dpi), bool(skip_text), _pages(path, pages), progress.reporter(job_id))

    def form_fields(self, path: str) -> list[dict]:
        return ed_forms.list_fields(path)

    @_records("Fill PDF form")
    def form_fill(self, path: str, output: str, values: dict, flatten: bool = False) -> dict:
        return ed_forms.fill(path, output, values, bool(flatten))

    @_records("Add PDF form fields")
    def form_add_fields(self, path: str, output: str, specs: list[dict]) -> dict:
        return ed_forms.add_fields(path, output, specs)

    @_records("Watermark PDF")
    def pdf_watermark(self, path: str, output: str, options: dict) -> dict:
        return ed_watermark.watermark(path, output, options)

    def pdf_watermark_preview(self, path: str, options: dict, page: int) -> dict:
        """The real watermark on just one page (fast), for an exact live preview."""
        from pypdf import PdfWriter

        selected = _pages(path, options.get("pages"))
        with self._previews.new("watermark-preview") as target, tempfile.TemporaryDirectory(prefix="toolbox-wm-") as tmp:
            single = Path(tmp) / "page.pdf"
            writer = PdfWriter()
            writer.append(path, pages=[int(page)])
            writer.write(single)
            if selected is None or int(page) in selected:
                ed_watermark.watermark(str(single), str(target), {**options, "pages": ""})
            else:
                filesystem.replace_with_retry(single, target)
            return pdf_common.pdf_info(target)

    # --- Security, Signatures & Optimization ---------------------------------------------

    def pdf_security_info(self, path: str) -> dict:
        return sec_protect.security_info(path)

    @_records("Protect PDF")
    def pdf_protect(self, path: str, output: str, user_password: str, owner_password: str, permissions: dict, algorithm: str = "AES-256") -> dict:
        return sec_protect.protect(path, output, user_password, owner_password, permissions, algorithm)

    @_records("Unlock PDF")
    def pdf_unlock(self, path: str, output: str, password: str) -> dict:
        return sec_protect.unlock(path, output, password)

    def cert_suggest_path(self, name: str) -> str:
        return sec_sign.suggest_certificate_path(name)

    @_records("Create certificate")
    def cert_create(self, output: str, password: str, name: str, email: str = "", organization: str = "", country: str = "") -> dict:
        return sec_sign.create_certificate(output, password, name, email, organization, country)

    def cert_info(self, path: str, password: str) -> dict:
        return sec_sign.certificate_info(path, password)

    @_records("Sign PDF")
    def pdf_sign(
        self, path: str, output: str, certificate: str, password: str, reason: str = "", location: str = "", contact: str = "", visible: dict | None = None
    ) -> dict:
        return sec_sign.sign(path, output, certificate, password, reason, location, contact, visible)

    def pdf_verify_signatures(self, path: str) -> list[dict]:
        return sec_sign.verify(path)

    @_records("Compress PDF")
    def pdf_compress(self, path: str, output: str, level: str = "medium", strip_metadata: bool = False, job_id: str = "") -> dict:
        return sec_optimize.compress(path, output, level, bool(strip_metadata), progress.reporter(job_id))

    def pdf_analyze(self, path: str) -> dict:
        return sec_optimize.analyze(path)

    @_records("Repair PDF")
    def pdf_repair(self, path: str, output: str) -> dict:
        return sec_optimize.repair(path, output)

    # --- Printing & Output --------------------------------------------------------------

    def printers(self) -> list[dict]:
        return pr_printer.printers()

    def print_preview(self, path: str, options: dict) -> dict:
        """Lay the sheets out into a temporary PDF the UI can preview."""
        with self._previews.new("print-preview") as target:
            result = pr_impose.impose(path, str(target), options)
            info = pdf_common.pdf_info(target)
        return {**info, "sheets": result["sheets"], "source_pages": result["source_pages"]}

    @_records("Print")
    def print_pdf(self, path: str, printer: str, options: dict, job_id: str = "") -> dict:
        return pr_printer.print_pdf(path, printer, options, progress.reporter(job_id))

    @_records("Print to PDF")
    def print_save_pdf(self, path: str, output: str, options: dict) -> dict:
        return pr_impose.impose(path, output, options)

    # --- LaTeX ----------------------------------------------------------------------------

    def latex_status(self) -> dict:
        return self._components.status()["latex"]

    def latex_templates(self) -> dict:
        return latex.TEMPLATES

    def latex_new_document(self, template: str = "article") -> dict:
        from .paths import user_data_dir

        if template not in latex.TEMPLATES:
            raise ValueError(f"Unknown template: {template!r}")
        base = user_data_dir() / "latex"
        n = 1
        while (base / f"untitled-{n}").exists():
            n += 1
        folder = base / f"untitled-{n}"
        folder.mkdir(parents=True)
        path = folder / "main.tex"
        path.write_text(latex.TEMPLATES[template], encoding="utf-8")
        return {"path": str(path), "text": latex.TEMPLATES[template], "untitled": True}

    def latex_read(self, path: str) -> dict:
        source = Path(path)
        if source.suffix.lower() != ".tex":
            raise ValueError("Choose a .tex file")
        return {"path": str(source), "text": source.read_text(encoding="utf-8", errors="replace"), "untitled": False}

    def latex_save(self, path: str, text: str) -> dict:
        target = Path(path)
        if target.suffix.lower() != ".tex":
            raise ValueError("LaTeX files must end in .tex")
        tmp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        tmp.write_text(text, encoding="utf-8")
        filesystem.replace_with_retry(tmp, target)
        return {"path": str(target), "saved": True}

    def latex_compile(self, path: str, engine: str = "auto") -> dict:
        return latex.compile_tex(path, engine, self._components.tectonic_path)

    def _print_html_document(self, document: str, output: str, options: dict, title: str) -> dict:
        with tempfile.TemporaryDirectory(prefix="toolbox-html-") as tmp:
            page = Path(tmp) / "document.html"
            page.write_text(document, encoding="utf-8")
            # Header shows the document's title; the footer mustn't show the temp file's path.
            return html_print.print_to_pdf(page.as_uri(), output, options, header_title=title, footer_uri=" ")
