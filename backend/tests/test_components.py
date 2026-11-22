"""The LaTeX engine setup (services/components.py), without any download or real compile."""

import threading

import pytest

from toolbox.services import components as comp
from toolbox.services import latex


def _engines(monkeypatch, **found):
    names = {name: None for name in latex.ENGINES}
    monkeypatch.setattr(latex, "find_engines", lambda tectonic_path=None: {**names, **found})


def _no_download(self):
    raise AssertionError("must not download")


def test_missing_when_no_engine_and_setup_never_ran(tmp_path, monkeypatch):
    _engines(monkeypatch)
    assert comp.Components(tmp_path).status()["latex"]["state"] == "missing"


def test_ready_when_an_engine_is_there(tmp_path, monkeypatch):
    _engines(monkeypatch, pdflatex="C:/texlive/pdflatex.exe")
    status = comp.Components(tmp_path).status()["latex"]
    assert status["state"] == "ready" and status["engine"] == "pdflatex"


def test_tectonic_on_path_is_warmed_up_not_downloaded(tmp_path, monkeypatch):
    _engines(monkeypatch, tectonic="C:/tools/tectonic.exe")
    compiled: list[str] = []
    monkeypatch.setattr(comp.Components, "_download", _no_download)
    monkeypatch.setattr(latex, "compile_tex", lambda doc, engine, exe, timeout=0: compiled.append(exe) or {"ok": True, "messages": []})

    c = comp.Components(tmp_path)
    c.ensure_latex()

    assert compiled == ["C:/tools/tectonic.exe"]
    assert c.status()["latex"]["state"] == "ready"
    assert (tmp_path / "tectonic" / ".warmed").is_file()


def test_overlapping_calls_set_up_once(tmp_path, monkeypatch):
    """Start-up and an "Install now" click at the same time: one setup, and no "missing" meanwhile."""
    _engines(monkeypatch, tectonic="C:/tools/tectonic.exe")
    started, release = threading.Event(), threading.Event()
    compiled: list[str] = []

    def slow_compile(doc, engine, exe, timeout=0):
        compiled.append(exe)
        started.set()
        release.wait(10)
        return {"ok": True, "messages": []}

    monkeypatch.setattr(latex, "compile_tex", slow_compile)
    c = comp.Components(tmp_path)
    first = threading.Thread(target=c.ensure_latex)
    first.start()
    assert started.wait(10)

    c.ensure_latex()  # returns at once: the first call owns the setup
    assert c.status()["latex"]["state"] == "warming"

    release.set()
    first.join(10)
    assert compiled == ["C:/tools/tectonic.exe"]
    assert c.status()["latex"]["state"] == "ready"


def test_no_engine_downloads_then_warms_its_own_copy(tmp_path, monkeypatch):
    _engines(monkeypatch)
    compiled: list[str] = []

    def fake_download(self):
        self._dir.mkdir(parents=True, exist_ok=True)
        (self._dir / "tectonic.exe").write_bytes(b"MZ")

    monkeypatch.setattr(comp.Components, "_download", fake_download)
    monkeypatch.setattr(latex, "compile_tex", lambda doc, engine, exe, timeout=0: compiled.append(exe) or {"ok": True, "messages": []})
    c = comp.Components(tmp_path)
    c.ensure_latex()
    assert compiled == [c.tectonic_path]


def test_setup_failure_is_reported(tmp_path, monkeypatch):
    _engines(monkeypatch)

    def broken(self):
        raise OSError("offline")

    monkeypatch.setattr(comp.Components, "_download", broken)
    c = comp.Components(tmp_path)
    c.ensure_latex()
    status = c.status()["latex"]
    assert status["state"] == "error" and "offline" in status["error"]


@pytest.fixture(autouse=True)
def _no_real_engines(monkeypatch):
    # Never let a test touch a real LaTeX install or the network.
    monkeypatch.setattr(comp.Components, "_download", _no_download, raising=True)
