"""
Task 1 - Load the raw sources into tables (standard library only, no pandas).

Every loader returns a `LoadedSource`:
    .entities   dict  entity name -> Table (cleaning/tabular.py: .columns + .rows, one dict per raw record,
                      every value kept as raw text;
                      an XML element that is absent is None, an empty element is "")
    .malformed  list  records that could not be read; they are LOGGED here, never silently dropped
    .meta       dict  format, delimiter, time zone, extract time, ...

Entity names are the common (target) names used by the whole pipeline:
    professionals, patients, admissions, triage, diagnoses, notes, orders,
    radiology, procedures, unit_stays, discharges

Every table has two technical columns in addition to the raw fields:
    _source_row   where the record came from (file:line for TXT, an element path for XML)
    _raw_record   the whole raw record as text (the TXT line / the XML element), for the quarantine

Source A  (CHU de Montclair-sur-Loire, Europe/Paris) - data/raw/A_txt/*.txt
    One file per entity. UTF-8, LF line endings. Line 1 is a header with the column names.
    Delimiter: the pipe character "|". No quoting and no escaping (a "|" inside a value was replaced
    by "/"), so a valid line has exactly len(header) - 1 pipes. A line with a different number of
    fields is malformed (truncated line or stray delimiter) and is logged.

Source C  (Straits Regional Medical Centre, Asia/Singapore) - data/raw/C_xml/hospital_records.xml
    <hospitalRecords system=.. timezone=.. extractTime=..>
        <staff><member staffId="S0001">..</member></staff>
        <patients><patient patientId="P000001"><name><family/><given/></name>..</patient></patients>
        <admissions><admission admissionId="E000001" patientRef="P000001">
            <triage id=..>, <wardMovement id=..>, <diagnosis id=.. patientRef=..>,
            <labOrder id=..> <imaging id=..>  (exam nested inside its order)  </labOrder>,
            <imaging id=..> (walk-in exam, or orderRef=".." pointing to an order),
            <operation id=..>, <note id=.. type=..>, <discharge id=..>
        </admission></admissions>
        <unlinkedRecords> child records that carry admissionRef=".." instead of being nested
    </hospitalRecords>
    The parent admission of a nested record is the enclosing <admission>. A record without its id
    attribute cannot be identified and is logged as malformed.
"""

from __future__ import annotations

PIPELINE_VERSION = "2026.11.15-abcd"   # run_all.py checks that every file has the same version

import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

PHASE2 = Path(__file__).resolve().parents[1]
if str(PHASE2) not in sys.path:
    sys.path.insert(0, str(PHASE2))

from cleaning.tabular import Table  # noqa: E402
RAW_DIR = PHASE2 / "data" / "raw"

ENTITIES = ["professionals", "patients", "admissions", "triage", "diagnoses", "notes", "orders",
            "radiology", "procedures", "unit_stays", "discharges"]


@dataclass
class LoadedSource:
    code: str
    name: str
    entities: dict = field(default_factory=dict)
    malformed: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)


def _malformed(src, entity, location, reason, raw):
    return {"source_system": src, "entity": entity, "source_row": location, "reason": reason,
            "raw_record": raw}


# =============================================================================
# Source A - pipe-delimited TXT
# =============================================================================
A_FILES = {
    "professionals": "professionnels.txt",
    "patients": "patients.txt",
    "admissions": "sejours.txt",
    "triage": "triage.txt",
    "diagnoses": "diagnostics.txt",
    "notes": "notes_cliniques.txt",
    "orders": "demandes_examens.txt",
    "radiology": "imagerie.txt",
    "procedures": "bloc_operatoire.txt",
    "unit_stays": "mouvements.txt",
    "discharges": "sorties.txt",
}
A_DELIMITER = "|"


