# Security policy

Tessera opens files that may come from anyone (PDFs, images, Office documents, web pages, LaTeX sources) and processes them on the user's PC. We take reports about anything that lets such a file, a web page or a download harm that PC or its data seriously.

## Supported versions

Security fixes go into the **latest release** only. Before you report, please check that the problem still happens with the newest version from the [releases page](https://github.com/epicabdou/tessera/releases/latest).

| Version | Supported |
|---|---|
| Latest release | Yes |
| Older releases | No: update to the latest release |
| Unreleased `main` | Best effort |

## Reporting a vulnerability

**Please don't report security problems in public issues, pull requests or discussions.**

Report them privately through GitHub: on the repository, open the **Security** tab and click **Report a vulnerability** (or go straight to <https://github.com/epicabdou/tessera/security/advisories/new>). Only the maintainer can see the report, and we can discuss it and prepare a fix there.

Please include:

- The Tessera version (click the status button, the green dot in the top bar, to open the About box) and your Windows version and edition.
- How Tessera was installed: the MSI for the current user, the MSI for all users (`ALLUSERS=1`), a folder or single-file build, or from source.
- The affected tool or component, and what an attacker can achieve (for example: run code, read or overwrite files, get around a protection).
- Exact steps to reproduce, and a proof-of-concept file if one is needed. Attach it to the advisory rather than linking to a public copy.
- The relevant part of the log at `%LOCALAPPDATA%\Tessera\toolbox.log`, if any.
- Whether the problem is already public, and how you'd like to be credited.

What happens next:

- We aim to acknowledge a report within 7 days and to keep you updated while we work on it.
- Once a fix is released, we publish a GitHub security advisory that credits you, unless you'd rather stay anonymous.
- Please give us a reasonable time to release a fix before you disclose the problem publicly. We'll agree on a date with you.

If the problem is in a third-party component (see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)), please report it to that project as well. Tell us too if the version Tessera ships is affected, so we can update it.

## Scope

In scope:

- **Crafted input files.** A PDF, image (including HEIC, AVIF, TIFF and SVG), Word, Excel or PowerPoint file, Markdown, HTML, CSV or text file, `.tex` source or `.pfx`/`.p12` certificate that, when opened, previewed or processed by Tessera, crashes it in a way that corrupts memory, runs code, or reads or writes files the user didn't choose. This includes bugs in the native libraries Tessera bundles (PDFium, Pillow's image codecs, libheif and others) when they are reachable through Tessera.
- **Output files.** A tool that writes outside the location the user picked, overwrites an input file without asking, or leaves behind content it claims to remove (for example text under a **Redact** box in Edit PDF).
- **Protection and signatures.** Protect PDF producing weaker encryption than it reports, or Sign PDF reporting a modified document as unchanged.
- **The local pywebview bridge.** The UI calls Python methods (`Api` in `backend/toolbox/api.py`) through `window.pywebview.api`. Any way for content other than Tessera's own UI to call them is in scope: a page converted with HTML to PDF or HTML to Image, Markdown being rendered, a previewed file, another website, or another program. So is the local HTTP server on `127.0.0.1` (port 47821 by default) that serves the built UI. Converted pages run in hidden windows that must not be able to read the user's files; a way around that is in scope.
- **Office conversion.** Tessera starts Word, Excel or PowerPoint with macros force-disabled. A document that runs a macro or other code anyway during conversion is in scope.
- **LaTeX.** Tessera doesn't turn on shell escape when it compiles. A document that runs programs when compiled with the Tectonic engine Tessera installs is in scope. (An installed MiKTeX or TeX Live follows its own shell-escape settings.)
- **Downloaded components.** On first use, Tessera downloads Tectonic 0.15.0 (the LaTeX engine) and two AI models (Real-ESRGAN General x4v3 and ISNet general-use). Each comes from a fixed HTTPS address in the code (`backend/toolbox/services/components.py` and `backend/toolbox/services/images/ai.py`). The download is written to a temporary folder and its SHA-256 is compared with the checksum pinned next to the address. A mismatch is discarded with an error; only a matching file is unpacked and moved into `%LOCALAPPDATA%\Tessera`. Any way to make Tessera install or load a file that doesn't match its pinned checksum is in scope.
- **The installer.** The MSI installs per user (in `%LocalAppData%\Programs\Tessera`, without elevation) or, with `ALLUSERS=1`, for every user in Program Files. Privilege escalation, weak permissions on installed files, DLL search-order hijacking from the install folder, and problems with the installer's actions are in scope.
- **Release integrity.** A release whose MSI doesn't match its `SHA256SUMS.txt`.

Out of scope:

- Attacks that need code already running as the same Windows user, or write access to `%LOCALAPPDATA%\Tessera` or the install folder. Once a downloaded component is installed it is trusted; it isn't re-checked on every start.
- Vulnerabilities in Microsoft Office, LibreOffice, Tesseract, WebView2 or Windows itself, unless Tessera makes them reachable when they otherwise wouldn't be. Report those to their vendors.
- What TeX itself is designed to do: a document can read files your account can read and include them in its PDF. Compile only documents you trust. The TeX packages Tectonic fetches from its own package server are checked by Tectonic, not by Tessera.
- Remote content loaded by a web page you chose to convert with HTML to PDF or HTML to Image.
- PDF restrictions (no printing, no copying, and so on) being ignored by other PDF readers. They are a request to readers, not encryption; an open password is.
- Self-signed certificates showing as "not verified" in PDF readers.
- Slowness or high memory use on very large files, unless it leads to one of the problems above.
- Reports from automated scanners without a demonstrated impact.
