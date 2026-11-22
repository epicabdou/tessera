import json
import os

import pytest

from toolbox.services.settings import Settings


@pytest.fixture
def folders(tmp_path):
    paths = []
    for name in ("one", "two", "three"):
        (tmp_path / name).mkdir()
        paths.append(str(tmp_path / name))
    return paths


def pinned_paths(settings):
    return [p["path"] for p in settings.pinned()]


def test_defaults_when_no_file(tmp_path):
    snap = Settings(tmp_path / "settings.json").snapshot()
    assert snap == {
        "pinned": [],
        "show_hidden": False,
        "browser_root": None,
        "sidebar_width": 300,
        "preview_open": True,
        "preview_width": 360,
    }


def test_pin_unpin_and_persist(tmp_path, folders):
    store = tmp_path / "settings.json"
    s = Settings(store)
    s.pin(folders[0])
    s.pin(folders[1])
    s.pin(folders[0])  # already pinned, no index: no-op
    assert pinned_paths(s) == folders[:2]

    s.unpin(folders[0].upper())  # comparison follows the OS's case rules
    case_insensitive = os.path.normcase("A") == os.path.normcase("a")
    expected = folders[1:2] if case_insensitive else folders[:2]
    assert pinned_paths(Settings(store)) == expected


def test_pin_at_index_moves(tmp_path, folders):
    s = Settings(tmp_path / "settings.json")
    for f in folders:
        s.pin(f)
    s.pin(folders[2], index=0)
    assert pinned_paths(s) == [folders[2], folders[0], folders[1]]
    s.pin(folders[2], index=99)
    assert pinned_paths(s) == [folders[0], folders[1], folders[2]]


def test_pin_requires_existing_folder(tmp_path):
    s = Settings(tmp_path / "settings.json")
    with pytest.raises(FileNotFoundError):
        s.pin(str(tmp_path / "nope"))


def test_missing_pin_is_reported_and_still_movable(tmp_path, folders):
    s = Settings(tmp_path / "settings.json")
    s.pin(folders[0])
    s.pin(folders[1])
    (tmp_path / "one").rmdir()
    assert [p["exists"] for p in s.pinned()] == [False, True]
    s.pin(folders[0], index=1)
    assert pinned_paths(s) == [folders[1], folders[0]]


def test_preferences_validate(tmp_path):
    s = Settings(tmp_path / "settings.json")
    s.set_preference("show_hidden", True)
    s.set_preference("sidebar_width", 420)
    with pytest.raises(ValueError):
        s.set_preference("sidebar_width", 5)
    with pytest.raises(ValueError):
        s.set_preference("show_hidden", "yes")
    with pytest.raises(ValueError):
        s.set_preference("unknown", 1)
    reloaded = Settings(tmp_path / "settings.json").snapshot()
    assert reloaded["show_hidden"] is True and reloaded["sidebar_width"] == 420


def test_corrupt_or_invalid_file_falls_back(tmp_path):
    store = tmp_path / "settings.json"
    store.write_text("{not json")
    assert Settings(store).snapshot()["pinned"] == []
    store.write_text(json.dumps({"pinned": ["x", 3], "sidebar_width": "wide", "show_hidden": True}))
    snap = Settings(store).snapshot()
    assert [p["path"] for p in snap["pinned"]] == ["x"]
    assert snap["sidebar_width"] == 300 and snap["show_hidden"] is True


def test_save_survives_a_briefly_locked_file(tmp_path, monkeypatch):
    """On Windows, renaming over settings.json fails while something has it open
    (antivirus, backup, another reader). The save should retry, not lose the change."""
    import toolbox.services.filesystem as fs

    real_replace = os.replace
    failures = {"left": 2}

    def flaky_replace(src, dst):
        if failures["left"]:
            failures["left"] -= 1
            raise PermissionError("locked")
        real_replace(src, dst)

    monkeypatch.setattr(fs.os, "replace", flaky_replace)
    store = tmp_path / "settings.json"
    Settings(store).set_preference("show_hidden", True)
    assert Settings(store).snapshot()["show_hidden"] is True
    assert not store.with_suffix(".tmp").exists()


def test_save_gives_up_and_cleans_up(tmp_path, monkeypatch):
    import toolbox.services.filesystem as fs

    def always_locked(src, dst):
        raise PermissionError("locked")

    monkeypatch.setattr(fs.os, "replace", always_locked)
    monkeypatch.setattr(fs.time, "sleep", lambda s: None)
    store = tmp_path / "settings.json"
    with pytest.raises(PermissionError):
        Settings(store).set_preference("show_hidden", True)
    assert not store.with_suffix(".tmp").exists()
