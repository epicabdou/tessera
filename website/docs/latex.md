---
title: LaTeX
description: Write LaTeX documents with highlighting, completion and a PDF preview that updates as you type.
---

# LaTeX

The LaTeX category has one tool, the LaTeX editor. You write the source on the left and see the compiled PDF on the right. Errors and warnings are listed with their line, and clicking one takes you there.

Start a new document from a template, click **Open .tex file…**, or right-click a `.tex` file in the Explorer and choose **Open in LaTeX editor**. See [The Tilepress window](/docs/interface) for the Explorer and the other general controls.

## LaTeX editor

A LaTeX editor with syntax highlighting, command completion, snippets and a live PDF preview. It compiles with Tectonic, which Tilepress sets up on first launch, or with a LaTeX distribution you already have.

### How to use it

1. On the start screen, under **New document**, click **Article**, **Report (chapters)**, **Presentation (Beamer)** or **Letter**. Or click **Open .tex file…**, or **Open** followed by the name of the `.tex` file selected in the Explorer. Files you opened recently are listed under **Recent**.
2. Type in the editor on the left. With **Live** ticked, the PDF on the right is rebuilt a moment after you stop typing. Otherwise click **Compile**.
3. If the panel under the editor lists errors, click one to jump to its line.
4. For a new document, click **Save as…** to keep it where you want it. For an existing file, click **Save** or press <kbd>Ctrl</kbd>+<kbd>S</kbd>.
5. Use **Open PDF** or **Show in folder** above the preview to get at the PDF.

### The toolbar

| Control | What it does |
|---|---|
| **New…** | Starts a new document from one of the four templates. |
| **Open…** | Opens a `.tex` file. |
| **Save** | Saves the document. A dot (**Save •**) means there are unsaved changes. On a new document it opens **Save as…**. |
| **Save as…** | Saves the document under a new name or in another folder, and goes on editing that copy. |
| **Insert…** | Inserts a snippet (see below). |
| **Image…** | Inserts a figure for a picture you choose (see below). |
| Document name | The file's name, or **Untitled** for a new document that hasn't been saved with **Save as…**. Hover to see the full path. |
| **Engine** | **Engine: automatic**, or one of the LaTeX engines found on your PC. |
| **Live** | Recompiles a moment after you stop typing. On by default; the app remembers your choice. |
| **Compile** | Compiles now. Disabled until a LaTeX engine is ready. |

### Templates

| Template | What you get |
|---|---|
| **Article** | An 11 pt article with amsmath, amssymb, graphicx and hyperref, 2.5 cm margins, a title and a sample equation. |
| **Report (chapters)** | An 11 pt report with a title page, a table of contents and two chapters. |
| **Presentation (Beamer)** | A Beamer presentation (Madrid theme) with a title slide and one slide with a list. |
| **Letter** | A letter with sender address, recipient, opening and closing. |

### Snippets

**Insert…** offers Section, Subsection, Bold, Italic, Bulleted list, Numbered list, Inline math, Equation, Aligned equations, Fraction, Table, Footnote, Link and Page break. The cursor lands where you type next. If you have text selected, the snippet goes round it: select a word and choose **Bold** to get `\textbf{word}`.

**Image…** asks for a picture (JPG, PNG, GIF, BMP, TIFF, WebP, PDF or EPS) and inserts a `figure` with `\includegraphics`, a caption and a label. The picture's path is written relative to the `.tex` file, with forward slashes. A picture on a different drive gets its full path. The figure needs the graphicx package, which the Article and Report templates already load.

::: tip Save before you add pictures
A new document lives in Tilepress's own folder until you use **Save as…**, so a relative picture path would point from there. Save the document where you want it first, then add pictures.
:::

### Completion and keyboard shortcuts

