"""AI image tools: super-resolution upscaling and background removal, run locally with
ONNX Runtime (DirectML on the GPU when available, otherwise the CPU).

Models are downloaded the first time a tool needs them, checked against a SHA-256
checksum, and kept in %LOCALAPPDATA%\\Toolbox\\models. Nothing is sent anywhere.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from ..filesystem import replace_with_retry
from ..progress import Progress
from . import imageio as iio

log = logging.getLogger(__name__)

MODELS = {
    "upscale": {
        "title": "Real-ESRGAN General x4v3",
        "license": "BSD-3-Clause",
        "source": "Qualcomm AI Hub",
        "url": "https://qaihub-public-assets.s3.us-west-2.amazonaws.com/qai-hub-models/models/real_esrgan_general_x4v3/releases/v0.67.0/real_esrgan_general_x4v3-onnx-float.zip",
        "sha256": "4f3619c89eb0727ff9170b977578d160fa4d696680a0cac4c7f870b52973033b",
        "size": 4_541_448,
        "zip_members": ["real_esrgan_general_x4v3.onnx", "real_esrgan_general_x4v3.data"],
        "model": "real_esrgan_general_x4v3.onnx",
    },
    "background": {
        "title": "ISNet (general use)",
        "license": "Apache-2.0",
        "source": "rembg project, GitHub",
        "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx",
        "sha256": "60920e99c45464f2ba57bee2ad08c919a52bbf852739e96947fbb4358c0d964a",
        "size": 178_648_008,
        "model": "isnet-general-use.onnx",
    },
}

_TILE = 128  # Real-ESRGAN export takes fixed 128x128 tiles and returns 512x512
_PAD = 10  # context around each tile so its edges match its neighbours
_SCALE = 4
_MAX_INPUT = {4: 4_200_000, 2: 16_000_000}  # pixels; keeps the output around 64 MP


class Models:
    """Download, verify and load models; one inference at a time per model."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self._lock = threading.Lock()
        self._sessions: dict[str, object] = {}
        self._run_locks: dict[str, threading.Lock] = {key: threading.Lock() for key in MODELS}
        self._download_locks: dict[str, threading.Lock] = {key: threading.Lock() for key in MODELS}

    def _dir(self, key: str) -> Path:
        return self.folder / key

    def installed(self, key: str) -> bool:
        return (self._dir(key) / ".ok").is_file()

    def status(self) -> dict:
        return {key: {"title": m["title"], "size": m["size"], "license": m["license"], "source": m["source"], "installed": self.installed(key)} for key, m in MODELS.items()}

    def ensure(self, key: str, progress: Progress | None = None) -> Path:
        meta = MODELS[key]
        with self._download_locks[key]:
            if not self.installed(key):
                self._download(key, meta, progress)
        return self._dir(key) / meta["model"]

    def _download(self, key: str, meta: dict, progress: Progress | None) -> None:
        target = self._dir(key)
        target.mkdir(parents=True, exist_ok=True)
        log.info("Downloading the %s model from %s", meta["title"], meta["url"])
        with tempfile.TemporaryDirectory(prefix="toolbox-model-") as tmp:
            file = Path(tmp) / "download"
            digest = hashlib.sha256()
            request = urllib.request.Request(meta["url"], headers={"User-Agent": "Toolbox-desktop"})
            with urllib.request.urlopen(request, timeout=60) as response, open(file, "wb") as out:
                total = int(response.headers.get("Content-Length") or meta["size"])
                done = 0
                while chunk := response.read(512 * 1024):
                    out.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, total, f"Downloading the AI model ({done / 1e6:.0f} of {total / 1e6:.0f} MB)…")
            if digest.hexdigest() != meta["sha256"]:
                raise RuntimeError("The downloaded model didn't match its checksum and was discarded. Try again later.")
            if "zip_members" in meta:
                with zipfile.ZipFile(file) as zf:
                    for wanted in meta["zip_members"]:
                        member = next((n for n in zf.namelist() if n.endswith("/" + wanted) or n == wanted), None)
                        if member is None:
                            raise RuntimeError(f"The model download didn't contain {wanted}")
                        staged = Path(tmp) / wanted
                        with zf.open(member) as src, open(staged, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        replace_with_retry(staged, target / wanted)
            else:
                replace_with_retry(file, target / meta["model"])
        (target / ".ok").write_text(meta["sha256"])
        log.info("The %s model is ready", meta["title"])

    def session(self, key: str, progress: Progress | None = None):
        path = self.ensure(key, progress)
        with self._lock:
            if key not in self._sessions:
                self._sessions[key] = _make_session(path)
            return self._sessions[key]

    def run(self, key: str, inputs: dict, progress: Progress | None = None):
        sess = self.session(key, progress)
        with self._run_locks[key]:
            return sess.run(None, inputs)

    def device(self, key: str) -> str:
        sess = self._sessions.get(key)
        if sess is None:
            return "not loaded"
        return "GPU (DirectML)" if "DmlExecutionProvider" in sess.get_providers() else "CPU"


def _make_session(path: Path):
    import onnxruntime as ort

    options = ort.SessionOptions()
    options.log_severity_level = 3
    available = ort.get_available_providers()
    if "DmlExecutionProvider" in available:
        options.enable_mem_pattern = False  # required by DirectML
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        try:
            return ort.InferenceSession(str(path), sess_options=options, providers=["DmlExecutionProvider", "CPUExecutionProvider"])
        except Exception as exc:  # noqa: BLE001 - no usable GPU: fall back to the CPU
            log.warning("DirectML unavailable (%s); using the CPU", exc)
    options = ort.SessionOptions()
    options.log_severity_level = 3
    return ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])