def load_source_a(folder: Path | None = None) -> LoadedSource:
    folder = Path(folder or RAW_DIR / "A_txt")
    src = LoadedSource("A", "CHU de Montclair-sur-Loire")
    src.meta = {"format": "TXT (one file per entity)", "delimiter": "|", "header": "line 1",
                "encoding": "UTF-8", "quoting": "none", "timezone": "Europe/Paris",
                "extract_time_local": "2025-10-31 18:00",
                "folder": str(folder.relative_to(PHASE2) if folder.is_relative_to(PHASE2) else folder)}
    for entity, fname in A_FILES.items():
        path = folder / fname
        if not path.exists():
            src.malformed.append(_malformed("A", entity, fname, "file not found", ""))
            src.entities[entity] = Table()
            continue
        data = path.read_bytes()
        lines = data.split(b"\n")
        header = lines[0].decode("utf-8-sig").rstrip("\r").split(A_DELIMITER)
        rows = []
        for no, bline in enumerate(lines[1:], start=2):
            try:
                line = bline.decode("utf-8").rstrip("\r")
            except UnicodeDecodeError as exc:
                src.malformed.append(_malformed("A", entity, f"{fname}:{no}", f"not valid UTF-8 ({exc.reason})",
                                                bline.decode("utf-8", "replace")))
                continue
            if line == "":
                if no != len(lines):                     # the final newline is normal; other blank lines are logged
                    src.malformed.append(_malformed("A", entity, f"{fname}:{no}", "blank line", ""))
                continue
            values = line.split(A_DELIMITER)
            if len(values) != len(header):
                src.malformed.append(_malformed(
                    "A", entity, f"{fname}:{no}",
                    f"wrong number of fields: expected {len(header)}, found {len(values)}", line))
                continue
            rec = dict(zip(header, values))
            rec["_source_row"] = f"{fname}:{no}"
            rec["_raw_record"] = line
            rows.append(rec)
        src.entities[entity] = Table(header + ["_source_row", "_raw_record"], rows)
    return src


# =============================================================================
# Source C - nested XML
# =============================================================================
# element tag -> (entity, id attribute, child fields). "a/b" means element b inside element a.
C_ELEMENTS = {
    "member": ("professionals", "staffId", ["name", "designation", "department"]),
    "patient": ("patients", "patientId", ["name/family", "name/given", "birthDate", "sex", "address", "phone",
                                         "nextOfKin", "vitalStatus"]),
    "admission": ("admissions", "admissionId", ["admittedBy", "admittedAt", "admissionClass", "chiefComplaint",
                                                "referralSource", "payer", "dischargedAt", "status"]),
    "triage": ("triage", "id", ["nurse", "assessedAt", "bloodPressure", "heartRate", "respRate", "temperature",
                                "oxygenSaturation", "painScore", "symptoms", "allergies", "homeMedication", "pacLevel"]),
    "diagnosis": ("diagnoses", "id", ["icd9", "type", "diagnosedAt", "doctor"]),
    "note": ("notes", "id", ["writtenAt", "author", "text"]),
    "labOrder": ("orders", "id", ["test", "orderedAt", "indication", "status", "priority", "orderedBy"]),
    "imaging": ("radiology", "id", ["modality", "performedAt", "bodyPart", "status", "pacsUrl", "report", "referrer",
                                    "radiographer"]),
    "operation": ("procedures", "id", ["procedure", "performedAt", "outcome", "surgeon"]),
    "wardMovement": ("unit_stays", "id", ["unit", "ward", "bed", "transferIn", "transferOut", "transferReason",
                                          "doctor"]),
    "discharge": ("discharges", "id", ["dischargedAt", "destination", "condition", "medications", "instructions",
                                       "followUp", "authorisedBy"]),
}
# extra attributes kept as columns (prefixed with @)
C_ATTRS = {"admission": ["patientRef"], "diagnosis": ["patientRef"], "note": ["type"], "imaging": ["orderRef"]}
C_CONTAINERS = {"staff": "member", "patients": "patient", "admissions": "admission"}


def _text(el, path):
    """None when the element is absent, "" when it is empty, else its text (not stripped)."""
    node = el.find(path)
    if node is None:
        return None
    return node.text if node.text is not None else ""


def _columns(tag):
    entity, idattr, fields = C_ELEMENTS[tag]
    cols = [f"@{idattr}"] + [f"@{a}" for a in C_ATTRS.get(tag, [])]
    if tag not in ("member", "patient", "admission"):
        cols.append("@admission")                         # parent admission (enclosing element or admissionRef)
    cols += fields
    if tag == "triage":
        cols.append("temperature@unit")
    return cols + ["_source_row", "_raw_record"]


