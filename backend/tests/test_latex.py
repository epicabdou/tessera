import pytest
from pypdf import PdfReader

from toolbox.paths import user_data_dir
from toolbox.services import latex
from toolbox.services.components import Components

PDFLATEX_LOG = r"""
./main.tex:7: Undefined control sequence.
l.7 \badcommand

LaTeX Warning: Reference `fig:x' on page 1 undefined on input line 12.
! Missing $ inserted.
<inserted text>
                $
l.15 x^2

"""

TECTONIC_ERR = """note: Running TeX ...
error: main.tex:3: Undefined control sequence
error: halted on potentially-recoverable error as specified
"""


def test_parse_log_pdflatex():
    items = latex.parse_log(PDFLATEX_LOG, "main.tex")
    errors = [(m["line"], m["message"]) for m in items if m["kind"] == "error"]
    assert (7, "Undefined control sequence.") in errors
    assert (15, "Missing $ inserted.") in errors
    warnings = [(m["line"], m["message"]) for m in items if m["kind"] == "warning"]
    assert warnings == [(12, "Reference `fig:x' on page 1 undefined")]


def test_parse_log_tectonic():
    items = latex.parse_log(TECTONIC_ERR, "main.tex")
    assert items[0] == {"kind": "error", "message": "Undefined control sequence", "line": 3, "file": "main.tex"}
    assert any(m["line"] is None and "halted" in m["message"] for m in items)


def test_pick_engine():
    engines = {"tectonic": None, "latexmk": None, "pdflatex": "C:/tex/pdflatex.exe", "xelatex": "x", "lualatex": None}
    assert latex.pick_engine(engines) == ("pdflatex", "C:/tex/pdflatex.exe")
    assert latex.pick_engine(engines, "xelatex") == ("xelatex", "x")
    assert latex.pick_engine(engines, "lualatex") is None
    assert latex.pick_engine({k: None for k in engines}) is None


@pytest.fixture
def engine():
    comps = Components(user_data_dir())
    chosen = latex.pick_engine(comps.latex_engines())
    if not chosen:
        pytest.skip("no LaTeX engine installed")
    return comps.tectonic_path


def test_compile_success(tmp_path, engine):
    src = tmp_path / "hello.tex"
    src.write_text(r"\documentclass{article}\begin{document}Hello from \LaTeX{} in Toolbox.\end{document}", encoding="utf-8")
    res = latex.compile_tex(str(src), tectonic_path=engine)
    assert res["ok"] and res["pdf"] == str(tmp_path / "hello.pdf")
    assert "Hello from" in PdfReader(res["pdf"]).pages[0].extract_text()
    assert not [m for m in res["messages"] if m["kind"] == "error"]


def test_compile_error_points_at_line(tmp_path, engine):
    src = tmp_path / "broken.tex"
    src.write_text("\\documentclass{article}\n\\begin{document}\nfine\n\\nosuchcommand\n\\end{document}\n", encoding="utf-8")
    res = latex.compile_tex(str(src), tectonic_path=engine)
    assert not res["ok"]
    err = next(m for m in res["messages"] if m["kind"] == "error")
    assert err["line"] == 4 and "Undefined control sequence" in err["message"]


def test_compile_rejects_non_tex(tmp_path):
    (tmp_path / "x.txt").write_text("x")
    with pytest.raises(ValueError):
        latex.compile_tex(str(tmp_path / "x.txt"))
