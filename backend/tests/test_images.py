"""Image tools: formats, compress, resize, convert, crop, rotate, editor, watermark, faces, AI."""

import functools
import hashlib
import http.server
import io
import os
import sys
import threading
import zipfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from toolbox.services.images import ai, basic, editor, faces
from toolbox.services.images import imageio as iio


def photo(path: Path, size=(640, 480), alpha=False, orientation=None) -> Path:
    """A busy test picture (gradient + noise + shapes) so compression has work to do."""
    w, h = size
    rng = np.random.default_rng(7)
    x = np.linspace(0, 255, w)[None, :, None]
    y = np.linspace(0, 255, h)[:, None, None]
    arr = np.concatenate([np.broadcast_to(x, (h, w, 1)), np.broadcast_to(y, (h, w, 1)), np.full((h, w, 1), 128.0)], axis=2)
    arr = np.clip(arr + rng.normal(0, 18, arr.shape), 0, 255).astype(np.uint8)
    im = Image.fromarray(arr, "RGB")
    d = ImageDraw.Draw(im)
    d.ellipse((w * 0.3, h * 0.25, w * 0.7, h * 0.75), fill="#e0442b")
    if alpha:
        im = im.convert("RGBA")
        im.putalpha(Image.new("L", im.size, 255).point(lambda v: v))
        ImageDraw.Draw(im).rectangle((0, 0, 40, 40), fill=(0, 0, 0, 0))
    kwargs = {}
    if orientation:
        exif = im.getexif()
        exif[0x0112] = orientation
        kwargs["exif"] = exif
    im.save(path, **kwargs)
    return path


# --- io ---------------------------------------------------------------------------------


def test_exif_orientation_is_applied(tmp_path):
    src = photo(tmp_path / "turned.jpg", (300, 200), orientation=6)
    info = iio.info(src)
    assert (info["width"], info["height"]) == (200, 300)
    assert iio.open_image(src).size == (200, 300)


@pytest.mark.parametrize("fmt", ["jpg", "png", "webp", "avif", "gif", "bmp", "tiff"])
def test_every_output_format_round_trips(tmp_path, fmt):
    src = photo(tmp_path / "src.png", (120, 80), alpha=True)
    saved = iio.save(iio.open_image(src), tmp_path / f"out.{iio.FORMATS[fmt][1]}", fmt)
    with Image.open(saved["path"]) as im:
        assert im.size == (120, 80)
    if not iio.FORMATS[fmt][2]:  # no alpha: transparent corner became the background (white)
        assert Image.open(saved["path"]).convert("RGB").getpixel((5, 5)) == (255, 255, 255)


def test_heic_is_readable(tmp_path):
    if not iio.HEIF:
        pytest.skip("pillow-heif not installed")
    src = photo(tmp_path / "src.png", (160, 120))
    try:
        Image.open(src).save(tmp_path / "phone.heic")
    except Exception as exc:  # noqa: BLE001 - no HEIF encoder in this build
        pytest.skip(f"can't write HEIC here: {exc}")
    assert iio.info(tmp_path / "phone.heic")["width"] == 160
    out = basic.convert([str(tmp_path / "phone.heic")], None, {"format": "jpg"})
    assert out[0]["name"] == "phone.jpg"


# --- compress / resize / convert ---------------------------------------------------------


def test_compress_shrinks_and_reports_sizes(tmp_path):
    src = photo(tmp_path / "big.png", (900, 700))
    est = basic.estimate(str(src), {"format": "jpg", "quality": 70})
    [res] = basic.compress([str(src)], None, {"format": "jpg", "quality": 70})
    assert res["name"] == "big_compressed.jpg"
    assert res["after"] < res["before"] / 3
    assert abs(res["after"] - est["after"]) < 2048


def test_compress_never_grows_a_file(tmp_path):
    src = tmp_path / "tiny.jpg"
    photo(tmp_path / "t.png", (64, 64))
    Image.open(tmp_path / "t.png").save(src, quality=20)
    [res] = basic.compress([str(src)], None, {"format": "keep", "quality": 95})
    assert res["kept_original"] and res["after"] == res["before"]


