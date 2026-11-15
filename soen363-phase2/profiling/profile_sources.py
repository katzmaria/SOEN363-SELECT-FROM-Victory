"""
Task 1 - Initial profile of the four raw sources.

    python profiling/profile_sources.py

Uses load_sources.py, then writes:
    output/profile_report.md               the profile (all sections below)
    output/profile/field_profile.csv       one row per source / entity / field
    output/profile/record_counts.csv       records by source and entity
    output/profile/duplicates.csv          duplicate counts by source and entity
    output/profile/invalid_values.csv      every suspicious / invalid value found
    output/profile/malformed_records.csv   malformed or unreadable records (logged, not dropped)

The profile describes the data AS DELIVERED: nothing is cleaned or changed.
Standard library only.
"""

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_sources import ENTITIES, KEYS, ROOT, load_all  # noqa: E402

OUT = ROOT / "output" / "profile"
REPORT = ROOT / "output" / "profile_report.md"

# How each source writes "no value" (from the source documentation).
MISSING_MARKERS = {"A": {"", "N/A"}, "B": {"", "NULL", "unknown"}, "C": {""}, "D": {"", "unknown"}}

# Date formats used to check that a NN/NN/YYYY value is a real calendar date.
SLASH_DATE = {"A": "%d/%m/%Y", "B": "%m/%d/%Y"}

# ---------------------------------------------------------------------------
# Value classification (type inference)
# ---------------------------------------------------------------------------

