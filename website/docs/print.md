---
title: Printing
description: Print PDFs with control over paper, two-sided printing, pages per sheet, booklets, crop marks and scaling.
---

# Printing

The Printing category has one tool, Advanced Print. It prints a PDF with more control than a normal print dialog, and shows the sheets exactly as they will come out of the printer.

Open a PDF with **Open PDF…**, with **Use** followed by the selected file's name, or by dragging it from the Explorer. You can also right-click a PDF in the Explorer and choose **Print…**. See [The Tilepress window](/docs/interface) for the Explorer and the other general controls.

## Advanced Print

Prints a PDF on any installed printer, with two-sided printing, several pages per sheet, booklets, crop marks and scaling. **Save layout as PDF…** writes the arranged sheets to a new PDF instead of printing them.

### How to use it

1. Open a PDF.
2. Choose the **Printer**, the number of **Copies**, **Two-sided** and **Colour**.
3. Under **Pages**, type a **Page range** if you don't want every page.
4. Under **Layout**, choose **One per sheet**, **Several per sheet** or **Booklet**, then the **Paper**, **Orientation** and **Scale**.
5. Check the preview on the left. Use the arrows or type a number to move between sheets. The line below it counts the pages, sheet sides and sheets of paper.
6. Click **Print**. When the job has gone to the printer, a line such as "Sent 6 sheets to Office printer." appears under the button.

To keep the arranged sheets as a file, click **Save layout as PDF…** instead.

### Options

**Printer**

| Option | What it does | Default |
|---|---|---|
| **Printer** | Every printer installed in Windows. The default printer is listed first, marked "(default)". | The Windows default printer |
| **Copies** | 1 to 999. | 1 |
| **Collate** | With several copies, prints each copy in full before starting the next. Available from 2 copies. | On |
| **Two-sided** | **One-sided**, **Flip on long edge** or **Flip on short edge**. Shows **Not supported** when the printer can't print on both sides. | One-sided |
| **Colour** | **Colour** or **Greyscale**. Fixed to greyscale for a printer that can't print colour. | Colour |

**Pages**

| Option | What it does | Default |
|---|---|---|
| **Page range** | The pages to print, such as `1-3, 5, 8-`. You can also type `odd`, `even` or `all`. | All pages |
| **Reverse order** | Prints the last page first. | Off |

**Layout**

| Option | What it does | Default |
|---|---|---|
| **One per sheet** / **Several per sheet** / **Booklet** | How pages are arranged on the sheets. See [Layouts](#layouts) below. | One per sheet |
| **Pages per sheet** | 2, 4, 6, 9 or 16. Several per sheet only. | 2 |
| **Page borders** | Draws a thin grey border round each page. Several per sheet only. | Off |
| **Paper** | **Same as the document**, A4, A3, A5, Letter, Legal or Tabloid. | Same as the document |
| **Orientation** | **Automatic**, **Portrait** or **Landscape**. Several per sheet only. | Automatic |
| **Scale** | **Fit to printable area**, **Actual size**, or **Custom…** with a **Percent** from 10 to 400. | Fit to printable area |

**Press marks**

| Option | What it does | Default |
|---|---|---|
| **Crop marks** | Draws marks at the corners showing where to trim the paper. One per sheet only. | Off |
| **Bleed** | 0 to 10 mm, in steps of 0.5 mm. How far the crop marks stay from the page edge, leaving room for artwork that runs past it. Shown when crop marks are on. | 3 mm |

### Layouts

- **One per sheet** prints each page on its own sheet. With **Paper** set to **Same as the document**, the pages are printed as they are.
- **Several per sheet** puts 2, 4, 6, 9 or 16 pages on each sheet in a grid, left to right and top to bottom, each scaled to fit its cell. With **Orientation** on **Automatic**, the sheet is turned whichever way wastes less paper; for example, two portrait pages go side by side on a landscape sheet.
- **Booklet** reorders the pages two to a sheet so the printed stack folds in the middle into a booklet. Blank pages are added at the end to make a multiple of four. With **Same as the document**, each sheet is two pages wide; with a paper size, the sheet is used landscape and folded in half. Choosing **Booklet** switches **Two-sided** to **Flip on short edge** when the printer can print on both sides. If it can't, print the first side, then feed the stack back in for the second.

### Good to know

- Pages are drawn straight to the printer as vectors rather than as pictures, so text stays sharp at any printer resolution.
- Landscape pages are turned to fit portrait paper, and the other way round.
- Pages print in the order you type them in **Page range**, so `5, 1-4` prints page 5 first.
- **Paper** asks the printer for the matching paper size. If the printer has no paper within 2 mm of that size, or you leave **Same as the document**, the printer uses its own paper setting.
- **Save layout as PDF…** saves the sheets as the preview shows them, suggesting `<name>_print.pdf` next to the original. Copies, two-sided, colour and scale are printer settings, so they don't affect the saved file.
- When the printer writes a file instead of paper (Microsoft Print to PDF, or an XPS printer), **Print** first asks where to save that file.
- A network printer that is off or slow to answer can take a while to report what it supports. It appears straight away marked "(checking…)", with the message "Asking this printer what it supports (two-sided, colour, paper)…", and its options fill in when the answer arrives.
- If no printers are installed, the tool says "No printers are installed." You can still use **Save layout as PDF…**.
- Password-protected PDFs can't be opened here. Unlock a copy with [Protect PDF](/docs/security) first.
- Each print is listed in [History](/docs/history) as "Print", and each saved layout as "Print to PDF".