def test_png_palette_compression(tmp_path):
    src = photo(tmp_path / "shot.png", (600, 400))
    [plain] = basic.compress([str(src)], None, {"format": "png", "png_colors": 0, "suffix": "_a"})
    [lossy] = basic.compress([str(src)], None, {"format": "png", "png_colors": 64, "suffix": "_b"})
    assert lossy["after"] < plain["after"] * 0.7
    assert Image.open(lossy["path"]).mode == "P"


@pytest.mark.parametrize(
    "options, size",
    [
        ({"mode": "percent", "percent": 50}, (320, 240)),
        ({"mode": "longest", "longest": 200}, (200, 150)),
        ({"mode": "pixels", "width": 100}, (100, 75)),
        ({"mode": "pixels", "width": 200, "height": 200, "fit": "contain"}, (200, 150)),
        ({"mode": "pixels", "width": 200, "height": 200, "fit": "cover"}, (200, 200)),
        ({"mode": "pixels", "width": 300, "height": 100, "keep_aspect": False}, (300, 100)),
        ({"mode": "percent", "percent": 300, "no_enlarge": True}, (640, 480)),
    ],
)
def test_resize_modes(tmp_path, options, size):
    src = photo(tmp_path / "p.jpg", (640, 480))
    [res] = basic.resize([str(src)], str(tmp_path / "out"), options)
    assert (res["width"], res["height"]) == size


def test_convert_to_jpg_flattens_transparency(tmp_path):
    src = photo(tmp_path / "logo.png", (100, 100), alpha=True)
    [res] = basic.convert([str(src)], None, {"format": "jpg", "background": "#00ff00"})
    assert res["name"] == "logo.jpg"
    r, g, b = Image.open(res["path"]).getpixel((5, 5))
    assert g > 200 and r < 60 and b < 60


def test_convert_all_frames(tmp_path):
    frames = [Image.new("RGB", (40, 30), c) for c in ("red", "green", "blue")]
    frames[0].save(tmp_path / "anim.gif", save_all=True, append_images=frames[1:])
    out = basic.convert([str(tmp_path / "anim.gif")], None, {"format": "png", "all_frames": True})
    assert [f["name"] for f in out] == ["anim_1.png", "anim_2.png", "anim_3.png"]


# --- crop / rotate ------------------------------------------------------------------------


def test_crop_rect_and_circle(tmp_path):
    src = photo(tmp_path / "p.jpg", (400, 300))
    res = basic.crop(str(src), str(tmp_path / "c.jpg"), {"x": 50, "y": 40, "w": 200, "h": 100})
    assert (res["width"], res["height"]) == (200, 100)
    res = basic.crop(str(src), str(tmp_path / "round.jpg"), {"x": 100, "y": 50, "w": 200, "h": 200}, {"shape": "circle"})
    assert res["name"] == "round.jpg.png" or res["path"].endswith(".png")
    im = Image.open(res["path"])
    assert im.mode == "RGBA" and im.getpixel((2, 2))[3] == 0 and im.getpixel((100, 100))[3] == 255


def test_rotate_and_flip(tmp_path):
    im = Image.new("RGB", (20, 10), "white")
    im.putpixel((0, 0), (255, 0, 0))  # red top-left
    im.save(tmp_path / "dot.png")
    [cw] = basic.rotate([{"path": str(tmp_path / "dot.png"), "turns": 1}], None, {"suffix": "_cw"})
    out = Image.open(cw["path"]).convert("RGB")
    assert out.size == (10, 20) and out.getpixel((9, 0)) == (255, 0, 0)  # now top-right
    [flip] = basic.rotate([{"path": str(tmp_path / "dot.png"), "flip_h": True}], None, {"suffix": "_fh"})
    assert Image.open(flip["path"]).convert("RGB").getpixel((19, 0)) == (255, 0, 0)


# --- editor & watermark -------------------------------------------------------------------


def test_adjustments_and_filters(tmp_path):
    src = photo(tmp_path / "p.jpg", (200, 150))
    base = np.asarray(editor.render(str(src), {}), dtype=float)
    brighter = np.asarray(editor.render(str(src), {"adjust": {"exposure": 60}}), dtype=float)
    assert brighter.mean() > base.mean() + 10
    mono = np.asarray(editor.render(str(src), {"adjust": {"filter": "mono"}}), dtype=float)
    assert np.abs(mono[..., 0] - mono[..., 1]).max() < 3
    for name in editor.FILTERS:
        editor.render(str(src), {"adjust": {"filter": name, "vignette": -30, "hue": 40, "sharpness": -20}})


