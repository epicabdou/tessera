---
title: Download
description: Download the free Tilepress installer for Windows, or get the source code.
---

# Download Tilepress

Free for everyone, for any use. No account, no trial, no ads.

<DownloadPanel />

## What you need

- **Windows 10 or 11, 64-bit.**
- **Microsoft Edge WebView2 Runtime**, which Tilepress uses to draw its window. It comes with Windows 11 and with current Windows 10 updates. If Tilepress's window stays blank, [install it from Microsoft](https://developer.microsoft.com/microsoft-edge/webview2/).
- **About 210 MB of disk space** (the installer is about 75 MB).

Optional, for some tools:

- **Microsoft Office or LibreOffice** to turn Word, Excel and PowerPoint files into PDFs. [Details](/docs/to-pdf)
- **Tesseract OCR** if you want more OCR languages than Windows provides. [Details](/docs/edit#ocr-pdf)

## Install

1. Run **Tilepress-x64.msi**.
2. Click **Next**, then **Install**. No administrator rights are needed: Tilepress installs for your Windows account, in `%LocalAppData%\Programs\Tilepress`.
3. Leave **Launch Tilepress** ticked and click **Finish**. You'll find Tilepress in the Start menu.

::: warning "Windows protected your PC"
The installer isn't code-signed yet, so Windows SmartScreen may warn you the first time. Click **More info**, then **Run anyway**. To check that your download is exactly the one built from the source on GitHub, compare its fingerprint with the `SHA256SUMS.txt` file attached to the release:

```powershell
Get-FileHash .\Tilepress-x64.msi -Algorithm SHA256
```
:::

### For every user of a PC

From a terminal opened as administrator:

```powershell
msiexec /i Tilepress-x64.msi ALLUSERS=1
```

This installs Tilepress in Program Files with a Start menu shortcut for everyone.

## Update

Download the latest installer and run it. It replaces the version you have and keeps your settings and history.

## Uninstall

Open **Settings → Apps → Installed apps**, find **Tilepress** and choose **Uninstall**.

Your settings, history and downloaded components stay in `%LOCALAPPDATA%\Tilepress`, in case you reinstall. Delete that folder to remove them too.

## Source code

Tilepress is free software under the [GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.html). The full source is on [GitHub](https://github.com/epicabdou/tilepress); every release also has its source attached as a .zip. To build it yourself, see [Build from source](/docs/build).
