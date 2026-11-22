"""Build the distributable desktop app.

1. Builds the React app into frontend/dist.
2. Bundles Python, pywebview and the built UI with PyInstaller.

3. With --msi, packs the folder build into a Windows Installer package (WiX, installer\\*.wxs).

    .venv\\Scripts\\python scripts\\build.py            # folder build: dist\\Tessera\\Tessera.exe
    .venv\\Scripts\\python scripts\\build.py --onefile  # single file:  dist\\Tessera.exe
    .venv\\Scripts\\python scripts\\build.py --msi      # installer:    dist\\Tessera-<version>-x64.msi

--msi needs the .NET SDK; it restores the WiX version pinned in dotnet-tools.json.
The icon and installer artwork come from assets\\ (regenerate them with scripts\\make_brand.py).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"
INSTALLER = ROOT / "installer"
NPM = "npm.cmd" if os.name == "nt" else "npm"
# WiX 5 is the last release under a plain open-source licence (6+ needs its maintenance-fee EULA).
# Keep the extension's version in step with the wix tool in dotnet-tools.json.
WIX_UI_EXT = ("WixToolset.UI.wixext", "5.0.2")

sys.path.insert(0, str(BACKEND))
from toolbox import APP_NAME, TAGLINE, __version__  # noqa: E402  (plain constants, no heavy imports)


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


def write_version_file(path: Path) -> None:
    """Windows file properties: shown in Explorer's Details tab and as the name in Task Manager."""
    nums = tuple(int(n) for n in __version__.split(".")[:3]) + (0,)
    strings = {
        "FileDescription": APP_NAME,
        "FileVersion": __version__,
        "InternalName": APP_NAME,
        "OriginalFilename": f"{APP_NAME}.exe",
        "ProductName": APP_NAME,
        "ProductVersion": __version__,
        "Comments": TAGLINE,
    }
    table = ",\n          ".join(f"StringStruct({k!r}, {v!r})" for k, v in strings.items())
    path.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
          {table}])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ],
)
""",
        encoding="utf-8",
    )


def build_app(web_dist: Path, onefile: bool) -> Path:
    work = ROOT / "build"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir()
    version_file = work / "version.txt"
    write_version_file(version_file)

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
        "--version-file", str(version_file),
    ]
    icon = ROOT / "assets" / "icon.ico"
    if icon.is_file():
        cmd += ["--icon", str(icon)]
    run(cmd)

    exe = APP_NAME + (".exe" if os.name == "nt" else "")
    if onefile:
        return ROOT / "dist" / exe
    # The GPL travels with the program: the license and third-party notices go next to the
    # exe (and so into the MSI). .txt so they open with a double-click.
    for name, target in (("LICENSE", "LICENSE.txt"), ("THIRD-PARTY-NOTICES.md", "THIRD-PARTY-NOTICES.txt")):
        if (ROOT / name).is_file():
            shutil.copyfile(ROOT / name, ROOT / "dist" / APP_NAME / target)
    copied = copy_licenses(ROOT / "dist" / APP_NAME, work)
    print(f"Copied the license files of {copied} bundled packages to dist\\{APP_NAME}\\licenses", flush=True)
    return ROOT / "dist" / APP_NAME / exe


LICENSE_FILE = re.compile(r"(licen[cs]e|copying|notice|authors)", re.IGNORECASE)


def copy_licenses(app_dir: Path, work: Path) -> int:
    """Put the license texts of every bundled Python package in <app>\\licenses\\<package>.
    Most of their licenses (MIT, BSD...) require the text to travel with the program."""
    import ast
    import importlib.metadata as md

    # What PyInstaller bundled: modules in its archive, plus extension modules and package folders.
    toc = ast.literal_eval((work / APP_NAME / "PYZ-00.toc").read_text(encoding="utf-8"))
    tops = {entry[0].split(".")[0] for entry in toc[1]}
    tops |= {p.name.split(".")[0] for p in (app_dir / "_internal").iterdir()}
    owners = md.packages_distributions()
    names = sorted({dist for top in tops for dist in owners.get(top, [])}, key=str.lower)

    out = app_dir / "licenses"
    shutil.rmtree(out, ignore_errors=True)
    count = 0
    for name in names:
        dist = md.distribution(name)
        # LICENSE, COPYING, NOTICE... in the .dist-info folder, or anything in its licenses/ folder;
        # failing that, the same names at the top of the package itself (onnxruntime keeps them there).
        files = [f for f in dist.files or [] if ".dist-info" in str(f) and LICENSE_FILE.search(str(f).split(".dist-info", 1)[1])]
        files = files or [f for f in dist.files or [] if len(f.parts) == 2 and LICENSE_FILE.search(f.name)]
        target = out / dist.metadata["Name"]
        target.mkdir(parents=True, exist_ok=True)
        for f in files:
            src = Path(f.locate())
            if src.is_file():
                shutil.copyfile(src, target / f.name)
        if not files:
            # No license file shipped at all: record what the package declares.
            meta = dist.metadata
            declared = [meta.get("License-Expression") or meta.get("License") or "not stated"]
            declared += [c for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
            (target / "LICENSE-declared.txt").write_text(
                f"{meta['Name']} {meta['Version']} ships no license file. Its package metadata declares:\n\n"
                + "\n".join(declared) + f"\n\nProject: {meta.get('Home-page') or meta.get('Project-URL') or 'unknown'}\n",
                encoding="utf-8",
            )
        count += 1
    return count


def build_msi(app_dir: Path) -> Path:
    """Pack the folder build into dist\\<name>-<version>-x64.msi."""
    run(["dotnet", "tool", "restore"])
    ext_id, ext_version = WIX_UI_EXT
    if not (ROOT / ".wix" / "extensions" / ext_id / ext_version).is_dir():
        run(["dotnet", "wix", "extension", "add", f"{ext_id}/{ext_version}"])

    msi = ROOT / "dist" / f"{APP_NAME}-{__version__}-x64.msi"
    variables = {
        "ProductName": APP_NAME,
        "Manufacturer": APP_NAME,
        "Version": __version__,
        "Description": TAGLINE,
        "SourceDir": app_dir,
        "AssetsDir": ROOT / "assets",
    }
    cmd = ["dotnet", "wix", "build", "-arch", "x64", "-ext", ext_id, "-pdbtype", "none", "-o", str(msi)]
    for key, value in variables.items():
        cmd += ["-d", f"{key}={value}"]
    cmd += [str(INSTALLER / "Tessera.wxs"), str(INSTALLER / "TesseraUI.wxs")]
    run(cmd)
    # Windows Installer's consistency checks. ICE57 misreads the HKMU key of a per-user-or-machine
    # package (see the comment in Tessera.wxs), so it's skipped.
    run(["dotnet", "wix", "msi", "validate", "-sice", "ICE57", str(msi)])
    return msi


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--onefile", action="store_true", help="produce a single self-extracting executable")
    parser.add_argument("--msi", action="store_true", help="also pack the folder build into an .msi installer")
    parser.add_argument("--skip-frontend", action="store_true", help="reuse the existing frontend/dist")
    parser.add_argument("--skip-app", action="store_true", help="with --msi: reuse the existing dist folder build")
    args = parser.parse_args()
    if args.msi and args.onefile:
        parser.error("--msi packs the folder build; leave out --onefile")
    if args.skip_app and not args.msi:
        parser.error("--skip-app only applies with --msi")

    if args.skip_app:
        exe = ROOT / "dist" / APP_NAME / f"{APP_NAME}.exe"
        if not exe.is_file():
            parser.error(f"--skip-app: {exe} doesn't exist yet")
    else:
        web_dist = FRONTEND / "dist" if args.skip_frontend else build_frontend()
        exe = build_app(web_dist, args.onefile)
        print(f"\nBuilt {exe}")

    if args.msi:
        print(f"\nBuilt {build_msi(exe.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
