---
title: Convert from PDF
description: Turn a PDF into a Word document, a PowerPoint presentation, an Excel workbook, images or Markdown.
---

# Convert from PDF

These tools turn a PDF into something you can edit or reuse: a Word document, a PowerPoint presentation, an Excel workbook, image files or a Markdown file. They never change the PDF itself.

Each tool starts with **Choose a PDF to work on**. Click **Open PDF…**, click **Use** followed by the file name to take the PDF selected in the Explorer, or drag a PDF from the Explorer onto the tool. You can also right-click a PDF in the Explorer and choose **Convert from PDF**, which opens it in the conversion tool you used last. The bar above the tool shows the file's name, page count and size, with **Change…** and **Close**. See [The Tilepress window](/docs/interface) for the Explorer and the other general controls.

The open PDF is shared with most of the other PDF tools, so you can switch between them without opening it again. While a conversion runs, a progress bar shows how far it has got. When it finishes, a **Saved** card lists the new file with **Open** and **Show in folder**. When PDF to JPG makes a single picture, **Keep editing this file** opens it in the [Photo editor](/docs/img-edit#photo-editor).

::: tip Page ranges
Where a tool has a **Pages** field, leave it empty for every page, or type pages and ranges separated by commas: `1-3, 5, 8-`. `8-` means page 8 to the end and `-4` means pages 1 to 4. You can also type `odd`, `even` or `all`.
:::

## PDF to Word

Turns a PDF into an editable Word document. Use it when you need to change the text of a document you only have as a PDF.

### How to use it

1. Open a PDF.
2. Pick a **Converter** and a **Format**.
3. Click **Convert to Word…**.
4. Choose where to save the document in the Save dialog.

### Options

| Option | What it does | Default |
|---|---|---|
| **Converter** | **Microsoft Word (keeps the layout)** uses Word's own PDF import. **Built-in (text, headings, lists, tables)** rebuilds the text and its structure without Word. | Microsoft Word when it's installed, otherwise Built-in |
| **Format** | **Word document (.docx)** or **Word 97–2003 (.doc)**. The `.doc` format needs Microsoft Word, so it can't be picked with the built-in converter. | Word document (.docx) |

### Good to know

- The **Microsoft Word** choice only appears when Word is installed. Word runs hidden in the background with macros disabled and opens the PDF read-only. Word reflows the PDF into an editable document, so complex layouts may shift a little.
- The built-in converter keeps the text and its structure only: headings (guessed from font size and bold text, up to four levels), paragraphs, bulleted and numbered lists, and tables. Images and exact positions are not kept. Each PDF page ends with a page break.
- The Save dialog suggests the PDF's name with `.docx` (or `.doc`) in the same folder. If that name is taken, it adds a number, as in `report (2).docx`.
- Scanned PDFs have no text to convert. Run [OCR PDF](/docs/edit) on them first.

## PDF to PowerPoint

Makes a presentation with one slide per page. Each slide shows its page exactly, as a picture, and the page's text can go into the speaker notes.

### How to use it

1. Open a PDF.
2. Choose the **Slide image quality**, and whether to put each page's text into the notes.
3. Click **Convert to PowerPoint…**.
4. Choose where to save the presentation.

### Options

| Option | What it does | Default |
|---|---|---|
| **Slide image quality** | How sharp the page pictures are: **Smaller file** (110 dpi), **Standard** (150 dpi) or **High (large screens, printing)** (220 dpi). Higher quality makes a bigger file. | Standard |
| **Put each page's text into the slide notes** | Copies the text of each page into that slide's speaker notes. | On |

### Good to know

- The slides take the size and shape of the first page. Pages with a different shape are fitted inside the slide and centred.
- Very large pages are scaled down to PowerPoint's maximum slide size (56 inches).
- The slides are pictures, so you can't edit the page text on the slide itself. Use the notes, or [PDF to Word](#pdf-to-word), to get at the text.
- The Save dialog suggests the PDF's name with `.pptx` in the same folder.
- Microsoft PowerPoint is not needed.

## PDF to Excel

Finds the tables in a PDF and puts each one on its own sheet. Numbers, percentages and amounts become real numbers you can calculate with.

### How to use it

1. Open a PDF.
2. Type the **Pages** to search, or leave the field empty for all of them.
3. Choose how to **Find tables by**.
4. Click **Convert to Excel…**.
5. Choose where to save the workbook.

### Options

| Option | What it does | Default |
|---|---|---|
| **Pages** | The pages to look for tables on. | All pages |
| **Find tables by** | **Ruled lines (grid tables)** finds tables drawn with lines. **Aligned text (tables without lines)** finds columns of text that line up. **Automatic** looks for ruled tables first, and on a page that has none, looks for aligned text. | Automatic |

### Good to know

- Each table gets its own sheet, named after its page: `Page 3`, or `Page 3 (1)`, `Page 3 (2)` when a page has several tables.
- The first row of each sheet is bold and frozen, and the columns are sized to their content.
- Cells that look like numbers are stored as numbers. This includes thousands separators in both styles (`1,234.50` and `1.234,50`), currency signs ($, €, £, ¥), negative amounts in brackets (`(12)` becomes -12) and percentages (`15%` becomes 0.15).
- If no tables are found on the chosen pages, nothing is saved and the tool tells you so. Try the other **Find tables by** settings.
- Scanned PDFs have no text to find. Run [OCR PDF](/docs/edit) on them first.
- The Save dialog suggests the PDF's name with `.xlsx` in the same folder. Microsoft Excel is not needed.

## PDF to JPG

Saves pages as image files, or pulls out the pictures embedded in the PDF.

### How to use it

1. Open a PDF.
2. Choose **Pages as images** or **Extract embedded images** at the top.
3. Set the options, and choose where to save: **Save next to each PDF** or **Save in a folder** (click **Choose…** to pick the folder).
4. Click **Save images** (or **Extract images**).

There is no Save dialog: the files go straight to the place you chose, and the **Saved** card lists them.

### Options

| Option | What it does | Default |
|---|---|---|
| **Pages as images** / **Extract embedded images** | Draw each page as a picture, or save the pictures that are inside the pages. | Pages as images |
| **Pages** | The pages to save or to take pictures from. | All pages |
| **Format** | **JPG** or **PNG (lossless)**. Pages as images only. | JPG |
| **Resolution** | 72, 96, 150, 220, 300 or 600 dpi. The size in pixels of the first page is shown underneath. Pages as images only. | 150 dpi |
| **JPG quality** | 40 to 100. Higher keeps more detail and makes bigger files. JPG only. | 90 |
| **Save next to each PDF** / **Save in a folder** | Where the images go. | Next to the PDF |

### Good to know

- Pages are named after the PDF and the page number: `report_p1.jpg`, `report_p2.jpg` and so on. Extracted pictures add a number for each picture on the page: `report_p3_1.jpg`, `report_p3_2.png`.
- Existing files are never overwritten: a number is added instead, as in `report_p1 (2).jpg`.
- Extracted pictures keep their original size and the format they are stored in, so you may get a mix of file types. A picture that appears on several pages, such as a logo, is saved once for each page.
- If the chosen pages have no embedded pictures, the tool tells you and saves nothing.
- In [History](/docs/history), runs that saved PNG files are listed as "PDF to PNG".

## PDF to Markdown

Turns the PDF's text and structure into Markdown: headings, paragraphs, lists and tables. A preview shows the result before you save.

### How to use it

1. Open a PDF.
2. Type the **Pages** to convert, or leave the field empty for all of them.
3. Check the preview below the options. Tick **Show Markdown source** to see the raw Markdown instead of the rendered page.
4. Click **Save as Markdown…** and choose where to save the file.

### Options

| Option | What it does | Default |
|---|---|---|
| **Pages** | The pages to convert. | All pages |
| **Mark page breaks with comments** | Adds a line such as `<!-- page 2 -->` where each new page starts. These comments don't show when the Markdown is displayed. | Off |
| **Show Markdown source** | Switches the preview between the rendered result and the Markdown text. It doesn't change the saved file. | Off |

### Good to know

- The preview shows the first five of the chosen pages, to stay quick. The saved file contains every chosen page.
- Headings are guessed from font size and bold text, and get up to four levels (`#` to `####`). Numbered lists are renumbered from 1. Tables become Markdown tables.
- Images are not included.
- Scanned PDFs have no text to convert. Run [OCR PDF](/docs/edit) on them first.
- The Save dialog suggests the PDF's name with `.md` in the same folder.

::: warning Password-protected PDFs
These tools can't open a PDF that needs a password. Unlock a copy with [Protect PDF](/docs/security) first.
:::
