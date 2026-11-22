"""Run the app in development mode.

Starts the Vite dev server (hot reload for React) and opens the native window
pointed at it. Closing the window stops Vite.

    .venv\\Scripts\\python scripts\\dev.py
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
HOST, PORT = "127.0.0.1", 5173
NPM = "npm.cmd" if os.name == "nt" else "npm"


def wait_for_port(proc: subprocess.Popen, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"Vite exited early with code {proc.returncode}")
        try:
            with socket.create_connection((HOST, PORT), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise SystemExit(f"Vite did not start on {HOST}:{PORT} within {timeout:.0f}s")


def main() -> int:
    if not (FRONTEND / "node_modules").is_dir():
        subprocess.run([NPM, "install"], cwd=FRONTEND, check=True)

    # Run Vite's own entry with node (not `npm run dev`) so terminate() stops the
    # real server process instead of an npm/cmd wrapper.
    vite = subprocess.Popen(
        ["node", str(FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"), "--host", HOST, "--port", str(PORT), "--strictPort"],
        cwd=FRONTEND,
    )
    try:
        wait_for_port(vite)
        env = {**os.environ, "TOOLBOX_DEV_URL": f"http://{HOST}:{PORT}"}
        # Extra flags (e.g. --self-test) are forwarded to the app.
        return subprocess.call([sys.executable, str(ROOT / "backend" / "main.py"), "--dev", *sys.argv[1:]], env=env)
    finally:
        vite.terminate()
        try:
            vite.wait(timeout=5)
        except subprocess.TimeoutExpired:
            vite.kill()


if __name__ == "__main__":
    sys.exit(main())
