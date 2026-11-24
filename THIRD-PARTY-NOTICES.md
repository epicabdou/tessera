# Third-party notices

Tilepress is licensed under the GNU General Public License, version 3 or later (see [LICENSE](LICENSE)). The Windows app built from this repository (`scripts/build.py`, and the MSI made from it) includes the third-party components below, each under its own license. Some others are downloaded the first time a feature needs them, and some are only used to build the app.

The license texts are in each project's repository and in its package (for Python packages, the `*.dist-info/licenses` folder of the installed wheel; for npm packages, the `LICENSE` file in `node_modules/<package>`). Licenses were read from the package metadata and license files of the versions installed from `requirements.txt` and `frontend/package.json` in November 2026. They can change between versions, so check again when you update a dependency (see [Keeping this file up to date](#keeping-this-file-up-to-date)).

## Python runtime and packaging

| Component | License | Project |
|---|---|---|
| Python (CPython 3.13), the interpreter and standard library | PSF-2.0. The Windows build includes, among others, bzip2, libffi (MIT), OpenSSL 3 (Apache-2.0), SQLite (public domain), Expat, liblzma, zlib and mpdecimal; see Python's `LICENSE.txt` and the [license page](https://docs.python.org/3/license.html) for their terms. | <https://www.python.org/> |
| Microsoft Visual C++ runtime and Universal C Runtime (`vcruntime140.dll`, `vcruntime140_1.dll`, `msvcp140.dll`, `msvcp140_1.dll`, `ucrtbase.dll`, `api-ms-win-*.dll`), shipped with Python and the packages below | Microsoft Distributable Code, redistributed under the "Additional Conditions for this Windows binary build" in Python's `LICENSE.txt` | <https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist> |
| PyInstaller bootloader and run-time modules (they start `Tilepress.exe` and unpack the bundle) | GPL-2.0-or-later with the PyInstaller Bootloader Exception, which allows distributing the combined program under any license. PyInstaller's run-time hooks and run-time modules are Apache-2.0. | <https://pyinstaller.org/> |
| pyinstaller-hooks-contrib run-time hooks | Apache-2.0 (the rest of the package is GPL-2.0-or-later and isn't shipped) | <https://github.com/pyinstaller/pyinstaller-hooks-contrib> |

## Python packages bundled in the app

Everything in `requirements.txt`, plus the packages they depend on at run time.

| Package | License | Project |
|---|---|---|
| aiohappyeyeballs | PSF-2.0 | <https://github.com/aio-libs/aiohappyeyeballs> |
| aiohttp | Apache-2.0 AND MIT | <https://github.com/aio-libs/aiohttp> |
| aiosignal | Apache-2.0 | <https://github.com/aio-libs/aiosignal> |
| asn1crypto | MIT | <https://github.com/wbond/asn1crypto> |
| attrs | MIT | <https://www.attrs.org/> |
| bottle | MIT | <https://bottlepy.org/> |
| certifi | MPL-2.0 | <https://github.com/certifi/python-certifi> |
| cffi | MIT-0 | <https://github.com/python-cffi/cffi> |
| charset-normalizer | MIT | <https://github.com/jawah/charset_normalizer> |
| clr-loader | MIT (from its `LICENSE` file; the package metadata states no license) | <https://github.com/pythonnet/clr-loader> |
| cryptography | Apache-2.0 OR BSD-3-Clause. Its compiled module includes OpenSSL (Apache-2.0) and Rust crates under MIT, Apache-2.0, BSD-3-Clause and Unicode-3.0 terms. | <https://github.com/pyca/cryptography> |
| et-xmlfile | MIT | <https://foss.heptapod.net/openpyxl/et_xmlfile> |
| frozenlist | Apache-2.0 | <https://github.com/aio-libs/frozenlist> |
| idna | BSD-3-Clause | <https://github.com/kjd/idna> |
| lxml | BSD-3-Clause. Its wheels include libxml2, libxslt and libexslt (MIT), zlib (Zlib) and libiconv (LGPL-2.1). | <https://lxml.de/> |
| markdown-it-py | MIT | <https://github.com/executablebooks/markdown-it-py> |
| mdurl | MIT | <https://github.com/executablebooks/mdurl> |
| multidict | Apache-2.0 | <https://github.com/aio-libs/multidict> |
| numpy | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0. Its wheels include OpenBLAS (BSD-3-Clause) with LAPACK (BSD-3-Clause-Open-MPI) and the GCC runtime (GPL-3.0-or-later WITH GCC-exception-3.1). | <https://numpy.org/> |
| onnxruntime-directml (ONNX Runtime) | MIT. Its `ThirdPartyNotices.txt` lists the code compiled into it. It also ships `DirectML.dll`: see [Microsoft components](#microsoft-components-inside-the-packages). | <https://onnxruntime.ai/> |
| openpyxl | MIT | <https://openpyxl.readthedocs.io/> |
| oscrypto | MIT | <https://github.com/wbond/oscrypto> |
| packaging | Apache-2.0 OR BSD-2-Clause | <https://github.com/pypa/packaging> |
| pdfminer.six | MIT | <https://github.com/pdfminer/pdfminer.six> |
| pdfplumber | MIT | <https://github.com/jsvine/pdfplumber> |
| Pillow | MIT-CMU. Its wheels include the image libraries listed [below](#native-libraries-inside-the-packages). | <https://python-pillow.github.io/> |
| pillow-heif | BSD-3-Clause for its own code. Its Windows wheels are GPL-2.0 as a whole because of the libraries they bundle, listed [below](#native-libraries-inside-the-packages). | <https://github.com/bigcat88/pillow_heif> |
| propcache | Apache-2.0 | <https://github.com/aio-libs/propcache> |
| proxy-tools | MIT | <https://github.com/jtushman/proxy_tools> |
| pycparser | BSD-3-Clause | <https://github.com/eliben/pycparser> |
| Pygments | BSD-2-Clause | <https://pygments.org/> |
| pyHanko | MIT | <https://github.com/MatthiasValvekens/pyHanko> |
| pyhanko-certvalidator | MIT | <https://github.com/MatthiasValvekens/pyHanko> |
| pypdf | BSD-3-Clause | <https://github.com/py-pdf/pypdf> |
| pypdfium2 | BSD-3-Clause and Apache-2.0 (as its metadata states). It ships PDFium: see [below](#native-libraries-inside-the-packages). | <https://github.com/pypdfium2-team/pypdfium2> |
| python-docx | MIT | <https://github.com/python-openxml/python-docx> |
| python-pptx | MIT | <https://github.com/scanny/python-pptx> |
| pythonnet (Python.NET, including `Python.Runtime.dll`) | MIT | <https://pythonnet.github.io/> |
| pywebview | BSD-3-Clause. It ships Microsoft's WebView2 SDK libraries: see [Microsoft components](#microsoft-components-inside-the-packages). | <https://pywebview.flowrl.com/> |
| pywin32 (including Pythonwin) | PSF-2.0 according to its metadata. Its parts carry BSD-3-Clause-style licenses (Mark Hammond, Greg Stein and others), and Pythonwin includes Scintilla under the Scintilla license. | <https://github.com/mhammond/pywin32> |
| ReportLab | BSD-3-Clause | <https://www.reportlab.com/> |
| setuptools (pulled into the bundle by PyInstaller's hooks) | MIT | <https://github.com/pypa/setuptools> |
| typing_extensions | PSF-2.0 | <https://github.com/python/typing_extensions> |
| tzdata | Apache-2.0 | <https://github.com/python/tzdata> |
| tzlocal | MIT | <https://github.com/regebro/tzlocal> |
| uritools | MIT | <https://github.com/tkem/uritools> |
| winrt-runtime and the WinRT projections (`winrt-Windows.Foundation`, `.Foundation.Collections`, `.Globalization`, `.Graphics.Imaging`, `.Media.FaceAnalysis`, `.Media.Ocr`, `.Storage.Streams`) | MIT | <https://github.com/pywinrt/pywinrt> |
| XlsxWriter | BSD-2-Clause | <https://github.com/jmcnamara/XlsxWriter> |
| yarl | Apache-2.0 | <https://github.com/aio-libs/yarl> |

ONNX Runtime also installs **sympy** (BSD-3-Clause), **mpmath** (BSD-3-Clause), **flatbuffers** (Apache-2.0) and **protobuf** (BSD-3-Clause) as dependencies. Tilepress doesn't import them, and PyInstaller leaves them out of the app.

### Native libraries inside the packages

**Pillow** bundles, according to the `LICENSE` file in its wheel: Brotli (MIT), FreeType (FreeType License), HarfBuzz (MIT), Little CMS (MIT), libavif (BSD-2-Clause), libjpeg-turbo (IJG and BSD-3-Clause), libpng (PNG Reference Library License v2), libwebp (BSD-3-Clause), OpenJPEG (BSD-2-Clause), LibTIFF (libtiff license), liblzma from XZ Utils (0BSD) and zlib-ng (Zlib).

**pillow-heif** bundles these as separate DLLs, according to `LICENSES_bundled.txt` in its wheel:

| Library | License | Source |
|---|---|---|
| libheif | LGPL-3.0 | <https://github.com/strukturag/libheif/tree/v1.23.6> |
| libde265 | LGPL-3.0 | <https://github.com/strukturag/libde265/tree/v1.1.3> |
| x265 | GPL-2.0-or-later | <https://github.com/Multicorewareinc/x265/tree/4.3> |
| MinGW-w64 runtime: `libgcc_s_seh-1.dll`, `libstdc++-6.dll` | GPL-3.0 with the GCC Runtime Library Exception | <https://sourceforge.net/p/mingw-w64/mingw-w64/ci/master/tree/COPYING> |
| MinGW-w64 runtime: `libwinpthread-1.dll` | MIT and BSD | <https://sourceforge.net/p/mingw-w64/mingw-w64/ci/master/tree/COPYING> |

**pypdfium2** ships `pdfium.dll`, a build of [PDFium](https://pdfium.googlesource.com/pdfium/) (BSD-3-Clause, with some Apache-2.0 code) made by the [pdfium-binaries](https://github.com/bblanchon/pdfium-binaries) project (MIT). The libraries compiled into it include abseil, Anti-Grain Geometry 2.3, FreeType, ICU, Little CMS, libjpeg-turbo, OpenJPEG, libpng, LibTIFF and zlib. Their license texts are in the `BUILD_LICENSES` folder of the pypdfium2 wheel.

### Microsoft components inside the packages

| Component | Shipped by | License |
|---|---|---|
| DirectML (`DirectML.dll`), which runs the AI models on the graphics card | onnxruntime-directml | Microsoft Software License Terms for Microsoft DirectX Machine Learning (DirectML), a proprietary license that allows redistributing it inside Windows applications. See the [Microsoft.AI.DirectML package](https://www.nuget.org/packages/Microsoft.AI.DirectML/). |
| WebView2 SDK (`Microsoft.Web.WebView2.Core.dll`, `Microsoft.Web.WebView2.WinForms.dll`, `WebView2Loader.dll`) | pywebview | Microsoft's BSD-3-Clause-style WebView2 SDK license. See the [Microsoft.Web.WebView2 package](https://www.nuget.org/packages/Microsoft.Web.WebView2/). |

## Frontend libraries bundled in the UI

The runtime dependencies in `frontend/package.json` and the packages they depend on. Vite compiles them into the UI in `frontend/dist`, which is bundled in the app.

| Package | License | Project |
|---|---|---|
| react, react-dom, scheduler | MIT | <https://react.dev/> |
| codemirror | MIT | <https://codemirror.net/> |
| @codemirror/autocomplete, /commands, /language, /legacy-modes, /lint, /search, /state, /streamparser, /view | MIT | <https://codemirror.net/> |
| @lezer/common, @lezer/highlight, @lezer/lr | MIT | <https://lezer.codemirror.net/> |
| @marijn/find-cluster-break | MIT | <https://code.haverbeke.berlin/marijn/find-cluster-break> |
| crelt | MIT | <https://code.haverbeke.berlin/marijn/crelt> |
| style-mod | MIT | <https://code.haverbeke.berlin/marijn/style-mod> |
| w3c-keyname | MIT | <https://github.com/marijnh/w3c-keyname> |

The UI uses fonts installed with Windows (Segoe UI, Segoe Script and others); no font files are bundled.

## Downloaded on first use, not shipped

These aren't part of the installer. Tilepress downloads each one the first time a feature needs it, from a fixed address, and checks it against a SHA-256 checksum pinned in the code before using it (`backend/toolbox/services/components.py` and `backend/toolbox/services/images/ai.py`). They are stored under `%LOCALAPPDATA%\Tilepress\`.

| Component | Used by | License | Downloaded from | Project |
|---|---|---|---|---|
| Tectonic 0.15.0, the LaTeX engine (only if no LaTeX engine is installed) | LaTeX editor | MIT | The Tectonic GitHub release | <https://tectonic-typesetting.github.io/> |
| TeX packages and fonts that Tectonic fetches as documents need them | LaTeX editor | Each under its own license (mostly the LaTeX Project Public License and other free licenses) | Tectonic's package server, by Tectonic itself | <https://tectonic-typesetting.github.io/> |
| Real-ESRGAN General x4v3 model (ONNX export) | Upscale Image | BSD-3-Clause | Qualcomm AI Hub | <https://github.com/xinntao/Real-ESRGAN>, <https://github.com/quic/ai-hub-models> |
| ISNet general-use model (ONNX) | Remove background | Apache-2.0 | The rembg project's GitHub release | <https://github.com/xuebinqin/DIS>, <https://github.com/danielgatis/rembg> |

## Used if installed, not shipped

Tilepress can use these when they are on the PC, but never ships or downloads them: Microsoft Office (Word, Excel, PowerPoint) or LibreOffice for Office conversions, Tesseract OCR, and an installed MiKTeX or TeX Live. It also uses parts of Windows: the WebView2 Runtime, Windows OCR and the Windows face detector.

## Used to build, not shipped

| Tool | License | Project |
|---|---|---|
| PyInstaller (apart from the bootloader and run-time files listed above) | GPL-2.0-or-later with the Bootloader Exception | <https://pyinstaller.org/> |
| WiX Toolset 5.0.2 and its WixToolset.UI.wixext extension, which build the MSI | MS-RL | <https://wixtoolset.org/> |
| .NET SDK, which runs WiX | MIT | <https://dotnet.microsoft.com/> |
| Vite and @vitejs/plugin-react | MIT | <https://vite.dev/> |
| TypeScript | Apache-2.0 | <https://www.typescriptlang.org/> |
| oxlint | MIT | <https://oxc.rs/> |
| pytest | MIT | <https://pytest.org/> |
| websocket-client, used by `scripts/screenshots.py` to take the website's screenshots | Apache-2.0 | <https://github.com/websocket-client/websocket-client> |

## Keeping this file up to date

When you add, remove or update a dependency, check its license again and update the tables above. For Python packages, this prints the license metadata of every installed distribution:

```powershell
.venv\Scripts\python -c "import importlib.metadata as m; [print(d.metadata['Name'], d.version, d.metadata.get('License-Expression') or d.metadata.get('License') or [c for c in (d.metadata.get_all('Classifier') or []) if c.startswith('License')]) for d in m.distributions()]"
```

For the frontend, read `license` in `frontend/node_modules/<package>/package.json`. To see which Python modules a build actually bundled, look in `build\Tilepress\Analysis-00.toc` after running `scripts\build.py`.
