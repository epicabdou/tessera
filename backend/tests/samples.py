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


PROSE = (
    "Deliveries reached every region on time this year, and the new routes through the east cut the "
    "average journey by almost a day. The depots now share one schedule, which keeps the vans full."
)


def make_layout(path: Path) -> Path:
    """What browsers and word processors print: three heading sizes, wrapped prose, list bullets
    drawn as small dots, short address lines, and a table without lines."""
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    # Word's Title / Heading 1 / Heading 2 sizes over 11 pt text: close together, but three levels.
    c.setFont("Helvetica-Bold", 26)
    c.drawString(72, h - 80, "Annual Review")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, h - 115, "Operations")
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(72, h - 140, "Logistics")
    para = Paragraph(PROSE, ParagraphStyle("body", fontName="Helvetica", fontSize=11, leading=14))
    _, ph = para.wrap(w - 144, h)
    para.drawOn(c, 72, h - 155 - ph)
    y = h - 175 - ph
    c.setFont("Helvetica", 11)
    for item in ("Fleet renewed", "Two depots opened"):
        c.circle(78, y + 3.5, 1.8, stroke=0, fill=1)  # a bullet drawn as a shape, as Chrome and Edge print them
        c.drawString(88, y, item)
        y -= 15
    y -= 12
    for line in ("Head office", "12 Rue Larbi Ben M'hidi", "Oran"):
        c.drawString(72, y, line)
        y -= 14
    y -= 16
    for row in (("Item", "Qty", "Total"), ("Steel brackets", "40", "100.00"), ("Hex bolts", "250", "30.00"), ("Delivery", "1", "25.00")):
        for x, value in zip((72, 250, 350), row):
            c.drawString(x, y, value)
        y -= 16
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