def test_layers_are_drawn_where_placed(tmp_path):
    src = tmp_path / "white.png"
    Image.new("RGB", (300, 200), "white").save(src)
    layers = [
        {"type": "rect", "x": 10, "y": 10, "w": 50, "h": 40, "fill": "#0000ff"},
        {"type": "text", "x": 100, "y": 20, "w": 150, "h": 40, "text": "Hi", "size": 40, "color": "#ff0000", "bold": True},
        {"type": "arrow", "x": 20, "y": 120, "w": 100, "h": 40, "points": [[0, 0], [1, 1]], "stroke": "#00aa00", "width": 6},
        {"type": "draw", "x": 200, "y": 120, "w": 80, "h": 60, "points": [[0, 0], [0.5, 1], [1, 0]], "stroke": "#000000", "width": 5},
    ]
    res = editor.editor_save(str(src), str(tmp_path / "out.png"), {"layers": layers}, {})
    out = Image.open(res["path"]).convert("RGB")
    assert out.getpixel((30, 30)) == (0, 0, 255)
    red = np.asarray(out.crop((100, 20, 250, 60)))
    assert ((red[..., 0] > 200) & (red[..., 1] < 60)).sum() > 50
    assert out.getpixel((70, 140))[1] > 120 and out.getpixel((70, 140))[0] < 80  # on the arrow (20,120)->(120,160)
    assert out.getpixel((240, 179)) != (255, 255, 255) or out.getpixel((240, 178)) != (255, 255, 255)


def test_watermark_position_and_tile(tmp_path):
    src = tmp_path / "white.png"
    Image.new("RGB", (400, 300), "white").save(src)
    one = editor.watermark_image(iio.open_image(src), {"text": "MARK", "color": "#000000", "opacity": 1, "position": "bottom-right", "size": 10})
    arr = np.asarray(one.convert("L"))
    assert arr[200:, 250:].min() < 100 and arr[:100, :150].min() > 250
    tiled = editor.watermark_image(iio.open_image(src), {"text": "MARK", "color": "#000000", "opacity": 1, "position": "tile", "size": 8, "rotation": 30})
    t = np.asarray(tiled.convert("L"))
    assert t[:150, :200].min() < 100 and t[150:, 200:].min() < 100
    res = editor.watermark([str(src)], None, {"text": "©", "opacity": 0.5})
    assert res[0]["name"] == "white_watermarked.png"


# --- faces --------------------------------------------------------------------------------


def test_obscure_changes_only_the_boxes(tmp_path):
    src = photo(tmp_path / "p.png", (300, 200))
    box = {"x": 10, "y": 110, "w": 70, "h": 70}  # a noisy area, away from the red disc
    before = np.asarray(iio.open_image(src), dtype=float)
    for style in ("blur", "pixelate", "solid"):
        after = np.asarray(faces.obscure(iio.open_image(src), [box], {"style": style, "padding": 0, "shape": "rect"}), dtype=float)
        assert np.abs(after[120:170, 20:70] - before[120:170, 20:70]).mean() > 5
        assert np.abs(after[:40, 200:] - before[:40, 200:]).max() == 0
    with pytest.raises(ValueError):
        faces.blur_faces(str(src), str(tmp_path / "x.png"), [], {})


@pytest.mark.skipif(sys.platform != "win32", reason="Windows face detector")
def test_detector_runs(tmp_path):
    src = photo(tmp_path / "p.jpg", (3000, 2000))
    assert faces.detect(str(src)) == []  # no faces in a synthetic picture; just proves it runs


# --- AI -----------------------------------------------------------------------------------


class FakeModels(ai.Models):
    """Stand-in model outputs, to test everything around the network exactly."""

    def __init__(self):
        super().__init__(Path("unused"))

    def session(self, key, progress=None):
        return None

    def run(self, key, inputs, progress=None):
        if key == "upscale":
            x = inputs["image"]
            return [x.repeat(4, axis=2).repeat(4, axis=3)]  # nearest-neighbour 4x
        x = inputs["input_image"][0]
        mask = (x[0] > 0.2).astype(np.float32)  # "subject" = the red parts
        return [mask[None, None] * 5 - 1]


