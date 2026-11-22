import inspect
import sqlite3
import threading
from pathlib import Path

import pytest

from tests.samples import make_numbered
from toolbox.api import Api
from toolbox.services.history import History
from toolbox.services.settings import Settings


def _add(h: History, label="Merge PDF", inputs=("a.pdf",), outputs=("out.pdf",), error=None, at=1000.0):
    return h.add("pdf_merge", label, at, 12, list(inputs), [{"path": p, "size": 10} for p in outputs], error)


# --- the store ---------------------------------------------------------------------------


def test_uses_wal(tmp_path):
    db = tmp_path / "history.db"
    h = History(db)
    _add(h)
    assert sqlite3.connect(db).execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    h.close()


def test_round_trip(tmp_path):
    out = tmp_path / "merged.pdf"
    out.write_bytes(b"%PDF")
    h = History(tmp_path / "history.db")
    entry_id = _add(h, inputs=["C:/x/a.pdf", "C:/x/b.pdf"], outputs=[str(out), str(tmp_path / "gone.pdf")])

    [e] = h.list()["entries"]
    assert e["id"] == entry_id and e["label"] == "Merge PDF" and e["status"] == "ok" and e["error"] is None
    assert e["duration_ms"] == 12 and e["started_at"] == 1000.0
    assert [i["name"] for i in e["inputs"]] == ["a.pdf", "b.pdf"]
    assert [(o["name"], o["exists"]) for o in e["outputs"]] == [("merged.pdf", True), ("gone.pdf", False)]


def test_failures_are_kept(tmp_path):
    h = History(tmp_path / "history.db")
    _add(h, outputs=[], error="The file is damaged")
    [e] = h.list()["entries"]
    assert e["status"] == "error" and e["error"] == "The file is damaged" and e["outputs"] == []


def test_newest_first_and_paging(tmp_path):
    h = History(tmp_path / "history.db")
    ids = [_add(h, label=f"Tool {i}", at=1000.0 + i) for i in range(5)]
    first = h.list(limit=2)
    assert [e["id"] for e in first["entries"]] == [ids[4], ids[3]] and first["more"]
    second = h.list(limit=2, before_id=first["entries"][-1]["id"])
    assert [e["id"] for e in second["entries"]] == [ids[2], ids[1]] and second["more"]
    last = h.list(limit=2, before_id=second["entries"][-1]["id"])
    assert [e["id"] for e in last["entries"]] == [ids[0]] and not last["more"]


def test_search_matches_tool_or_any_file(tmp_path):
    h = History(tmp_path / "history.db")
    _add(h, label="Merge PDF", inputs=["C:/docs/invoice.pdf"], outputs=["C:/docs/merged.pdf"])
    _add(h, label="Compress Image", inputs=["C:/pics/cat.png"], outputs=["C:/pics/cat_small.png"])
    _add(h, label="Rotate PDF", inputs=["C:/docs/100%_final.pdf"], outputs=["C:/docs/r.pdf"])
    labels = lambda q: [e["label"] for e in h.list(q)["entries"]]  # noqa: E731
    assert labels("compress") == ["Compress Image"]
    assert labels("invoice") == ["Merge PDF"]
    assert labels("merged") == ["Merge PDF"]
    assert labels("100%") == ["Rotate PDF"]  # % is matched literally, not as a wildcard
    assert labels("_final") == ["Rotate PDF"]
    assert labels("nothing") == []


def test_keeps_only_the_newest(tmp_path):
    h = History(tmp_path / "history.db", keep=3)
    for i in range(5):
        _add(h, label=f"Tool {i}", at=1000.0 + i)
    assert [e["label"] for e in h.list()["entries"]] == ["Tool 4", "Tool 3", "Tool 2"]
    # Their files went with them.
    assert sqlite3.connect(tmp_path / "history.db").execute("SELECT COUNT(*) FROM files").fetchone()[0] == 6


def test_delete_and_clear(tmp_path):
    db = tmp_path / "history.db"
    h = History(db)
    a, b = _add(h), _add(h)
    h.delete([a])
    assert [e["id"] for e in h.list()["entries"]] == [b]
    h.clear()
    assert h.list()["entries"] == []
    assert sqlite3.connect(db).execute("SELECT COUNT(*) FROM files").fetchone()[0] == 0


def test_two_writers_at_once(tmp_path):
    """Two app windows (two connections) writing from several threads: nothing lost, nothing locked."""
    db = tmp_path / "history.db"
    first, second = History(db), History(db)
    errors: list[Exception] = []

    def work(h: History, n: int) -> None:
        try:
            for i in range(25):
                assert _add(h, label=f"w{n}-{i}") is not None
        except Exception as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(h, n)) for n, h in enumerate([first, second, first, second])]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert len(first.list(limit=200)["entries"]) == 100


def test_reopening_keeps_entries(tmp_path):
    db = tmp_path / "history.db"
    h = History(db)
    _add(h)
    h.close()
    assert len(History(db).list()["entries"]) == 1