def load_source_c(path: Path | None = None) -> LoadedSource:
    path = Path(path or RAW_DIR / "C_xml" / "hospital_records.xml")
    src = LoadedSource("C", "Straits Regional Medical Centre")
    rows = {C_ELEMENTS[t][0]: [] for t in C_ELEMENTS}
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:          # the whole file is unreadable: log it and return nothing
        src.malformed.append(_malformed("C", "*", str(path.name), f"XML could not be parsed: {exc}", ""))
        src.entities = {e: Table() for e in ENTITIES}
        return src
    src.meta = {"format": "XML (single nested file)", "root": root.tag, **root.attrib,
                "file": str(path.relative_to(PHASE2) if path.is_relative_to(PHASE2) else path)}

    def record(el, where, admission=None, order=None):
        tag = el.tag
        entity, idattr, fields = C_ELEMENTS[tag]
        raw = ET.tostring(el, encoding="unicode").strip()
        rid = el.get(idattr)
        if rid is None or rid.strip() == "":
            src.malformed.append(_malformed("C", entity, where, f"<{tag}> has no {idattr} attribute", raw))
            return
        rec = {f"@{idattr}": rid}
        for a in C_ATTRS.get(tag, []):
            rec[f"@{a}"] = el.get(a)
        if tag not in ("member", "patient", "admission"):
            rec["@admission"] = el.get("admissionRef") if el.get("admissionRef") is not None else admission
        if tag == "imaging" and order is not None:
            rec["@orderRef"] = order
        for f in fields:
            rec[f] = _text(el, f)
        if tag == "triage":
            t = el.find("temperature")
            rec["temperature@unit"] = t.get("unit") if t is not None else None
        known = {f.split("/")[0] for f in fields} | {"labOrder", "imaging"}
        for child in el:
            if child.tag not in known and tag != "admission":
                src.malformed.append(_malformed("C", entity, f"{where}/{child.tag}",
                                                f"unexpected element <{child.tag}> inside <{tag}> (ignored)",
                                                ET.tostring(child, encoding="unicode").strip()))
        rec["_source_row"] = where
        rec["_raw_record"] = raw if tag != "admission" else _shallow(el)
        rows[entity].append(rec)
        return rid

    for container, tag in C_CONTAINERS.items():
        holder = root.find(container)
        if holder is None:
            src.malformed.append(_malformed("C", C_ELEMENTS[tag][0], container, f"<{container}> section missing", ""))
            continue
        for i, el in enumerate(holder, start=1):
            where = f"{container}/{el.tag}[{i}]"
            if el.tag != tag:
                src.malformed.append(_malformed("C", C_ELEMENTS[tag][0], where, f"unexpected element <{el.tag}>",
                                                ET.tostring(el, encoding="unicode").strip()))
                continue
            record(el, where)
            if tag != "admission":
                continue
            adm_id = el.get("admissionId")
            for j, child in enumerate(el, start=1):
                cwhere = f"{where}/{child.tag}[{j}]"
                if child.tag in C_ELEMENTS["admission"][2]:
                    continue                                      # a field of the admission itself
                if child.tag not in C_ELEMENTS or child.tag in C_CONTAINERS.values():
                    src.malformed.append(_malformed("C", "admissions", cwhere, f"unexpected element <{child.tag}>",
                                                    ET.tostring(child, encoding="unicode").strip()))
                    continue
                record(child, cwhere, admission=adm_id)
                if child.tag == "labOrder":
                    for k, img in enumerate(child.findall("imaging"), start=1):
                        record(img, f"{cwhere}/imaging[{k}]", admission=adm_id, order=child.get("id"))

    unl = root.find("unlinkedRecords")
    if unl is not None:
        for i, el in enumerate(unl, start=1):
            where = f"unlinkedRecords/{el.tag}[{i}]"
            if el.tag not in C_ELEMENTS or el.tag in C_CONTAINERS.values():
                src.malformed.append(_malformed("C", "*", where, f"unexpected element <{el.tag}>",
                                                ET.tostring(el, encoding="unicode").strip()))
                continue
            record(el, where)

    for tag, (entity, _, _) in C_ELEMENTS.items():
        cols = _columns(tag)
        src.entities[entity] = Table(cols, [{c: r.get(c) for c in cols} for r in rows[entity]])
    return src


