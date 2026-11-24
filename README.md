<img src="frontend/public/favicon.svg" alt="" width="72" height="72">

# Tilepress

**PDF and image tools that run on your own computer.**

Merge, split, convert, sign, protect, OCR and compress PDFs; resize, convert, crop and enhance images; write LaTeX. Your files are processed on your PC, never uploaded. A free, open-source alternative to online tools like iLovePDF and iLoveIMG.

**[Download for Windows](https://github.com/epicabdou/tilepress/releases/latest/download/Tilepress-x64.msi)** · [Website](https://epicabdou.github.io/tilepress/) · [Documentation](https://epicabdou.github.io/tilepress/docs/) · [Support](https://epicabdou.github.io/tilepress/support) · [Releases](https://github.com/epicabdou/tilepress/releases)

![Tilepress merging three PDFs, with the Explorer on the left and a live preview on the right](https://epicabdou.github.io/tilepress/screenshots/merge.webp)

## For developers

Under the hood it's a desktop app with a **React** UI and **Python** business logic, shipped as a native Windows executable.

```
┌──────────────── Tilepress.exe ─────────────────┐
│  Native window (pywebview → WebView2)        │
│  ┌────────────────────────────────────────┐  │
│  │ React + TypeScript (Vite)              │  │
│  │   call('pdf_merge', items, output)     │  │
│  └──────────────┬─────────────────────────┘  │
│                 │ window.pywebview.api (IPC) │
│  ┌──────────────▼─────────────────────────┐  │
│  │ backend/toolbox/api.py   (thin bridge) │  │
│  │ backend/toolbox/services (logic)       │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

- **[pywebview](https://pywebview.flowrl.com/)** opens a native window using the WebView2 runtime built into Windows 10/11. Python methods are callable from JavaScript directly, so there's no REST API and no open port for the bridge.
- **Vite + React + TypeScript** for the UI, with hot reload during development.
- **PyInstaller** bundles Python, the backend and the built UI into `Tilepress.exe`.
- **pypdf** (BSD) edits PDFs and **pypdfium2** (PDFium, Apache/BSD) renders page previews. Both have permissive licences that are compatible with Tilepress's GPL. PyMuPDF was avoided because it is AGPL.
- **pywin32** drives Microsoft Office for document conversion. **markdown-it-py** and **Pygments** render Markdown. All three are permissively licensed.
- **pdfplumber**, **python-docx**, **python-pptx** and **openpyxl** (all MIT) convert PDFs to Office files. **ReportLab** (BSD) draws text, images and shapes onto pages. **pyHanko** (MIT) and **cryptography** (Apache/BSD) make and check digital signatures. OCR uses **Tesseract** when it's installed, otherwise the OCR engine built into Windows (through the **winrt** packages).
- The LaTeX editor uses **CodeMirror** (MIT) and compiles with **Tectonic** (MIT), which the app downloads on first launch (see [Runtime notes](#runtime-notes)).
- The image tools use **Pillow** (HPND) and **numpy** (BSD), **pillow-heif** for iPhone HEIC photos (its wheel bundles libheif and libde265, LGPL-3.0, and x265, GPL-2.0-or-later, as separate DLLs), and **ONNX Runtime with DirectML** (MIT) to run the AI models on the graphics card, or on the CPU when there's no suitable GPU. The models are downloaded the first time an AI tool needs them (see [Runtime notes](#runtime-notes)); face detection uses the detector built into Windows.

## Layout

The window uses a frosted-glass design: three floating panels over a soft colour backdrop. It follows the Windows light or dark app theme.

- A resizable **Explorer** on the left.
- The tools in the middle. A switch at the left of the top bar picks the section, **Documents** (PDF tools and LaTeX) or **Images**. The section's **categories** are tabs next to it (icons with short names; hover for the full name), and the selected category's tools appear as a row underneath. Each section remembers its last category, and each category its last tool. A category with a single tool (Print, LaTeX) has no tool row. When the middle panel is narrow, the switch and tabs show icons only.
- A resizable **Preview** on the right.

The top bar also has:

- **Find a tool** (`Ctrl+K`): type any part of a tool's name, what it does, or its category (for example *merge*, *sign*, *word*), then press Enter. Arrow keys move through the list; Esc closes it.
- A **status** button (green dot): click it for the app version, the Python and Windows versions, and which engines are available (LaTeX, OCR, Office). If the LaTeX setup failed, it offers **Retry LaTeX setup**.
- The button that shows or hides the Preview panel.

Drag the gap between two panels to resize them (or focus it and use ←/→), and double-click it to reset. A status bar at the bottom of the middle panel shows the selected item.

The Explorer has three parts:

- **Pinned:** your saved folders. Pin a folder by right-clicking it, with the pin button in the path bar, with the **+** button, or by dragging a folder from the tree onto the list. Drag pins to reorder them, or right-click a pin and choose Move up / Move down. Pins whose folder no longer exists are struck through.
- **Locations:** Home, Desktop, Documents and Downloads (including OneDrive-redirected ones), plus every drive.
- **Tree:** the current folder, with folders loaded as you expand them.
  - Navigation: Back, Forward and Up buttons; clickable breadcrumbs. Click the path bar (or press `Ctrl+L`) to type a path; `~` and `%VARS%` work.
  - Filter: narrows the folders that are already open.
  - Show hidden items: a toggle in the Explorer header.
  - Keyboard: arrow keys, Home/End, Enter, Backspace for up, `Alt+←/→` for back/forward, and type a name to jump to it.
  - Double-click: opens a file with its default app, or browses into a folder.
  - Right-click: Pin, Open in File Explorer, Show in File Explorer and Copy path. PDFs also get **Open in PDF tools**, **Add to Merge PDF**, **Edit PDF**, **Convert from PDF**, **Sign PDF**, **Protect PDF** and **Print…**. Images get **Edit photo**, **Compress image**, **Resize image**, **Crop image**, **Add to collage**, **Remove background** and **Upscale image** (and **Convert to PDF**). Office files, HTML and Markdown get **Convert to PDF**; `.tex` files get **Open in LaTeX editor**.
  - Drag: drag a folder onto Pinned, or a PDF onto a PDF tool.

### Preview

The Preview panel shows whatever is selected in the Explorer. It follows arrow-key navigation in the tree.

| Selection | Preview |
|---|---|
| PDF | Every page, loaded as you scroll; a **PDF tools** button |
| Image (PNG, JPEG, GIF, WebP, BMP, TIFF, ICO, SVG) | The picture, upright for rotated photos. Click to toggle actual size. Dimensions and colour mode are shown. An **Edit photo** button opens it in the Photo editor. |
| Text and code (and unknown files that look like text) | The first 256 KB with line numbers and a Wrap toggle; encoding and line endings |
| CSV / TSV | A table of the first 300 rows. `;`, `,`, tab and `\|` separators are detected automatically. |
| Folder | Counts of folders and files, total size, the most common file types, and the last change |
| Anything else | Details only: type, size, modified and created dates, location |

Every preview has **Open**, **Show in folder** and **Copy path** buttons. Hide the panel with its × button, and bring it back with the panel button at the right of the top bar.

Pins, the last folder, the hidden-items toggle, both panel widths and whether the Preview is open are saved by Python in `%LOCALAPPDATA%\Tilepress\settings.json`.

## Tools

**Combine, Split & Page Management**

| Tool | What it does |
|---|---|
| Merge PDF | Combine PDFs in list order. Optionally choose a page range per file (`2-5, 9`) and add a bookmark for each file. Reorder by dragging. |
| Split PDF | Split by ranges (each range becomes a file), every N pages, or extract pages (into one file or one file per page). Pages are colour-coded by output file. |
| Organize PDF | Drag to reorder; rotate, duplicate or delete pages; insert blank pages or pages from another PDF. Undo/redo, multi-select (Ctrl/Shift-click), Delete key. |
| Rotate PDF | Rotate selected, odd, even or all pages by 90°, 180° or 270°, with a live preview. |
| Crop | Drag the crop box or draw a new one on the page; type margins in mm; or auto-detect the content. Applies to all pages, one page or a range. |
| Page numbers | 6 positions, preset or custom formats (`Page {n} of {total}`), start number, page range, size, margin, colour, and mirroring for double-sided printing. Live preview. |

Split, Organize, Rotate, Crop and Page numbers share the open PDF, so you can switch between them without reopening it. Every tool saves to a **new** file; it suggests `name_rotated.pdf` and so on and never overwrites without asking. After saving, **Keep editing this file** opens the result for the next step.

**Conversion: To PDF**

| Tool | What it does |
|---|---|
| Word to PDF | DOC, DOCX (also RTF and ODT). Options: bookmarks from headings, include comments and tracked changes, PDF/A. |
| PowerPoint to PDF | PPT, PPTX. Output as slides, notes pages or handouts (2, 3 or 6 per page). Options: include hidden slides, frame slides. |
| Excel to PDF | XLS, XLSX (also CSV and ODS). Whole workbook or active sheet; fit each sheet to one page wide; landscape; respect print areas. |
| JPG to PDF | JPG, PNG, GIF, BMP, TIFF (multi-page) and WebP. Page size (or same as the image), orientation, margin, and fit or fill. Produces one PDF, or one PDF per image. Images can be reordered and rotated. |
| HTML to PDF | A web page (by address), an HTML file, or pasted HTML code. Page size, orientation, margins, scale, backgrounds, and header/footer. For web pages, optionally wait or scroll first so lazy content loads. |
| Markdown to PDF | A .md file or typed Markdown, with a live preview. Supports tables, code highlighting and local images. Three themes. |

How the conversions work:

- **Word, PowerPoint, Excel:**
  - Converted by **Microsoft Office** when it's installed, for the most faithful output. Otherwise the free **LibreOffice** is used.
  - The tool shows which app it will use. If both are installed, you can switch between them.
  - Office runs invisibly, as its own instance, with macros force-disabled. Your open documents are never touched. Several files convert one after another, each with its own status.
- **JPG to PDF:** JPEG files are copied into the PDF byte-for-byte (no quality loss). Other formats are stored losslessly.
- **HTML and Markdown:** printed by WebView2, the Chromium engine that also draws the app. HTML being converted runs in a hidden window that can't read other files on your computer.
- **Starting points:** right-click a convertible file in the Explorer, or use the Preview panel's **Convert to PDF** button, to open the matching tool with that file.

**Conversion: From PDF**

| Tool | What it does |
|---|---|
| PDF to Word | DOCX (or DOC, with Word). Uses Microsoft Word when it's installed (keeps the layout closest), otherwise a built-in converter that rebuilds headings, paragraphs, bullet and numbered lists, and tables as editable Word content. |
| PDF to PowerPoint | One slide per page, sized to the page, as a sharp picture of the page. Optionally puts the page's text in the speaker notes. Three quality levels. |
| PDF to Excel | Finds tables (ruled grids, or aligned text without lines) and writes one sheet per table. Numbers, percentages and amounts become real numbers. Choose the pages. |
| PDF to JPG | Every page (or a range) as JPG or PNG at 72–600 dpi, or extract the images embedded in the PDF at their original quality. |
| PDF to Markdown | Headings, paragraphs, lists and tables as Markdown, with a live preview (rendered or raw) and optional page-break markers. |

**Editing, Forms & Text Recognition**

| Tool | What it does |
|---|---|
| Edit PDF | **Edit text**: click a line of existing text to retype it (same size, weight and font family). Add text, images, boxes, ellipses and highlights; white-out; and **redact**, which blacks out an area *and removes the text underneath* so it can't be copied or searched. Move and resize anything; Delete removes it. |
| OCR PDF | Adds an invisible, selectable text layer to scanned pages so the PDF becomes searchable. The pages look exactly the same. Tesseract or Windows OCR, document language, 200–400 dpi, page range, and skipping pages that already have text. |
| PDF Forms | **Fill**: every field (text, multi-line, checkbox, radio, dropdown, list) in a side panel, highlighted on the page; optionally flatten the answers into the page. **Design**: click or drag on a page to add text boxes, multi-line boxes, checkboxes, dropdowns and list boxes, with names, options, default values and a Required flag. |
| Watermark | Text (font, size, colour, bold) or an image (sized as a share of the page width). Opacity, rotation, 9 positions or tiled across the page, over or behind the content, and a page range. The preview is the actual result, rendered by the same code that saves. |

**Security, Signatures & Optimization**

| Tool | What it does |
|---|---|
| Protect PDF | An open password and/or restrictions (printing, high-quality printing, copying, editing, comments, form filling, page assembly, screen-reader access) with a separate permissions password. AES-256 by default; AES-128 and RC4-128 for older readers. Opening a protected file offers **Unlock** instead (needs its password). |
| Sign PDF | **Electronic**: draw (mouse, pen or touch), type (handwriting fonts) or upload a signature, place it anywhere as often as needed, and add the date. **Digital**: sign with a `.pfx`/`.p12` certificate (PAdES) with reason, location and contact, optionally with a visible signature box. You can create a self-signed certificate in the app. Signed files list each signature and whether the document has changed since. |
| Compress PDF | Three levels that downsample and re-encode large images, merge duplicate objects and compress page content. Optionally strips metadata. Shows the size before and after; if the file can't get smaller, the copy is left unchanged. |
| Repair PDF | Checks the file and lists what's wrong, then rebuilds it: a fresh cross-reference table, PDFium's recovery, or (for truncated or badly damaged files) a scan for surviving objects. Keeps whichever recovers the most pages. Works on files the other tools can't open. |

**Printing & Output**

| Tool | What it does |
|---|---|
| Advanced Print | Printer, copies and collation, two-sided (long or short edge), colour or greyscale, page range and reverse order. Layouts: one page per sheet, 2/4/6/9/16 pages per sheet (with optional borders), or **booklet** (pages reordered to fold; short-edge duplex is selected for you). Paper size, orientation, scale (fit, actual size or a percentage), and **crop marks with bleed**. The preview shows the actual sheets. **Save layout as PDF** writes the arranged sheets instead of printing. Pages are drawn as vectors straight to the printer, so text stays sharp. |

**LaTeX**

| Tool | What it does |
|---|---|
| LaTeX editor | Article, report, Beamer presentation and letter templates, or open any `.tex`. Syntax highlighting, command and environment completion, snippets (sections, lists, equations, tables, figures, links), and **Image…** to insert a figure with a relative path. **Live** mode recompiles a moment after you stop typing (or press `Ctrl+Enter`; `Ctrl+S` saves). The PDF appears beside the source; errors and warnings are listed with their line, and clicking one jumps there. The PDF is written next to the `.tex` file. Uses Tectonic, or an installed pdfLaTeX, XeLaTeX or LuaLaTeX (choose under **Engine**). |

Notes:

- Page numbers use the standard Helvetica font, so the text must use Latin characters. Edit PDF and Watermark embed Arial, Times New Roman or Courier New from Windows.
- Crop hides content outside the box; it doesn't delete it. To really remove content, use **Redact** in Edit PDF.
- Edit text replaces a whole line with newly typed text. It works best on ordinary text PDFs; on scans, run OCR first.
- Password-protected PDFs open only in Protect PDF (to unlock them) and Repair PDF. Unlock a copy first to use the other tools.
- A self-signed certificate proves the file hasn't changed since signing, but PDF readers will show the signer as not verified. For a trusted signature, use a certificate from a certificate authority.
- Restrictions (no printing, no copying…) are honoured by PDF readers but aren't a strong barrier on their own. An open password is real encryption.

### Images

The image tools read JPG, PNG, WebP, HEIC/HEIF (iPhone), AVIF, GIF, BMP, TIFF and ICO, and save JPG, PNG, WebP, AVIF, GIF, BMP or TIFF. Photos are always handled upright (the camera's rotation flag is applied) and keep their colour profile. Every tool saves a **new** file and never changes the original. Batch tools save next to each image unless you pick a folder. The previews are rendered by the same code that saves, so they show exactly what you'll get.

**Format & Size Optimization**

| Tool | What it does |
|---|---|
| Compress Image | Three presets plus a quality slider; keep the format or switch to JPG, WebP, AVIF or PNG; optionally limit the longest side; for PNG, reduce to 256/128/64 colours (often 60–80% smaller). The new size of each file is **measured** (compressed in memory) and shown before you save, with the total. Metadata (camera, location) is removed unless you keep it. A file that can't get smaller is copied unchanged rather than grown. |
| Resize Image | By percentage, exact pixels (keep proportions, then fit inside or fill and crop), or longest side. Lanczos, bicubic or nearest-neighbour (pixel art). "Never enlarge" leaves smaller images alone. Each row shows the size it will become. |
| Convert to JPG | PNG, WebP, HEIC, AVIF, GIF, BMP, TIFF and ICO into JPG, with a background colour for transparent areas, quality, and optionally every page/frame of a multi-page TIFF or animated GIF as its own JPG. |
| Convert from JPG | JPG into PNG, WebP, AVIF, GIF, BMP or TIFF, or into a PDF (all photos in one document, or one per photo). |

**Framing, Layout & Generation**

| Tool | What it does |
|---|---|
| Crop Image | Drag the box, its corners or edges, or draw a new one; rule-of-thirds guides; aspect presets (free, original, 1:1, 4:3, 3:4, 16:9, 9:16, 3:2, 2:3, 5:4, 4:5); exact X/Y/width/height in pixels; rectangle or circle/oval (outside becomes transparent). |
| Rotate Image | Rotate left, right or 180°, or flip, each image on its own or all at once, with live thumbnails. |
| Photo collage | 2 to 40 photos on one canvas: a **grid** (automatic or chosen columns; photos cropped to fill their cell or shown whole), a **mosaic** (rows that keep every photo's shape, scaled to the full width), or one **featured** photo with the rest beside it. Canvas shape (1:1, 4:5, 3:2, 16:9, 9:16, A4) and width; spacing, border and rounded corners; a background colour or transparent; reorder or shuffle the photos. The preview is the real result. |
| HTML to Image | A web page, an HTML file or HTML/CSS code, rendered at a desktop, laptop, tablet, phone or custom width, as the whole page or the visible area, at 1×, 2× or 3× sharpness, to PNG, JPG or WebP. Snippets can have a transparent background. |

**AI & Smart Enhancements**

| Tool | What it does |
|---|---|
| Upscale Image | Real-ESRGAN super-resolution at 2× or 4×. It rebuilds detail rather than stretching pixels, and processes the picture in overlapping tiles, so there are no seams. Optional extra sharpening. Afterwards a before/after slider with 2×–4× zoom shows the difference. Up to about 4 MP for 4× and 16 MP for 2× (output around 64 MP). |
| Remove background | ISNet finds the subject. Make the background transparent, a colour, or a blurred copy of the photo; firm up hazy edges or soften them; optionally trim to the subject. The model runs once per photo; changing the options afterwards is instant. Compare with the original using a slider. |
| Blur face | Faces are found with the detector built into Windows (big photos are also scanned in tiles, for small faces in groups). Every box can be moved, resized, deleted, or drawn by hand for anything it missed. Blur, pixelate or cover with a colour, in ovals or rectangles. Saved copies leave out metadata by default. |

**Editing & Branding**

| Tool | What it does |
|---|---|
| Photo editor | Nine looks (Vivid, Warm, Cool, Mono, Noir, Sepia, Vintage, Fade, Dramatic) with live thumbnails, and sliders for exposure, brightness, contrast, highlights, shadows, saturation, warmth, tint, hue, sharpness/blur, vignette and fade (double-click a slider to reset it). Rotate and flip. Layers: text (six fonts, size, colour, bold/italic, outline, shadow), freehand drawing, arrows, lines, boxes and ellipses, and logos or other images, each movable, resizable, with opacity and stacking order; layers move with the picture when you rotate or flip it. Undo/redo (`Ctrl+Z`, `Ctrl+Y`), Delete removes the selected layer. |
| Watermark Image | Text (font, size relative to the image, colour, dark outline) or a logo, with opacity, rotation, 9 positions with a margin, or repeated across the image. Applied to a whole batch; the preview shows the real result on the selected image. |

## Prerequisites

- Python 3.11+
- Node.js 20+
- .NET SDK 6+ (only to build the `.msi` installer)

## Setup

```powershell
python -m venv .venv
```
```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
```
```powershell
npm --prefix frontend install
```

## Develop

```powershell
.venv\Scripts\python scripts\dev.py
```

This starts the Vite dev server and opens the app window pointed at it. React changes hot-reload. After changing Python, close the window and run the command again. DevTools are enabled in dev mode (right-click → Inspect). Closing the window stops Vite.

Opening `http://127.0.0.1:5173` in a regular browser shows the UI, but it can't reach Python; the status button shows "No Python backend".

## Build the desktop app

```powershell
.venv\Scripts\python scripts\build.py
```

This produces `dist\Tilepress\Tilepress.exe`, a folder build that starts fastest. Zip the `dist\Tilepress` folder to distribute it.

```powershell
.venv\Scripts\python scripts\build.py --onefile
```

This produces a single `dist\Tilepress.exe`. It's easier to hand around, but it starts more slowly because it unpacks itself to a temporary folder on every launch.

### Windows installer (.msi)

```powershell
.venv\Scripts\python scripts\build.py --msi
```

This builds the folder version, then packs it into `dist\Tilepress-<version>-x64.msi` (about 75 MB) and runs Windows Installer's consistency checks on it. Add `--skip-app` to repack the existing `dist\Tilepress` without rebuilding it.

- **Install:** double-click the MSI. It installs for the current user in `%LocalAppData%\Programs\Tilepress`, with no admin prompt, adds a Start menu shortcut, and offers to launch Tilepress at the end. To install for everyone on the PC in Program Files, run it elevated: `msiexec /i Tilepress-<version>-x64.msi ALLUSERS=1`.
- **Upgrade:** bump `__version__` in `backend/toolbox/__init__.py` and build again. A newer MSI replaces the installed version; an older one refuses to install over a newer one. Never change the `UpgradeCode` in `installer/Tilepress.wxs`.
- **Uninstall:** Settings → Apps, or `msiexec /x Tilepress-<version>-x64.msi`. Your data in `%LOCALAPPDATA%\Tilepress\` is kept.
- **Tooling:** the [WiX Toolset](https://wixtoolset.org/) 5.0.2, pinned in `dotnet-tools.json` and restored automatically (it needs the .NET SDK 6 or later). WiX 6 and later require accepting the Open Source Maintenance Fee EULA, which is why the project stays on 5.
- **Sources:** `installer\Tilepress.wxs` (package, files, shortcut) and `installer\TilepressUI.wxs` (dialogs: Welcome, Ready, Finish; no licence page). The dialog artwork in `assets\installer\` comes from `scripts\make_brand.py`.

The app icon is `assets\icon.ico`, also generated by `scripts\make_brand.py`.

## Test

```powershell
.venv\Scripts\python -m pytest
```

Unit tests cover the business logic in `backend/toolbox/services`.

The tests that actually start Microsoft Office or LibreOffice are slow, so they're skipped by default. To run them:

```powershell
$env:TOOLBOX_OFFICE_TESTS = "1"; .venv\Scripts\python -m pytest backend/tests/test_convert.py
```

The image AI tests use stand-in models by default (to check tiling, masking and the checksum-verified download exactly). To also run the real models, point `TOOLBOX_AI_MODELS` at a models folder, such as the app's own:

```powershell
$env:TOOLBOX_AI_MODELS = "$env:LOCALAPPDATA\Tilepress\models"; .venv\Scripts\python -m pytest backend/tests/test_images.py
```

```powershell
dist\Tilepress\Tilepress.exe --self-test
```

The self-test checks the whole stack:

1. It renders a PDF page with PDFium. This catches a packaged build that's missing `pdfium.dll`.
2. It opens the real window and waits until the UI has connected to Python and the Explorer has listed its first folder.
3. It runs a quick conversion check:
   - prints Markdown with code highlighting to PDF through WebView2,
   - converts an image,
   - loads the Office automation modules (it doesn't start Office).
4. It runs the PDF tools on a small generated PDF: to Word, PowerPoint, Excel and Markdown, watermark, protect, compress, booklet layout, and a digital signature that it then verifies. It also loads the Windows OCR modules. Then it runs the image tools on generated pictures (HEIC, WebP and AVIF, resize, the editor with text and a filter, a watermark, the Windows face detector) and loads ONNX Runtime. This catches a packaged build that's missing a library or its data files.
5. It exits with code `0` (pass) or `1` (fail). It works with `backend\main.py`, `scripts\dev.py` and packaged builds, so you can use it in CI.

## Project layout

```
backend/
  main.py                  entry point (source and PyInstaller)
  toolbox/
    app.py                 window creation, dev/prod URL, --self-test
    api.py                 methods exposed to JS as window.pywebview.api
    paths.py               source vs. frozen paths, per-user data dir
    services/              business logic: no UI imports, unit-tested
      filesystem.py        directory listing, locations, open/reveal, read text
      settings.py          pinned folders + preferences (settings.json)
      preview.py           Preview panel data: text, tables, images, folders
      pdf/
        common.py          open/describe PDFs, page-range parsing, safe writes
        ops.py             merge, split, organize, rotate, crop
        numbering.py       page numbers (Helvetica, no font files)
        render.py          page previews + auto-crop detection (PDFium)
      convert/
        office.py          Word/Excel/PowerPoint via Office (COM) or LibreOffice
        images.py          images to PDF (lossless JPEG embedding)
        markdown.py        Markdown to styled HTML (markdown-it + Pygments)
        web.py             print options, URL checks, HTML sources
      frompdf/
        structure.py       text lines → headings, paragraphs, lists (by font size and layout)
        convert.py         PDF to Word, PowerPoint, Excel, images, Markdown
      editing/
        geometry.py        page coordinates as displayed ↔ PDF coordinates (any rotation)
        overlay.py         ReportLab overlays, fonts, images
        edit.py            Edit PDF: objects, text lines, removing text under redactions
        ocr.py             Tesseract / Windows OCR → invisible text layer
        forms.py           list, fill and create form fields
        watermark.py       text and image watermarks
      security/
        protect.py         encryption, restrictions, unlock
        sign.py            certificates, PAdES signing (pyHanko), verification
        optimize.py        compress, analyze, repair
      printing/
        impose.py          page selection, n-up, booklets, crop marks
        printer.py         printers and vector printing (PDFium → printer DC)
      images/
        imageio.py         open (upright, HEIC), preview, encode/save every format
        basic.py           compress, resize, convert, crop, rotate/flip
        ai.py              model downloads (checksummed), ONNX Runtime, upscale, background removal
        faces.py           Windows face detection, blur/pixelate/cover
        editor.py          photo editor (adjustments, looks, layers) and image watermarks
      latex.py             find engines, compile, parse the log, templates
      components.py        first-run download of Tectonic (checksum-verified)
      progress.py          progress of long jobs, polled by the UI
    html_print.py          HTML to PDF with WebView2 in a hidden window
  tests/
frontend/
  src/lib/bridge.ts        typed wrapper around window.pywebview.api
  src/lib/workspace.ts     shared selection + "open this file in tool X"
  src/browser/             Explorer: tree, pinned list, path bar
  src/preview/             Preview panel and its per-type views
  src/components/Resizer   drag/keyboard resize handle for both side panels
  src/tools/registry.tsx   categories and tools (navigation and Find a tool are built from this)
  src/components/          shared UI: CommandPalette (Ctrl+K), StatusPill (status panel), menus, icons
  src/pdf/                 PDF tools, shared previews, open/save flow
  src/convert/             Conversion: To PDF tools
  src/frompdf/             Conversion: From PDF tools
  src/editing/             Edit PDF, OCR, Forms, Watermark; BoxLayer (boxes over a page)
  src/security/            Protect, Sign (signature pad), Compress, Repair
  src/print/               Advanced Print
  src/latex/               LaTeX editor (CodeMirror)
  src/images/              image tools; ImageGate/ImageStage (shared open image), batch list, crop box, layers
scripts/
  dev.py                   Vite + window, one command
  build.py                 frontend build + PyInstaller
  make_brand.py            regenerates the logo (favicon.svg), the Windows icon and the installer artwork
  screenshots.py           real screenshots for the website repo (demo files, local bridge, headless Edge)
assets/
  icon.ico                 the app icon, 16–256 px
  installer/               MSI dialog artwork (dialog.bmp, banner.bmp)
installer/
  Tilepress.wxs              the MSI: files, Start menu shortcut, upgrades
  TilepressUI.wxs            its dialogs
.github/workflows/         CI, and MSI releases on v* tags
```

## Adding a feature

1. Write the logic in `backend/toolbox/services/` and add tests.
2. Expose it with a public method on `Api` in `backend/toolbox/api.py`. Return JSON-serialisable values. A raised exception rejects the JS promise with its message. If it writes files, decorate it with `@_records("<tool name>")` so its runs appear in History; name its source argument `path`, `paths` or `items` and return `{path, ...}`, `{files: [...]}` or a list of those, and the inputs and outputs are picked up automatically.
3. Add the method's signature to `PyApi` in `frontend/src/lib/bridge.ts`.
4. Call it from React with `await call('your_method', arg1, arg2)`.
5. For a new screen, add a component and register it under a category in `frontend/src/tools/registry.tsx`, with an icon and a one-line `hint` (shown in Find a tool). To add a category, add its id to `CategoryId` in `src/lib/workspace.ts`, then add an entry to `CATEGORIES` with its `short` tab name and icon.
6. Style it with the shared classes (`card`, `btn btn-primary`/`btn-secondary`/`btn-ghost`, `text-input`, `segmented`, `side-panel`, `action-bar`) and the colour tokens in `src/index.css` (`--glass`, `--bg-elev`, `--field`, `--accent`, `--accent-grad`…), so it works in both light and dark themes. Pop-ups that use `position: fixed` must be rendered with a portal (as `ContextMenu` is): inside a frosted panel they would be clipped by it.
7. To work with files from the Explorer:
   - Read the selected item with `useWorkspace().selected`.
   - Accept "open in this tool" requests with `useToolRequest('<tool id>', path => …)`.
   - Add a matching entry to the file context menu in `src/browser/FileBrowser.tsx`.

Calls from JS run on pywebview worker threads, so slow work won't freeze the window. Show a busy state in the UI while you wait.

## Brand

- **Name.** Tiles, as in the mosaic mark, and a press, as in printing: many small tools that make one whole. The app was called Tessera until 0.2.0; that name was already taken.
- **Tagline.** "PDF and image tools that run on your own computer." Lead with what the app does and that files stay on the PC.
- **Mark.** A "T" laid from five white tiles on a rounded gradient square. From 32 px up, the four empty cells of the 3 × 3 grid show faintly. Use it as is: don't recolour the tiles, add effects, or set it on a busy background.
- **Wordmark.** "Tilepress" in Segoe UI Variable Display, bold, next to the mark (as in the app header).
- **Colour.** The aurora gradient, `#7c6cff` → `#4f8bff` → `#36c5ef` (violet, blue, cyan) at 135°, is `--accent-grad` in `src/index.css`. Ink is `#090c18` (dark theme background).
- **Where the name lives.** `APP_NAME` / `TAGLINE` in `backend/toolbox/__init__.py` (window title, exe name, data folder, About box) and `frontend/src/brand.ts` (UI). A data folder left by an older name (`Tessera`, or `Toolbox` before that) moves across on first start (`LEGACY_DATA_DIRS` in `backend/toolbox/paths.py`). The Python package and internal identifiers (`toolbox`, `TOOLBOX_*` test variables, drag-and-drop types, storage keys) keep the old name on purpose: renaming them would only break saved state.
- **Logo files** are generated: edit `scripts/make_brand.py`, then run `.venv\Scripts\python scripts\make_brand.py`.

## Runtime notes

- Everything is stored under `%LOCALAPPDATA%\Tilepress\`. A folder left by a build from when the app was called Toolbox (`%LOCALAPPDATA%\Toolbox\`) is moved there on first start:
  - `settings.json`: pins and preferences.
  - `history.db` (with `-wal` and `-shm` while the app runs): the activity history.
  - `toolbox.log`: the log.
  - `webview\`: WebView storage.
  - `tectonic\`: the LaTeX engine (see below).
  - `latex\untitled-N\`: new LaTeX documents until you **Save as** somewhere else.
  - `models\`: the AI models, once downloaded.
- **Activity history.** Every tool run is recorded in `history.db`: the tool, its input and output files (paths and sizes), when it ran, how long it took, and the error if it failed. Tool options are never stored, so passwords given to Protect, Unlock or Sign don't reach the disk. The **History** button in the top bar lists it, newest first, with search, Open / Show in folder, and a way to remove entries or clear everything. Untick **Keep history** there to stop recording. The newest 5,000 runs are kept. It's SQLite in WAL mode, so two open copies of the app can write to it at once, and a problem with the database never fails a tool: recording just stops for that session. Code: `backend/toolbox/services/history.py`, the `@_records` decorator in `api.py`, and `frontend/src/components/HistoryPanel.tsx`.
- **First launch: LaTeX engine download.** If no LaTeX engine is installed (Tectonic, or a MiKTeX/TeX Live pdfLaTeX, XeLaTeX or LuaLaTeX), the app downloads Tectonic 0.15.0 from its GitHub release in the background (a 19 MB download), checks its SHA-256 checksum, and compiles a small document once so the common LaTeX packages are cached (about 12 MB more, from Tectonic's package server, kept in `%LOCALAPPDATA%\TectonicProject`). This takes about two minutes and only happens once. The status bar shows progress; the rest of the app works meanwhile. If it fails (for example, offline), the status panel and the LaTeX editor offer to try again. Tectonic fetches any other package the first time a document uses it.
- **AI models, on first use.** Nothing is downloaded until you use an AI tool. The first time, Upscale downloads Real-ESRGAN General x4v3 (4.5 MB, BSD-3, from Qualcomm AI Hub) and Remove background downloads ISNet general-use (179 MB, Apache-2.0, from the rembg project's GitHub release), with a progress bar. Each is checked against its SHA-256 checksum before use (a mismatch is discarded) and kept for next time. After that the tools work offline, and images never leave the computer. They run on the graphics card through DirectML when possible, otherwise on the CPU. Blur face needs no download.
- **HTML to Image** renders in an off-screen window (out of sight and out of the taskbar), because Chromium only draws, and can only screenshot, a window that has been shown.
- Printers: a network printer that is off or unreachable can take half a minute to tell Windows what it supports. The Print screen lists it straight away, marked "(checking…)", and fills in two-sided, colour and paper sizes when the answer arrives; the rest of the app isn't slowed down meanwhile.
- OCR uses Tesseract if it's installed (`C:\Program Files\Tesseract-OCR`), with whichever languages it has. Otherwise it uses Windows OCR, which supports the languages installed in Windows Settings → Time & language → Language (those with "Optical character recognition").
- The built UI is served from `127.0.0.1:47821`. A fixed port keeps `localStorage` between launches. pywebview's shared default port (42001) isn't used, because other pywebview apps that keep storage use it too, and on Windows two apps on the same port can end up showing each other's pages. If 47821 is already taken, the app uses a random free port for that session.
- WebView2 is preinstalled on Windows 11 and current Windows 10. For older machines, ship Microsoft's [Evergreen bootstrapper](https://developer.microsoft.com/microsoft-edge/webview2/).

## Website and screenshots

The website and user documentation have their own repository, [epicabdou/tilepress-website](https://github.com/epicabdou/tilepress-website) (VitePress). It's still served at <https://epicabdou.github.io/tilepress/>: its workflow publishes each build to this repo's `gh-pages` branch, which GitHub Pages serves. Leave that branch alone; every publish replaces it.

The screenshots are real: `scripts/screenshots.py` generates fictional demo files, runs the built UI against the real Python backend through a small local bridge, and captures it with headless Microsoft Edge. Browsing is confined to the demo folder, and the app's data folder is a temporary one, so nothing personal can appear. It writes them into the website repo, cloned next to this one (`..	ilepress-website`, or pass `--site <folder>`). After a UI change:

```powershell
cd frontend; npm run build; cd ..
.venv\Scripts\python scripts\screenshots.py            # or name scenes: merge history
```

## Contributing

Bug reports, ideas and pull requests are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). Please report security problems privately, as described in [SECURITY.md](SECURITY.md).

## License

Copyright (C) 2026 epicabdou.

Tilepress is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. It is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY. See [LICENSE](LICENSE) for the full text.

Tilepress bundles and downloads third-party components under their own licenses: see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). iLovePDF and iLoveIMG are trademarks of their respective owners; Tilepress is not affiliated with them.
