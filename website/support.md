---
title: Support
description: Get help with Tessera, report a problem, suggest a feature, or help the project.
---

# Support

Tessera is a free, community project. Here's how to get help, and how to help in return.

## Get help

1. **Read the guide for your tool.** Every tool has a step-by-step page in the [documentation](/docs/), with its options and limits.
2. **Check the questions below**, and [troubleshooting](#troubleshooting).
3. **Ask the community** in [GitHub Discussions](https://github.com/epicabdou/tessera/discussions).
4. **Found a bug?** [Open an issue](https://github.com/epicabdou/tessera/issues/new/choose). The form asks for what you need to include.

## Questions

### Is Tessera really free?

Yes. It's free software under the GNU GPL v3: free to use for anything, at home or at work, with no account, ads, trial or premium tier. You may also change it and share it, as long as what you share stays under the same license.

### Are my files uploaded anywhere?

No. Tessera opens, changes and saves files on your own computer, and sends no telemetry. It only goes online when it has to fetch something you asked for: the LaTeX engine (once), an AI model the first time you use an AI tool, or a web page you give to HTML to PDF or HTML to Image. [Privacy, in detail](/docs/privacy)

### Is Tessera related to iLovePDF or iLoveIMG?

No. Tessera is an independent, open-source project. Its tools have familiar names so you can find your way, but it works entirely on your PC.

### Does it run on Mac or Linux?

Not yet: Tessera is a Windows 10 and 11 app. The code is on [GitHub](https://github.com/epicabdou/tessera) if you'd like to help port it.

### Do I need Microsoft Office?

Only for Word to PDF, Excel to PDF and PowerPoint to PDF, which need Microsoft Office or the free LibreOffice. Everything else, including PDF to Word, Excel and PowerPoint, works without it.

### Why does Windows warn me about the installer?

The installer isn't code-signed yet, so SmartScreen doesn't know it. Choose **More info → Run anyway**. You can [check the download's checksum](/download#install) first.

### Where are my settings and history?

In `%LOCALAPPDATA%\Tessera`: your settings, the [history](/docs/history), the LaTeX engine and any AI models you've downloaded. Uninstalling keeps this folder; delete it to start fresh.

### Why is the first LaTeX compile slow?

On first launch Tessera downloads its LaTeX engine (about 19 MB) and caches the common packages. That takes a couple of minutes, once. The rest of the app works meanwhile.

## Troubleshooting

### The window stays blank

Tessera draws its window with Microsoft Edge WebView2. Install the [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) and start Tessera again.

### Word, Excel or PowerPoint to PDF fails

These need Microsoft Office or LibreOffice installed. The status button at the top right (click **Ready**) shows which one Tessera found.

### OCR finds no text, or the wrong language

Choose the document's language in OCR PDF. Windows OCR only knows languages installed in **Settings → Time & language → Language** with "Optical character recognition"; installing Tesseract OCR adds many more.

### An AI tool can't download its model

The first use of Upscale Image or Remove background downloads a model (4.5 MB and 179 MB). Check your internet connection and try again; after that the tool works offline.

### My antivirus flags Tessera

Apps packaged with PyInstaller, as Tessera is, are sometimes flagged by mistake. You can check your download against the release's `SHA256SUMS.txt`, read the source, or build it yourself. Please report false positives to your antivirus vendor.

### Sending a useful bug report

Include your Tessera version (click **Ready**, top right), your Windows version, the tool, and what you did. The log file at `%LOCALAPPDATA%\Tessera\toolbox.log` helps a lot; check it for anything private before attaching it.

## Help the project

- **Star it** on [GitHub](https://github.com/epicabdou/tessera), and tell people who still upload their files to online tools.
- **Report bugs and suggest tools** in [Issues](https://github.com/epicabdou/tessera/issues).
- **Improve these docs**: every page has an "Improve this page on GitHub" link.
- **Contribute code**: start with the [contributing guide](https://github.com/epicabdou/tessera/blob/main/CONTRIBUTING.md).
- **Security problems**: please report them privately, as described in the [security policy](https://github.com/epicabdou/tessera/blob/main/SECURITY.md).