def _shallow(adm_el):
    """An <admission> without its nested children (they are records of their own)."""
    copy = ET.Element(adm_el.tag, adm_el.attrib)
    for child in adm_el:
        if child.tag in C_ELEMENTS["admission"][2]:
            copy.append(child)
    return ET.tostring(copy, encoding="unicode").replace("\n", " ").strip()


# =============================================================================
# Source B - CSV
# =============================================================================
B_FILES = {
    "professionals": "staff.csv",
    "patients": "patients.csv",
    "admissions": "admissions.csv",
    "triage": "triage.csv",
    "diagnoses": "diagnoses.csv",
    "notes": "clinical_notes.csv",
    "orders": "investigation_requests.csv",
    "radiology": "radiology.csv",
    "procedures": "theatre.csv",
    "unit_stays": "ward_movements.csv",
    "discharges": "discharges.csv",
}


def load_source_b(folder: Path | None = None) -> LoadedSource:
    """CSV: UTF-8, comma-delimited, header row, minimal quoting ("..." around values that contain a comma,
    a quote or a line break; "" inside is a quote). A quoted clinical note can span several physical lines, so
    records are read with the csv module, not line by line. A record whose field count differs from the
    header is logged as malformed."""
    import csv
    folder = Path(folder or RAW_DIR / "B_csv")
    src = LoadedSource("B", "Uganda National Hospital")
    src.meta = {"format": "CSV (one file per entity)", "delimiter": ",", "quoting": "minimal, double quote",
                "header": "line 1", "encoding": "UTF-8", "timezone": "Africa/Kampala",
                "extract_time_local": "2025-10-31 18:00",
                "folder": str(folder.relative_to(PHASE2) if folder.is_relative_to(PHASE2) else folder)}
    for entity, fname in B_FILES.items():
        path = folder / fname
        if not path.exists():
            src.malformed.append(_malformed("B", entity, fname, "file not found", ""))
            src.entities[entity] = Table()
            continue
        try:
            text = path.read_bytes().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            src.malformed.append(_malformed("B", entity, fname, f"not valid UTF-8 ({exc.reason})", ""))
            src.entities[entity] = Table()
            continue
        lines = text.splitlines(keepends=True)
        reader = csv.reader(lines)
        rows, start = [], 0
        header = None
        for values in reader:
            end = reader.line_num
            raw = "".join(lines[start:end]).rstrip("\r\n")
            where = f"{fname}:{start + 1}" + (f"-{end}" if end - start > 1 else "")
            start = end
            if header is None:
                header = values
                continue
            if not values or values == [""]:
                continue                                          # blank line
            if len(values) != len(header):
                src.malformed.append(_malformed("B", entity, where, f"wrong number of fields: expected "
                                                f"{len(header)}, found {len(values)}", raw))
                continue
            rec = dict(zip(header, values))
            rec["_source_row"], rec["_raw_record"] = where, raw
            rows.append(rec)
        src.entities[entity] = Table((header or []) + ["_source_row", "_raw_record"], rows)
    return src


# =============================================================================
# Source D - nested JSON
# =============================================================================
class JNum(str):
    """A JSON number kept as its exact text (so 250.00 stays '250.00'), marked so its JSON type is known."""


def _dumps(v):
    """JSON text of a parsed value, numbers written exactly as in the file (for the quarantine raw_record)."""
    if isinstance(v, JNum):
        return str(v)
    if isinstance(v, dict):
        return "{" + ", ".join(f"{json.dumps(k, ensure_ascii=False)}: {_dumps(x)}" for k, x in v.items()) + "}"
    if isinstance(v, list):
        return "[" + ", ".join(_dumps(x) for x in v) + "]"
    return json.dumps(v, ensure_ascii=False)


import json  # noqa: E402

# Keys whose JSON value must be a string (a number, boolean, object or array there is a wrong JSON type).
D_TEXT_ONLY = {"fullName", "designation", "department", "honorific", "patientName", "sex", "encounterClass",
               "presentingProblem", "referralSource", "fundingSource", "episodeStatus", "rank", "noteType", "body",
               "testName", "indication", "status", "priority", "modality", "bodySite", "imageUrl", "report",
               "procedureName", "outcome", "unit", "transferReason", "separationMode", "conditionAtSeparation",
               "followUp", "symptoms"}
