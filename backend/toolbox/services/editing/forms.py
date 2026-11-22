"""PDF forms: list, fill (optionally flatten) and create fields.

Created fields are standard AcroForm widgets: text (single/multi-line), checkbox
(with on/off appearances), dropdown and list box. NeedAppearances is set so
viewers draw text and choice fields with their current values.
"""

from __future__ import annotations

from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    BooleanObject,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

from ..pdf.common import open_reader, write_pdf
from .geometry import visual_rect_to_user

FIELD_TYPES = ("text", "multiline", "checkbox", "dropdown", "listbox")
_MULTILINE, _COMBO, _REQUIRED, _READONLY = 1 << 12, 1 << 17, 1 << 1, 1 << 0
_RADIO, _PUSH = 1 << 15, 1 << 16


def _field_name(annot: DictionaryObject) -> str:
    parts = []
    node = annot
    while node is not None:
        if "/T" in node:
            parts.append(str(node["/T"]))
        node = node.get("/Parent")
        node = node.get_object() if node is not None else None
    return ".".join(reversed(parts))


def _inherited(annot: DictionaryObject, key: str):
    node = annot
    while node is not None:
        if key in node:
            return node[key]
        node = node.get("/Parent")
        node = node.get_object() if node is not None else None
    return None


def _user_to_visual(page, rect) -> dict:
    llx, lly, urx, ury = (float(v) for v in rect)
    box = page.cropbox
    left, bottom, right, top = float(box.left), float(box.bottom), float(box.right), float(box.top)
    rot = page.rotation % 360
    if rot == 0:
        x, y, w, h = llx - left, top - ury, urx - llx, ury - lly
    elif rot == 90:
        x, y, w, h = lly - bottom, llx - left, ury - lly, urx - llx
    elif rot == 180:
        x, y, w, h = right - urx, lly - bottom, urx - llx, ury - lly
    else:
        x, y, w, h = top - ury, right - urx, ury - lly, urx - llx
    return {"x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "h": round(h, 2)}


def list_fields(path: str) -> list[dict]:
    reader = open_reader(path)
    fields: dict[str, dict] = {}
    for p, page in enumerate(reader.pages):
        for ref in page.get("/Annots") or []:
            annot = ref.get_object()
            if annot.get("/Subtype") != "/Widget":
                continue
            name = _field_name(annot)
            ft = _inherited(annot, "/FT")
            flags = int(_inherited(annot, "/Ff") or 0)
            if ft == "/Tx":
                kind = "multiline" if flags & _MULTILINE else "text"
            elif ft == "/Btn":
                kind = "radio" if flags & _RADIO else "button" if flags & _PUSH else "checkbox"
            elif ft == "/Ch":
                kind = "dropdown" if flags & _COMBO else "listbox"
            elif ft == "/Sig":
                kind = "signature"
            else:
                continue
            on_states = [str(k)[1:] for k in ((annot.get("/AP") or {}).get("/N") or {}) if k != "/Off"]
            value = _inherited(annot, "/V")
            entry = fields.setdefault(
                name,
                {
                    "name": name,
                    "type": kind,
                    "value": "",
                    "options": [],
                    "required": bool(flags & _REQUIRED),
                    "readonly": bool(flags & _READONLY),
                    "widgets": [],
                },
            )
            if kind in ("checkbox", "radio"):
                entry["options"] += on_states
                entry["value"] = str(value)[1:] if value is not None and str(value) != "/Off" else ""
            elif kind in ("dropdown", "listbox"):
                opts = _inherited(annot, "/Opt") or []
                entry["options"] = [str(o[1] if isinstance(o, list | ArrayObject) else o) for o in opts]
                entry["value"] = str(value) if value is not None else ""
            elif value is not None:
                entry["value"] = str(value)
            entry["widgets"].append({"page": p, **_user_to_visual(page, annot["/Rect"]), "state": on_states[0] if on_states else None})
    return list(fields.values())


def fill(path: str, output: str, values: dict, flatten: bool = False) -> dict:
    """values: {field name: text | option | True/False (checkbox) | radio state name}."""
    known = {f["name"]: f for f in list_fields(path)}
    unknown = [k for k in values if k not in known]
    if unknown:
        raise ValueError(f"No field named {unknown[0]!r}")
    writer = PdfWriter(clone_from=open_reader(path))
    resolved: dict[str, str] = {}
    for name, value in values.items():
        kind = known[name]["type"]
        if kind == "checkbox":
            on = (known[name]["options"] or ["Yes"])[0]
            resolved[name] = f"/{on}" if value in (True, "true", "on", on) else "/Off"
        elif kind == "radio":
            resolved[name] = f"/{value}" if value else "/Off"
        else:
            resolved[name] = "" if value is None else str(value)
    for page in writer.pages:
        if page.get("/Annots"):
            writer.update_page_form_field_values(page, resolved, auto_regenerate=False, flatten=flatten)
    writer.set_need_appearances_writer(True)
    result = write_pdf(writer, output)
    result["filled"] = len(values)
    return result


# --- creating fields -----------------------------------------------------------------


def _check_appearances(w: float, h: float) -> tuple[DecodedStreamObject, DecodedStreamObject]:
    size = min(w, h) * 0.8
    on = DecodedStreamObject()
    on.set_data(f"q 0 g BT /ZaDb {size:.2f} Tf {(w - size * 0.8) / 2:.2f} {(h - size * 0.7) / 2:.2f} Td (4) Tj ET Q".encode())
    off = DecodedStreamObject()
    off.set_data(b"")
    for stream in (on, off):
        stream.update(
            {
                NameObject("/Type"): NameObject("/XObject"),
                NameObject("/Subtype"): NameObject("/Form"),
                NameObject("/BBox"): ArrayObject([FloatObject(0), FloatObject(0), FloatObject(w), FloatObject(h)]),
                NameObject("/Resources"): DictionaryObject(
                    {
                        NameObject("/Font"): DictionaryObject(
                            {
                                NameObject("/ZaDb"): DictionaryObject(
                                    {
                                        NameObject("/Type"): NameObject("/Font"),
                                        NameObject("/Subtype"): NameObject("/Type1"),
                                        NameObject("/BaseFont"): NameObject("/ZapfDingbats"),
                                    }
                                )
                            }
                        )
                    }
                ),
            }
        )
    return on, off


def add_fields(path: str, output: str, specs: list[dict]) -> dict:
    """specs: [{page, type, name, x, y, w, h, options?, value?, required?, font_size?}] in displayed coordinates."""
    if not specs:
        raise ValueError("Add at least one field")
    reader = open_reader(path)
    writer = PdfWriter(clone_from=reader)
    existing = {f["name"] for f in list_fields(path)}
    root = writer._root_object
    if "/AcroForm" not in root:
        root[NameObject("/AcroForm")] = writer._add_object(DictionaryObject())
    acro = root["/AcroForm"].get_object()
    fields = acro.setdefault(NameObject("/Fields"), ArrayObject())
    helv = DictionaryObject(
        {NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica"), NameObject("/Encoding"): NameObject("/WinAnsiEncoding")}
    )
    dr = acro.setdefault(NameObject("/DR"), DictionaryObject())
    dr.get_object().setdefault(NameObject("/Font"), DictionaryObject())[NameObject("/Helv")] = writer._add_object(helv)
    acro[NameObject("/DA")] = TextStringObject("/Helv 0 Tf 0 g")
    acro[NameObject("/NeedAppearances")] = BooleanObject(True)

    for spec in specs:
        kind = spec.get("type")
        if kind not in FIELD_TYPES:
            raise ValueError(f"Unknown field type: {kind!r}")
        name = str(spec.get("name") or "").strip()
        if not name:
            raise ValueError("Every field needs a name")
        if name in existing:
            raise ValueError(f"There's already a field named {name!r}")
        existing.add(name)
        index = int(spec.get("page", 0))
        if not 0 <= index < len(writer.pages):
            raise ValueError(f"Page {index + 1} doesn't exist")
        page = writer.pages[index]
        rect = visual_rect_to_user(page, float(spec["x"]), float(spec["y"]), float(spec["w"]), float(spec["h"]))
        flags = _REQUIRED if spec.get("required") else 0
        size = float(spec.get("font_size") or 0)  # 0 = auto size
        field = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Widget"),
                NameObject("/T"): TextStringObject(name),
                NameObject("/Rect"): ArrayObject([FloatObject(v) for v in rect]),
                NameObject("/F"): NumberObject(4),  # print
                NameObject("/P"): page.indirect_reference,
                NameObject("/DA"): TextStringObject(f"/Helv {size:g} Tf 0 g"),
                NameObject("/MK"): DictionaryObject(
                    {
                        NameObject("/BC"): ArrayObject([FloatObject(0.6), FloatObject(0.6), FloatObject(0.6)]),
                        NameObject("/R"): NumberObject(page.rotation % 360),
                    }
                ),
            }
        )
        if kind in ("text", "multiline"):
            field[NameObject("/FT")] = NameObject("/Tx")
            flags |= _MULTILINE if kind == "multiline" else 0
            if spec.get("value"):
                field[NameObject("/V")] = TextStringObject(str(spec["value"]))
        elif kind == "checkbox":
            w, h = rect[2] - rect[0], rect[3] - rect[1]
            on, off = _check_appearances(w, h)
            checked = bool(spec.get("value"))
            field[NameObject("/FT")] = NameObject("/Btn")
            field[NameObject("/V")] = NameObject("/Yes" if checked else "/Off")
            field[NameObject("/AS")] = NameObject("/Yes" if checked else "/Off")
            field[NameObject("/AP")] = DictionaryObject(
                {NameObject("/N"): DictionaryObject({NameObject("/Yes"): writer._add_object(on), NameObject("/Off"): writer._add_object(off)})}
            )
            field[NameObject("/MK")][NameObject("/CA")] = TextStringObject("4")
        else:
            options = [str(o) for o in spec.get("options") or [] if str(o).strip()]
            if not options:
                raise ValueError(f"Field {name!r} needs at least one option")
            field[NameObject("/FT")] = NameObject("/Ch")
            flags |= _COMBO if kind == "dropdown" else 0
            field[NameObject("/Opt")] = ArrayObject([TextStringObject(o) for o in options])
            value = str(spec.get("value") or (options[0] if kind == "dropdown" else ""))
            if value:
                field[NameObject("/V")] = TextStringObject(value)
        field[NameObject("/Ff")] = NumberObject(flags)
        ref = writer._add_object(field)
        page.setdefault(NameObject("/Annots"), ArrayObject()).append(ref)
        fields.append(ref)
    result = write_pdf(writer, output)
    result["fields_added"] = len(specs)
    return result
