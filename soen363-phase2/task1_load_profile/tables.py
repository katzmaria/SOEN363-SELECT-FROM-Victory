"""
Task 1 result tables, built from output/profile/ (printed by show_tables.py).

    python show_tables.py --task 1
"""

PIPELINE_VERSION = "2026.11.17-tasks"   # run_all.py checks that every file has the same version

import re
from collections import Counter, defaultdict
from pathlib import Path

from common.standards import COLUMN_MAP, SOURCES
from common.tabular import ENT, ENT_NAME, cut, n, rows

OUT = Path(__file__).resolve().parents[1] / "output"


def tables(d):
    """Adds the Task 1 tables to `d` (show_tables.TerminalDoc): d.h(...) for section titles, d.table(...)."""
    counts = rows(OUT / "profile" / "record_counts.csv")
    if not counts:
        raise SystemExit("No Task 1 results yet: run  python show_tables.py --task 1")
    srcs = list(dict.fromkeys(r["source_system"] for r in counts))
    raw = {s: sum(int(r["records_loaded"]) + int(r["malformed_not_loaded"]) for r in counts if r["source_system"] == s)
           for s in srcs}
    fprof = rows(OUT / "profile" / "field_profile.csv")
    dups = rows(OUT / "profile" / "duplicates.csv")
    fmt = rows(OUT / "profile" / "format_differences.csv")
    inval = rows(OUT / "profile" / "invalid_values.csv")
    malf = rows(OUT / "profile" / "malformed_records.csv")

    d.h("Task 1: Inspect and Load the Data")
    d.h("1.0 The four sources", 2)
    d.table(["Source", "Continent", "Hospital system", "Format", "Raw files", "Time zone", "Raw records"],
            [[s, SOURCES[s]["continent"], SOURCES[s]["name"], SOURCES[s]["format"],
              {"A": "data/raw/A_txt/*.txt", "B": "data/raw/B_csv/*.csv", "C": "data/raw/C_xml/hospital_records.xml",
               "D": "data/raw/D_json/*.json"}[s], SOURCES[s]["timezone"], n(raw[s])]
             for s in srcs], "The four sources", widths=[6, 8, 22, 6, 24, 14, 9])
    d.h("1.1 Loading the four formats", 2)
    lay = []
    for e in ENT:
        flds = [r["raw_field"] for r in fprof if r["source_system"] == "A" and r["entity"] == e]
        rc = next((r for r in counts if r["source_system"] == "A" and r["entity"] == e), None)
        if rc:
            lay.append([f"`{rc['raw_name']}`", ENT_NAME[e], len(flds), " | ".join(flds)])
    d.table(["File", "Entity", "Fields", "Record layout (header line, delimiter |)"], lay,
            "Record layout of the Source A TXT files", widths=[16, 17, 6, 61])
    d.table(["File", "Entity", "Fields"],
            [[f"`{r['raw_name']}`", ENT_NAME[r["entity"]], r["fields"]] for r in counts if r["source_system"] == "B"],
            "Source B CSV files", widths=[30, 30, 10])
    from task1_load_profile.load_sources import C_ELEMENTS
    paths = {"member": "staff/member", "patient": "patients/patient", "admission": "admissions/admission"}
    d.table(["XML element", "Path", "Entity", "Parent link"],
            [[f"`<{t}>`", paths.get(t, "admissions/admission/" + ("labOrder/" if t == "imaging" else "") + t),
              ENT_NAME[e], "-" if t in paths else ("enclosing <admission> (or admissionRef); enclosing <labOrder> for "
                                                   "the order" if t == "imaging" else "enclosing <admission> (or "
                                                   "admissionRef)")] for t, (e, _, _) in C_ELEMENTS.items()],
            "Nested records extracted from the Source C XML file", widths=[14, 34, 20, 40])
    from task1_load_profile.profile_sources import D_WHERE
    d.table(["Entity", "Where in the JSON"], [[ENT_NAME[e], f"`{D_WHERE[e]}`"] for e in ENT],
            "Nested records extracted from the Source D JSON files", widths=[30, 50])
    d.h("1.2 Running Task 1", 2)
    tot = []
    for s in srcs:
        loaded = sum(int(r["records_loaded"]) for r in counts if r["source_system"] == s)
        mal = sum(int(r["malformed_not_loaded"]) for r in counts if r["source_system"] == s)
        tot.append([s, SOURCES[s]["format"], n(loaded), n(mal), n(loaded + mal)])
    d.table(["Source", "Format", "Records loaded", "Malformed (logged)", "Raw records"], tot,
            "Output of Task 1: records loaded per source")
    d.h("1.3 Profile results", 2)
    rc_rows = []
    for e in ENT:
        vals = [int(next((r["records_loaded"] for r in counts if r["source_system"] == s and r["entity"] == e), 0))
                + int(next((r["malformed_not_loaded"] for r in counts if r["source_system"] == s and r["entity"] == e),
                           0)) for s in srcs]
        rc_rows.append([ENT_NAME[e]] + [n(v) for v in vals] + [n(sum(vals))])
    colsum = [sum(int(x.replace(",", "")) for x in col) for col in list(zip(*[r[1:] for r in rc_rows]))]
    rc_rows.append(["**Total**"] + [f"**{n(v)}**" for v in colsum])
    d.table(["Entity"] + srcs + ["Total"], rc_rows, "Record counts by entity and source")
    for s in srcs:
        fr = [r for r in fprof if r["source_system"] == s and r["entity"] == "admissions"]
        d.table(["Raw field", "Common field", "Level", "Inferred type", "Formats found", "Missing", "Placeholders"],
                [[f"`{r['raw_field']}`", r["common_field"], r["level"], r["inferred_type"], cut(r["value_formats"], 60),
                  f"{r['missing_total']} ({r['missing_pct']}%)", cut(r["placeholders_seen"], 50)] for r in fr],
                f"Source {s} - admission fields, inferred types and missing values", widths=[16, 18, 9, 16, 22, 10, 18])
    mrows = []
    for e in ENT:
        mrows.append([ENT_NAME[e]] + [n(sum(int(r["missing_total"]) for r in fprof
                                            if r["source_system"] == s and r["entity"] == e)) for s in srcs])
    mrows.append(["**Total**"] + [f"**{n(sum(int(r['missing_total']) for r in fprof if r['source_system'] == s))}**"
                                  for s in srcs])
    d.table(["Entity"] + [f"{s}: missing values" for s in srcs], mrows, "Missing values by entity and source")
    ph = defaultdict(Counter)
    for r in fprof:
        for m in re.finditer(r"'([^']*)'x(\d+)", r["placeholders_seen"] or ""):
            ph[r["source_system"]][m.group(1)] += int(m.group(2))
        if int(r["missing_absent"]):
            ph[r["source_system"]]["(field/element absent)"] += int(r["missing_absent"])
        if int(r["missing_empty"]):
            ph[r["source_system"]]["(empty)"] += int(r["missing_empty"])
    d.table(["Source", "How missing values are written (count)"],
            [[s, ", ".join(f"{k} {v}" for k, v in ph[s].most_common())] for s in srcs],
            "Missing-value markers found in each source", widths=[8, 92])
    drows = []
    for e in ENT:
        cells = []
        for s in srcs:
            r = next((x for x in dups if x["source_system"] == s and x["entity"] == e), None)
            cells.append(f"{r['exact_duplicate_rows']} / {r['records_sharing_a_key_with_an_earlier_record']}" if r else "")
        drows.append([ENT_NAME[e]] + cells)
    d.table(["Entity"] + [f"{s}: exact / same key" for s in srcs], drows, "Duplicate counts")
    concepts = [("Admission time", "admissions", "admit_time"), ("Date of birth", "patients", "date_of_birth"),
                ("Temperature", "triage", "temperature"), ("Oxygen saturation", "triage", "spo2"),
                ("Blood pressure", "triage", "blood_pressure"), ("Phone", "patients", "phone"),
                ("ICD-9 code", "diagnoses", "icd9_code"), ("Admission type", "admissions", "admission_type"),
                ("Triage priority", "triage", "triage_priority"), ("Patient id", "patients", "patient_id")]
    crow = []
    for label, e, f in concepts:
        cells = []
        for s in srcs:
            raw = next((k for k, v in COLUMN_MAP[s][e].items() if v == f), None)
            fx = [r for r in fmt if r["source_system"] == s and r["entity"] == e and r["raw_field"] == raw]
            lab = next((r for r in fx if "distinct labels" in r["format_shape"]), None)
            if lab:
                ex = f"{lab['format_shape']}: " + cut(lab["example"], 70)
            else:
                shapes = [r for r in fx if not re.search("spaces|CAPS|inverted", r["format_shape"])]
                shapes.sort(key=lambda r: -int(r["count"]))
                ex = "; ".join(dict.fromkeys(r["example"] for r in shapes[:4]))
            cells.append(f"`{raw}`: {cut(ex, 95)}" if raw else "")
        crow.append([label] + cells)
    d.table(["Concept"] + srcs, crow, "The same concept in the four sources (raw field and example formats)",
            widths=[12, 22, 22, 22, 22], font_half_pts=15)
    plabel = {"invalid_date": "Impossible or unreadable date", "ambiguous_date": "Ambiguous date (DD/MM or MM/DD)",
              "out_of_range": "Number outside its valid range", "invalid_number": "Not a number",
              "unmappable_label": "Label with no standard value", "unknown_icd9_code": "ICD-9 code not in the dictionary",
              "invalid_icd9_format": "Not an ICD-9 code", "invalid_phone": "Unreadable phone number",
              "invalid_id": "Unreadable identifier"}
    ir = []
    for p_, lbl in plabel.items():
        cells = []
        for s in srcs:
            xs = [r for r in inval if r["source_system"] == s and r["problem"] == p_]
            c = sum(int(r["count"]) for r in xs)
            cells.append(f"{c} (e.g. `{cut(xs[0]['examples'].split(' | ')[0], 28)}`)" if c else "0")
        if any(c != "0" for c in cells):
            ir.append([lbl] + cells)
    d.table(["Check"] + srcs, ir, "Invalid and suspicious values found in the raw data", widths=[22, 19, 19, 19, 19])
    d.table(["Source", "Entity", "Location", "Reason", "Raw record (start)"],
            [[r["source_system"], ENT_NAME.get(r["entity"], r["entity"]), cut(r["source_row"], 50), cut(r["reason"], 60),
              cut(r["raw_record"], 70)] for r in malf],
            "Malformed records (logged, not loaded)", widths=[6, 14, 28, 26, 26], font_half_pts=15)
