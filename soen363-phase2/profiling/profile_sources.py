"""
Task 1 - Initial profile of the raw sources (before any cleaning).

    python profiling/profile_sources.py                (run from soen363-phase2/)

For every source and entity: record counts, field names with inferred data types, missing-value counts,
duplicate counts, examples of formatting differences and of invalid values. Malformed records found by
the loaders are listed too.

Writes output/profile/*.csv and output/profile_report.md
"""

from __future__ import annotations

PIPELINE_VERSION = "2026.11.15-abcd"

PIPELINE_VERSION = "2026.11.15-abcd"

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PHASE2 = Path(__file__).resolve().parents[1]
if str(PHASE2) not in sys.path:
    sys.path.insert(0, str(PHASE2))

from cleaning import parsers as P
from cleaning.tabular import md_table, write_csv
from cleaning.standards import COLUMN_MAP, ENTITY_SPECS, SOURCES
from profiling.load_sources import ENTITIES, PHASE2 as ROOT, load_all

OUT = ROOT / "output"
ICD_DEFAULT = ROOT.parent / "soen363-phase1" / "data" / "icd9_dictionary.csv"
TECH = {"_source_row", "_raw_record"}


# -----------------------------------------------------------------------------
# Type inference
# -----------------------------------------------------------------------------
def value_class(s):
    s = P.collapse_ws(s)
    if re.fullmatch(r"[+-]?\d+", s):
        return "integer"
    if re.fullmatch(r"[+-]?\d+\.\d+", s):
        return "decimal"
    if re.fullmatch(r"[+-]?\d+,\d+", s):
        return "decimal (comma)"
    if re.fullmatch(r"[A-Z]{1,2}\d{3,}", s):
        return "code/id"
    if re.fullmatch(r"\d{1,3}\s*[/-]\s*\d{1,4}(\s*mmhg)?", s, re.I) and not re.fullmatch(r"\d+-\d+-\d+.*", s):
        return "ratio (n/n)"
    if P.parse_number(s).status == "ok":
        return "number + unit"
    for name, rx in P.DT_PATTERNS:
        m = rx.fullmatch(s)
        if m:
            return "datetime" if m.group(4) else "date"
    if re.fullmatch(r"[a-z]+://\S+", s):
        return "url"
    return "text"


def infer_type(values):
    cls = Counter(value_class(v) for v in values)
    if not cls:
        return "unknown (all missing)", ""
    n = sum(cls.values())
    top, k = cls.most_common(1)[0]
    breakdown = ", ".join(f"{c} {100 * x / n:.0f}%" for c, x in cls.most_common())
    if top == "text":
        distinct = len({P.collapse_ws(v).casefold() for v in values})
        top = "categorical text" if distinct <= 30 else "text"
    if k / n >= 0.95:
        return top, breakdown
    numeric = {"integer", "decimal", "decimal (comma)", "number + unit"}
    if set(cls) <= numeric | {"text"} and sum(cls[c] for c in numeric) / n >= 0.8:
        return "numeric (mixed formats)", breakdown
    if {"datetime", "date"} & set(cls) and (cls["datetime"] + cls["date"]) / n >= 0.8:
        return f"{top} (mixed formats)", breakdown
    return f"mixed (mostly {top})", breakdown


def text_issues(values):
    c = Counter()
    for v in values:
        if v != v.strip():
            c["leading/trailing spaces"] += 1
        if "  " in v.strip():
            c["double spaces"] += 1
        if P.case_inverted(v):
            c["inverted case"] += 1
        elif P.case_damaged(v) and len(v) > 4:
            c["ALL CAPS"] += 1
    return c


