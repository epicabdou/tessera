"""Photo collage: layout geometry and rendering (services/images/collage.py)."""

from __future__ import annotations

import itertools

import pytest
from PIL import Image

from toolbox.services.images import collage

LANDSCAPE, PORTRAIT, SQUARE = (1600, 1000), (900, 1350), (800, 800)


def overlaps(a: collage.Cell, b: collage.Cell) -> bool:
    ax0, ay0, ax1, ay1 = a.box()
    bx0, by0, bx1, by1 = b.box()
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def check_inside(W: int, H: int, cells: list[collage.Cell], margin: float) -> None:
    for c in cells:
        x0, y0, x1, y1 = c.box()
        assert x0 >= round(margin) - 1 and y0 >= round(margin) - 1, c
        assert x1 <= W - round(margin) + 1 and y1 <= H - round(margin) + 1, c
        assert x1 > x0 and y1 > y0, c
    for a, b in itertools.combinations(cells, 2):
        assert not overlaps(a, b), (a, b)


@pytest.mark.parametrize("n", [2, 3, 4, 5, 7, 9, 12, 40])
@pytest.mark.parametrize("aspect", ["square", "portrait", "wide", "story"])
def test_grid_fills_the_canvas_without_overlaps(n, aspect):
    sizes = [LANDSCAPE, PORTRAIT, SQUARE][: 3] * 14
    W, H, cells = collage.plan(sizes[:n], {"layout": "grid", "aspect": aspect, "width": 1200, "margin": 0.02, "spacing": 0.01})
    assert W == 1200 and H == round(1200 / collage.ASPECTS[aspect])
    assert len(cells) == n
    check_inside(W, H, cells, 0.02 * W)
    # Every row reaches the right margin, including a shorter last row.
    rows: dict[int, list[collage.Cell]] = {}
    for c in cells:
        rows.setdefault(round(c.y), []).append(c)
    for row in rows.values():
        assert max(c.box()[2] for c in row) == pytest.approx(W - 0.02 * W, abs=1)


def test_grid_columns_can_be_chosen():
    _W, _H, cells = collage.plan([SQUARE] * 6, {"layout": "grid", "columns": 3, "width": 900, "margin": 0, "spacing": 0})
    assert len({round(c.y) for c in cells}) == 2
    assert [c.box()[2] for c in cells[:3]] == [300, 600, 900]


def test_auto_columns_suit_the_photos():
    def columns(size):
        _W, _H, cells = collage.plan([size] * 6, {"layout": "grid", "aspect": "wide", "width": 1600, "margin": 0, "spacing": 0})
        return sum(1 for c in cells if round(c.y) == 0)

    # On the same canvas, tall photos get more (narrower) columns than wide ones.
    assert columns(PORTRAIT) > columns(LANDSCAPE)
    # Square photos on a square canvas: a square grid.
    _W, _H, cells = collage.plan([SQUARE] * 9, {"layout": "grid", "aspect": "square", "width": 900, "margin": 0, "spacing": 0})
    assert {round(c.w) for c in cells} == {300}


def test_mosaic_rows_are_full_width_and_keep_photo_shapes():
    sizes = [LANDSCAPE, PORTRAIT, SQUARE, LANDSCAPE, LANDSCAPE, PORTRAIT, SQUARE, (2000, 800)]
    W, H, cells = collage.plan(sizes, {"layout": "mosaic", "width": 1500, "margin": 0.02, "spacing": 0.01, "per_row": 3})
    margin = 0.02 * W
    check_inside(W, H, cells, margin)
    for (w, h), c in zip(sizes, cells):
        assert c.w / c.h == pytest.approx(w / h, rel=1e-6)  # nothing is cropped
    rows: dict[int, list[collage.Cell]] = {}
    for c in cells:
        rows.setdefault(round(c.y), []).append(c)
    *full, last = [rows[k] for k in sorted(rows)]
    for row in full:
        assert row[-1].x + row[-1].w == pytest.approx(W - margin, abs=0.01)
    assert round(last[-1].y + last[-1].h + margin) == H


def test_mosaic_doesnt_blow_up_a_short_last_row():
    sizes = [LANDSCAPE] * 7
    _W, _H, cells = collage.plan(sizes, {"layout": "mosaic", "width": 1200, "margin": 0, "spacing": 0, "per_row": 3})
    full_height, last_height = cells[0].h, cells[-1].h
    assert last_height <= full_height * 1.25


