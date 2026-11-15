"""
Task 1 - Load the four raw sources into Python data structures.

Every source is loaded into the same structure:

    SourceData
      .entities   {entity: [record, ...]}  one list of dicts per entity, using the
                                           SOURCE'S OWN field names and values exactly
                                           as read (no cleaning, no renaming)
      .layout     {entity: [field, ...]}   field order as found in the source
      .malformed  [ {...}, ... ]           malformed / unreadable records (logged,
                                           never silently dropped)
      .containers [ {...}, ... ]           C/D structural shells that are not records

Each record also carries "_loc" (file + line / XML path / JSON path) so that any
value can be traced back to where it was read. Nested XML/JSON children get their
parent's key as an extra field (admissionNo / encounter_id, and orderRef for
radiology exams nested inside an order).

Representation of "no value" is kept as read:
    TXT/CSV  -> the text that was written ("", "N/A", "NULL", "unknown")
    XML      -> "" for an empty element; the key is ABSENT if the element is absent
    JSON     -> None for null, "" / "unknown" as written; key ABSENT if absent

Standard library only.
"""

import csv
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "output" / "raw"

ENTITIES = ["professionals", "icd9_dictionary", "patients", "admissions", "triage", "unit_stays",
            "diagnoses", "orders", "radiology", "procedures", "notes", "discharges"]

# File per entity for the two flat sources.
A_FILES = {"professionals": "professionals.txt", "icd9_dictionary": "icd9_dictionary.txt",
           "patients": "patients.txt", "admissions": "admissions.txt", "triage": "triage.txt",
           "unit_stays": "mouvements.txt", "diagnoses": "diagnostics.txt", "orders": "demandes_examen.txt",
           "radiology": "radiologie.txt", "procedures": "chirurgie.txt", "notes": "notes_cliniques.txt",
           "discharges": "sorties.txt"}
B_FILES = {"professionals": "professionals.csv", "icd9_dictionary": "icd9_codes.csv",
           "patients": "patients.csv", "admissions": "encounters.csv", "triage": "triage.csv",
           "unit_stays": "unit_stays.csv", "diagnoses": "diagnoses.csv", "orders": "orders.csv",
           "radiology": "imaging.csv", "procedures": "procedures.csv", "notes": "notes.csv",
           "discharges": "discharges.csv"}

# Primary key field of each entity, per source (used for duplicate checks).
KEYS = {
    "A": {"professionals": "prof_no", "icd9_dictionary": "code_cim9", "patients": "pat_no",
          "admissions": "sejour_no", "triage": "triage_no", "unit_stays": "mvt_no", "diagnoses": "diag_no",
          "orders": "demande_no", "radiology": "examen_no", "procedures": "acte_no", "notes": "note_no",
          "discharges": "sortie_no"},
    "B": {"professionals": "ProviderID", "icd9_dictionary": "ICD9Code", "patients": "PatientID",
          "admissions": "EncounterID", "triage": "TriageID", "unit_stays": "StayID", "diagnoses": "DxID",
          "orders": "OrderID", "radiology": "ImagingID", "procedures": "ProcedureID", "notes": "NoteID",
          "discharges": "DischargeID"},
    "C": {"professionals": "staffId", "icd9_dictionary": "code", "patients": "patientNo",
          "admissions": "admissionNo", **{e: "id" for e in ENTITIES[4:]}},
    "D": {"professionals": "practitioner_id", "icd9_dictionary": "icd9", "patients": "mrn",
          "admissions": "encounter_id", "triage": "triage_id", "unit_stays": "movement_id", "diagnoses": "dx_id",
          "orders": "order_id", "radiology": "imaging_id", "procedures": "procedure_id", "notes": "note_id",
          "discharges": "discharge_id"},
}