# -----------------------------------------------------------------------------
def profile(codes=("A", "B", "C", "D"), icd9_path=ICD_DEFAULT, out_dir=OUT):
    from cleaning.clean_sources import MISSING, Rec, clean_value, field_level, load_icd9
    icd9, _ = load_icd9(icd9_path)
    loaded = load_all(codes)
    counts, fields, dups, shapes, invalid, malformed = [], [], [], [], [], []
    for code in codes:
        src = loaded[code]
        cfg = SOURCES[code]
        tz = P.get_tz(cfg["timezone"])
        ctx = {"tz": tz, "icd9": icd9}
        malformed += src.malformed
        mal = Counter(m["entity"] for m in src.malformed)
        for e in ENTITIES:
            df = src.entities[e]
            cmap = COLUMN_MAP[code][e]
            spec = ENTITY_SPECS[e]
            raw_cols = [c for c in df.columns if c not in TECH]
            counts.append({"source_system": code, "entity": e, "raw_name": _raw_name(code, e),
                           "records_loaded": len(df), "malformed_not_loaded": mal.get(e, 0), "fields": len(raw_cols)})
            recs = []
            for row in df.rows:
                raw = {common: row.get(rc) for rc, common in cmap.items()}
                recs.append(Rec(e, code, raw, row["_source_row"], row["_raw_record"]))

            # fields
            for rc in raw_cols:
                common = cmap.get(rc, "")
                kind = spec["fields"].get(common, "") if common else ""
                numeric = kind in ("bp", "temperature", "spo2") or kind.startswith("vital:")
                col = df.column(rc)
                kinds = Counter(P.missing_kind(v, numeric) for v in col)
                present = [str(v) for v in col if P.missing_kind(v, numeric) is None]
                ph = Counter(P.collapse_ws(str(v)) for v in col if P.missing_kind(v, numeric) == "placeholder")
                t, breakdown = infer_type(present)
                level = field_level(code, e, common) if common in spec["fields"] else "-"
                fields.append({"source_system": code, "entity": e, "raw_field": rc, "common_field": common,
                               "level": level, "inferred_type": t, "value_formats": breakdown,
                               "non_missing": len(present), "missing_absent": kinds["absent"],
                               "missing_empty": kinds["empty"], "missing_placeholder": kinds["placeholder"],
                               "missing_total": len(col) - len(present),
                               "missing_pct": round(100 * (len(col) - len(present)) / max(1, len(col)), 1),
                               "placeholders_seen": ", ".join(f"{k!r}x{n}" for k, n in ph.most_common()),
                               "distinct_values": len(set(present)),
                               "example_values": " | ".join(list(dict.fromkeys(present))[:4])})
                # formatting differences
                if kind in ("datetime", "date", "phone", "bp", "temperature", "spo2", "icd9") or \
                        kind.startswith("vital:") or kind == "id" or kind.startswith("fk:"):
                    sh = defaultdict(list)
                    for v in present:
                        sh[P.date_shape(v)].append(v)
                    for s_, vs in sorted(sh.items(), key=lambda kv: -len(kv[1])):
                        shapes.append({"source_system": code, "entity": e, "raw_field": rc, "kind": kind,
                                       "format_shape": s_, "count": len(vs), "example": vs[0]})
                if kind.startswith("label:") or kind in ("text", "name", "lower_list", "none_or_text", "free_text"):
                    ti = text_issues(present)
                    for k, n in ti.items():
                        shapes.append({"source_system": code, "entity": e, "raw_field": rc, "kind": kind,
                                       "format_shape": k, "count": n,
                                       "example": next(v for v in present if k in text_issues([v]))})
                    if kind.startswith("label:"):
                        variants = Counter(P.collapse_ws(v) for v in present)
                        shapes.append({"source_system": code, "entity": e, "raw_field": rc, "kind": kind,
                                       "format_shape": f"{len(variants)} distinct labels",
                                       "count": len(present),
                                       "example": ", ".join(f"{k} ({n})" for k, n in variants.most_common(12))})
                # invalid values (same rules as the cleaning)
                if kind:
                    probs = defaultdict(list)
                    for r in recs:
                        out = clean_value(r, common, kind, ctx)
                        if out is not MISSING and out.problem:
                            probs[out.problem].append(str(r.raw.get(common)))
                    for p_, vs in probs.items():
                        invalid.append({"source_system": code, "entity": e, "raw_field": rc, "problem": p_,
                                        "count": len(vs),
                                        "examples": " | ".join(list(dict.fromkeys(vs))[:6])})

            # duplicates
            pk = spec["pk"]
            raw_pk = next(rc for rc, c in cmap.items() if c == pk)
            norm = [tuple("" if row.get(c) is None else P.collapse_ws(str(row[c])).casefold() for c in raw_cols)
                    for row in df.rows]
            exact = len(norm) - len(set(norm))
            ids = [P.collapse_ws(str(v)) for v in df.column(raw_pk)]
            dup_ids = len(ids) - len(set(ids))
            key_dups, example = _key_duplicates(recs, e, ctx, clean_value, MISSING, raw_pk)
            dups.append({"source_system": code, "entity": e, "records": len(df),
                         "exact_duplicate_rows": exact, "duplicate_ids": dup_ids,
                         "same_id_different_values": dup_ids - exact,
                         "duplicate_entity_key": " + ".join(spec["dup_key"]).replace("_key", ""),
                         "records_sharing_a_key_with_an_earlier_record": key_dups, "example": example})

    (out_dir / "profile").mkdir(parents=True, exist_ok=True)
    tables = {"record_counts": counts, "field_profile": fields, "duplicates": dups, "format_differences": shapes,
              "invalid_values": invalid, "malformed_records": malformed}
    mal_cols = ["source_system", "entity", "source_row", "reason", "raw_record"]
    for k, rows in tables.items():
        cols = list(dict.fromkeys(c for r in rows for c in r)) or (mal_cols if k == "malformed_records" else [])
        write_csv(out_dir / "profile" / f"{k}.csv", rows, cols)
    write_report(out_dir, loaded, tables, icd9_path if icd9 else None)
    return tables


