---
title: Convert to PDF
description: Turn Word, PowerPoint and Excel files, images, web pages, HTML and Markdown into PDF files.
---

# Convert to PDF

These tools turn other kinds of files into PDFs: Office documents, images, web pages and HTML, and Markdown. You can add a file with the tool's own buttons, drag it in from the Explorer, right-click it in the Explorer and choose **Convert to PDF**, or select it and use the **Convert to PDF** button in the Preview panel. Each of these opens the right tool for the file type. See [The Tessera window](/docs/interface) for the controls all tools share.

Tessera never overwrites a file without asking. When a tool saves next to the original or in a folder you chose, and a file with that name already exists, it adds a number, for example `report (2).pdf`. When a tool shows a Save dialog, Windows asks before replacing a file. Every conversion is listed in [History](/docs/history).

## Word to PDF

Converts Word documents to PDF using Microsoft Word or LibreOffice. Use it for one document or a whole batch.

### How to use it

1. Click **Add word documents…** and pick one or more files. You can also drag files from the Explorer onto the list, or select a document in the Explorer and click **Add** followed by its name.
2. Check the line under the title. It says which app will do the conversion, for example **Converts with Microsoft Word**.
3. Set the options in the **Options** card.
4. Choose where to save: **Save next to each document**, or **Save in a folder** and then **Choose…**.
5. Click **Convert to PDF** (with several files, the button says **Convert 3 to PDF**, and so on).

Each row shows **Ready**, then **Converting…**, then the new file's name, page count and size, with **Open** and **Show in folder** buttons. If a file fails, its row shows the reason and the others carry on.

### Options

| Option | What it does | Default |
|---|---|---|
| Create bookmarks from headings | Adds a PDF bookmark for each heading in the document. | On |
| Include comments and tracked changes | Shows comments and tracked changes in the PDF, as Word displays them. | Off |
| Optimise for | **Printing (best quality)** or **Screen (smaller file)**. | Printing (best quality) |
| PDF/A (for long-term archiving) | Makes a PDF/A file, a PDF format meant for archives. | Off |
| Where to save | **Save next to each document** or **Save in a folder**. | Save next to each document |

When both Microsoft Word and LibreOffice are installed, the engine line becomes a list where you can choose **Microsoft Word (best)** or **LibreOffice**.

### Good to know