D_CHILDREN = {"diagnoses": "diagnoses", "clinicalNotes": "notes", "orders": "orders", "imaging": "radiology",
              "procedures": "procedures", "wardStays": "unit_stays"}
D_SINGLE = {"triage": "triage", "separation": "discharges"}        # one object (an array of two when duplicated)
D_ID = {"professionals": "practitionerId", "patients": "patientId", "admissions": "admissionId",
        "triage": "triageId", "diagnoses": "diagnosisId", "notes": "noteId", "orders": "orderId",
        "radiology": "examId", "procedures": "procedureId", "unit_stays": "stayId", "discharges": "separationId"}


def _flatten_d(entity, obj):
    """One D record -> flat dict of text values (None = missing). Returns (flat, problem) where problem names a
    field with the wrong JSON type (the record is then malformed)."""
    from cleaning.standards import COLUMN_MAP
    flat = {}
    for key in COLUMN_MAP["D"][entity]:
        if key == "@admission" or key.endswith("@unit"):
            continue
        head, _, sub = key.partition(".")
        v = obj.get(head)
        if sub and head == "vitals":
            if v is not None and not isinstance(v, dict):
                return None, f"vitals has the wrong JSON type ({type(v).__name__})"
            v = (v or {}).get(sub)
            if sub == "temp" and isinstance(v, dict):
                flat["vitals.temp@unit"] = None if v.get("unit") is None else str(v.get("unit"))
                v = v.get("value")
            elif sub == "bp" and isinstance(v, dict):
                v = f"{v.get('systolic')}/{v.get('diastolic')}"
        elif head == "appointments":                       # follow-up: the first appointment's time
            from cleaning.parsers import is_missing
            if isinstance(v, str) and is_missing(v):          # placeholder instead of the array = missing
                v = None
            if v is not None and not isinstance(v, list):
                return None, f"appointments has the wrong JSON type ({type(v).__name__})"
            first = next((a for a in v or [] if isinstance(a, dict)), None)
            v = first.get("at") if first else None
        elif head in ("allergies", "currentMeds", "dischargeMeds") and isinstance(v, list):
            if not all(isinstance(x, str) for x in v):
                return None, f"{head} contains a non-text element"
            v = "; ".join(v) if v else None
        elif head == "address" and isinstance(v, dict):
            v = ", ".join(x for x in (v.get("line"), " ".join(str(y) for y in (v.get("suburb"), v.get("state"),
                                                                                  v.get("postcode")) if y))
                          if x) or None
        elif head == "nextOfKin" and isinstance(v, dict):
            parts = [v.get("name") or ""] + ([f"({v['relationship']})"] if v.get("relationship") else []) + \
                    [v.get("phone") or ""]
            v = " ".join(str(x) for x in parts if x) or None
        elif head == "location" and isinstance(v, dict):
            v = ", ".join(str(x) for x in (v.get("ward"), v.get("room")) if x) or None
        if isinstance(v, bool):
            if head != "deceased":
                return None, f"{key} has the wrong JSON type (boolean)"
            v = "true" if v else "false"
        elif isinstance(v, (dict, list)):
            return None, f"{key} has the wrong JSON type ({type(v).__name__})"
        elif isinstance(v, JNum) and head in D_TEXT_ONLY:
            return None, f"{key} has the wrong JSON type (number)"
        flat[key] = None if v is None else str(v)
    return flat, None


