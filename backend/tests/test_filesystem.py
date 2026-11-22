import os
import sys

import pytest

from toolbox.services import filesystem as fs


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "beta").mkdir()
    (tmp_path / "Alpha").mkdir()
    (tmp_path / "file10.txt").write_text("ten")
    (tmp_path / "file2.txt").write_text("two")
    (tmp_path / ".secret").write_text("x")
    return tmp_path


def test_list_dir_sorts_folders_first_then_naturally(tree):
    listing = fs.list_dir(str(tree))
    assert [e["name"] for e in listing["entries"]] == ["Alpha", "beta", "file2.txt", "file10.txt"]
    first_file = listing["entries"][2]
    assert first_file["size"] == 3 and first_file["ext"] == "txt" and not first_file["is_dir"]
    assert listing["entries"][0]["size"] is None


def test_list_dir_hidden_toggle(tree):
    names = {e["name"] for e in fs.list_dir(str(tree), show_hidden=True)["entries"]}
    assert ".secret" in names


@pytest.mark.skipif(sys.platform != "win32", reason="Windows hidden attribute")
def test_list_dir_respects_windows_hidden_attribute(tree):
    import ctypes

    target = tree / "hidden.txt"
    target.write_text("h")
    ctypes.windll.kernel32.SetFileAttributesW(str(target), 0x2)  # FILE_ATTRIBUTE_HIDDEN
    assert "hidden.txt" not in {e["name"] for e in fs.list_dir(str(tree))["entries"]}


def test_list_dir_truncates(tree, monkeypatch):
    monkeypatch.setattr(fs, "MAX_ENTRIES", 2)
    listing = fs.list_dir(str(tree))
    assert len(listing["entries"]) == 2
    assert listing["truncated"] is True


def test_list_dir_parent_and_crumbs(tree):
    listing = fs.list_dir(str(tree / "beta"))
    assert listing["parent"] == str(tree)
    assert listing["crumbs"][-1] == {"name": "beta", "path": str(tree / "beta")}
    assert listing["crumbs"][-2]["path"] == str(tree)


def test_filesystem_root_has_no_parent():
    root = os.path.abspath(os.sep)
    assert fs.list_dir(root)["parent"] is None


def test_resolve_dir(tree, monkeypatch):
    monkeypatch.setenv("TOOLBOX_TEST_DIR", str(tree))
    typed = '  "%TOOLBOX_TEST_DIR%"  ' if sys.platform == "win32" else "$TOOLBOX_TEST_DIR"
    assert fs.resolve_dir(typed) == str(tree)
    with pytest.raises(FileNotFoundError):
        fs.resolve_dir(str(tree / "missing"))
    with pytest.raises(FileNotFoundError):
        fs.resolve_dir(str(tree / "file2.txt"))
    with pytest.raises(ValueError):
        fs.resolve_dir("   ")


def test_display_name():
    assert fs.display_name(os.path.join("a", "b")) == "b"
    if sys.platform == "win32":
        assert fs.display_name("C:\\") == "C:"


def test_quick_locations_include_home_and_a_drive():
    locations = fs.quick_locations()
    kinds = [loc["kind"] for loc in locations]
    assert kinds[0] == "home"
    assert "drive" in kinds
    assert all(os.path.isdir(loc["path"]) for loc in locations if loc["kind"] != "drive")


def test_read_text_file(tree):
    (tree / "bom.txt").write_bytes(b"\xef\xbb\xbfhello")
    assert fs.read_text_file(str(tree / "bom.txt"))["text"] == "hello"


def test_read_text_file_rejects_binary_and_large(tree):
    (tree / "bin.dat").write_bytes(b"ab\x00cd")
    with pytest.raises(ValueError, match="binary"):
        fs.read_text_file(str(tree / "bin.dat"))
    with pytest.raises(ValueError, match="too large"):
        fs.read_text_file(str(tree / "file10.txt"), max_bytes=1)
