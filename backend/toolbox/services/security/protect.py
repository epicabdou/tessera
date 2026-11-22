"""Passwords, encryption and usage restrictions (and removing them)."""

from __future__ import annotations

import secrets
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions as P

from ..pdf.common import write_pdf

PERMISSIONS = {
    "print": P.PRINT,
    "print_high": P.PRINT_TO_REPRESENTATION,
    "modify": P.MODIFY,
    "copy": P.EXTRACT,
    "annotate": P.ADD_OR_MODIFY,
    "fill_forms": P.FILL_FORM_FIELDS,
    "accessibility": P.EXTRACT_TEXT_AND_GRAPHICS,
    "assemble": P.ASSEMBLE_DOC,
}
ALGORITHMS = ("AES-256", "AES-128", "RC4-128")


def security_info(path: str) -> dict:
    """Works on protected files too (doesn't need the password)."""
    file = Path(path)
    if not file.is_file():
        raise FileNotFoundError(f"Not a file: {file}")
    reader = PdfReader(file)
    info = {"path": str(file), "name": file.name, "size": file.stat().st_size, "encrypted": reader.is_encrypted, "needs_password": False, "permissions": {}}
    if not reader.is_encrypted:
        info["permissions"] = {k: True for k in PERMISSIONS}
        info["page_count"] = len(reader.pages)
        return info
    try:
        opened = bool(reader.decrypt(""))
    except Exception:  # noqa: BLE001 - unsupported encryption; treat as needing a password
        opened = False
    info["needs_password"] = not opened
    try:
        flags = reader.user_access_permissions
        info["permissions"] = {k: bool(flags & v) for k, v in PERMISSIONS.items()}
    except Exception:  # noqa: BLE001
        info["permissions"] = {}
    if opened:
        info["page_count"] = len(reader.pages)
    return info


def protect(path: str, output: str, user_password: str = "", owner_password: str = "", permissions: dict | None = None, algorithm: str = "AES-256") -> dict:
    """user_password: needed to open the file (may be empty).
    owner_password: needed to change restrictions; a random one is used if empty.
    permissions: {name: allowed} for the keys in PERMISSIONS (missing = allowed)."""
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unknown encryption: {algorithm!r}")
    reader = PdfReader(path)
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError("This PDF is already password-protected. Remove the protection first.")
    allowed = {k: True for k in PERMISSIONS} | {k: bool(v) for k, v in (permissions or {}).items() if k in PERMISSIONS}
    restricted = not all(allowed.values())
    if not user_password and not restricted:
        raise ValueError("Set an open password, or restrict at least one permission")
    flags = P(0)
    for key, flag in PERMISSIONS.items():
        if allowed[key]:
            flags |= flag
    writer = PdfWriter(clone_from=reader)
    writer.encrypt(
        user_password=user_password,
        owner_password=owner_password or secrets.token_urlsafe(24),
        permissions_flag=flags,
        algorithm=algorithm,
    )
    result = write_pdf(writer, output)
    result.update(open_password=bool(user_password), restricted=[k for k, v in allowed.items() if not v], algorithm=algorithm)
    return result


def unlock(path: str, output: str, password: str = "") -> dict:
    """Remove the password and restrictions (needs the open or the owner password)."""
    reader = PdfReader(path)
    if not reader.is_encrypted:
        raise ValueError("This PDF isn't protected")
    if not reader.decrypt(password or ""):
        raise ValueError("That password is wrong" if password else "This PDF needs a password")
    writer = PdfWriter(clone_from=reader)
    return write_pdf(writer, output)