@dataclass
class SourceData:
    source: str
    label: str
    fmt: str
    path: Path
    entities: dict = field(default_factory=lambda: {e: [] for e in ENTITIES})
    layout: dict = field(default_factory=dict)
    malformed: list = field(default_factory=list)
    containers: list = field(default_factory=list)

    def log_malformed(self, entity, loc, reason, raw):
        self.malformed.append({"source": self.source, "entity": entity, "location": loc,
                               "reason": reason, "raw": raw if isinstance(raw, str) else repr(raw)})

    def add(self, entity, record):
        self.entities[entity].append(record)
        order = self.layout.setdefault(entity, [])
        for k in record:
            if not k.startswith("_") and k not in order:
                order.append(k)


# ---------------------------------------------------------------------------
# Source A - TXT, pipe-delimited
# ---------------------------------------------------------------------------

def load_source_a():
    """Layout of every TXT file:
         * UTF-8 text, one record per line, '\\n' line ends ('\\r\\n' tolerated)
         * line 1 is a header with the field names
         * fields separated by '|' ; no quoting / escaping ('|' inside a value
           was replaced with '/' by the producer, so '|' is always a delimiter)
         * every data line must have exactly as many fields as the header
    """
    base = RAW / "source_A_europe"
    sd = SourceData("A", "A - Europe", "TXT (pipe-delimited)", base)
    for entity, fname in A_FILES.items():
        path = base / fname
        if not path.exists():
            sd.log_malformed(entity, fname, "file_missing", "")
            continue
        raw_lines = path.read_bytes().split(b"\n")
        try:
            header = raw_lines[0].decode("utf-8").rstrip("\r").split("|")
        except UnicodeDecodeError as e:
            sd.log_malformed(entity, f"{fname}:line 1", f"header_not_utf8: {e}", repr(raw_lines[0]))
            continue
        sd.layout[entity] = list(header)
        for n, b in enumerate(raw_lines[1:], start=2):
            loc = f"{fname}:line {n}"
            try:
                line = b.decode("utf-8").rstrip("\r")
            except UnicodeDecodeError as e:
                sd.log_malformed(entity, loc, f"not_utf8: {e}", repr(b))
                continue
            if line == "":
                if n != len(raw_lines):  # the final '' after the last newline is normal
                    sd.log_malformed(entity, loc, "blank_line", "")
                continue
            parts = line.split("|")
            if len(parts) != len(header):
                sd.log_malformed(entity, loc, f"wrong_field_count: {len(parts)} fields, header has {len(header)}",
                                 line)
                continue
            rec = dict(zip(header, parts))
            rec["_loc"] = loc
            sd.add(entity, rec)
    return sd


# ---------------------------------------------------------------------------
# Source B - CSV
# ---------------------------------------------------------------------------

