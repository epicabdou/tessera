"""Activity history: what each tool made, from which files, and when. SQLite in WAL mode.

WAL lets a second running copy of the app read and write the same file without "database is
locked" errors, and makes each write a cheap append instead of a full journal rewrite.

Only file paths, sizes, timings and error messages are stored, never a tool's options:
some of those are passwords (Protect, Unlock, Sign).

The history must never get in the way of the work: if the database can't be opened or written,
recording is switched off for the session and the failure is logged.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

KEEP = 5000  # entries; older ones are dropped
PAGE_MAX = 200
OPEN_RETRIES = 50  # x 0.1 s, on top of the 5 s busy timeout

# Each step brings the schema from version i to i + 1 (PRAGMA user_version).
MIGRATIONS = [
    """
    CREATE TABLE entries (
        id          INTEGER PRIMARY KEY,
        started_at  REAL    NOT NULL,              -- Unix time, seconds
        duration_ms INTEGER NOT NULL,
        action      TEXT    NOT NULL,              -- API method, e.g. pdf_merge
        label       TEXT    NOT NULL,              -- what the UI calls it, e.g. "Merge PDF"
        status      TEXT    NOT NULL CHECK (status IN ('ok', 'error')),
        error       TEXT
    );
    CREATE INDEX entries_started ON entries (started_at DESC, id DESC);
    CREATE TABLE files (
        entry_id INTEGER NOT NULL REFERENCES entries (id) ON DELETE CASCADE,
        role     TEXT    NOT NULL CHECK (role IN ('input', 'output')),
        position INTEGER NOT NULL,
        path     TEXT    NOT NULL,
        size     INTEGER,
        PRIMARY KEY (entry_id, role, position)
    ) WITHOUT ROWID;
    CREATE INDEX files_path ON files (path);
    """,
]


class History:
    """Thread-safe: one connection, used under a lock (pywebview runs each JS call on its own thread)."""

    def __init__(self, path: Path, keep: int = KEEP) -> None:
        self._path = path
        self._keep = keep
        self._lock = threading.Lock()
        self._db: sqlite3.Connection | None = None
        self._broken = False

    # --- connection ----------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        # Caller holds the lock.
        if self._db is None:
            # Two copies of the app opening a new database at once can briefly lock each other
            # out of the one-time switch to WAL (which needs exclusive access): try again.
            for attempt in range(OPEN_RETRIES):
                try:
                    self._db = self._open()
                    break
                except sqlite3.OperationalError as exc:
                    if not _transient(exc) or attempt == OPEN_RETRIES - 1:
                        raise
                    time.sleep(0.1)
        assert self._db is not None
        return self._db

    def _open(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self._path, timeout=5, check_same_thread=False, isolation_level=None)
        try:
            db.row_factory = sqlite3.Row
            mode = db.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            if mode.lower() != "wal":
                log.warning("History database is in %s mode, not WAL", mode)
            db.execute("PRAGMA synchronous = NORMAL")  # durable across app crashes; WAL makes this safe
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("PRAGMA busy_timeout = 5000")
            _migrate(db)
        except BaseException:
            db.close()
            raise
        return db

    def close(self) -> None:
        with self._lock:
            if self._db is not None:
                self._db.close()
                self._db = None

    # --- writes --------------------------------------------------------------

    def add(
        self,
        action: str,
        label: str,
        started_at: float,
        duration_ms: int,
        inputs: list[str],
        outputs: list[dict],
        error: str | None = None,
    ) -> int | None:
        """Record one run. Never raises: returns None if the history couldn't be written."""
        with self._lock:
            if self._broken:
                return None
            try:
                db = self._conn()
                db.execute("BEGIN IMMEDIATE")
                try:
                    entry_id = db.execute(
                        "INSERT INTO entries (started_at, duration_ms, action, label, status, error) VALUES (?, ?, ?, ?, ?, ?)",
                        (started_at, duration_ms, action, label, "error" if error else "ok", error),
                    ).lastrowid
                    rows = [(entry_id, "input", i, p, None) for i, p in enumerate(inputs)]
                    rows += [(entry_id, "output", i, f["path"], f.get("size")) for i, f in enumerate(outputs)]
                    db.executemany("INSERT INTO files (entry_id, role, position, path, size) VALUES (?, ?, ?, ?, ?)", rows)
                    db.execute(
                        "DELETE FROM entries WHERE id IN (SELECT id FROM entries ORDER BY started_at DESC, id DESC LIMIT -1 OFFSET ?)",
                        (self._keep,),
                    )
                    db.execute("COMMIT")
                except BaseException:
                    db.execute("ROLLBACK")
                    raise
                return entry_id
            except (sqlite3.Error, OSError) as exc:
                if _transient(exc):
                    log.warning("Skipped a history entry, the database was busy: %s", exc)
                else:
                    log.warning("History is off for this session: %s", exc)
                    self._broken = True
                return None

    def delete(self, ids: list[int]) -> None:
        ids = [int(i) for i in ids]
        if not ids:
            return
        with self._lock:
            self._conn().execute(f"DELETE FROM entries WHERE id IN ({','.join('?' * len(ids))})", ids)

    def clear(self) -> None:
        with self._lock:
            db = self._conn()
            db.execute("DELETE FROM entries")
            # Give the space back and fold the WAL into the main file.
            db.execute("VACUUM")
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    # --- reads ---------------------------------------------------------------

    def list(self, query: str = "", limit: int = 50, before_id: int | None = None) -> dict:
        """Newest first. ``query`` matches the tool name or any file path; ``before_id`` pages on."""
        limit = max(1, min(int(limit), PAGE_MAX))
        where, args = [], []
        if before_id is not None:
            where.append("(e.started_at, e.id) < (SELECT started_at, id FROM entries WHERE id = ?)")
            args.append(int(before_id))
        text = query.strip()
        if text:
            pattern = "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            where.append(
                "(e.label LIKE ? ESCAPE '\\' OR EXISTS (SELECT 1 FROM files f WHERE f.entry_id = e.id AND f.path LIKE ? ESCAPE '\\'))"
            )
            args += [pattern, pattern]
        sql = "SELECT * FROM entries e"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY e.started_at DESC, e.id DESC LIMIT ?"
        with self._lock:
            db = self._conn()
            rows = db.execute(sql, [*args, limit + 1]).fetchall()
            more = len(rows) > limit
            rows = rows[:limit]
            files: dict[int, dict[str, list]] = {r["id"]: {"input": [], "output": []} for r in rows}
            if files:
                ids = list(files)
                for f in db.execute(
                    f"SELECT entry_id, role, path, size FROM files WHERE entry_id IN ({','.join('?' * len(ids))}) ORDER BY entry_id, role, position",
                    ids,
                ):
                    files[f["entry_id"]][f["role"]].append((f["path"], f["size"]))
        return {"entries": [_entry(r, files[r["id"]]) for r in rows], "more": more}


