## What this changes

<!-- What does this pull request do, and why? Link the issue it addresses, e.g. "Fixes #123". -->

## How it was tested

<!-- Steps you followed, files you tried, and screenshots or a short recording for UI changes. -->

## Checklist

- [ ] `.venv\Scripts\python -m pytest` passes, and new logic in `backend/toolbox/services/` has tests.
- [ ] `npm run build` and `npx oxlint` pass in `frontend/`.
- [ ] If packaging changed (dependencies, `scripts/build.py`, `installer/`): I built the app and `dist\Tilepress\Tilepress.exe --self-test` passes.
- [ ] `README.md` is updated where behaviour changed, and the user guide too if needed (a pull request on epicabdou/tilepress-website).
- [ ] New dependencies, if any, have a GPL-3.0-compatible license and are listed in `THIRD-PARTY-NOTICES.md`.
- [ ] I agree that my contribution is licensed under GPL-3.0-or-later, as described in `CONTRIBUTING.md`.