PATTERNS = [
    ("integer", re.compile(r"[+-]?\d+")),
    ("decimal", re.compile(r"[+-]?\d+\.\d+")),
    ("decimal (comma)", re.compile(r"[+-]?\d+,\d+")),
    ("datetime DD/MM/YYYY HH:MM", re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}")),
    ("datetime MM/DD/YYYY hh:mm AM/PM", re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2} [AP]M")),
    ("date NN/NN/YYYY", re.compile(r"\d{2}/\d{2}/\d{4}")),
    ("date ISO", re.compile(r"\d{4}-\d{2}-\d{2}")),
    ("datetime ISO UTC (Z)", re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")),
    ("datetime ISO +offset, fractional seconds",
     re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[+-]\d{2}:\d{2}")),
    ("datetime ISO +offset", re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}")),
    ("datetime ISO no zone", re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")),
    ("blood pressure N/N", re.compile(r"\d{2,3}/\d{2,3}")),
    ("staff code S###", re.compile(r"S\d{3}")),
    ("staff code PR-#", re.compile(r"PR-\d+")),
]
FAMILY = {"integer": "number", "decimal": "number", "decimal (comma)": "number", "json integer": "number",
          "json decimal": "number", "numeric text": "number"}


def _valid_calendar(cls, s, source):
    try:
        if cls == "datetime DD/MM/YYYY HH:MM":
            datetime.strptime(s, "%d/%m/%Y %H:%M")
        elif cls == "datetime MM/DD/YYYY hh:mm AM/PM":
            datetime.strptime(s, "%m/%d/%Y %I:%M %p")
        elif cls == "date NN/NN/YYYY":
            datetime.strptime(s, SLASH_DATE.get(source, "%d/%m/%Y"))
        elif cls == "date ISO":
            datetime.strptime(s, "%Y-%m-%d")
        elif cls.startswith("datetime ISO"):
            datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def classify(v, source):
    """Return (kind, cls). kind is 'absent', 'null', 'marker', 'value' or 'invalid'."""
    if v is None:
        return "null", "null"
    if isinstance(v, bool):
        return "value", "json boolean"
    if isinstance(v, int):
        return "value", "json integer"
    if isinstance(v, float):
        return "value", "json decimal"
    if isinstance(v, list):
        return "value", "json list"
    s = str(v)
    if s.strip() in MISSING_MARKERS[source]:
        return "marker", repr(s)
    st = s.strip()
    for cls, rx in PATTERNS:
        if rx.fullmatch(st):
            if cls.startswith(("date", "datetime")) and not _valid_calendar(cls, st, source):
                return "invalid", f"impossible {cls}"
            if source in ("C", "D") and cls == "integer":
                return "value", "numeric text"
            return "value", cls
    return "value", "text"


def family(cls):
    if cls.startswith("impossible "):
        cls = cls[len("impossible "):]
    if cls in FAMILY:
        return FAMILY[cls]
    if cls.startswith(("date", "datetime")):
        return "date/time"
    return cls


# ---------------------------------------------------------------------------
# Field profile
# ---------------------------------------------------------------------------

# Code fields: digits and dots, but identifiers - never numbers (leading zeros matter).
CODE_FIELDS = {"code_cim9", "ICD9", "ICD9Code", "icd9", "code"}


def profile_field(rows, fname, source):
    n = len(rows)
    kinds, classes, values = Counter(), Counter(), Counter()
    examples = {}
    for r in rows:
        if fname not in r:
            kinds["absent"] += 1
            continue
        kind, cls = classify(r[fname], source)
        if kind in ("null", "marker"):
            kinds[cls if kind == "marker" else "null"] += 1
            continue
        classes[cls] += 1
        key = json.dumps(r[fname], ensure_ascii=False) if isinstance(r[fname], list) else r[fname]
        values[key] += 1
        examples.setdefault(cls, r[fname])
    missing = sum(kinds.values())
    present = n - missing
    fam = Counter()
    for c, k in classes.items():
        fam[family(c)] += k
    dominant_family = fam.most_common(1)[0][0] if fam else "-"
    # Inferred type = most common class inside the dominant family.
    inferred = max((c for c in classes if family(c) == dominant_family), key=lambda c: classes[c], default="-")
    # Categorical = few distinct labels once case and spacing are ignored.
    norm_distinct = len({_norm(v) for v in values})
    if fname in CODE_FIELDS:
        inferred, dominant_family = "ICD-9 code (string)", "code"
        fam = Counter({"code": present})
    elif dominant_family == "text" and 0 < norm_distinct <= 12 and present >= 20:
        inferred = "categorical text"
    elif dominant_family == "number" and 0 < norm_distinct <= 8 and present >= 20:
        inferred = f"categorical code ({inferred})"
    is_cat = inferred.startswith("categorical")
    others = {c: k for c, k in classes.items() if (family(c) != dominant_family or c.startswith("impossible"))
              and dominant_family != "code"}
    variants = {c: k for c, k in classes.items() if family(c) == dominant_family and c != inferred
                and not c.startswith("impossible") and not inferred.startswith("categorical")}
    return {
        "records": n, "present": present, "missing": missing,
        "missing_breakdown": ", ".join(f"{k}: {v}" for k, v in kinds.most_common()),
        "inferred_type": inferred,
        "conforming_pct": round(100 * sum(k for c, k in classes.items() if (family(c) == dominant_family
                                          or dominant_family == "code")
                                          and not c.startswith("impossible")) / present, 1) if present else 0,
        "format_variants": "; ".join(f"{c}: {k} (e.g. {examples[c]!r})" for c, k in variants.items()),
        "other_types": "; ".join(f"{c}: {k} (e.g. {examples[c]!r})" for c, k in
                                 sorted(others.items(), key=lambda x: -x[1])),
        "distinct": len(values),
        "top_values": "; ".join(f"{v!r}: {k}" for v, k in values.most_common(12)) if is_cat else "",
        "example": next(iter(examples.values()), ""),
    }


# ---------------------------------------------------------------------------
# Duplicates
# ---------------------------------------------------------------------------

PERSON = {  # fields identifying a person: (given name, birth date, extra name field)
    "A": ("prenom", "date_naissance", "nom"),
    "B": (None, "DOB", "FullName"),
    "C": ("name.given", "birthDate", "name.family"),
    "D": ("first_names", "birth_date", "surname"),
}


def _norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().casefold() if s is not None else ""


def duplicates(sd):
    out = []
    for e in ENTITIES:
        rows = sd.entities[e]
        sig = Counter(json.dumps({k: v for k, v in r.items() if k != "_loc"}, sort_keys=True, ensure_ascii=False)
                      for r in rows)
        exact = sum(c - 1 for c in sig.values() if c > 1)
        key = KEYS[sd.source][e]
        kc = Counter(str(r.get(key)) for r in rows)
        dup_keys = {k: c for k, c in kc.items() if c > 1}
        row = {"source": sd.source, "entity": e, "records": len(rows), "key_field": key,
               "exact_duplicate_rows": exact, "keys_appearing_more_than_once": len(dup_keys),
               "extra_rows_on_repeated_keys": sum(c - 1 for c in dup_keys.values()),
               "repeated_key_examples": ", ".join(list(dup_keys)[:6]),
               "possible_same_person_new_id": ""}
        if e == "patients":
            g, dob, fam = PERSON[sd.source]
            groups = defaultdict(set)
            for r in rows:
                if sd.source == "B":
                    last, _, first = str(r.get("FullName", "")).partition(",")
                    k = (_norm(first), _norm(last), _norm(r.get(dob)))
                else:
                    k = (_norm(r.get(g)), _norm(r.get(fam)), _norm(r.get(dob)))
                if all(k):
                    groups[k].add(str(r.get(key)))
            same = [sorted(ids, key=lambda x: int(x) if x.isdigit() else 0) for ids in groups.values() if len(ids) > 1]
            row["possible_same_person_new_id"] = len(same)
            row["same_person_examples"] = "; ".join("/".join(ids) for ids in same[:5])
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# Invalid / suspicious values (domain checks)
# ---------------------------------------------------------------------------

# field -> (low, high, unit, value transform) per source; ranges are generous on purpose
VITALS = {
    "A": {"fc": (20, 300, "bpm"), "fr": (4, 80, "/min"), "temp_c": (25, 45, "degC"), "spo2_pct": (50, 100, "%"),
          "douleur": (0, 10, "pain 0-10")},
    "B": {"HeartRate": (20, 300, "bpm"), "RespRate": (4, 80, "/min"), "TempF": (77, 113, "degF"),
          "SpO2": (50, 100, "%"), "PainScore": (0, 10, "pain 0-10")},
    "C": {"pulse": (20, 300, "bpm"), "respiration": (4, 80, "/min"), "temperatureC": (25, 45, "degC"),
          "oxygenSaturation": (0.5, 1.0, "fraction"), "pain": (0, 10, "pain 0-10")},
    "D": {"pulse": (20, 300, "bpm"), "resp_rate": (4, 80, "/min"), "temp_c": (25, 45, "degC"),
          "spo2": (50, 100, "%"), "pain_score": (0, 10, "pain 0-10")},
}
NAME_FIELDS = {"A": ["nom", "prenom"], "B": ["FullName"], "C": ["name.family", "name.given"],
               "D": ["surname", "first_names"]}
ICD_FIELD = {"A": ("code_cim9", "code_cim9"), "B": ("ICD9", "ICD9Code"), "C": ("icd9", "code"),
             "D": ("icd9", "icd9")}  # (diagnosis field, dictionary field)


def _num(v, source):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", ".") if source == "A" else str(v).strip()
    try:
        return float(s)
    except ValueError:
        return None


def invalid_values(sd, fprof):
    S, found = sd.source, []

    def add(entity, field, check, rec, value, detail=""):
        found.append({"source": S, "entity": entity, "field": field, "check": check,
                      "location": rec.get("_loc", ""), "value": repr(value), "detail": detail})

    for e in ENTITIES:
        rows = sd.entities[e]
        for f in sd.layout.get(e, []):
            p = fprof[(S, e, f)]
            dom = family(p["inferred_type"].replace("categorical code (", "").rstrip(")")) \
                if not p["inferred_type"].startswith(("categorical text", "ICD-9")) else "text"
            for r in rows:
                if f not in r:
                    continue
                v = r[f]
                kind, cls = classify(v, S)
                if kind == "invalid":
                    add(e, f, "impossible date/time", r, v, cls)
                elif kind == "value" and dom == "date/time" and cls == "json integer":
                    add(e, f, "timestamp as Unix epoch seconds", r, v)
                elif kind == "value" and dom == "date/time" and cls == "datetime ISO no zone" \
                        and p["inferred_type"] != cls:
                    add(e, f, "timestamp without time zone", r, v, f"field is mostly {p['inferred_type']}")
                elif kind == "value" and dom in ("number", "date/time") and family(cls) != dom:
                    add(e, f, f"not a {dom}", r, v, f"read as {cls}")
                if isinstance(v, str) and kind == "value" and (v != v.strip() or "  " in v):
                    add(e, f, "extra whitespace", r, v)
        # case variants of the same categorical label (e.g. 'Urgent' vs 'URGENT')
        for f in sd.layout.get(e, []):
            p = fprof[(S, e, f)]
            if not p["inferred_type"].startswith("categorical") or not p["distinct"]:
                continue
            labels = Counter(r[f] for r in rows if isinstance(r.get(f), str))
            by_fold = defaultdict(list)
            for lab in labels:
                by_fold[_norm(lab)].append(lab)
            for variants in by_fold.values():
                if len(variants) > 1:
                    main = max(variants, key=lambda x: labels[x])
                    for lab in variants:
                        if lab != main and lab.strip() == lab and "  " not in lab:
                            for r in rows:
                                if r.get(f) == lab:
                                    add(e, f, "label case variant", r, lab, f"usual form {main!r}")

    for f, (lo, hi, unit) in VITALS[S].items():
        for r in sd.entities["triage"]:
            if f not in r or classify(r[f], S)[0] != "value":
                continue
            x = _num(r[f], S)
            if x is None:
                continue  # already reported as 'not a number'
            if not lo <= x <= hi:
                add("triage", f, "out of plausible range", r, r[f], f"expected {lo}-{hi} {unit}")

    for f in NAME_FIELDS[S]:
        for r in sd.entities["patients"]:
            v = r.get(f)
            if isinstance(v, str) and v.strip() not in MISSING_MARKERS[S]:
                parts = [p.strip() for p in v.split(",")] if S == "B" else [v.strip()]
                if any(len(p) > 1 and (p == p.upper() or p == p.lower()) for p in parts if p):
                    add("patients", f, "name all upper / all lower case", r, v)

    dx_field, dict_field = ICD_FIELD[S]
    codes = {str(r.get(dict_field)) for r in sd.entities["icd9_dictionary"]}
    for r in sd.entities["diagnoses"]:
        v = r.get(dx_field)
        if v is None or (isinstance(v, str) and v.strip() in MISSING_MARKERS[S]):
            continue
        if str(v) not in codes:
            m = re.fullmatch(r"(\d{1,2})(\.\d+)?", str(v))
            if m and (m.group(1).zfill(3) + (m.group(2) or "")) in codes:
                add("diagnoses", dx_field, "ICD-9 leading zero lost", r, v,
                    f"dictionary has {m.group(1).zfill(3) + (m.group(2) or '')}")
            else:
                add("diagnoses", dx_field, "ICD-9 code not in dictionary", r, v)
    return found


# ---------------------------------------------------------------------------
# Cross-source formatting differences
# ---------------------------------------------------------------------------

CONCEPTS = [  # concept, entity, field per source
    ("Patient id", "patients", {"A": "pat_no", "B": "PatientID", "C": "patientNo", "D": "mrn"}),
    ("Family name", "patients", {"A": "nom", "B": "FullName", "C": "name.family", "D": "surname"}),
    ("Birth date", "patients", {"A": "date_naissance", "B": "DOB", "C": "birthDate", "D": "birth_date"}),
    ("Sex", "patients", {"A": "sexe", "B": "Sex", "C": "gender", "D": "sex"}),
    ("Vital status", "patients", {"A": "statut_vital", "B": "Deceased", "C": "vitalStatus", "D": "deceased"}),
    ("Admission time", "admissions", {"A": "date_entree", "B": "AdmitDateTime", "C": "admittedAt", "D": "start"}),
    ("Admission type", "admissions", {"A": "type_sejour", "B": "AdmitType", "C": "category", "D": "encounter_type"}),
    ("Admission status", "admissions", {"A": "statut", "B": "EncounterStatus", "C": "status", "D": "outcome"}),
    ("Admitting staff ref", "admissions",
     {"A": "medecin_admission", "B": "AdmittingProviderID", "C": "admittingStaff", "D": "admitted_by"}),
    ("Triage priority", "triage", {"A": "priorite", "B": "Acuity", "C": "level", "D": "category"}),
    ("Temperature", "triage", {"A": "temp_c", "B": "TempF", "C": "temperatureC", "D": "temp_c"}),
    ("Oxygen saturation", "triage", {"A": "spo2_pct", "B": "SpO2", "C": "oxygenSaturation", "D": "spo2"}),
    ("Symptoms", "triage", {"A": "symptomes", "B": "Symptoms", "C": "symptoms", "D": "complaints"}),
    ("Unit", "unit_stays", {"A": "unite", "B": "Unit", "C": "unit", "D": "ward"}),
    ("ICD-9 code", "diagnoses", {"A": "code_cim9", "B": "ICD9", "C": "icd9", "D": "icd9"}),
    ("Diagnosis rank", "diagnoses", {"A": "rang", "B": "DxRank", "C": "kind", "D": "primary"}),
]


def concept_rows(data, fprof):
    rows = []
    for concept, e, fields in CONCEPTS:
        row = [concept]
        for S, sd in data.items():
            f = fields[S]
            p = fprof.get((S, e, f))
            ex = next((r[f] for r in sd.entities[e] if f in r and classify(r[f], S)[0] == "value"), "")
            row.append(f"`{f}` = `{json.dumps(ex, ensure_ascii=False) if isinstance(ex, list) else ex}`"
                       + (f"<br>{p['inferred_type']}" if p else ""))
        rows.append(row)
    return rows


def category_rows(data, fprof):
    rows = []
    for concept, e, fields in CONCEPTS:
        if concept in ("Admitting staff ref", "Patient id"):
            continue
        cells, any_cat = [concept], False
        for S in data:
            p = fprof.get((S, e, fields[S]))
            if p and p["inferred_type"].startswith("categorical") and p["top_values"]:
                any_cat = True
                cells.append(p["top_values"].replace("; ", "<br>"))
            else:
                cells.append("")
        if any_cat:
            rows.append(cells)
    return rows


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_csv(path, rows, header=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    header = header or (list(rows[0]) if rows else ["empty"])
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def md(header, rows):
    esc = lambda x: str(x).replace("|", "\\|").replace("\n", " ")
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
                     + ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows])


def main():
    data = load_all()

    fprof, field_rows = {}, []
    for S, sd in data.items():
        for e in ENTITIES:
            for f in sd.layout.get(e, []):
                p = profile_field(sd.entities[e], f, S)
                fprof[(S, e, f)] = p
                field_rows.append({"source": S, "entity": e, "field": f, **p})
    dup_rows = [row for sd in data.values() for row in duplicates(sd)]
    inv_rows = [row for sd in data.values() for row in invalid_values(sd, fprof)]
    mal_rows = [m for sd in data.values() for m in sd.malformed]
    cont_rows = [c for sd in data.values() for c in sd.containers]
    count_rows = [{"source": S, "entity": e, "records_loaded": len(sd.entities[e]),
                   "malformed_logged": sum(m["entity"] == e for m in sd.malformed)}
                  for S, sd in data.items() for e in ENTITIES]

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "field_profile.csv", field_rows)
    write_csv(OUT / "record_counts.csv", count_rows)
    write_csv(OUT / "duplicates.csv", dup_rows, list(dup_rows[0]) + ["same_person_examples"])
    write_csv(OUT / "invalid_values.csv", inv_rows,
              ["source", "entity", "field", "check", "location", "value", "detail"])
    write_csv(OUT / "malformed_records.csv", mal_rows, ["source", "entity", "location", "reason", "raw"])
    write_csv(OUT / "structural_containers.csv", cont_rows,
              ["source", "location", "admissionNo", "encounter_id", "children", "note"])

    L = []
    w = L.append
    w("# Phase 2 - Task 1: Loading and Initial Profile of the Raw Sources\n")
    w("_Generated by `profiling/profile_sources.py`. It describes the data **as delivered**: nothing is cleaned "
      "or changed here (cleaning is Task 2)._\n")

    # 1 loading
    w("## 1. How each format is loaded\n")
    w("`profiling/load_sources.py` loads every source into the same structure: a `SourceData` object holding, "
      "for each of the 12 entities, a **list of dicts** (one dict per record) with the source's own field names "
      "and the values exactly as read, plus the field order (`layout`), a log of malformed records and a list of "
      "structural containers. `to_dataframes()` turns a source into pandas DataFrames if pandas is installed.\n")
    w(md(["Source", "Format", "How it is read", "Nested records"], [
        ["A - Europe", "TXT, 12 files", "Split each line on `|` (see 1.1)", "none (flat files)"],
        ["B - North America", "CSV, 12 files", "`csv.reader` (comma, `\"` quotes, header row)", "none (flat files)"],
        ["C - Asia", "1 XML file", "`xml.etree.ElementTree`, walk `staff`, `icd9Dictionary`, `patients`, "
                                   "`admissions`", "children of `<admission>` become their own entity with "
                                   "`admissionNo` added; `<radiologyExam>` inside `<order>` gets `orderRef` = "
                                   "the order's id; `<name><family/><given/></name>` -> `name.family`, `name.given`"],
        ["D - Africa", "1 JSON file", "`json.load`, walk `practitioners`, `icd9_reference`, `patients`, "
                                      "`encounters`", "encounter arrays (`triage`, `ward_movements`, `diagnoses`, "
                                      "`investigations`, `imaging`, `theatre`, `notes`) and `discharge` (object, "
                                      "list or null) become entities with `encounter_id` added; "
                                      "`contact{...}` -> `contact.address` etc."],
    ]))
    w("\n### 1.1 Source A (TXT): delimiter and record layout\n")
    w("* Encoding UTF-8; one record per line; line end `\\n` (`\\r\\n` tolerated).\n"
      "* **Line 1 is a header** with the field names.\n"
      "* Field delimiter **`|`** (pipe). No quoting or escaping: the producer replaced any `|` inside a value "
      "with `/`, so every `|` is a delimiter.\n"
      "* A valid data line has exactly as many fields as the header; any other line is **logged** in "
      "`malformed_records.csv` (not loaded, not dropped silently).\n"
      "* Missing values are written as an empty field or `N/A`. Decimals use a comma (`37,2`).\n")
    w(md(["File", "Entity", "Fields (in order)"],
         [[f"`{data['A'].entities[e][0]['_loc'].split(':')[0] if data['A'].entities[e] else ''}`", e,
           " \\| ".join(data["A"].layout.get(e, []))] for e in ENTITIES]))
    w("\n### 1.2 Source B (CSV) layout\n")
    w(md(["File", "Entity", "Fields (in order)"],
         [[f"`{data['B'].entities[e][0]['_loc'].split(':')[0] if data['B'].entities[e] else ''}`", e,
           ", ".join(data["B"].layout.get(e, []))] for e in ENTITIES]))
    for S, title in (("C", "1.3 Source C (XML): extracted fields"), ("D", "1.4 Source D (JSON): extracted fields")):
        w(f"\n### {title}\n")
        w(md(["Entity", "Fields"], [[e, ", ".join(data[S].layout.get(e, []))] for e in ENTITIES]))

    # 2 counts
    w("\n## 2. Record counts by entity\n")
    rows = []
    for e in ENTITIES:
        rows.append([e] + [len(data[S].entities[e]) for S in data])
    rows.append(["**Total loaded**"] + [sum(len(v) for v in data[S].entities.values()) for S in data])
    rows.append(["Malformed lines (logged, not loaded)"] + [len(data[S].malformed) for S in data])
    rows.append(["**Total records in file**"] + [sum(len(v) for v in data[S].entities.values())
                                                 + len(data[S].malformed) for S in data])
    w(md(["Entity", "A (TXT)", "B (CSV)", "C (XML)", "D (JSON)"], rows))
    w(f"\nStructural containers (not records): C has {len(data['C'].containers)} empty `<admission>` shells and "
      f"D has {len(data['D'].containers)} encounter shells. They have no patient and no fields; they only hold "
      "child records whose admission does not exist. They are listed in `structural_containers.csv`.\n")

    # 3 field profile
    w("\n## 3. Field names, inferred types and missing values\n")
    w("*Inferred type* = the most common value format among non-missing values. *Conforming* = share of "
      "non-missing values that fit that type. *Missing* counts every way the source writes 'no value' "
      "(absent key/element, JSON null, empty text, or a marker such as `N/A`, `NULL`, `unknown`). "
      "*Other formats* lists values that do not fit the inferred type: these are the formatting differences and "
      "invalid values inside one field.\n")
    for S, sd in data.items():
        w(f"\n### Source {sd.label} ({sd.fmt})\n")
        for e in ENTITIES:
            rows = []
            for f in sd.layout.get(e, []):
                p = fprof[(S, e, f)]
                rows.append([f"`{f}`", p["inferred_type"], f"{p['conforming_pct']}%",
                             p["missing"] if not p["missing"] else f"{p['missing']} ({p['missing_breakdown']})",
                             p["distinct"], (p["format_variants"] + ("; " if p["format_variants"] and
                                                                   p["other_types"] else "") + p["other_types"])[:220]])
            w(f"**{e}** ({len(sd.entities[e])} records)\n")
            w(md(["Field", "Inferred type", "Conforming", "Missing", "Distinct", "Other formats / invalid"], rows))
            w("")

    # 4 duplicates
    w("\n## 4. Duplicate counts\n")
    w("*Exact duplicate rows* = records identical in every field (extra copies counted). *Repeated keys* = "
      "the entity's id appears on more than one record. *Possible same person* = patients with different ids but "
      "the same given name, family name and birth date (ignoring case and spaces).\n")
    rows = [[d["source"], d["entity"], f"`{d['key_field']}`", d["records"], d["exact_duplicate_rows"],
             d["keys_appearing_more_than_once"], d["extra_rows_on_repeated_keys"],
             d["possible_same_person_new_id"] if d["entity"] == "patients" else ""]
            for d in dup_rows if d["exact_duplicate_rows"] or d["keys_appearing_more_than_once"]
            or d["entity"] == "patients"]
    w(md(["Src", "Entity", "Key", "Records", "Exact duplicate rows", "Keys repeated", "Extra rows on repeated keys",
          "Possible same person"], rows))
    w("\nAll other entities have no duplicates. Local ids also repeat **across** sources (patient 125 exists in "
      "A, B, C and D as four different people), so a source id is only unique together with its source.\n")

    # 5 formatting differences
    w("\n## 5. Formatting differences between sources\n")
    w("The same concept, first non-missing value of each source, and the inferred format:\n")
    w(md(["Concept", "A", "B", "C", "D"], concept_rows(data, fprof)))
    w("\n**Category labels as written (value: count)** - case and spacing variants show up as separate labels:\n")
    w(md(["Concept", "A", "B", "C", "D"], category_rows(data, fprof)))
    w("\nMissing-value markers found: " + "; ".join(
        f"{S}: " + ", ".join(sorted({k.split(':')[0] for (s, e, f), p in fprof.items() if s == S
                                    for k in p['missing_breakdown'].split(', ') if k}))
        for S in data) + ".\n")

    # 6 invalid values
    w("\n## 6. Invalid and suspicious values\n")
    ic = Counter((r["check"], r["source"]) for r in inv_rows)
    checks = sorted({c for c, _ in ic})
    w(md(["Check", "A", "B", "C", "D", "Examples"],
         [[c] + [ic.get((c, S), 0) for S in data] +
          ["<br>".join(f"{r['source']} {r['entity']}.{r['field']} = {r['value']}"
                       + (f" ({r['detail']})" if r['detail'] else "")
                       for r in _examples(inv_rows, c))] for c in checks]))
    w("\nEvery occurrence (with its location) is in `output/profile/invalid_values.csv`. Two problem types cannot "
      "be seen from a single value and are left to Task 2: ambiguous dates in source A (a US-style MM/DD date is "
      "a valid DD/MM date when both parts are <= 12) and broken references / chronology between records.\n")

    # 7 malformed
    w("\n## 7. Malformed or unreadable records (logged, not discarded)\n")
    if mal_rows:
        w(md(["Src", "Entity", "Location", "Reason", "Raw text"],
             [[m["source"], m["entity"], m["location"], m["reason"], f"`{m['raw'][:140]}`"] for m in mal_rows]))
    else:
        w("None.")
    w("\nThese lines are not loaded as records (their fields cannot be assigned to columns reliably), but each is "
      "kept with its raw text in `output/profile/malformed_records.csv` so that it can be reviewed. The XML and "
      "JSON files parsed without errors.\n")

    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    for S, sd in data.items():
        print(f"{sd.label:20s} loaded {sum(len(v) for v in sd.entities.values()):>6,d}  "
              f"malformed {len(sd.malformed)}  containers {len(sd.containers)}")
    print(f"invalid/suspicious values: {len(inv_rows)}   report: {REPORT.relative_to(ROOT)}")


def _examples(rows, check, per_source=1, limit=4):
    out, seen = [], Counter()
    for r in rows:
        if r["check"] == check and seen[r["source"]] < per_source:
            seen[r["source"]] += 1
            out.append(r)
        if len(out) >= limit:
            break
    return out


if __name__ == "__main__":
    main()
