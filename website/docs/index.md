---
title: Getting started
description: What Tessera needs, how to install, update and remove it, and how to open a file in a tool.
---

# Getting started

Tessera is a Windows app with PDF and image tools. It works on the files on your own PC: nothing is uploaded. This page covers installing it, the first launch, and the ways to get a file into a tool.

## System requirements

- **Windows 10 or Windows 11, 64-bit.** The installer is for x64 PCs.
- **The Microsoft Edge WebView2 Runtime.** Tessera draws its window with it. It comes with Windows 11 and with up-to-date Windows 10. On an older PC that doesn't have it, install the Evergreen WebView2 Runtime from [Microsoft's WebView2 page](https://developer.microsoft.com/microsoft-edge/webview2/).
- **A screen with room for the window.** The window can't be made smaller than 980 × 600 pixels.
- **An internet connection only for a few things:** the one-time LaTeX engine download, each AI model the first time you use its tool, and web pages you ask a tool to load. Everything else works offline. See [Privacy](/docs/privacy) for the full list.

Some tools use other software when it's there:

| Tool | Uses | Without it |
|---|---|---|
| Word to PDF, PowerPoint to PDF, Excel to PDF | Microsoft Office, or LibreOffice | These three tools can't convert. Install either one, then restart Tessera. |
| PDF to Word | Microsoft Word, for the closest layout | A built-in converter is used. |
| OCR PDF | Tesseract OCR, if it's installed | Windows OCR is used, with the languages installed in Windows that include text recognition. |
| LaTeX editor | An installed LaTeX engine (Tectonic, or pdfLaTeX, XeLaTeX or LuaLaTeX from MiKTeX or TeX Live) | Tessera downloads Tectonic on first launch. |
| Upscale Image, Remove background | A graphics card, through DirectML | The models run on the processor instead. It's slower, but the result is the same. |

## Install Tessera

1. Download the installer (`.msi`) from the [Download](/download) page.
2. Double-click it. On the welcome page click **Next**, then **Install**.
3. On the last page, **Launch Tessera** is ticked. Click **Finish** to start Tessera.

The installer doesn't ask for administrator rights. It installs Tessera for your Windows account only, in `%LocalAppData%\Programs\Tessera`, and adds Tessera to the Start menu.

### Install for everyone on the PC

To install in Program Files for every user of the PC, open Command Prompt or Windows Terminal **as administrator**, go to the folder that holds the installer, and run:

```
msiexec /i Tessera-x64.msi ALLUSERS=1
```

Use the name of the file you downloaded if it's different.

## The first launch

Tessera opens with three panels: the **Explorer** on the left, the tools in the middle, and the **Preview** on the right. The Explorer starts in your home folder. After that it reopens the last folder you were in. [The Tessera window](/docs/interface) explains every part.

### The LaTeX engine downloads in the background

If no LaTeX engine is installed on your PC, Tessera sets one up the first time it starts:

1. It downloads Tectonic 0.15.0 (about 19 MB) and checks it against its known SHA-256 checksum. A file that doesn't match is thrown away.
2. It compiles a small test document once, so Tectonic downloads the LaTeX packages most documents need (about 12 MB more).

This takes about two minutes and happens only once. The status bar at the bottom of the middle panel shows the progress: **Downloading LaTeX engine…**, then **Installing LaTeX engine…** and **Fetching LaTeX packages…**. You can use every other tool in the meantime.

If the setup fails, for example because you're offline, the status bar shows **LaTeX setup failed**. Click the status button in the top bar and choose **Retry LaTeX setup**, or just start Tessera again later: it tries again on every start until the setup succeeds.

Nothing else is downloaded at start-up. The AI tools download their model the first time you use them, and tell you so first.

## Open a file in a tool

First pick a tool. Choose **Documents** or **Images** at the left of the top bar, then a category tab, then the tool in the row underneath. Or press <kbd>Ctrl</kbd>+<kbd>K</kbd>, type part of the tool's name or what it does (for example *merge*, *sign* or *word*), and press <kbd>Enter</kbd>.

Then give the tool a file in any of these ways:

- **Select it in the Explorer.** When the selected file suits the open tool, the tool shows a **Use** button with the file's name. Click it.
- **Drag it from the Explorer** onto the tool. Dragging works from Tessera's own Explorer pane; files dragged in from Windows File Explorer aren't picked up.
- **Right-click it in the Explorer** and choose a tool from the menu (see the table below).
- **Use the buttons in the Preview pane.** A PDF has **PDF tools**, an image has **Edit photo**, and a file that can be converted has **Convert to PDF**.
- **Use the tool's own button**, such as **Open PDF…**, **Open image…**, **Add PDFs…** or **Add images…**, to pick a file in a Windows file dialog.

The right-click menu offers these tools:

| File | Menu entries |
|---|---|
| PDF | **Open in PDF tools**, **Add to Merge PDF**, **Edit PDF**, **Convert from PDF**, **Sign PDF**, **Protect PDF**, **Print…** |
| Image (JPG, PNG, WebP, HEIC, HEIF, AVIF, GIF, BMP, TIFF, ICO) | **Edit photo**, **Compress image**, **Resize image**, **Crop image**, **Remove background**, **Upscale image**, and **Convert to PDF** for JPG, PNG, GIF, BMP, TIFF and WebP |
| Word, PowerPoint, Excel, CSV, HTML, Markdown | **Convert to PDF** (it picks the matching tool) |
| `.tex` | **Open in LaTeX editor** |

**Open in PDF tools** opens the PDF in the page tool you used last (Organize PDF if that was Merge PDF). **Convert from PDF** opens it in the From PDF tool you used last.

::: tip One open PDF, one open image
The tools that work on a single PDF share it. Open a file in Split PDF, switch to Watermark PDF or Sign PDF, and the same file is already open. Merge PDF keeps its own list, and Protect PDF and Repair PDF keep their own file. In the same way, Crop Image, the AI tools and the Photo editor share one open image, while the batch image tools each keep their own list.
:::

Every tool saves a **new** file and leaves the original alone. See [The Tessera window](/docs/interface) for the **Saved** card that appears afterwards.

## Update Tessera

Download the newer installer and run it. It replaces the installed version and keeps your pins, settings, history and downloaded models. Close Tessera before you install the update.

An older installer won't install over a newer version. It stops with the message "A newer version of Tessera is already installed."

## Uninstall Tessera

Open **Settings** > **Apps** > **Installed apps**, find **Tessera**, and choose **Uninstall**. You can also run `msiexec /x` with the installer file.

Uninstalling removes the program but keeps your data in `%LOCALAPPDATA%\Tessera`: settings, pins, history, the log, the LaTeX engine and the AI models. To remove those too, delete that folder after uninstalling. Tectonic keeps its downloaded LaTeX packages in `%LOCALAPPDATA%\TectonicProject`, which you can delete as well. [Privacy](/docs/privacy) lists what each item in the data folder is.

## The tools

Documents:

- [Combine, split & pages](/docs/pdf-pages): Merge PDF, Split PDF, Organize PDF, Rotate PDF, Crop PDF, Page numbers
- [Convert to PDF](/docs/to-pdf): Word, PowerPoint, Excel, images, HTML and Markdown to PDF
- [Convert from PDF](/docs/from-pdf): PDF to Word, PowerPoint, Excel, JPG and Markdown
- [Edit, forms & OCR](/docs/edit): Edit PDF, OCR PDF, PDF Forms, Watermark PDF
- [Security, signing & size](/docs/security): Protect PDF, Sign PDF, Compress PDF, Repair PDF
- [Printing](/docs/print): Advanced Print
- [LaTeX](/docs/latex): the LaTeX editor

Images:

- [Format & size](/docs/img-optimize): Compress Image, Resize Image, Convert to JPG, Convert from JPG
- [Crop, rotate & capture](/docs/img-layout): Crop Image, Rotate Image, HTML to Image
- [AI enhancements](/docs/img-ai): Upscale Image, Remove background, Blur face
- [Edit & brand](/docs/img-edit): Photo editor, Watermark Image

Something not working? See [Support](/support).