def test_upscale_tiling_is_seamless(tmp_path):
    src = photo(tmp_path / "p.png", (301, 223))  # not a multiple of the tile size
    res = ai.upscale(FakeModels(), str(src), str(tmp_path / "x4.png"), 4)
    expected = np.asarray(Image.open(src).convert("RGB").resize((1204, 892), Image.Resampling.NEAREST))
    got = np.asarray(Image.open(res["path"]).convert("RGB"))
    assert got.shape == expected.shape
    assert np.abs(got.astype(int) - expected.astype(int)).max() <= 1
    res2 = ai.upscale(FakeModels(), str(src), str(tmp_path / "x2.png"), 2)
    assert (res2["width"], res2["height"]) == (602, 446)


def test_upscale_refuses_huge_images(tmp_path):
    src = tmp_path / "huge.png"
    Image.new("RGB", (2500, 2000)).save(src)
    with pytest.raises(ValueError, match="MP"):
        ai.upscale(FakeModels(), str(src), str(tmp_path / "x.png"), 4)


def test_background_removal_options(tmp_path):
    src = photo(tmp_path / "p.png", (320, 240))
    models = FakeModels()
    cut = ai.remove_background(models, str(src), str(tmp_path / "cut.png"), {"background": "transparent"})
    im = Image.open(cut["path"])
    assert im.mode == "RGBA" and im.getpixel((160, 120))[3] == 255 and im.getpixel((5, 230))[3] == 0
    trimmed = ai.remove_background(models, str(src), str(tmp_path / "trim.png"), {"background": "transparent", "trim": True})
    assert trimmed["width"] < 320
    white = ai.remove_background(models, str(src), str(tmp_path / "white.jpg"), {"background": "color", "color": "#ffffff", "format": "jpg"})
    assert Image.open(white["path"]).convert("RGB").getpixel((5, 230)) == (255, 255, 255)
    prev = ai.remove_background_preview(models, str(src), {"background": "blur"}, max_side=100)
    assert prev["data_url"].startswith("data:image/") and prev["width"] == 100


def _serve(folder: Path):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(folder)))
    server.RequestHandlerClass.log_message = lambda *a: None
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_model_download_verifies_and_extracts(tmp_path, monkeypatch):
    web = tmp_path / "web"
    web.mkdir()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("pkg/sub/net.onnx", b"onnx-bytes")
        zf.writestr("pkg/sub/net.data", b"weights")
    (web / "model.zip").write_bytes(buf.getvalue())
    server = _serve(web)
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/model.zip"
        good = {"title": "T", "license": "MIT", "source": "test", "url": url, "size": len(buf.getvalue()), "sha256": hashlib.sha256(buf.getvalue()).hexdigest(), "zip_members": ["net.onnx", "net.data"], "model": "net.onnx"}
        monkeypatch.setitem(ai.MODELS, "upscale", good)
        models = ai.Models(tmp_path / "models")
        seen = []
        path = models.ensure("upscale", lambda d, t, m: seen.append(d))
        assert path.read_bytes() == b"onnx-bytes" and (path.parent / "net.data").read_bytes() == b"weights"
        assert models.installed("upscale") and seen and models.status()["upscale"]["installed"]

        monkeypatch.setitem(ai.MODELS, "background", {**good, "sha256": "0" * 64, "zip_members": None, "model": "x.onnx"})
        ai.MODELS["background"].pop("zip_members")
        with pytest.raises(RuntimeError, match="checksum"):
            models.ensure("background")
        assert not models.installed("background") and not (tmp_path / "models" / "background" / "x.onnx").exists()
    finally:
        server.shutdown()


AI_MODELS = os.environ.get("TOOLBOX_AI_MODELS")


@pytest.mark.skipif(not AI_MODELS, reason="set TOOLBOX_AI_MODELS to a folder with installed models")
def test_real_models(tmp_path):
    models = ai.Models(Path(AI_MODELS))
    src = photo(tmp_path / "p.png", (200, 150))
    up = ai.upscale(models, str(src), str(tmp_path / "up.png"), 4)
    assert (up["width"], up["height"]) == (800, 600)
    cut = ai.remove_background(models, str(src), str(tmp_path / "cut.png"), {})
    assert Image.open(cut["path"]).mode == "RGBA"
