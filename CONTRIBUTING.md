# Contributing to Tessera

Thanks for helping. Tessera is a Windows desktop app: a React + TypeScript UI (`frontend/`) over Python business logic (`backend/`), bundled with PyInstaller and shipped as an MSI. The user guide lives at **<https://epicabdou.github.io/tessera/>** (sources in `website/`).

By taking part you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Reporting bugs and proposing features

- **Bugs:** open an issue with the **Bug report** form. Include the Tessera version (click the status button, the green dot in the top bar, to open the About box), your Windows version, the tool you used, the steps, and the relevant part of the log at `%LOCALAPPDATA%\Tessera\toolbox.log`. A small sample file that shows the problem helps a lot; remove anything private from it first.
- **Features:** open an issue with the **Feature request** form. Describe the task you're trying to get done before the solution you have in mind.
- **Security problems:** don't open a public issue. Follow [SECURITY.md](SECURITY.md).
- **Questions about using the app:** read the [docs](https://epicabdou.github.io/tessera/) and the [support page](https://epicabdou.github.io/tessera/support) first.

Search the existing issues before opening a new one. For anything bigger than a small fix, open an issue (or comment on one) before you start, so we can agree on the approach first.

## Set up

You need Windows 10 or 11. The app uses pywin32, WinRT and WebView2, so it doesn't run on other systems.

- Python 3.11 or later (CI uses 3.13)
- Node.js 20 or later (CI uses 22)
- .NET SDK 6 or later, only to build the `.msi` installer

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
npm --prefix frontend install
```

## Run it

```powershell
.venv\Scripts\python scripts\dev.py
```

This starts the Vite dev server and opens the app window pointed at it. React changes hot-reload. After changing Python, close the window and run the command again. DevTools are enabled in dev mode (right-click, then Inspect). Closing the window stops Vite.

`http://127.0.0.1:5173` in a regular browser shows the UI but can't reach Python: the status button shows "No Python backend".

## Test

```powershell
.venv\Scripts\python -m pytest
```

The tests cover the business logic in `backend/toolbox/services`. Two groups are opt-in:

- Tests that start Microsoft Office or LibreOffice are slow and skipped by default:

  ```powershell
  $env:TOOLBOX_OFFICE_TESTS = "1"; .venv\Scripts\python -m pytest backend/tests/test_convert.py
  ```

- The image AI tests use stand-in models by default. To also run the real models, point `TOOLBOX_AI_MODELS` at a models folder, such as the app's own:

  ```powershell
  $env:TOOLBOX_AI_MODELS = "$env:LOCALAPPDATA\Tessera\models"; .venv\Scripts\python -m pytest backend/tests/test_images.py
  ```

The self-test checks the whole stack: PDF rendering, the UI-to-Python bridge, conversions, and the PDF and image tools. It exits with `0` (pass) or `1` (fail), and works from source, from `scripts\dev.py` and on packaged builds:

```powershell
dist\Tessera\Tessera.exe --self-test
```

## Build

```powershell
.venv\Scripts\python scripts\build.py            # folder build: dist\Tessera\Tessera.exe (starts fastest)
.venv\Scripts\python scripts\build.py --onefile  # single file:  dist\Tessera.exe (slower to start)
.venv\Scripts\python scripts\build.py --msi      # installer:    dist\Tessera-<version>-x64.msi
```

`--skip-frontend` reuses the existing `frontend/dist`. With `--msi`, `--skip-app` repacks the existing `dist\Tessera` without rebuilding it.

About the installer:

- `--msi` restores WiX Toolset 5.0.2, pinned in `dotnet-tools.json`, and runs Windows Installer's consistency checks on the result. The project stays on WiX 5 because WiX 6 and later need a separate EULA.
- The sources are `installer\Tessera.wxs` (package, files, shortcut) and `installer\TesseraUI.wxs` (dialogs). Never change the `UpgradeCode` in `Tessera.wxs`: upgrades depend on it.
- The version comes from `__version__` in `backend/toolbox/__init__.py`. A newer MSI replaces the installed version; an older one refuses to install over it.
- The icon (`assets\icon.ico`), the logo and the installer artwork (`assets\installer\`) are generated: edit `scripts\make_brand.py` and run it rather than editing the files.

## Adding a feature

1. Write the logic in `backend/toolbox/services/` and add tests in `backend/tests/`.
2. Expose it with a public method on `Api` in `backend/toolbox/api.py`. Return JSON-serialisable values; a raised exception rejects the JavaScript promise with its message. If the method writes files, decorate it with `@_records("<tool name>")` so its runs appear in History. Name its source argument `path`, `paths` or `items` and return `{path, ...}`, `{files: [...]}` or a list of those, and the inputs and outputs are picked up automatically.
3. Add the method's signature to `PyApi` in `frontend/src/lib/bridge.ts`.
4. Call it from React with `await call('your_method', arg1, arg2)`. Calls run on pywebview worker threads, so slow work doesn't freeze the window; show a busy state while you wait.
5. For a new screen, add a component and register it under a category in `frontend/src/tools/registry.tsx`, with an icon and a one-line `hint` (shown in Find a tool). A new category also needs its id in `CategoryId` (`src/lib/workspace.ts`) and an entry in `CATEGORIES`.
6. To work with files from the Explorer, read the selection with `useWorkspace().selected`, accept "open in this tool" requests with `useToolRequest('<tool id>', path => …)`, and add an entry to the file context menu in `src/browser/FileBrowser.tsx`.

The project layout is described in [README.md](README.md#project-layout).

## Conventions

**General**

- Files stay on the user's PC. Don't add telemetry or uploads. New downloads happen only when a feature first needs them, from a fixed HTTPS address with a SHA-256 checksum pinned in the code, the way `services/components.py` (Tectonic) and `services/images/ai.py` (models) do it.
- Tools never overwrite their input. They save a new file, suggest a name like `name_rotated.pdf`, and ask before replacing an existing file.
- The product is called Tessera, but the Python package and internal identifiers (`toolbox`, `TOOLBOX_*` variables, storage keys, drag-and-drop types) keep the old name on purpose. Renaming them would break saved state.
- New dependencies need a license compatible with GPL-3.0 (permissive licenses are preferred). Say why you need it in the pull request, and add it to [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
- When behaviour changes, update the user guide in `website/docs/` and, for developer-facing changes, `README.md`.

**Python** (`backend/`)

- `services/` holds the logic and imports nothing from the UI, so it can be unit-tested. `api.py` is a thin bridge over it. Code that needs a pywebview window (such as `html_print.py`) lives outside `services/`.
- Start modules with a docstring and `from __future__ import annotations`. Type-annotate function signatures.
- Log with `log = logging.getLogger(__name__)`. Error messages that reach the UI are written for users: say what went wrong and what to do.
- Use `pytest` and its `tmp_path` fixture; build sample files in code (see `backend/tests/samples.py`) instead of committing binaries. Guard tests that need Windows, Office or real models with `pytest.mark.skipif`.

**TypeScript and React** (`frontend/`)

- Function components and hooks. Match the existing style: two-space indentation, single quotes, no semicolons. The TypeScript config is strict and rejects unused locals and parameters.
- Style with the shared classes (`card`, `btn btn-primary` / `btn-secondary` / `btn-ghost`, `text-input`, `segmented`, `side-panel`, `action-bar`) and the colour tokens in `src/index.css` (`--glass`, `--bg-elev`, `--field`, `--accent`, `--accent-grad` and so on), so screens work in both light and dark themes.
- Pop-ups that use `position: fixed` must be rendered through a portal (as `ContextMenu` is). Inside a frosted panel they would be clipped.

## Pull requests

1. Fork the repository and create a branch from `main` with a short descriptive name, such as `fix-split-ranges` or `pdf-to-epub`.
2. Keep each pull request to one change. Write commit messages with a short summary line in the imperative ("Add page labels to Organize PDF").
3. Run the checks below and make sure they pass.
4. Open the pull request against `main` and fill in the template. Link the issue it addresses (`Fixes #123`) and add screenshots for UI changes.
5. CI runs the same checks on every pull request. A maintainer will review; please answer comments by pushing new commits to the same branch.

Checks to run before opening a pull request:

```powershell
.venv\Scripts\python -m pytest
```
```powershell
cd frontend
npm run build
npx oxlint
```

If you changed the docs in `website/`:

```powershell
cd website
npm install
npm run build
```

Preview the site while you write with `npm run dev` in `website/` (it serves on port 5174).

If you changed packaging (dependencies, `scripts/build.py`, `installer/`, data files a library needs at runtime), also build the app and run `dist\Tessera\Tessera.exe --self-test`.

## Releases

Maintainers publish a release by bumping `__version__` in `backend/toolbox/__init__.py` and pushing a matching tag (`v0.2.0` for `0.2.0`). The release workflow checks that the two match, builds and smoke-tests the MSI, and attaches it to a GitHub release with its SHA-256 checksums.

## License

Tessera is licensed under the GNU General Public License, version 3 or (at your option) any later version (GPL-3.0-or-later); see [LICENSE](LICENSE). There's no contributor license agreement: by submitting a contribution, you agree that it's licensed under the same terms, and you confirm that you have the right to submit it.