def _entry(row: sqlite3.Row, files: dict[str, list]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "started_at": row["started_at"],
        "duration_ms": row["duration_ms"],
        "action": row["action"],
        "label": row["label"],
        "status": row["status"],
        "error": row["error"],
        "inputs": [{"path": p, "name": _name(p)} for p, _ in files["input"]],
        # "exists": the file may have been moved or deleted since.
        "outputs": [{"path": p, "name": _name(p), "size": s, "exists": Path(p).exists()} for p, s in files["output"]],
    }


def _name(path: str) -> str:
    return Path(path).name or path


def _transient(exc: BaseException) -> bool:
    """Another connection held the lock for longer than the busy timeout; worth retrying later."""
    text = str(exc).lower()
    return isinstance(exc, sqlite3.OperationalError) and ("locked" in text or "busy" in text)


def _migrate(db: sqlite3.Connection) -> None:
    # Read the version under the write lock, so two connections opening a new file at once
    # can't both create the tables. Statement by statement: executescript() would commit midway.
    db.execute("BEGIN IMMEDIATE")
    try:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version > len(MIGRATIONS):
            raise sqlite3.DatabaseError(f"History database is from a newer version of the app (schema {version})")
        for step in range(version, len(MIGRATIONS)):
            for statement in _statements(MIGRATIONS[step]):
                db.execute(statement)
        db.execute(f"PRAGMA user_version = {len(MIGRATIONS)}")
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise


def _statements(script: str) -> list[str]:
    """Split a migration into statements (no semicolons inside our DDL strings)."""
    lines = [line.split("--", 1)[0] for line in script.splitlines()]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]