# --- upscale ----------------------------------------------------------------------------


def upscale_limit(scale: int) -> int:
    return _MAX_INPUT[scale]


def upscale(models: Models, path: str, output: str, scale: int = 4, options: dict | None = None, progress: Progress | None = None) -> dict:
    """Real-ESRGAN 4x super-resolution, tile by tile. 2x is the 4x result averaged down,
    which keeps the recovered detail. Transparency is scaled conventionally."""
    options = options or {}
    if scale not in (2, 4):
        raise ValueError("Scale must be 2 or 4")
    im = iio.open_image(path)
    w, h = im.size
    if w * h > _MAX_INPUT[scale]:
        mp = _MAX_INPUT[scale] / 1e6
        raise ValueError(f"This image is {w * h / 1e6:.1f} MP; {scale}x upscaling takes images up to {mp:.1f} MP. Resize or crop it first.")
    alpha = im.getchannel("A") if iio.has_alpha(im) else None
    rgb = np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0

    core = _TILE - 2 * _PAD
    rows, cols = -(-h // core), -(-w // core)
    mode = "reflect" if min(h, w) > _PAD else "edge"
    padded = np.pad(rgb, ((_PAD, rows * core - h + _PAD), (_PAD, cols * core - w + _PAD), (0, 0)), mode=mode)
    step = _SCALE if scale == 4 else 2
    out = np.zeros((rows * core * step, cols * core * step, 3), dtype=np.uint8)
    total = rows * cols
    models.session("upscale", progress)
    for r in range(rows):
        for c in range(cols):
            tile = padded[r * core : r * core + _TILE, c * core : c * core + _TILE]
            x = np.ascontiguousarray(tile.transpose(2, 0, 1)[None])
            y = models.run("upscale", {"image": x})[0][0].transpose(1, 2, 0)
            y = y[_PAD * _SCALE : (_PAD + core) * _SCALE, _PAD * _SCALE : (_PAD + core) * _SCALE]
            if scale == 2:  # exact 2x2 average: no seams between tiles
                y = y.reshape(core * 2, 2, core * 2, 2, 3).mean(axis=(1, 3))
            out[r * core * step : (r + 1) * core * step, c * core * step : (c + 1) * core * step] = np.clip(y * 255 + 0.5, 0, 255).astype(np.uint8)
            if progress:
                progress(r * cols + c + 1, total, f"Upscaling… {r * cols + c + 1} of {total} tiles")
    result = Image.fromarray(out[: h * step, : w * step])
    if alpha is not None:
        result = result.convert("RGBA")
        result.putalpha(alpha.resize(result.size, Image.Resampling.LANCZOS))
    if options.get("sharpen"):
        result = result.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    result.info.update({k: v for k, v in im.info.items() if k in ("icc_profile", "exif")})
    if "dpi" in im.info:
        result.info["dpi"] = tuple(d * scale for d in im.info["dpi"])
    fmt = iio.resolve_format(path, options.get("format", "keep"))
    saved = iio.save(result, output, fmt, quality=int(options.get("quality", 92)), keep_metadata=True)
    saved["device"] = models.device("upscale")
    return saved


# --- background removal -------------------------------------------------------------------

_MASKS: dict[tuple, Image.Image] = {}
_MASKS_LOCK = threading.Lock()


def subject_mask(models: Models, path: str, progress: Progress | None = None) -> Image.Image:
    """Soft mask (L, image size) of the foreground subject. Cached per file version."""
    file = iio.check_input(path)
    st = file.stat()
    key = (str(file), st.st_mtime_ns, st.st_size)
    with _MASKS_LOCK:
        if key in _MASKS:
            return _MASKS[key]
    im = iio.open_image(file)
    if progress:
        progress(0, 1, "Finding the subject…")
    small = np.asarray(im.convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS), dtype=np.float32)
    small = small / max(float(small.max()), 1e-6) - 0.5  # the normalisation ISNet was trained with
    x = np.ascontiguousarray(small.transpose(2, 0, 1)[None])
    pred = models.run("background", {"input_image": x}, progress)[0][0, 0]
    lo, hi = float(pred.min()), float(pred.max())
    pred = (pred - lo) / max(hi - lo, 1e-6)
    mask = Image.fromarray(np.clip(pred * 255, 0, 255).astype(np.uint8)).resize(im.size, Image.Resampling.LANCZOS)
    with _MASKS_LOCK:
        if len(_MASKS) > 6:
            _MASKS.pop(next(iter(_MASKS)))
        _MASKS[key] = mask
    if progress:
        progress(1, 1, "Done")
    return mask


