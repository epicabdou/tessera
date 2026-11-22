"""Progress of long jobs (OCR, page rendering, printing…), polled by the UI.

The UI picks a job id, starts the call, and polls `get(job_id)` until the call returns.
"""

from __future__ import annotations

import threading
from typing import Callable

_lock = threading.Lock()
_jobs: dict[str, dict] = {}

Progress = Callable[[int, int, str], None]


def reporter(job_id: str | None) -> Progress:
    def report(done: int, total: int, message: str = "") -> None:
        if not job_id:
            return
        with _lock:
            _jobs[job_id] = {"done": done, "total": total, "message": message}

    return report


def get(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def clear(job_id: str) -> None:
    with _lock:
        _jobs.pop(job_id, None)
