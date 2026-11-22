from toolbox import APP_NAME
from toolbox.paths import user_data_dir


def _local(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    return tmp_path


def test_fresh_install_creates_folder(monkeypatch, tmp_path):
    root = _local(monkeypatch, tmp_path)
    assert user_data_dir() == root / APP_NAME
    assert (root / APP_NAME).is_dir()


def test_moves_data_from_old_name(monkeypatch, tmp_path):
    root = _local(monkeypatch, tmp_path)
    old = root / "Toolbox"
    (old / "models").mkdir(parents=True)
    (old / "settings.json").write_text('{"pins": []}', encoding="utf-8")
    (old / "models" / "x.onnx").write_bytes(b"model")

    path = user_data_dir()

    assert path == root / APP_NAME
    assert not old.exists()
    assert (path / "settings.json").read_text(encoding="utf-8") == '{"pins": []}'
    assert (path / "models" / "x.onnx").read_bytes() == b"model"


def test_leaves_unrelated_toolbox_folder_alone(monkeypatch, tmp_path):
    root = _local(monkeypatch, tmp_path)
    other = root / "Toolbox"
    other.mkdir()
    (other / "something-else.db").write_bytes(b"not ours")

    assert user_data_dir() == root / APP_NAME
    assert (other / "something-else.db").is_file()


def test_existing_folder_wins_over_old_one(monkeypatch, tmp_path):
    root = _local(monkeypatch, tmp_path)
    (root / APP_NAME).mkdir()
    (root / APP_NAME / "settings.json").write_text("new", encoding="utf-8")
    (root / "Toolbox").mkdir()
    (root / "Toolbox" / "settings.json").write_text("old", encoding="utf-8")

    path = user_data_dir()

    assert (path / "settings.json").read_text(encoding="utf-8") == "new"
    assert (root / "Toolbox" / "settings.json").read_text(encoding="utf-8") == "old"