def test_unwritable_history_is_switched_off_quietly(tmp_path):
    blocked = tmp_path / "history.db"
    blocked.mkdir()  # a folder where the database file should be
    h = History(blocked)
    assert _add(h) is None
    assert _add(h) is None  # stays off, no retry storm


def test_refuses_a_newer_schema(tmp_path):
    db = tmp_path / "history.db"
    con = sqlite3.connect(db)
    con.execute("PRAGMA user_version = 99")
    con.close()
    assert _add(History(db)) is None
    with pytest.raises(sqlite3.DatabaseError):
        History(db).list()


# --- recording through the Api -------------------------------------------------------------


def _api(tmp_path: Path) -> tuple[Api, Settings]:
    settings = Settings(tmp_path / "settings.json")
    return Api(settings, components=object(), history=History(tmp_path / "history.db")), settings


def test_recorded_methods_keep_their_parameters_for_pywebview(tmp_path):
    api, _ = _api(tmp_path)
    # pywebview builds the JS functions from getfullargspec, which ignores functools.wraps.
    assert inspect.getfullargspec(api.pdf_merge).args == ["self", "items", "output", "bookmarks"]
    assert inspect.getfullargspec(api.pdf_rotate).args == ["self", "path", "output", "rotations"]


def test_a_tool_run_is_recorded(tmp_path):
    api, _ = _api(tmp_path)
    a, b = make_numbered(tmp_path / "a.pdf", 2), make_numbered(tmp_path / "b.pdf", 1)
    out = tmp_path / "merged.pdf"
    api.pdf_merge([{"path": str(a)}, {"path": str(b)}], str(out))

    [e] = api.history_list()["entries"]
    assert e["label"] == "Merge PDF" and e["action"] == "pdf_merge" and e["status"] == "ok"
    assert [i["path"] for i in e["inputs"]] == [str(a), str(b)]
    assert [(o["path"], o["exists"]) for o in e["outputs"]] == [(str(out), True)]
    assert e["outputs"][0]["size"] == out.stat().st_size


def test_several_outputs_are_recorded(tmp_path):
    api, _ = _api(tmp_path)
    src = make_numbered(tmp_path / "doc.pdf", 3)
    (tmp_path / "parts").mkdir()
    api.pdf_split(str(src), str(tmp_path / "parts"), "every", "1")
    [e] = api.history_list()["entries"]
    assert e["label"] == "Split PDF" and len(e["outputs"]) == 3


def test_a_failed_run_is_recorded_and_still_raises(tmp_path):
    api, _ = _api(tmp_path)
    with pytest.raises(Exception):
        api.pdf_rotate(str(tmp_path / "missing.pdf"), str(tmp_path / "out.pdf"), [90])
    [e] = api.history_list()["entries"]
    assert e["status"] == "error" and e["error"] and e["outputs"] == []


def test_passwords_never_reach_the_database(tmp_path):
    api, _ = _api(tmp_path)
    src = make_numbered(tmp_path / "doc.pdf", 1)
    api.pdf_protect(str(src), str(tmp_path / "locked.pdf"), "open-sesame-123", "owner-secret-456", {})
    raw = b"".join(p.read_bytes() for p in tmp_path.glob("history.db*"))
    assert b"open-sesame-123" not in raw and b"owner-secret-456" not in raw
    assert api.history_list()["entries"][0]["label"] == "Protect PDF"


def test_turning_history_off_stops_recording(tmp_path):
    api, settings = _api(tmp_path)
    src = make_numbered(tmp_path / "doc.pdf", 1)
    api.set_preference("history_enabled", False)
    api.pdf_rotate(str(src), str(tmp_path / "r.pdf"), [90])
    page = api.history_list()
    assert page["entries"] == [] and page["enabled"] is False


def test_labels_follow_the_tool(tmp_path):
    from toolbox.api import _OFFICE_LABELS, _history_inputs, _history_outputs

    assert _OFFICE_LABELS["word"] == "Word to PDF"
    assert _history_inputs({"kind": "url", "value": "https://example.com"}) == ["https://example.com"]
    assert _history_inputs({"kind": "code", "value": "<p>hi</p>"}) == []  # HTML source isn't a file
    assert _history_inputs({"path": "a", "paths": ["a", "b"]}) == ["a", "b"]  # de-duplicated
    assert _history_outputs([{"path": "x", "size": 1}, {"error": "bad"}]) == [{"path": "x", "size": 1}]
    assert _history_outputs({"files": [{"path": "y"}], "folder": "f"}) == [{"path": "y", "size": None}]
    assert _history_outputs(None) == []


# --- project links (About box) ----------------------------------------------------------------


def test_open_link_only_opens_project_pages(tmp_path, monkeypatch):
    import webbrowser

    from toolbox import LINKS

    opened: list[str] = []
    monkeypatch.setattr(webbrowser, "open", opened.append)
    api, _ = _api(tmp_path)
    api.open_link("source")
    assert opened == [LINKS["source"]]
    with pytest.raises(ValueError):
        api.open_link("https://example.com")
    assert opened == [LINKS["source"]]
