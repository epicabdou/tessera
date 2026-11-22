from __future__ import annotations

import os
import platform
import sys

from .. import APP_NAME, __version__


def get_system_info() -> dict:
    return {
        "app_name": APP_NAME,
        "app_version": __version__,
        "os": f"{platform.system()} {platform.release()}",
        "os_version": platform.version(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count() or 0,
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "frozen": getattr(sys, "frozen", False),
    }
