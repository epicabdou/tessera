"""Realistic sample PDFs for tests, drawn with ReportLab."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def make_report(path: Path, with_image: bool = False) -> Path:
    """Two pages: title, headings, a paragraph, bullets, numbered items and a ruled table."""
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 24)
    c.drawString(72, h - 90, "Quarterly Report")
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, h - 130, "Summary")
    c.setFont("Helvetica", 11)
    c.drawString(72, h - 155, "Sales grew strongly this quarter across all")
    c.drawString(72, h - 169, "regions, led by the north.")
    c.drawString(72, h - 200, "• Revenue up 12%")
    c.drawString(72, h - 214, "• Costs down 3%")
    c.drawString(72, h - 240, "1. Hire two engineers")
    c.drawString(72, h - 254, "2. Open the Oran office")
    # Ruled table: 3 columns x 3 rows
    top, row_h, xs = h - 300, 20, [72, 200, 300, 400]
    for r in range(4):
        c.line(xs[0], top - r * row_h, xs[-1], top - r * row_h)
    for x in xs:
        c.line(x, top, x, top - 3 * row_h)
    cells = [["Region", "Units", "Price"], ["North", "1,200", "3.50"], ["South", "950", "4.25"]]
    for r, row in enumerate(cells):
        for k, value in enumerate(row):
            c.drawString(xs[k] + 5, top - (r + 1) * row_h + 6, value)
    if with_image:
        img = path.with_suffix(".png")
        Image.new("RGB", (120, 80), (10, 150, 90)).save(img)
        c.drawImage(str(img), 72, 200, width=120, height=80)
    c.showPage()
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, h - 90, "Outlook")
    c.setFont("Helvetica", 11)
    c.drawString(72, h - 115, "Next quarter looks stable.")
    c.showPage()
    c.save()
    return path


def make_scan(path: Path, text: str = "Scanned invoice 4711") -> Path:
    """An image-only PDF (like a scanner makes): big black text on white, no text layer."""
    from PIL import ImageDraw, ImageFont

    img = Image.new("RGB", (1240, 1754), "white")  # A4 at 150 dpi
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 64)
    except OSError:
        font = ImageFont.load_default()
    draw.text((120, 200), text, fill="black", font=font)
    draw.text((120, 320), "Total due 128 EUR", fill="black", font=font)
    img.save(path, "PDF", resolution=150)
    return path


def make_numbered(path: Path, count: int, size=A4) -> Path:
    """`count` pages, each saying "Page N" large near the top-left."""
    c = canvas.Canvas(str(path), pagesize=size)
    for n in range(1, count + 1):
        c.setFont("Helvetica-Bold", 40)
        c.drawString(60, size[1] - 120, f"Page {n}")
        c.showPage()
    c.save()
    return path
