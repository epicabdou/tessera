import re

import pytest
from PIL import Image
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from samples import make_report
from toolbox.services.security import optimize, protect, sign


@pytest.fixture
def report(tmp_path):
    return str(make_report(tmp_path / "report.pdf"))


# --- protect -----------------------------------------------------------------------


def test_protect_and_unlock(report, tmp_path):
    locked = tmp_path / "locked.pdf"
    res = protect.protect(report, str(locked), user_password="s3cret", permissions={"copy": False, "print": True})
    assert res["open_password"] and res["restricted"] == ["copy"]
    info = protect.security_info(str(locked))
    assert info["encrypted"] and info["needs_password"]
    r = PdfReader(locked)
    assert r.decrypt("s3cret") and "Quarterly" in r.pages[0].extract_text()
    with pytest.raises(ValueError, match="wrong"):
        protect.unlock(str(locked), str(tmp_path / "x.pdf"), "nope")
    open_ = tmp_path / "open.pdf"
    protect.unlock(str(locked), str(open_), "s3cret")
    plain = protect.security_info(str(open_))
    assert not plain["encrypted"] and plain["page_count"] >= 1


def test_restrictions_without_open_password(report, tmp_path):
    out = tmp_path / "r.pdf"
    protect.protect(report, str(out), permissions={"modify": False, "copy": False})
    info = protect.security_info(str(out))
    assert info["encrypted"] and not info["needs_password"] and info["page_count"] == 2
    assert info["permissions"]["copy"] is False and info["permissions"]["print"] is True
    with pytest.raises(ValueError, match="open password"):
        protect.protect(report, str(out))


def test_cannot_re_protect_a_locked_file(report, tmp_path):
    locked = tmp_path / "locked.pdf"
    protect.protect(report, str(locked), user_password="pw")
    with pytest.raises(ValueError, match="already password-protected"):
        protect.protect(str(locked), str(tmp_path / "again.pdf"), user_password="other")


# --- sign ----------------------------------------------------------------------------


@pytest.fixture
def cert(tmp_path):
    res = sign.create_certificate(str(tmp_path / "me"), "pfx-pass", "Amina Benali", "amina@example.com", "Toolbox QA", "DZ")
    assert res["name"] == "me.pfx"
    return res["path"]


def test_certificate_info(cert):
    info = sign.certificate_info(cert, "pfx-pass")
    assert info["subject"] == "Amina Benali" and info["self_signed"] and not info["expired"]
    with pytest.raises(ValueError, match="Wrong certificate password"):
        sign.certificate_info(cert, "bad")


def test_sign_verify_and_detect_tampering(report, cert, tmp_path):
    signed = tmp_path / "signed.pdf"
    res = sign.sign(report, str(signed), cert, "pfx-pass", reason="Approved", location="Oran", visible={"page": 0, "x": 330, "y": 700, "w": 200, "h": 60})
    assert res["field"] == "Signature1" and res["signer"] == "Amina Benali"
    (sig,) = sign.verify(str(signed))
    assert sig["intact"] and sig["valid"] and not sig["trusted"]  # self-signed: valid but untrusted
    assert "Amina Benali" in sig["signer"] and sig["reason"] == "Approved" and sig["covers_whole_file"]

    # A second signature gets its own field and keeps the first valid.
    twice = tmp_path / "twice.pdf"
    assert sign.sign(str(signed), str(twice), cert, "pfx-pass")["field"] == "Signature2"
    assert [s["intact"] for s in sign.verify(str(twice))] == [True, True]

    data = bytearray(signed.read_bytes())
    m = re.search(rb"Quarterly", data) or re.search(rb"/Type\s*/Page\b", data)
    pos = m.start() if m else len(data) // 3
    data[pos] = data[pos] ^ 0x01
    tampered = tmp_path / "tampered.pdf"
    tampered.write_bytes(bytes(data))
    (bad,) = sign.verify(str(tampered))
    assert not bad["intact"] or bad["error"]


# --- compress --------------------------------------------------------------------------


def test_compress_shrinks_photos(tmp_path):
    import random

    random.seed(1)
    photo = tmp_path / "photo.jpg"
    img = Image.effect_noise((3000, 2000), 64).convert("RGB")
    img.save(photo, quality=98)
    src = tmp_path / "big.pdf"
    c = canvas.Canvas(str(src), pagesize=A4)
    c.drawString(72, 800, "Holiday photos")
    c.drawImage(str(photo), 72, 300, width=450, height=300)
    c.save()
    out = tmp_path / "small.pdf"
    res = optimize.compress(str(src), str(out), "high")
    assert res["images_recompressed"] == 1 and res["after"] < res["before"] * 0.5
    assert "Holiday photos" in PdfReader(out).pages[0].extract_text()


def test_compress_never_grows(report, tmp_path):
    res = optimize.compress(report, str(tmp_path / "c.pdf"), "low")
    assert res["after"] <= res["before"]


# --- repair ----------------------------------------------------------------------------


def test_repair_broken_xref(report, tmp_path):
    data = (tmp_path / "report.pdf").read_bytes()
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(re.sub(rb"startxref\s+\d+", b"startxref\n999999", data))
    report_ = optimize.analyze(str(broken))
    assert not report_["healthy"] and report_["issues"]
    res = optimize.repair(str(broken), str(tmp_path / "fixed.pdf"))
    assert res["page_count"] == 2
    assert optimize.analyze(res["path"])["healthy"]


def test_repair_truncated_file(report, tmp_path):
    data = (tmp_path / "report.pdf").read_bytes()
    cut = tmp_path / "cut.pdf"
    cut.write_bytes(data[: int(len(data) * 0.8)])
    assert "end-of-file marker" in " ".join(optimize.analyze(str(cut))["issues"])
    res = optimize.repair(str(cut), str(tmp_path / "fixed.pdf"))
    assert res["page_count"] >= 1 and PdfReader(res["path"]).pages[0].extract_text()


def test_repair_hopeless(tmp_path):
    junk = tmp_path / "junk.pdf"
    junk.write_bytes(b"%PDF-1.7\nnothing to see here")
    with pytest.raises(ValueError, match="too damaged"):
        optimize.repair(str(junk), str(tmp_path / "out.pdf"))
