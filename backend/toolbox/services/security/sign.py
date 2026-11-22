"""Digital signatures (pyHanko, PAdES) and the certificates they use.

Electronic signatures (a drawn/typed/uploaded image placed on the page) are applied
by editing.edit.apply_edits; this module handles cryptographic signing.
"""

from __future__ import annotations

import datetime as dt
import io
import logging
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from pypdf import PdfReader

from ..editing.geometry import visual_rect_to_user
from ..filesystem import replace_with_retry
from ..pdf.common import unique_path


def create_certificate(output: str, password: str, name: str, email: str = "", organization: str = "", country: str = "", years: int = 3) -> dict:
    """A self-signed signing certificate (.pfx). Fine for your own approvals; recipients
    will see it as "not trusted" unless they trust it explicitly."""
    if len(password) < 4:
        raise ValueError("Choose a password of at least 4 characters for the certificate")
    if not name.strip():
        raise ValueError("Enter the signer's name")
    attrs = [x509.NameAttribute(NameOID.COMMON_NAME, name.strip())]
    if organization.strip():
        attrs.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization.strip()))
    if len(country.strip()) == 2:
        attrs.append(x509.NameAttribute(NameOID.COUNTRY_NAME, country.strip().upper()))
    if email.strip():
        attrs.append(x509.NameAttribute(NameOID.EMAIL_ADDRESS, email.strip()))
    subject = x509.Name(attrs)
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    now = dt.datetime.now(dt.timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=365 * years))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=True, key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
    )
    if email.strip():
        builder = builder.add_extension(x509.SubjectAlternativeName([x509.RFC822Name(email.strip())]), critical=False)
    cert = builder.sign(key, hashes.SHA256())
    data = pkcs12.serialize_key_and_certificates(
        name.strip().encode(), key, cert, None, serialization.BestAvailableEncryption(password.encode())
    )
    out = Path(output)
    if out.suffix.lower() not in (".pfx", ".p12"):
        out = out.with_name(out.name + ".pfx")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".{out.name}.{os.getpid()}.tmp")
    tmp.write_bytes(data)
    replace_with_retry(tmp, out)
    return {"path": str(out), "name": out.name, "subject": name.strip(), "valid_until": cert.not_valid_after_utc.date().isoformat()}


def certificate_info(path: str, password: str) -> dict:
    try:
        _key, cert, _extra = pkcs12.load_key_and_certificates(Path(path).read_bytes(), password.encode())
    except ValueError:
        raise ValueError("Wrong certificate password, or not a .pfx/.p12 file") from None
    if cert is None:
        raise ValueError("The file has no certificate")
    cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    return {
        "subject": cn[0].value if cn else cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "self_signed": cert.issuer == cert.subject,
        "valid_from": cert.not_valid_before_utc.date().isoformat(),
        "valid_until": cert.not_valid_after_utc.date().isoformat(),
        "expired": cert.not_valid_after_utc < dt.datetime.now(dt.timezone.utc),
    }


def _free_field_name(path: str) -> str:
    fields = PdfReader(path).get_fields() or {}
    n = 1
    while f"Signature{n}" in fields:
        n += 1
    return f"Signature{n}"


