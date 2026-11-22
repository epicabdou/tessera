"""Build the distributable desktop app.

1. Builds the React app into frontend/dist.
2. Bundles Python, pywebview and the built UI with PyInstaller.

    .venv\\Scripts\\python scripts\\build.py            # folder build: dist\\Toolbox\\Toolbox.exe
    .venv\\Scripts\\python scripts\\build.py --onefile  # single file:  dist\\Toolbox.exe
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"
APP_NAME = "Toolbox"
NPM = "npm.cmd" if os.name == "nt" else "npm"


def run(cmd: list[str], cwd: Path = ROOT) -> None:
    print(f"\n> {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def build_frontend() -> Path:
    if not (FRONTEND / "node_modules").is_dir():
        run([NPM, "ci" if (FRONTEND / "package-lock.json").exists() else "install"], cwd=FRONTEND)
    run([NPM, "run", "build"], cwd=FRONTEND)
    dist = FRONTEND / "dist"
    if not (dist / "index.html").is_file():
        raise SystemExit("Frontend build did not produce dist/index.html")
    return dist


def build_app(web_dist: Path, onefile: bool) -> Path:
    work = ROOT / "build"
    shutil.rmtree(work, ignore_errors=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(BACKEND / "main.py"),
        "--name", APP_NAME,
        "--windowed",
        "--noconfirm",
        "--clean",
        "--paths", str(BACKEND),
        "--add-data", f"{web_dist}{os.pathsep}web",
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(work),
        "--specpath", str(work),
        "--onefile" if onefile else "--onedir",
    ]
    icon = ROOT / "assets" / "icon.ico"
    if icon.is_file():
        cmd += ["--icon", str(icon)]
    run(cmd)

    exe = APP_NAME + (".exe" if os.name == "nt" else "")
    return ROOT / "dist" / exe if onefile else ROOT / "dist" / APP_NAME / exe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--onefile", action="store_true", help="produce a single self-extracting executable")
    parser.add_argument("--skip-frontend", action="store_true", help="reuse the existing frontend/dist")
    args = parser.parse_args()

    web_dist = FRONTEND / "dist" if args.skip_frontend else build_frontend()
    exe = build_app(web_dist, args.onefile)
    print(f"\nBuilt {exe}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