D_WHERE = {"professionals": "practitioners[]", "patients": "patients[]", "admissions": "patients[].admissions[]",
           "triage": "admissions[].triage", "diagnoses": "admissions[].diagnoses[]",
           "notes": "admissions[].clinicalNotes[]", "orders": "admissions[].orders[]",
           "radiology": "admissions[].imaging[]", "procedures": "admissions[].procedures[]",
           "unit_stays": "admissions[].wardStays[]", "discharges": "admissions[].separation"}


def _raw_name(code, e):
    from profiling.load_sources import A_FILES, B_FILES, C_ELEMENTS
    if code == "A":
        return A_FILES[e]
    if code == "B":
        return B_FILES[e]
    if code == "D":
        return D_WHERE[e]
    return "<" + next(t for t, v in C_ELEMENTS.items() if v[0] == e) + ">"


def _key_duplicates(recs, e, ctx, clean_value, MISSING, raw_pk):
    """Entity-key duplicates, computed with the cleaning parsers (dates, labels, case) - exact copies included."""
    spec = ENTITY_SPECS[e]
    from cleaning.clean_sources import compose_full_name
    need = {"full_name_key": "full_name", "department_key": "department"}

    def value(r, f):
        out = clean_value(r, f, spec["fields"][f], ctx)
        return None if out is MISSING or out.problem else out.value

    seen, n, example = {}, 0, ""
    for r in recs:
        key = []
        for k in spec["dup_key"]:
            f = need.get(k, k)
            v = value(r, f)
            if e == "patients" and f == "full_name" and v is None:
                v = compose_full_name(r.src, value(r, "first_name"), value(r, "last_name"))
            key.append(v.casefold() if isinstance(v, str) else v)
        if any(x is None for x in key):
            continue
        key = tuple(key)
        if key in seen:
            n += 1
            if not example and seen[key] != r.sid:
                example = f"{seen[key]} ~ {r.sid}"
        else:
            seen[key] = r.sid
    return n, example


# -----------------------------------------------------------------------------
def _md(rows, cols=None):
    return md_table(rows, cols, max_len=120)