def _refine(mask: Image.Image, options: dict) -> Image.Image:
    """Edge controls: `cleanup` (0-100) firms up a soft, hazy mask; `feather` (px) softens the edge."""
    cleanup = float(options.get("cleanup", 40)) / 100
    if cleanup > 0:
        lo = 0.5 * cleanup * 255
        hi = 255 - 0.5 * cleanup * 255
        span = max(hi - lo, 1)
        mask = mask.point(lambda v: 0 if v <= lo else 255 if v >= hi else int((v - lo) * 255 / span))
    feather = float(options.get("feather", 0))
    if feather > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    return mask


def cut_out(im: Image.Image, mask: Image.Image, options: dict) -> Image.Image:
    """Apply the mask. background: "transparent", "color" (with `color`), or "blur"."""
    mask = _refine(mask, options)
    if iio.has_alpha(im):
        mask = Image.composite(im.getchannel("A"), Image.new("L", im.size, 0), mask)
    background = options.get("background", "transparent")
    if background == "color":
        out = Image.new("RGB", im.size, options.get("color") or "#ffffff")
        out.paste(im.convert("RGB"), mask=mask)
    elif background == "blur":
        radius = max(4.0, max(im.size) / 60 * float(options.get("blur", 50)) / 50)
        out = im.convert("RGB").filter(ImageFilter.GaussianBlur(radius))
        out.paste(im.convert("RGB"), mask=mask)
    else:
        out = im.convert("RGBA")
        out.putalpha(mask)
    if options.get("trim") and background == "transparent":
        box = mask.point(lambda v: 255 if v > 8 else 0).getbbox()
        if box:
            margin = round(max(im.size) * 0.01)
            out = out.crop((max(0, box[0] - margin), max(0, box[1] - margin), min(im.width, box[2] + margin), min(im.height, box[3] + margin)))
    return out


def remove_background_preview(models: Models, path: str, options: dict, max_side: int = 1400, progress: Progress | None = None) -> dict:
    mask = subject_mask(models, path, progress)
    im = iio.open_image(path)
    if max(im.size) > max_side:
        k = max_side / max(im.size)
        size = (max(1, round(im.width * k)), max(1, round(im.height * k)))
        im, mask = im.resize(size, Image.Resampling.LANCZOS), mask.resize(size, Image.Resampling.LANCZOS)
        options = {**options, "feather": float(options.get("feather", 0)) * k}
    out = cut_out(im, mask, options)
    return {"data_url": iio.data_url(out, fmt="png" if out.mode == "RGBA" else "jpeg"), "width": out.width, "height": out.height, "device": models.device("background")}


def remove_background(models: Models, path: str, output: str, options: dict, progress: Progress | None = None) -> dict:
    mask = subject_mask(models, path, progress)
    im = iio.open_image(path)
    out = cut_out(im, mask, options)
    fmt = options.get("format", "png")
    if out.mode == "RGBA" and not iio.FORMATS[fmt][2]:
        fmt = "png"
    return iio.save(out, output, fmt, quality=int(options.get("quality", 92)), keep_metadata=True)

