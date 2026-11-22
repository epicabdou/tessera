---
title: "Privacy: what stays on your PC"
description: When Tessera uses the internet, what it never sends, and every file it keeps on your PC.
---

# Privacy: what stays on your PC

Tessera works on your files on your own PC. It never uploads them, needs no account, and has no telemetry, analytics, crash reporting, ads or automatic update check. This page lists every time Tessera uses the internet and everything it stores. The list comes from the source code, which you can check yourself on [GitHub](https://github.com/epicabdou/tessera).

## When Tessera uses the internet

Apart from the cases below, no tool makes a network request. Everything else works offline.

### The LaTeX engine, once

If no LaTeX engine is installed on your PC, Tessera downloads one in the background when it starts:

- **What:** Tectonic 0.15.0 for Windows, about 19 MB, from the Tectonic project's release page on `github.com`.
- **Check:** the file must match a SHA-256 checksum built into Tessera, or it's thrown away.
- **Sent:** an ordinary download request that identifies the client only as `Tessera-desktop`.
- **When:** on start-up, until the setup has succeeded once. If it fails, Tessera tries again at the next start, or when you click **Retry LaTeX setup**.

Tessera then compiles a small test document so that Tectonic downloads the LaTeX packages most documents need (about 12 MB). Later, the first time one of your documents uses a package Tectonic doesn't have yet, Tectonic downloads that package too. These downloads come from Tectonic's own package server. Tectonic fetches the package files it needs; it doesn't send your document.

If you use a LaTeX engine you installed yourself, such as MiKTeX or TeX Live, Tessera downloads nothing, and that engine follows its own settings.

### AI models, the first time you use them

Two AI tools need a model file. Each is downloaded the first time you run its tool, and the tool tells you beforehand.

| Tool | Model | Size | Licence | Downloaded from |
|---|---|---|---|---|
| Upscale Image | Real-ESRGAN General x4v3 | 4.5 MB | BSD-3-Clause | Qualcomm AI Hub (`qaihub-public-assets.s3.us-west-2.amazonaws.com`) |
| Remove background | ISNet (general use) | 179 MB | Apache-2.0 | The rembg project's release on `github.com` |

Each download is checked against a SHA-256 checksum built into Tessera; a file that doesn't match is thrown away. The request identifies the client only as `Tessera-desktop`. After that the model is kept on your PC and the tool works offline. **Your images are never sent anywhere.** The models run on your graphics card or processor.

Blur face downloads nothing: it uses the face detector built into Windows.

### Web pages you ask for

**HTML to PDF** and **HTML to Image** can take a web address. Tessera then opens that page in a hidden window, the way a browser would:

- The website sees an ordinary visit from your PC, and the page's scripts run.
- Only `http://` and `https://` addresses are accepted. If you type a bare address such as `example.com`, `https://` is added.
- Like any browser visit, the page can leave cookies and cached files. They're kept in Tessera's `webview` folder (see below).

### Online content in your own HTML or Markdown

An HTML file, pasted HTML code or a Markdown document can refer to pictures, fonts, style sheets or scripts on the internet. When Tessera shows or converts it, those are downloaded, just as a browser would. This applies to the live previews too. The previews don't run scripts, but they do load online pictures and styles while you type.

Pictures stored on your PC that a Markdown document uses are built into the page, with no network use.

### Printing to a network printer

Advanced Print sends the pages to the printer you choose, through Windows. If that's a network printer, the pages travel over your network to it, as with any other app.

### What doesn't use the network

- **OCR** runs on your PC, with Tesseract or with Windows OCR.
- **Face detection** uses the detector built into Windows.
- **Word, PowerPoint and Excel to PDF** use Microsoft Office or LibreOffice on your PC, and **PDF to Word** uses Microsoft Word or a built-in converter. Microsoft Office runs as a hidden, separate copy with macros turned off.
- **Signing** adds no time stamp from a server, and checking signatures doesn't download revocation lists.
- **Previews and thumbnails** are drawn on your PC.

Windows, the WebView2 runtime that draws Tessera's window, Microsoft Office and LibreOffice are separate software with their own privacy settings.

## The local web server

Tessera's interface is loaded from a small web server inside the app, at `127.0.0.1` port 47821 (or another free port if that one is taken). It listens only on `127.0.0.1`, so other computers can't reach it. A fixed port lets the window keep its saved choices between sessions.

## What Tessera keeps on your PC

Tessera keeps its data in one folder, `%LOCALAPPDATA%\Tessera\`:

| Item | What it is |
|---|---|
| `settings.json` | Your pinned folders, the last folder you opened, whether hidden items are shown, the panel widths, whether the Preview is open, and whether history is on. |
| `history.db` (and `history.db-wal`, `history.db-shm` while Tessera runs) | The [activity history](/docs/history): tool names, file paths and sizes, times and error messages. Never tool options or passwords. |
| `toolbox.log` | A log of start-ups, downloads and errors. Error messages can include file names. It stays on your PC. |
| `webview\` | The window's own browser storage. It holds a few choices made in tools (the LaTeX editor's recent files and **Live** setting, and the path of the last certificate used in Sign PDF, never its password), plus cookies and cached files from web pages you converted. |
| `tectonic\` | The LaTeX engine, if Tessera downloaded it. |
| `latex\untitled-1\`, `latex\untitled-2\`… | New LaTeX documents, until you save them somewhere else with **Save as**. |
| `models\` | The AI models, once downloaded. |

If you used an earlier build from when the app was called Toolbox, its `%LOCALAPPDATA%\Toolbox\` folder is moved to `%LOCALAPPDATA%\Tessera\` on first start.

Outside that folder:

- **Tectonic's package cache**, `%LOCALAPPDATA%\TectonicProject`, holds the LaTeX packages Tectonic has downloaded.
- **Temporary files** go to your Windows temporary folder while tools work, for example live previews and files being converted. Their names start with `toolbox-`. They're deleted when the work is done, or when Tessera closes.

Your own files are only ever read, never changed: every tool writes a new file, in the place you choose.

## Removing your data

- To clear the activity history, or stop recording it, see [History](/docs/history).
- Uninstalling Tessera keeps the data folder. To remove everything, delete `%LOCALAPPDATA%\Tessera` (and `%LOCALAPPDATA%\TectonicProject` if you like) after uninstalling, or while Tessera is closed.
