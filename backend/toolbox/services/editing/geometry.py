"""Convert between the page as displayed and PDF user space."""

from __future__ import annotations

from pypdf import PageObject


def visual_size(page: PageObject) -> tuple[float, float]:
    box = page.cropbox
    w, h = float(box.width), float(box.height)
    return (h, w) if page.rotation % 180 else (w, h)


def visual_rect_to_user(page: PageObject, x: float, y: float, w: float, h: float) -> tuple[float, float, float, float]:
    """(x, y-from-top, width, height) as displayed -> (llx, lly, urx, ury) in user space."""
    box = page.cropbox
    left, bottom, right, top = float(box.left), float(box.bottom), float(box.right), float(box.top)
    rot = page.rotation % 360
    if rot == 0:
        return left + x, top - y - h, left + x + w, top - y
    if rot == 90:  # displayed top = user's left edge, displayed right = user's top
        return left + y, bottom + x, left + y + h, bottom + x + w
    if rot == 180:
        return right - x - w, bottom + y, right - x, bottom + y + h
    return right - y - h, top - x - w, right - y, top - x  # 270


def bake_rotation(page: PageObject) -> None:
    """Make the page upright in user space, so overlays drawn upright land upright."""
    if page.rotation % 360:
        page.transfer_rotation_to_content()