def load_source_b():
    """Comma-separated, '"'-quoted (RFC 4180), header row, UTF-8."""
    base = RAW / "source_B_north_america"
    sd = SourceData("B", "B - North America", "CSV", base)
    for entity, fname in B_FILES.items():
        path = base / fname
        if not path.exists():
            sd.log_malformed(entity, fname, "file_missing", "")
            continue
        try:
            with open(path, encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                header = next(reader)
                sd.layout[entity] = list(header)
                n = 1
                while True:
                    try:
                        parts = next(reader)
                    except StopIteration:
                        break
                    except csv.Error as e:
                        sd.log_malformed(entity, f"{fname}:line {reader.line_num}", f"csv_error: {e}", "")
                        continue
                    n += 1
                    loc = f"{fname}:row {n}"
                    if len(parts) != len(header):
                        sd.log_malformed(entity, loc,
                                         f"wrong_field_count: {len(parts)} fields, header has {len(header)}",
                                         ",".join(parts))
                        continue
                    rec = dict(zip(header, parts))
                    rec["_loc"] = loc
                    sd.add(entity, rec)
        except UnicodeDecodeError as e:
            sd.log_malformed(entity, fname, f"not_utf8: {e}", "")
    return sd


# ---------------------------------------------------------------------------
# Source C - XML (nested)
# ---------------------------------------------------------------------------

C_CHILD = {"triage": "triage", "unitStay": "unit_stays", "diagnosis": "diagnoses", "order": "orders",
           "radiologyExam": "radiology", "surgery": "procedures", "note": "notes", "discharge": "discharges"}


def _leaf_fields(el, prefix=""):
    """Attributes + text of leaf children. Empty element -> ''. Absent -> no key."""
    d = {f"{prefix}{k}": v for k, v in el.attrib.items()}
    for ch in el:
        if len(ch) == 0:
            d[f"{prefix}{ch.tag}"] = ch.text if ch.text is not None else ""
    return d


def load_source_c():
    """Structure:
       hospitalSystem
         staff/member[@staffId]                 -> professionals
         icd9Dictionary/entry[@code]            -> icd9_dictionary
         patients/patient[@patientNo]           -> patients  (name/family, name/given nested)
         admissions/admission[@admissionNo,@patientRef]  -> admissions
             triage | unitStay | diagnosis | order | surgery | note | discharge  -> children
             order/radiologyExam                -> radiology (order id = parent order)
             radiologyExam[@orderRef]           -> radiology (stand-alone, explicit order ref)
       An <admission> with no patientRef and no fields is a container for
       orphan children, not an admission record.
    """
    path = RAW / "source_C_asia" / "hospital_asia.xml"
    sd = SourceData("C", "C - Asia", "XML (nested)", path)
    if not path.exists():
        sd.log_malformed("*", path.name, "file_missing", "")
        return sd
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        sd.log_malformed("*", f"{path.name}:{e.position}", f"xml_parse_error: {e}", "")
        return sd

    sections = {"staff": ("member", "professionals"), "icd9Dictionary": ("entry", "icd9_dictionary"),
                "patients": ("patient", "patients")}
    for sec, (tag, entity) in sections.items():
        node = root.find(sec)
        if node is None:
            sd.log_malformed(entity, f"/{sec}", "section_missing", "")
            continue
        for i, el in enumerate(node, start=1):
            loc = f"/{sec}/{el.tag}[{i}]"
            if el.tag != tag:
                sd.log_malformed(entity, loc, f"unexpected_element <{el.tag}>", ET.tostring(el, "unicode")[:200])
                continue
            rec = _leaf_fields(el)
            for sub in el:          # one level of nesting (patient/name/family, patient/name/given)
                if len(sub):
                    rec.update(_leaf_fields(sub, prefix=f"{sub.tag}."))
            rec["_loc"] = loc
            sd.add(entity, rec)

    adms = root.find("admissions")
    for i, a in enumerate(adms if adms is not None else [], start=1):
        aid = a.get("admissionNo")
        aloc = f"/admissions/admission[{i}]"
        fields = _leaf_fields(a)
        if "patientRef" not in a.attrib and len(fields) == 1:
            sd.containers.append({"source": "C", "location": aloc, "admissionNo": aid,
                                  "children": len(a), "note": "empty <admission> shell holding orphan children"})
        else:
            fields["_loc"] = aloc
            sd.add("admissions", fields)
        for j, ch in enumerate(a, start=1):
            if len(ch) == 0:
                continue  # a field of the admission itself
            entity = C_CHILD.get(ch.tag)
            loc = f"{aloc}/{ch.tag}[{j}]"
            if entity is None:
                sd.log_malformed("admissions", loc, f"unexpected_element <{ch.tag}>",
                                 ET.tostring(ch, "unicode")[:200])
                continue
            rec = {"admissionNo": aid, **_leaf_fields(ch), "_loc": loc}
            sd.add(entity, rec)
            if ch.tag == "order":
                for k, rad in enumerate(ch.findall("radiologyExam"), start=1):
                    r = {"admissionNo": aid, "orderRef": ch.get("id"), **_leaf_fields(rad),
                         "_loc": f"{loc}/radiologyExam[{k}]"}
                    sd.add("radiology", r)
    return sd


# ---------------------------------------------------------------------------
# Source D - JSON (nested)
# ---------------------------------------------------------------------------

D_CHILD = {"triage": "triage", "ward_movements": "unit_stays", "diagnoses": "diagnoses",
           "investigations": "orders", "imaging": "radiology", "theatre": "procedures", "notes": "notes",
           "discharge": "discharges"}


def _flatten(obj, prefix=""):
    """Nested objects -> dotted keys (contact.phone). Lists are kept as lists."""
    out = {}
    for k, v in obj.items():
        if isinstance(v, dict):
            out.update(_flatten(v, f"{prefix}{k}."))
        else:
            out[f"{prefix}{k}"] = v
    return out


def load_source_d():
    """Structure:
       { facility{..., codebook}, practitioners[], icd9_reference[], patients[], encounters[] }
       encounter = admission fields + child arrays triage[], ward_movements[], diagnoses[],
                   investigations[], imaging[], theatre[], notes[], and 'discharge'
                   (an object for one discharge, a list for several, or null).
       An encounter with patient_mrn = null and no encounter fields is a container
       for orphan children, not an admission record.
    """
    path = RAW / "source_D_africa" / "hospital_africa.json"
    sd = SourceData("D", "D - Africa", "JSON (nested)", path)
    if not path.exists():
        sd.log_malformed("*", path.name, "file_missing", "")
        return sd
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        sd.log_malformed("*", path.name, f"json_parse_error: {e}", "")
        return sd
    sd.codebook = doc.get("facility", {}).get("codebook")

    for key, entity in (("practitioners", "professionals"), ("icd9_reference", "icd9_dictionary"),
                        ("patients", "patients")):
        for i, item in enumerate(doc.get(key, [])):
            loc = f"$.{key}[{i}]"
            if not isinstance(item, dict):
                sd.log_malformed(entity, loc, f"not_an_object ({type(item).__name__})", item)
                continue
            sd.add(entity, {**_flatten(item), "_loc": loc})

    for i, enc in enumerate(doc.get("encounters", [])):
        eloc = f"$.encounters[{i}]"
        if not isinstance(enc, dict):
            sd.log_malformed("admissions", eloc, f"not_an_object ({type(enc).__name__})", enc)
            continue
        eid = enc.get("encounter_id")
        own = {k: v for k, v in enc.items() if k not in D_CHILD}
        if enc.get("patient_mrn") is None and "encounter_type" not in enc:
            sd.containers.append({"source": "D", "location": eloc, "encounter_id": eid,
                                  "children": sum(len(v) if isinstance(v, list) else (v is not None)
                                                  for k, v in enc.items() if k in D_CHILD),
                                  "note": "encounter shell (no patient, no fields) holding orphan children"})
        else:
            sd.add("admissions", {**_flatten(own), "_loc": eloc})
        for key, entity in D_CHILD.items():
            items = enc.get(key)
            if items is None:
                continue
            if isinstance(items, dict):
                items = [items]
            if not isinstance(items, list):
                sd.log_malformed(entity, f"{eloc}.{key}", f"unexpected_type ({type(items).__name__})", items)
                continue
            for j, item in enumerate(items):
                loc = f"{eloc}.{key}[{j}]"
                if not isinstance(item, dict):
                    sd.log_malformed(entity, loc, f"not_an_object ({type(item).__name__})", item)
                    continue
                sd.add(entity, {"encounter_id": eid, **_flatten(item), "_loc": loc})
    return sd


def load_all():
    """Return {'A': SourceData, 'B': ..., 'C': ..., 'D': ...}."""
    return {"A": load_source_a(), "B": load_source_b(), "C": load_source_c(), "D": load_source_d()}


def to_dataframes(sd):
    """Optional: {entity: pandas.DataFrame} for one source (requires pandas)."""
    import pandas as pd
    return {e: pd.DataFrame([{k: v for k, v in r.items() if k != "_loc"} for r in rows])
            for e, rows in sd.entities.items()}


if __name__ == "__main__":
    for s, sd in load_all().items():
        n = sum(len(v) for v in sd.entities.values())
        print(f"{sd.label:20s} {sd.fmt:22s} records={n:>6,d}  malformed={len(sd.malformed)}  "
              f"containers={len(sd.containers)}")