def sign(
    path: str,
    output: str,
    certificate: str,
    password: str,
    reason: str = "",
    location: str = "",
    contact: str = "",
    visible: dict | None = None,
) -> dict:
    """Digitally sign. visible = {page, x, y, w, h} (displayed coordinates) adds a stamp box."""
    from pyhanko import stamp
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import fields, signers

    info = certificate_info(certificate, password)
    if info["expired"]:
        raise ValueError("The certificate has expired")
    signer = signers.SimpleSigner.load_pkcs12(pfx_file=certificate, passphrase=password.encode())
    if signer is None:
        raise ValueError("Couldn't load the certificate")
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise ValueError("Remove the PDF's password before signing")
    name = _free_field_name(path)
    data = Path(path).read_bytes()
    writer = IncrementalPdfFileWriter(io.BytesIO(data), strict=False)
    style = None
    if visible:
        page_index = int(visible.get("page", 0))
        if not 0 <= page_index < len(reader.pages):
            raise ValueError(f"Page {page_index + 1} doesn't exist")
        box = visual_rect_to_user(reader.pages[page_index], float(visible["x"]), float(visible["y"]), float(visible["w"]), float(visible["h"]))
        fields.append_signature_field(writer, fields.SigFieldSpec(name, on_page=page_index, box=tuple(int(round(v)) for v in box)))
        lines = ["Digitally signed by %(signer)s", "Date: %(ts)s"]
        if reason:
            lines.append(f"Reason: {reason}")
        style = stamp.TextStampStyle(stamp_text="\n".join(lines), timestamp_format="%Y-%m-%d %H:%M %Z")
    meta = signers.PdfSignatureMetadata(
        field_name=name,
        reason=reason or None,
        location=location or None,
        contact_info=contact or None,
        md_algorithm="sha256",
        subfilter=fields.SigSeedSubFilter.PADES,
    )
    pdf_signer = signers.PdfSigner(meta, signer=signer, stamp_style=style, new_field_spec=None)
    out = Path(output)
    if out.suffix.lower() != ".pdf":
        out = out.with_name(out.name + ".pdf")
    tmp = out.with_name(f".{out.stem}.{os.getpid()}.signing.pdf")
    try:
        with open(tmp, "wb") as fh:
            pdf_signer.sign_pdf(writer, output=fh)
        replace_with_retry(tmp, out)
    finally:
        tmp.unlink(missing_ok=True)
    return {"path": str(out), "name": out.name, "size": out.stat().st_size, "page_count": len(reader.pages), "field": name, "signer": info["subject"]}


def verify(path: str) -> list[dict]:
    """Check every signature: is the signed content intact, and is the signer trusted?"""
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko_certvalidator import ValidationContext

    # pyHanko logs a full traceback for every untrusted (e.g. self-signed) signer; that is
    # an expected result here, reported in "trusted", not an error worth logging.
    logging.getLogger("pyhanko.sign.validation").setLevel(logging.ERROR)
    results = []
    with open(path, "rb") as fh:
        reader = PdfFileReader(fh, strict=False)
        for sig in reader.embedded_signatures:
            entry = {"field": sig.field_name, "signer": None, "signed_at": None, "intact": False, "valid": False, "trusted": False, "covers_whole_file": False, "error": None}
            try:
                status = validate_pdf_signature(sig, ValidationContext(allow_fetching=False))
                cert = status.signing_cert
                names = cert.subject.native if cert else {}
                entry.update(
                    signer=(names.get("common_name") or cert.subject.human_friendly) if cert else None,
                    signer_details=cert.subject.human_friendly if cert else None,
                    signed_at=status.signer_reported_dt.isoformat() if status.signer_reported_dt else None,
                    intact=bool(status.intact),
                    valid=bool(status.valid),
                    trusted=bool(status.trusted),
                    covers_whole_file=str(status.coverage).endswith("ENTIRE_FILE"),
                )
                sig_obj = sig.sig_object
                entry["reason"] = str(sig_obj.get("/Reason")) if "/Reason" in sig_obj else None
                entry["location"] = str(sig_obj.get("/Location")) if "/Location" in sig_obj else None
            except Exception as exc:  # noqa: BLE001 - report, don't crash the list
                entry["error"] = str(exc)
            results.append(entry)
    return results


def suggest_certificate_path(name: str) -> str:
    from ..filesystem import known_folder

    folder = Path(known_folder("documents") or Path.home())
    safe = "".join(c for c in name if c.isalnum() or c in " -_").strip() or "signature"
    return str(unique_path(folder / f"{safe} certificate.pfx"))