def write_report(out_dir, loaded, d, icd9_path):
    L = []
    w = L.append
    w("# Profile of the raw sources (Task 1)\n")
    w("Generated by `profiling/profile_sources.py` from the raw files, **before** any cleaning. The full tables are "
      "in `output/profile/` (`record_counts.csv`, `field_profile.csv`, `duplicates.csv`, `format_differences.csv`, "
      "`invalid_values.csv`, `malformed_records.csv`).\n")
    w("## 1. Sources and how they are loaded\n")
    for code, s in loaded.items():
        cfg = SOURCES[code]
        w(f"### Source {code} - {s.name} ({cfg['continent']}, {cfg['timezone']})\n")
        if code == "A":
            w("- **Format:** TXT, one file per entity in `data/raw/A_txt/`, UTF-8, LF line endings.")
            w("- **Delimiter:** pipe `|`. No quoting or escaping (a `|` inside a value was replaced by `/` at export).")
            w("- **Record layout:** line 1 is a header with the field names; every following line is one record with "
              "exactly one value per header field (so `len(header) - 1` pipes). Empty field = no value.")
            w("- **Loading:** each line is split on `|` (no CSV quoting rules apply). A line whose field count differs "
              "from the header (truncated line, or a stray `|` inside a value) cannot be aligned to the columns and "
              "is **logged as malformed** with its file, line number and text, then left out of the table.")
            w("- **Data structure:** one table per file (`cleaning/tabular.py`: column names + one dict per record); every value kept as raw text.\n")
            w("| File | Entity | Header (record layout) |\n|---|---|---|")
            for e, df in s.entities.items():
                w(f"| `{_raw_name('A', e)}` | {e} | `{'|'.join(c for c in df.columns if c not in TECH)}` |")
            w("")
        elif code == "B":
            w("- **Format:** CSV, one file per entity in `data/raw/B_csv/`, UTF-8.")
            w("- **Delimiter:** comma `,`. Minimal quoting: a value containing a comma, a double quote or a line "
              "break is wrapped in `\"...\"`, and a quote inside it is doubled (`\"\"`). Some clinical notes span "
              "several physical lines.")
            w("- **Record layout:** line 1 is a header with the field names; each record has one value per header "
              "field. Empty field = no value.")
            w("- **Loading:** read with Python's `csv` module (not line by line), so quoted commas and line breaks "
              "stay inside their value. A record whose field count differs from the header is **logged as "
              "malformed** with its file, line number(s) and text.")
            w("- **Data structure:** one table per file; every value kept as raw text.\n")
            w("| File | Entity | Header |\n|---|---|---|")
            for e, df in s.entities.items():
                w(f"| `{_raw_name('B', e)}` | {e} | `{','.join(c for c in df.columns if c not in TECH)}` |")
            w("")
        elif code == "D":
            w("- **Format:** JSON, `data/raw/D_json/practitioners.json` (`practitioners[]`) and three pages "
              "`patients_p1..p3.json` (`patients[]`, plus `unlinkedEncounters[]` in page 3), parsed with `json`. "
              "Each file has a `meta` object (export time " + str(s.meta.get("extractTime", "")) + ").")
            w("- **Nesting:** `patients[]` -> `admissions[]` -> `triage` (an object, or an array of two when "
              "duplicated), `diagnoses[]`, `clinicalNotes[]`, `orders[]`, `imaging[]` (with an optional `orderRef`), "
              "`procedures[]`, `wardStays[]`, `separation` (object/array = discharge record). "
              "`unlinkedEncounters[]` are admissions that carry their own `patientId`.")
            w("- **Extraction:** every nested object becomes one row of its entity's table. The parent is taken from "
              "the structure (the enclosing patient / admission). Sub-objects are flattened: `vitals.bp/hr/rr/temp/"
              "spo2` (a `{value, unit}` temperature gives `vitals.temp@unit`, a `{systolic, diastolic}` blood "
              "pressure gives `s/d`), `address` and `nextOfKin` objects become one text value, lists of allergies or "
              "medications are joined with `; `, `appointments[0].at` is the follow-up time. JSON numbers are kept "
              "as their exact text (so `250.00` stays `250.00`).")
            w("- **Malformed:** junk array elements (`null`, a bare string, `[]`, `{}`, an error object) and records "
              "with a field of the wrong JSON type (e.g. `writtenAt: true`, `body` as an object, `orderedBy` as an "
              "array, `modality` as a number) are **logged as malformed** with their JSON path and left out.\n")
            w("| Entity | Where in the JSON |\n|---|---|")
            for e in s.entities:
                w(f"| {e} | `{_raw_name('D', e)}` |")
            w("")
        else:
            w("- **Format:** one XML file `data/raw/C_xml/hospital_records.xml`, UTF-8, parsed with "
              "`xml.etree.ElementTree`.")
            w("- **Root:** `<hospitalRecords>` with attributes "
              + ", ".join(f"`{k}={v}`" for k, v in s.meta.items() if k not in ("format", "root", "file")) + ".")
            w("- **Nesting:** `<staff>/<member>`, `<patients>/<patient>` (name split into `<name><family/><given/>`), "
              "`<admissions>/<admission patientRef=..>` which **contains** its `<triage>`, `<wardMovement>`, "
              "`<diagnosis patientRef=..>`, `<labOrder>` (its `<imaging>` exams nested **inside** the order), walk-in "
              "`<imaging>`, `<operation>`, `<note type=..>` and `<discharge>`. `<unlinkedRecords>` holds children "
              "that carry `admissionRef=..` instead of being nested.")
            w("- **Extraction:** every nested record becomes one row of its entity's table; the parent keys are "
              "taken from the structure (`@admission` = enclosing `<admission>`, `@orderRef` = enclosing "
              "`<labOrder>`), or from `admissionRef` / `orderRef` attributes. Attributes become `@name` columns, "
              "child elements become columns, `<temperature unit=..>` gives `temperature@unit`. An absent element is "
              "None, an empty element is `\"\"` (both are counted as missing).")
            w("- A record **without its id attribute** cannot be identified: it is **logged as malformed** (with its "
              "element path and XML) and left out.\n")
    w(_md(d["record_counts"]))

    w("## 2. Malformed / unreadable records (logged, not loaded)\n")
    w(_md(d["malformed_records"], ["source_system", "entity", "source_row", "reason", "raw_record"]))

    w("## 3. Duplicates\n")
    w("`exact_duplicate_rows` = same values in every field after trimming spaces and ignoring case. "
      "`duplicate_ids` = an ID used more than once. `records_sharing_a_key...` = records whose entity key "
      "(after parsing dates and labels) equals an earlier record's - includes the exact copies and the "
      "near duplicates written under a new ID.\n")
    w(_md(d["duplicates"]))

    w("## 4. Fields: inferred types and missing values\n")
    w("`missing_absent` = XML element not present, `missing_empty` = empty value, `missing_placeholder` = "
      "`N/A`, `null`, `-`, `?`, `0000-00-00` (and `-1` in numeric vitals). `level` is the cleaning rule applied "
      "later (required -> reject, expected -> NULL + flag, optional -> NULL). Note: an empty optional value can be "
      "legitimate (no discharge time for an active admission, no order for a walk-in exam).\n")
    for code in loaded:
        w(f"### Source {code}\n")
        fp = d["field_profile"]
        w(_md([r for r in fp if r["source_system"] == code], ["entity", "raw_field", "common_field", "level", "inferred_type",
                                              "value_formats", "missing_total", "missing_pct", "placeholders_seen",
                                              "distinct_values"]))

    w("## 5. Formatting differences (examples)\n")
    w("Format shapes: digits shown as `9`, letters as `a`. Labels: number of different spellings in the raw "
      "data. Text: case and spacing problems.\n")
    fd = d["format_differences"]
    for code in loaded:
        w(f"### Source {code}\n")
        x = [r for r in fd if r["source_system"] == code]
        multi = Counter((r["entity"], r["raw_field"]) for r in x)
        x = [r for r in x if multi[(r["entity"], r["raw_field"])] > 1
             or re.search("distinct labels|spaces|CAPS|inverted", r["format_shape"])]
        shown, keep = Counter(), []
        for r in x:
            shown[(r["entity"], r["raw_field"])] += 1
            if shown[(r["entity"], r["raw_field"])] <= 6:
                keep.append(r)
        w(_md(keep, ["entity", "raw_field", "format_shape", "count", "example"]))

    w("## 6. Invalid values (examples)\n")
    w("Checked with the same parsers as the cleaning: impossible or ambiguous dates, unparseable numbers, "
      "values outside plausible clinical ranges, labels with no standard value, malformed or unknown ICD-9 "
      "codes" + ("" if icd9_path else " (no ICD-9 dictionary found: only the code format was checked)") + ".\n")
    w(_md(d["invalid_values"], ["source_system", "entity", "raw_field", "problem", "count", "examples"]))
    (out_dir / "profile_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", nargs="+", default=["A", "B", "C", "D"])
    ap.add_argument("--icd9", default=str(ICD_DEFAULT))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    tables = profile(tuple(a.sources), Path(a.icd9), Path(a.out))
    print(md_table(tables["record_counts"]))
    print(f"Written to {Path(a.out) / 'profile_report.md'}")