- Accepts DOC, DOCX, DOCM, DOT, DOTX, DOTM, RTF and ODT files.
- The PDF has the same name as the document, with `.pdf` at the end.
- The options in the table apply to Microsoft Word only. With LibreOffice, the tool says so and LibreOffice uses its own settings.
- See [Office conversions](#office-conversions) below for how Word and LibreOffice are found and run.

## PowerPoint to PDF

Converts presentations to PDF using Microsoft PowerPoint or LibreOffice. You can export the slides, the notes pages or handouts.

### How to use it

1. Click **Add powerpoint presentations…**, drag presentations from the Explorer onto the list, or select one in the Explorer and click **Add** followed by its name.
2. Check which app the line under the title names (**Converts with Microsoft PowerPoint** or **Converts with LibreOffice**).
3. Pick a **Layout** and the other options in the **Options** card.
4. Choose **Save next to each presentation** or **Save in a folder**.
5. Click **Convert to PDF**.

### Options

| Option | What it does | Default |
|---|---|---|
| Layout | **Slides**, **Notes pages**, or **Handouts, 2 per page**, **Handouts, 3 per page** or **Handouts, 6 per page**. | Slides |
| Include hidden slides | Also exports slides that are hidden in the presentation. | Off |
| Frame slides | Draws a thin frame around each slide. | Off |
| Optimise for | **Printing (best quality)** or **Screen (smaller file)**. | Printing (best quality) |
| PDF/A (for long-term archiving) | Makes a PDF/A file. | Off |
| Where to save | **Save next to each presentation** or **Save in a folder**. | Save next to each presentation |

### Good to know

- Accepts PPT, PPTX, PPTM, PPS, PPSX, POT, POTX and ODP files.
- The PDF has the same name as the presentation, with `.pdf` at the end.
- Layout and the other options apply to Microsoft PowerPoint only. LibreOffice exports the slides with its own settings.

## Excel to PDF

Converts spreadsheets to PDF using Microsoft Excel or LibreOffice. You can export the whole workbook or only the active sheet.

### How to use it

1. Click **Add excel spreadsheets…**, drag spreadsheets from the Explorer onto the list, or select one in the Explorer and click **Add** followed by its name.
2. Check which app the line under the title names.
3. Set **Sheets** and the other options in the **Options** card.
4. Choose **Save next to each spreadsheet** or **Save in a folder**.
5. Click **Convert to PDF**.

### Options

| Option | What it does | Default |
|---|---|---|
| Sheets | **Whole workbook**, or **Active sheet only** (the sheet that was open when the file was last saved). | Whole workbook |
| Fit each sheet to one page wide | Scales each sheet so its columns fit across one page. Long sheets still run over several pages. | On |
| Landscape pages | Turns every sheet's pages to landscape. | Off |
| Use print areas set in the workbook | Exports only the print areas the workbook defines. Untick it to export everything. | On |
| Optimise for | **Printing (best quality)** or **Screen (smaller file)**. | Printing (best quality) |
| PDF/A (for long-term archiving) | Makes a PDF/A file. | Off |
| Where to save | **Save next to each spreadsheet** or **Save in a folder**. | Save next to each spreadsheet |

### Good to know

- Accepts XLS, XLSX, XLSM, XLSB, XLTX, XLTM, ODS and CSV files.
- The PDF has the same name as the spreadsheet, with `.pdf` at the end.
- The page setup changes (fit to width, landscape) are made to a read-only copy that Excel has open. Your spreadsheet isn't changed.
- Links to other workbooks aren't updated during the conversion.
- The options apply to Microsoft Excel only. LibreOffice uses its own settings.

### Office conversions

These points apply to Word to PDF, PowerPoint to PDF and Excel to PDF.

- **You need Microsoft Office or LibreOffice.** Tessera checks for each Office app separately (Word, Excel, PowerPoint), so you can have one and not the others. It finds LibreOffice on your `PATH` or in `Program Files\LibreOffice`.
- **Which one is used.** Microsoft Office is used when it's installed, because its output is closest to the original. Otherwise LibreOffice is used. If both are installed, you can switch in the list under the title.
- **If neither is installed**, the tool shows a message and the convert button stays disabled. Tessera looks for these apps when it starts, so after installing one, close and reopen Tessera.
- **Your documents are safe.** Files are opened read-only, and macros are turned off before a file is opened. Office runs invisibly as its own copy, so documents you have open aren't touched, and Tessera only closes the copy it started. LibreOffice runs with a separate, temporary profile, so it works even while you have LibreOffice open.
- **One at a time.** Files convert one after another. If you click the button again, files that already converted are skipped, and files that failed are tried again.
- **Password-protected** Word and Excel files fail with an error instead of asking for the password.
- **Time limit.** LibreOffice gets 5 minutes per file and is stopped after that.

## JPG to PDF

Turns images into PDF pages: one PDF with all the images in order, or one PDF per image. JPEG photos keep their exact quality, and other formats are stored without loss.

### How to use it

1. Click **Add images…**, drag images from the Explorer onto the list, or select one in the Explorer and click **Add** followed by its name.
2. Put the images in order. Drag rows up or down, use the **Move up** and **Move down** buttons, or click **Sort A–Z** to sort by file name.
3. Turn any image that's on its side with **Rotate left** or **Rotate right**. Remove one with the **×** button.
4. Set up the pages in the **Page setup** card. The small page next to each image shows how it will sit on its page.
5. Choose **One PDF with all images** or **One PDF per image**.
6. Click **Convert and save…** and choose a name and folder. With **One PDF per image**, the button says **Convert each to PDF** and saves without asking, next to each image or in the folder you chose.

When it's done, a **Saved** card appears with **Open** and **Show in folder**. For a single PDF, **Keep editing this file** opens it in the page tools (see [Combine, split & pages](/docs/pdf-pages)).

### Options

| Option | What it does | Default |
|---|---|---|
| Page size | **Same as image**, **A4**, **Letter**, **Legal**, **A3** or **A5**. **Same as image** makes each page exactly the size of its image (plus the margin). | A4 |
| Orientation | **Match each image** (landscape pages for wide images, portrait for tall ones), **Portrait** or **Landscape**. Not available with **Same as image**. | Match each image |
| Margin | **None**, **Small (10 mm)** or **Large (20 mm)**. | Small (10 mm) |
| Image | **Fit whole image** shows all of it; **Fill page (crop edges)** fills the area inside the margin and cuts off what doesn't fit. Not available with **Same as image**. | Fit whole image |
| Output | **One PDF with all images** or **One PDF per image**. | One PDF with all images |
| Where to save (one PDF per image) | **Save next to each image** or **Save in a folder**. | Save next to each image |

### Good to know

- Accepts JPG, JPEG, JFIF, PNG, GIF, BMP, TIF, TIFF and WebP. To use a HEIC, AVIF or ICO picture, convert it to JPG first with [Convert to JPG](/docs/img-optimize).
- A multi-page TIFF becomes one page per frame. An animated GIF uses its first frame only.
- JPEG photos are normally copied into the PDF byte for byte, so there's no quality loss. PNG, GIF, BMP, TIFF and WebP are stored losslessly, and transparency is kept.
- Photos are placed upright, following the camera's rotation setting.
- With **Same as image**, the page size comes from the image's resolution (dpi) when the file records one, otherwise 96 dpi.
- The bar at the bottom counts the images and the pages they will make.
- For one PDF, the suggested name is the image's name with `.pdf`, or `images.pdf` in the first image's folder when there are several. For one PDF per image, each PDF has the image's name with `.pdf`.

## HTML to PDF

Prints a web page, an HTML file or HTML code that you paste or type to a PDF. It uses WebView2, the Chromium engine that also draws the Tessera window.

### How to use it

1. Choose the source at the top: **Web page**, **HTML file** or **HTML code**.
2. Give it the content:
   - **Web page:** type or paste the address, for example `example.com/article`.
   - **HTML file:** click **Choose file…**, drag an `.html` file from the Explorer, or click **Use** followed by the name of the file selected in the Explorer.
   - **HTML code:** type or paste HTML in the box. A preview appears beside it.
3. Set up the pages in the **Page setup** card.
4. Click **Convert and save…** and choose a name and folder. For a web page you can also press <kbd>Enter</kbd> in the address box.

When it's done, a **Saved** card appears with **Open**, **Show in folder** and **Keep editing this file**, which opens the PDF in the page tools.

### Options

| Option | What it does | Default |
|---|---|---|
| Page size | **A4**, **Letter**, **Legal**, **A3** or **A5**. | A4 |
| Orientation | **Portrait** or **Landscape**. | Portrait |
| Margins | **None**, **Narrow (6 mm)**, **Normal (12 mm)** or **Wide (25 mm)**. | Normal (12 mm) |
| Scale (%) | Makes the content smaller or larger on the page, from 10 to 200. | 100 |
| Wait after loading (s) | Extra seconds to wait after the page has loaded, from 0 to 30. Web page only. | 0 |
| Print background colours and images | Keeps the page's background colours and images. | On |
| Header and footer (title, date, page numbers) | Adds a header and footer to each page. | Off |
| Scroll through the page first, so lazy-loaded images appear | Scrolls down the whole page before printing, so images that load only when you scroll are included. Web page only. | On |

### Good to know

- **Web addresses:** if you leave out `https://`, it's added. Only `http://` and `https://` addresses work.
- **Logins:** the page loads in a hidden window, so a site that needs you to sign in prints as it looks to a signed-out visitor.
- **Waiting for the page:** Tessera waits up to 60 seconds for the page to load, then up to 15 more seconds for its fonts and images. If the page can't load, you see "The page couldn't be loaded. Check the address and your internet connection."
- **Files:** accepts `.html`, `.htm` and `.xhtml` files.
- **Pasted code:** you can paste a whole document or just a fragment; a fragment is wrapped in a page for you. Styles in `<style>` tags are kept. The preview beside the box doesn't run scripts, but the PDF is made from the full page. Links to local files by relative path don't work for pasted code, because it's printed from a temporary copy.
- **Header and footer:** for a web page or an HTML file, the footer shows the page's address. For pasted code, the header shows the PDF's file name instead of a temporary path.
- **Suggested name:** for a web page, the site and page name in your Downloads folder (for example `example.com-article.pdf`). For an HTML file, the file's name with `.pdf`, next to it. For pasted code, `page.pdf` in Downloads.
- **Your files:** the page being printed can't read other files on your PC through scripts.
- **Network use:** printing a web page downloads it, like opening it in a browser. HTML files and pasted code can also load pictures, fonts or scripts from the internet if they link to them. See [Privacy](/docs/privacy).

## Markdown to PDF

Turns a `.md` file, or Markdown you type, into a formatted PDF with tables, highlighted code and pictures. A live preview shows the result as you type.

### How to use it

1. Click **Open .md file…**, drag a `.md` file from the Explorer onto the editor, or click **Use** followed by the name of the Markdown file selected in the Explorer. You can also type in the editor straight away; it starts with a short example you can replace.
2. Edit the text if you like. The preview on the right updates a moment after you stop typing.
3. Pick a **Theme**.
4. Set up the pages in the **Page setup** card.
5. Click **Convert and save…** and choose a name and folder.

To start over with an empty editor after opening a file, click **New text**.

### Options

| Option | What it does | Default |
|---|---|---|
| Theme | **GitHub** (clean sans-serif), **Document (serif)** (justified text, centred title) or **Compact** (smaller text and spacing). | GitHub |
| Page size | **A4**, **Letter**, **Legal**, **A3** or **A5**. | A4 |
| Orientation | **Portrait** or **Landscape**. | Portrait |
| Margins | **None**, **Narrow (6 mm)**, **Normal (12 mm)** or **Wide (25 mm)**. | Wide (25 mm) |
| Scale (%) | Makes the content smaller or larger, from 10 to 200. | 100 |
| Print background colours and images | Keeps background colours, such as code block shading and table stripes. | On |
| Header and footer (title, date, page numbers) | Adds a header and footer to each page. The header shows the document's title. | Off |

### Good to know

- Accepts `.md` and `.markdown` files.
- Editing the text changes only the PDF. Your `.md` file isn't modified.
- Supported Markdown: standard CommonMark, plus tables and ~~strikethrough~~. Quotes and dashes are made typographic. HTML inside the Markdown is allowed.
- Code blocks are highlighted when you name the language after the opening fence, for example ` ```python `.
- **Pictures:** local images written as `![alt](picture.png)` are found relative to the `.md` file's folder (or by full path) and built into the PDF. Each can be up to 15 MB. When you type Markdown without opening a file, use full paths for local images. Images given as web addresses are downloaded from the internet, both for the preview and for the PDF.
- **Title:** the file's name, or for typed text the first `# Heading`. It's used in the header (when turned on) and for the suggested file name.
- **Suggested name:** next to the `.md` file with `.pdf`, or for typed text, the title with `.pdf` in your Downloads folder.