def load_source_d(folder: Path | None = None) -> LoadedSource:
    """JSON: practitioners.json -> practitioners[]; patients_p*.json -> patients[] with nested
    admissions[] -> triage (object, or array when duplicated), diagnoses[], clinicalNotes[], orders[], imaging[],
    procedures[], wardStays[], separation (object/array); patients_p3.json also has unlinkedEncounters[]
    (admissions carrying their own patientId). The parent of a nested record is the enclosing object.
    Numbers are kept as their exact text. Junk array elements (null, strings, [], {}, error objects) and records
    with a field of the wrong JSON type are logged as malformed."""
    from cleaning.standards import COLUMN_MAP
    folder = Path(folder or RAW_DIR / "D_json")
    src = LoadedSource("D", "Coral Coast Health Service")
    rows = {e: [] for e in ENTITIES}

    def bad(entity, where, reason, obj):
        src.malformed.append(_malformed("D", entity, where, reason, _dumps(obj)))

    def add(entity, obj, where, extra=None, shallow=()):
        if not isinstance(obj, dict) or not obj or D_ID[entity] not in obj:
            what = type(obj).__name__ if not isinstance(obj, dict) else ("empty object" if not obj else
                                                                         "object without " + D_ID[entity])
            bad(entity, where, f"junk element ({what})", obj)
            return None
        flat, problem = _flatten_d(entity, obj)
        if problem:
            bad(entity, where, problem, {k: v for k, v in obj.items() if k not in shallow})
            return None
        rid = flat[D_ID[entity]]
        if rid is None or rid.strip() == "":
            bad(entity, where, f"missing {D_ID[entity]}", obj)
            return None
        flat.update(extra or {})
        flat["_source_row"] = where
        flat["_raw_record"] = _dumps({k: v for k, v in obj.items() if k not in shallow})
        rows[entity].append(flat)
        return rid

    def load(fname):
        path = folder / fname
        try:
            with open(path, encoding="utf-8-sig") as f:
                return json.load(f, parse_int=JNum, parse_float=JNum)
        except (OSError, ValueError) as exc:
            src.malformed.append(_malformed("D", "*", fname, f"JSON could not be read: {exc}", ""))
            return None

    def admission(a, where, patient_id):
        nested = set(D_CHILDREN) | set(D_SINGLE)
        own = isinstance(a, dict) and a.get("patientId") is not None
        aid = add("admissions", a, where, extra=None if own else {"patientId": patient_id}, shallow=nested)
        if aid is None:
            return
        for key, entity in D_CHILDREN.items():
            arr = a.get(key)
            if arr is None:
                continue
            if not isinstance(arr, list):
                bad(entity, f"{where}.{key}", f"{key} is not an array", arr)
                continue
            for k, c in enumerate(arr):
                add(entity, c, f"{where}.{key}[{k}]", extra={"@admission": aid})
        for key, entity in D_SINGLE.items():
            v = a.get(key)
            for k, c in enumerate(v if isinstance(v, list) else [] if v is None else [v]):
                add(entity, c, f"{where}.{key}" + (f"[{k}]" if isinstance(v, list) else ""),
                    extra={"@admission": aid})

    doc = load("practitioners.json")
    if doc is not None:
        src.meta = {"format": "JSON (practitioners file + paged patient files, nested)",
                    "extractTime": str((doc.get("meta") or {}).get("exportedAt") or ""),
                    "timezone": "Australia/Sydney", "folder": str(folder)}
        for i, p in enumerate(doc.get("practitioners") or []):
            add("professionals", p, f"practitioners.json:practitioners[{i}]")
    for fname in sorted(x.name for x in folder.glob("patients_p*.json")):
        doc = load(fname)
        if doc is None:
            continue
        for i, p in enumerate(doc.get("patients") or []):
            where = f"{fname}:patients[{i}]"
            pid = add("patients", p, where, shallow=("admissions",))
            if pid is None:
                continue
            adms = p.get("admissions")
            if adms is not None and not isinstance(adms, list):
                bad("admissions", f"{where}.admissions", "admissions is not an array", adms)
                continue
            for j, a in enumerate(adms or []):
                admission(a, f"{where}.admissions[{j}]", pid)
        for j, a in enumerate(doc.get("unlinkedEncounters") or []):
            admission(a, f"{fname}:unlinkedEncounters[{j}]", None)

    for e in ENTITIES:
        cols = [c for c in COLUMN_MAP["D"][e]] + ["_source_row", "_raw_record"]
        src.entities[e] = Table(cols, [{c: r.get(c) for c in cols} for r in rows[e]])
    return src


# =============================================================================
LOADERS = {"A": load_source_a, "B": load_source_b, "C": load_source_c, "D": load_source_d}


def load_all(codes=("A", "B", "C", "D")) -> dict:
    return {c: LOADERS[c]() for c in codes}


if __name__ == "__main__":
    for code, s in load_all().items():
        print(f"Source {code} - {s.name}")
        for e, df in s.entities.items():
            print(f"  {e:14s} {len(df):6d} records, {len(df.columns) - 2} fields")
        print(f"  malformed      {len(s.malformed):6d}")
    sys.exit(0)
