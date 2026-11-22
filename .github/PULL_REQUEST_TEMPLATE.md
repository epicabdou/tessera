## What this changes

<!-- What does this pull request do, and why? Link the issue it addresses, e.g. "Fixes #123". -->

## How it was tested

<!-- Steps you followed, files you tried, and screenshots or a short recording for UI changes. -->

## Checklist

- [ ] `.venv\Scripts\python -m pytest` passes, and new logic in `backend/toolbox/services/` has tests.
- [ ] `npm run build` and `npx oxlint` pass in `frontend/`.
- [ ] If the docs changed: `npm run build` passes in `website/`.
- [ ] If packaging changed (dependencies, `scripts/build.py`, `installer/`): I built the app and `dist\Tessera\Tessera.exe --self-test` passes.
- [ ] The user guide (`website/docs/`) and `README.md` are updated where behaviour changed.
- [ ] New dependencies, if any, have a GPL-3.0-compatible license and are listed in `THIRD-PARTY-NOTICES.md`.
- [ ] I agree that my contribution is licensed under GPL-3.0-or-later, as described in `CONTRIBUTING.md`.