@pytest.mark.parametrize("side", ["left", "right", "top", "bottom"])
def test_featured_puts_the_first_photo_big(side):
    W, H, cells = collage.plan([LANDSCAPE] * 5, {"layout": "featured", "side": side, "share": 0.6, "width": 1200, "aspect": "landscape"})
    check_inside(W, H, cells, 0.02 * W)
    big, *rest = cells
    assert all(big.w * big.h > 2 * c.w * c.h for c in rest)
    if side == "left":
        assert big.x < min(c.x for c in rest)
    if side == "bottom":
        assert big.y > max(c.y for c in rest)


@pytest.mark.parametrize(
    "sizes, options, message",
    [
        ([SQUARE], {}, "at least 2"),
        ([SQUARE] * 41, {}, "up to 40"),
        ([SQUARE] * 2, {"layout": "spiral"}, "Unknown layout"),
        ([SQUARE] * 2, {"aspect": "circle"}, "Unknown canvas shape"),
        ([SQUARE] * 2, {"background": "not a colour"}, ""),
        ([(100, 10000)] * 40, {"layout": "mosaic", "width": 10000, "per_row": 1, "spacing": 0, "margin": 0}, "too big"),
    ],
)
def test_bad_input_is_refused(sizes, options, message):
    with pytest.raises(ValueError, match=message):
        collage.plan(sizes, options)


@pytest.fixture
def photos(tmp_path):
    paths = []
    for i, (size, colour) in enumerate([(LANDSCAPE, "red"), (PORTRAIT, "green"), (SQUARE, "blue"), (LANDSCAPE, "yellow")]):
        p = tmp_path / f"p{i}.jpg"
        Image.new("RGB", size, colour).save(p, quality=95)
        paths.append(str(p))
    return paths


def test_save_writes_the_collage(photos, tmp_path):
    out = collage.save(photos, str(tmp_path / "collage.jpg"), {"layout": "grid", "aspect": "square", "width": 800, "margin": 0.05, "background": "#000000"})
    assert out["photos"] == 4 and out["name"] == "collage.jpg"
    with Image.open(out["path"]) as im:
        assert im.size == (800, 800)
        assert max(im.getpixel((5, 5))) < 30  # the margin shows the background
        r, g, b = im.getpixel((200, 200))  # first cell: the red photo
        assert r > 200 and g < 60 and b < 60


def test_rounded_corners_and_transparent_background(photos, tmp_path):
    options = {"layout": "grid", "columns": 2, "width": 600, "margin": 0, "spacing": 0.02, "radius": 0.05, "background": "transparent", "format": "png"}
    out = collage.save(photos, str(tmp_path / "c.png"), options)
    with Image.open(out["path"]) as im:
        assert im.mode == "RGBA"
        assert im.getpixel((0, 0))[3] == 0  # outside the rounded corner
        assert im.getpixel((300, 150))[3] == 0  # in the gap between cells
        assert im.getpixel((150, 150))[3] == 255
    # JPEG has no transparency: the background becomes white.
    out = collage.save(photos, str(tmp_path / "c.jpg"), {**options, "format": "jpg"})
    with Image.open(out["path"]) as im:
        assert im.getpixel((300, 150)) == pytest.approx((255, 255, 255), abs=3)


def test_fit_keeps_whole_photos(photos, tmp_path):
    out = collage.save(photos[:2], str(tmp_path / "c.png"), {"layout": "grid", "columns": 2, "aspect": "square", "width": 800, "margin": 0, "spacing": 0, "fit": "fit", "background": "#000000", "format": "png"})
    with Image.open(out["path"]) as im:
        # The landscape photo in a tall cell: black above and below it, red in the middle.
        assert im.getpixel((200, 10))[:3] == (0, 0, 0)
        assert im.getpixel((200, 400))[0] > 200


def test_preview_is_small_and_reports_the_full_size(photos):
    p = collage.preview(photos, {"layout": "mosaic", "width": 4000}, max_side=500)
    assert max(p["width"], p["height"]) <= 500
    assert p["full_width"] == 4000 and p["full_height"] > 0
    assert p["data_url"].startswith("data:image/jpeg")


def test_exif_rotation_is_respected(tmp_path):
    p = tmp_path / "rotated.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90°: stored landscape, shown portrait
    Image.new("RGB", (1200, 800), "red").save(p, exif=exif)
    assert collage._upright_size(str(p)) == (800, 1200)