Type `\` and a few letters to see matching commands, such as `\section`, `\textbf`, `\includegraphics` or Greek letters. After `\begin{`, the list offers environments such as `itemize`, `equation`, `align`, `figure`, `table`, `tabular` and `frame`.

| Keys | Action |
|---|---|
| <kbd>Ctrl</kbd>+<kbd>S</kbd> | Save (Save as for a new document) |
| <kbd>Ctrl</kbd>+<kbd>Enter</kbd> | Compile |
| <kbd>Ctrl</kbd>+<kbd>Space</kbd> | Show the completion list after a `\` |
| <kbd>Tab</kbd> / <kbd>Shift</kbd>+<kbd>Tab</kbd> | Indent / unindent the line or selection |
| <kbd>Ctrl</kbd>+<kbd>F</kbd> | Find and replace in the source |
| <kbd>Ctrl</kbd>+<kbd>Z</kbd> / <kbd>Ctrl</kbd>+<kbd>Y</kbd> | Undo / redo |

### Errors, warnings and the log

The panel under the editor says how the last compile went, for example "Compiled with tectonic in 1.4 s" or "Compilation failed", and counts the errors and warnings. Click an error or warning that has a line number to select that line in the editor. Click **Show log** to read the engine's full output, and **Hide log** to go back to the list.

When a compile fails, the preview keeps the last PDF that worked and says "showing the last good version".

### LaTeX engines

With **Engine: automatic**, the editor uses the first engine it finds, in this order: Tectonic, latexmk, pdfLaTeX, XeLaTeX, LuaLaTeX. Choose an engine from the **Engine** list to use a particular one. The list shows the program names: `tectonic`, `latexmk`, `pdflatex`, `xelatex`, `lualatex`.

Tilepress finds engines that are on your PATH, MiKTeX in its standard folders (in `%LOCALAPPDATA%\Programs\MiKTeX` or `Program Files\MiKTeX`), TeX Live under `C:\texlive`, and its own copy of Tectonic.

**First launch.** If no engine is found when Tilepress starts, it downloads Tectonic 0.15.0 (about 19 MB) from Tectonic's GitHub releases in the background, checks the download against its SHA-256 checksum, and installs it in `%LOCALAPPDATA%\Tilepress\tectonic`. It then compiles a small test document once, so Tectonic downloads the packages most documents need (fonts, amsmath, amssymb, graphicx, hyperref). This takes a few minutes and happens only once. The rest of the app works meanwhile, and the editor shows a banner with the progress:

- "Downloading the LaTeX engine (Tectonic)…" with a percentage
- "Installing the LaTeX engine…"
- "Downloading the standard LaTeX packages (first run only, a few minutes)…"

If setup fails, for example because you're offline, the banner says "LaTeX setup failed" with the reason and a **Try again** button. The status panel in the top bar offers **Retry LaTeX setup** too, and Tilepress tries again the next time it starts. If you already have MiKTeX or TeX Live installed, nothing is downloaded. If Tectonic is already on your `PATH`, Tilepress uses that copy and only runs the one-time package download. If no engine is installed and setup hasn't started, the banner says so and offers **Install now**.

Tectonic downloads any other package the first time a document uses it, so a document with new packages needs an internet connection the first time you compile it. See [Privacy](/docs/privacy).

### Good to know

- **Compiling saves first.** Every compile, including Live ones, writes the source to the `.tex` file before compiling it.
- **Where the PDF goes.** The PDF is written next to the `.tex` file with the same name: `thesis.tex` makes `thesis.pdf`. A PDF of that name is replaced. The log and other working files go in a `.toolbox-build` folder next to the `.tex` file.
- **New documents** are created as `main.tex` in `%LOCALAPPDATA%\Tilepress\latex\untitled-1` (then `untitled-2` and so on), and their PDF is written there too. **Save as…** suggests `document.tex` in your Documents folder. After that you're editing the saved copy, and the untitled folder stays where it was.
- pdfLaTeX, XeLaTeX and LuaLaTeX are run a second time when the log asks for it, so cross-references and the table of contents come out right.
- A compile that takes longer than 5 minutes is stopped.
- The document compiles once when you open it, if an engine is ready.
- If you edit while a compile is running, one more compile follows when it finishes.
- **Recent** lists the last eight `.tex` files you opened or saved.
- LaTeX compiles are not recorded in [History](/docs/history).
