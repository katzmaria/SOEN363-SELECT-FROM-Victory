"""
Builds output/Phase2_Tasks1-2_report.docx: the Task 1 and Task 2 write-up with every table generated from the
results of the last run (output/profile/, output/cleaning_log/, output/quarantine/). Standard library only.

    python reporting/make_report.py            (run_all.py calls it at the end)
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cleaning.standards import (COLUMN_MAP, ENTITY_SPECS, LABEL_MAPS, LEVEL_OVERRIDES, NONE_KNOWN,  # noqa: E402
                                SOURCES, VITAL_RANGES)
from cleaning.tabular import read_csv  # noqa: E402
from reporting.docx_writer import Docx  # noqa: E402

PIPELINE_VERSION = "2026.11.15-abcd"
OUT = ROOT / "output"
REPORT = OUT / "Phase2_Tasks1-2_report.docx"
ENT = ["professionals", "patients", "admissions", "triage", "diagnoses", "notes", "orders", "radiology",
       "procedures", "unit_stays", "discharges"]
ENT_NAME = {"professionals": "HealthcareProfessional", "patients": "Patient", "admissions": "Admission",
            "triage": "TriageAssessment", "diagnoses": "Diagnosis", "notes": "ClinicalNote",
            "orders": "DiagnosticOrder", "radiology": "RadiologyExamination", "procedures": "SurgicalProcedure",
            "unit_stays": "UnitStay", "discharges": "DischargeRecord"}


def rows(path):
    return read_csv(path)[1] if path.exists() else []


def n(x):
    return f"{int(x):,}"


def vis(s):
    """Make removed spaces visible: leading/trailing spaces and double spaces shown as a middle dot."""
    s = str(s or "")
    core = s.strip(" ")
    lead, trail = len(s) - len(s.lstrip(" ")), len(s) - len(s.rstrip(" "))
    return "\u00b7" * lead + re.sub(r" {2,}", lambda m: "\u00b7" * len(m.group(0)), core) + "\u00b7" * trail


def cut(s, k=90):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= k else s[:k - 3] + "..."


def build(out_path=REPORT):
    summ = rows(OUT / "cleaning_log" / "summary.csv")
    if not summ:
        raise SystemExit("No results found: run  python run_all.py  first.")
    srcs = list(dict.fromkeys(r["source_system"] for r in summ))
    counts = rows(OUT / "profile" / "record_counts.csv")
    fprof = rows(OUT / "profile" / "field_profile.csv")
    dups = rows(OUT / "profile" / "duplicates.csv")
    fmt = rows(OUT / "profile" / "format_differences.csv")
    inval = rows(OUT / "profile" / "invalid_values.csv")
    malf = rows(OUT / "profile" / "malformed_records.csv")
    log = rows(OUT / "cleaning_log" / "cleaning_log.csv")
    labels = rows(OUT / "cleaning_log" / "label_mappings.csv")
    quar = [r for e in ENT for r in rows(OUT / "quarantine" / f"{e}.csv")]
    S = {s: {k: sum(int(r[k]) for r in summ if r["source_system"] == s) for k in summ[0]
             if k not in ("source_system", "entity")} for s in srcs}
    T = {k: sum(S[s][k] for s in srcs) for k in S[srcs[0]]}
    act = Counter((r["source_system"], r["action"], r["rule"]) for r in log)
    reasons = Counter((r["source_system"], c.split(":")[0]) for r in quar for c in r["reason_codes"].split(";"))

    d = Docx()
    d.title("SOEN 363 - Project Phase 2", "Tasks 1 and 2: loading, profiling, cleaning and standardization of the "
                                         "four hospital sources")

    # =========================================================================
    d.h("1. Introduction")
    d.p("For Phase 2 we work with four synthetic hospital sources, one per continent, and each one uses a different "
        "file format. All four describe the same entities as Phase 1 (healthcare professionals, patients, "
        "admissions, triage assessments, diagnoses, clinical notes, diagnostic orders, radiology examinations, "
        "surgical procedures, unit stays and discharge records), but each source has its own field names, date "
        "formats, labels, units and missing-value markers.")
    d.table(["Source", "Continent", "Hospital system", "Format", "Raw files", "Time zone", "Raw records"],
            [[s, SOURCES[s]["continent"], SOURCES[s]["name"], SOURCES[s]["format"],
              {"A": "data/raw/A_txt/*.txt", "B": "data/raw/B_csv/*.csv", "C": "data/raw/C_xml/hospital_records.xml",
               "D": "data/raw/D_json/*.json"}[s], SOURCES[s]["timezone"], n(S[s]["raw_records_read"])]
             for s in srcs], "The four sources", widths=[6, 8, 22, 6, 24, 14, 9])
    d.p("Task 1 loads the raw files and builds an initial profile of them. Task 2 cleans the data and converts it to "
        "one common format. Both parts are written in Python and use **only the standard library** (no pandas), so "
        "they run on any Python 3.10+ without installing anything. On Windows the optional `tzdata` package gives "
        "Python the official time-zone database; without it the code uses built-in rules for the four time zones, "
        "which give exactly the same results.")
    d.h("1.1 Folder structure", 2)
    d.bullets([
        "**data/raw/** - the original source files (A_txt, B_csv, C_xml, D_json). They are only read, never modified.",
        "**profiling/** - Task 1 code: `load_sources.py` (one loader per format) and `profile_sources.py`.",
        "**cleaning/** - Task 2 code: `standards.py` (every rule and mapping in one place), `parsers.py` (dates, "
        "time zones, numbers, units, ICD-9, phones, names), `clean_sources.py` (the pipeline), `report.py` and "
        "`tabular.py` (small table/CSV helpers).",
        "**reporting/** - builds this document from the results.",
        "**output/profile/** and **output/profile_report.md** - Task 1 results.",
        "**output/clean/**, **output/quarantine/**, **output/cleaning_log/** and **output/cleaning_report.md** - "
        "Task 2 results.",
        "**run_all.py** - runs everything in order.",
    ])
    d.h("1.2 How to run", 2)
    d.p("One command, run from the `soen363-phase2` folder, does Task 1, Task 2 and rebuilds this document:")
    d.code(["python run_all.py --icd9 ../soen363-phase1/data/icd9_dictionary.csv"])
    d.p("It first checks that every code file is the current version (and names any file that is outdated), then "
        "profiles the raw files, cleans them and writes the outputs. The run takes about ten seconds. Running it "
        "again on the same raw files gives exactly the same output files, byte for byte.")

    # =========================================================================
    d.h("2. Task 1: Inspect and Load the Data")
    d.h("2.1 Loading the four formats", 2)
    d.p("`load_sources.py` reads every source into the same structure: for each of the 11 entities a table "
        "(column names plus one Python dictionary per record). The values are kept exactly as they were read, as "
        "text, so nothing is cleaned at this step. Every record also keeps its location (file and line number, or "
        "the XML/JSON path) and its original raw text, which lets us trace any value back to the raw file and "
        "copy it unchanged into the quarantine.")

    d.p("**Source A (TXT).** One `.txt` file per entity, encoded in UTF-8 with LF line endings. **The first line is a "
        "header with the field names, and the fields are separated by a pipe character (`|`).** There is no "
        "quoting and no escaping: the producer replaced any pipe inside a value with a slash, so every pipe is a "
        "delimiter and a valid record has exactly one pipe less than its number of fields. Each line is one record "
        "and each record has one value per header field; an empty field means no value. A line is only accepted if "
        "it has the same number of fields as the header. Decimal numbers use a comma (`37,2`) and timestamps are "
        "local Paris time written `DD/MM/YYYY HH:MM`. The table below gives the record layout of every file.")
    lay = []
    for e in ENT:
        flds = [r["raw_field"] for r in fprof if r["source_system"] == "A" and r["entity"] == e]
        rc = next((r for r in counts if r["source_system"] == "A" and r["entity"] == e), None)
        if rc:
            lay.append([f"`{rc['raw_name']}`", ENT_NAME[e], len(flds), " | ".join(flds)])
    d.table(["File", "Entity", "Fields", "Record layout (header line, delimiter |)"], lay,
            "Record layout of the Source A TXT files", widths=[16, 17, 6, 61])

    d.p("**Source B (CSV).** One `.csv` file per entity, UTF-8, comma-delimited, with a header row. Values that "
        "contain a comma, a double quote or a line break are wrapped in double quotes (a quote inside is doubled), "
        "and some clinical notes span several physical lines. The files are therefore read with Python's `csv` "
        "module and not line by line. A record whose number of fields differs from the header is logged as "
        "malformed.")
    d.table(["File", "Entity", "Fields"],
            [[f"`{r['raw_name']}`", ENT_NAME[r["entity"]], r["fields"]] for r in counts if r["source_system"] == "B"],
            "Source B CSV files", widths=[30, 30, 10])

    d.p("**Source C (XML).** One file, `hospital_records.xml`, parsed with `xml.etree.ElementTree`. Staff and patients "
        "are simple lists. Everything that belongs to an admission is **nested inside its `<admission>` element**, "
        "so each child is taken out as its own record and gets the admission id of the element that encloses it. "
        "Radiology exams are nested one level deeper, inside their `<labOrder>`, so they also get that order's id. "
        "The patient name is nested as `name/family` and `name/given`, and the temperature unit is an attribute "
        "(`<temperature unit=\"F\">`). Records in `<unlinkedRecords>` carry an `admissionRef` attribute instead of "
        "being nested. An element without its id attribute cannot be identified and is logged as malformed.")
    from profiling.load_sources import C_ELEMENTS
    paths = {"member": "staff/member", "patient": "patients/patient", "admission": "admissions/admission"}
    d.table(["XML element", "Path", "Entity", "Parent link"],
            [[f"`<{t}>`", paths.get(t, "admissions/admission/" + ("labOrder/" if t == "imaging" else "") + t),
              ENT_NAME[e], "-" if t in paths else ("enclosing <admission> (or admissionRef); enclosing <labOrder> for "
                                                   "the order" if t == "imaging" else "enclosing <admission> (or "
                                                   "admissionRef)")] for t, (e, _, _) in C_ELEMENTS.items()],
            "Nested records extracted from the Source C XML file", widths=[14, 34, 20, 40])

    d.p("**Source D (JSON).** Four files parsed with the `json` module: `practitioners.json` and three pages "
        "`patients_p1..p3.json`. Each patient object holds its `admissions[]` array, and each admission holds its "
        "children: `triage` (an object, or an array of two when duplicated), `diagnoses[]`, `clinicalNotes[]`, "
        "`orders[]`, `imaging[]`, `procedures[]`, `wardStays[]` and `separation` (the discharge record). Every "
        "nested object becomes one record with the id of its parent. Sub-objects are flattened: `vitals.bp`, "
        "`vitals.temp` (with its unit), `address`, `nextOfKin` and `location` become one value each, lists of "
        "allergies or medications are joined with `; `, and JSON numbers are kept as their exact text so that "
        "`250.00` does not turn into `250.0`. Page 3 also has `unlinkedEncounters[]`, admissions carrying their own "
        "patient id.")
    from profiling.profile_sources import D_WHERE
    d.table(["Entity", "Where in the JSON"], [[ENT_NAME[e], f"`{D_WHERE[e]}`"] for e in ENT],
            "Nested records extracted from the Source D JSON files", widths=[30, 50])

    mal_by = Counter(r["source_system"] for r in malf)
    d.p("**Malformed records.** A record is never dropped silently. A TXT line or CSV record with the wrong number of "
        "fields, a line that is not valid UTF-8, an XML element without its id, a JSON array element that is not a "
        "record (`null`, a bare string, `[]`, `{}`, an error object) or a JSON record with a field of the wrong type "
        "(for example `writtenAt: true` or `body` as an object) is written to `output/profile/malformed_records.csv` "
        "with its location, the reason and its raw text, and to the quarantine. In our data this happened for "
        + ", ".join(f"{mal_by.get(s, 0)} record(s) in {s}" for s in srcs) + " (last table of section 2.3).")

    d.h("2.2 Running Task 1", 2)
    d.p("`run_all.py` (or `python profiling/profile_sources.py` alone) prints the number of records loaded per "
        "source and entity. For every source, the records loaded plus the malformed records equal the total number "
        "of records in the raw files.")
    tot = []
    for s in srcs:
        loaded = sum(int(r["records_loaded"]) for r in counts if r["source_system"] == s)
        mal = sum(int(r["malformed_not_loaded"]) for r in counts if r["source_system"] == s)
        tot.append([s, SOURCES[s]["format"], n(loaded), n(mal), n(loaded + mal)])
    d.table(["Source", "Format", "Records loaded", "Malformed (logged)", "Raw records"], tot,
            "Output of Task 1: records loaded per source")

    d.h("2.3 Profile results", 2)
    d.p("**Record counts.** The table below shows the number of records per entity and source (malformed records included, "
        "duplicates included).")
    rc_rows = []
    for e in ENT:
        vals = [int(next((r["records_loaded"] for r in counts if r["source_system"] == s and r["entity"] == e), 0))
                + int(next((r["malformed_not_loaded"] for r in counts if r["source_system"] == s and r["entity"] == e),
                           0)) for s in srcs]
        rc_rows.append([ENT_NAME[e]] + [n(v) for v in vals] + [n(sum(vals))])
    colsum = [sum(int(x.replace(",", "")) for x in col) for col in list(zip(*[r[1:] for r in rc_rows]))]
    rc_rows.append(["**Total**"] + [f"**{n(v)}**" for v in colsum])
    d.table(["Entity"] + srcs + ["Total"], rc_rows, "Record counts by entity and source")

    d.p("**Field names, inferred types and missing values.** For each field, the profiler infers the type from the "
        "values (integer, decimal, decimal with a comma, number with a unit, date, timestamp, code/id, categorical "
        "text or text), shows the share of each format, and counts the missing values. The next four tables show "
        "the admission fields of each source as an example; the profile of every field of every source is in "
        "`output/profile/field_profile.csv` and `output/profile_report.md`.")
    for s in srcs:
        fr = [r for r in fprof if r["source_system"] == s and r["entity"] == "admissions"]
        d.table(["Raw field", "Common field", "Level", "Inferred type", "Formats found", "Missing", "Placeholders"],
                [[f"`{r['raw_field']}`", r["common_field"], r["level"], r["inferred_type"], cut(r["value_formats"], 60),
                  f"{r['missing_total']} ({r['missing_pct']}%)", cut(r["placeholders_seen"], 50)] for r in fr],
                f"Source {s} - admission fields, inferred types and missing values", widths=[16, 18, 9, 16, 22, 10, 18])

    d.p("**Missing-value counts.** The next table adds up the missing values of all fields of each entity. A missing value "
        "is an absent field/element/key, an empty value, or a placeholder (`N/A`, `null`, `-`, `?`, `0000-00-00`, "
        "and `-1` in numeric vital signs). Some empty values are legitimate (no discharge time for an active "
        "admission, no order for a walk-in exam); the cleaning decides which ones matter.")
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

    d.p("**Duplicates.** We count exact duplicate rows (every field equal after trimming spaces and ignoring case), "
        "ids that appear more than once, and records whose entity key (patient: name + date of birth; staff: name + "
        "role + department; admission: patient + admission time; other records: admission + timestamp + type) is "
        "the same as an earlier record's after parsing the dates and labels. The last count includes the copies "
        "written under a new id.")
    drows = []
    for e in ENT:
        cells = []
        for s in srcs:
            r = next((x for x in dups if x["source_system"] == s and x["entity"] == e), None)
            cells.append(f"{r['exact_duplicate_rows']} / {r['records_sharing_a_key_with_an_earlier_record']}" if r else "")
        drows.append([ENT_NAME[e]] + cells)
    d.table(["Entity"] + [f"{s}: exact / same key" for s in srcs], drows, "Duplicate counts")

    d.p("**Formatting differences.** The table below compares how each source writes the same information (the raw field and "
        "examples of its most frequent formats). Dates, units, codes and labels are all written differently, which "
        "is why Task 2 needs rules and mappings for each source.")
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

    d.p("**Invalid values.** The profiler checks every value with the same parsers the cleaning uses. The table below gives "
        "the number of invalid values per check and source with an example. Every occurrence is listed in "
        "`output/profile/invalid_values.csv`. Problems that involve two records (a missing parent, an event "
        "outside its admission) are checked in Task 2.")
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

    # =========================================================================
    d.h("3. Task 2: Clean and Standardize the Data")
    d.h("3.1 Cleaning steps", 2)
    d.p("`clean_sources.py` runs the following steps for each source, in this order:")
    d.bullets([
        "Read the source (Task 1 loaders) and map every raw field to a common field name.",
        "Remove exact duplicates (same id and every field equal after trimming and ignoring case). The same id with "
        "different values is a conflict: the later copy is rejected.",
        "Standardize each field: placeholders, identifiers, text, dates and time zones, numbers and units, labels, "
        "ICD-9 codes. A missing or invalid required value rejects the record.",
        "Standardize capitalization (the most common spelling of a value in its column is applied to its variants).",
        "Process the entities parent-first (professionals, patients, admissions, orders, radiology, then the other "
        "children): re-point references to merged duplicates, check references, merge duplicate entities, check "
        "chronology. A child of a rejected parent is rejected too (cascade).",
        "Write the clean tables, the quarantine tables, the cleaning log, the label mappings and the reports.",
    ], numbered=True)
    d.p("The order matters: for example, references to a duplicate patient are moved to the kept patient **before** "
        "references are checked, so those admissions are not rejected as orphans. Our main rule is that **we never "
        "invent a value to make a record pass**. A value is only corrected when the data itself gives the answer "
        "(format, unit, case, a merged duplicate, the admission of a diagnosis). Otherwise an invalid optional value "
        "becomes NULL, and a record that misses required information goes to the quarantine with the reason and its "
        "original raw text. Every change is written to `output/cleaning_log/cleaning_log.csv` with the value before "
        "and after.")

    d.h("3.2 Missing values", 2)
    d.p("Each source writes missing values in its own way (see section 2.3): an empty field, `N/A`, `null`, `-`, `?`, "
        "`0000-00-00` for dates, `-1` for numbers, an absent XML element or JSON key. All of them become NULL. Some "
        "values look similar but are real information and are kept: " + ", ".join(f"`{x}`" for x in sorted(NONE_KNOWN))
        + " in allergies and medications mean the patient has none, so they become the value `none`, not NULL.")
    lv = []
    for e in ENT:
        sp = ENTITY_SPECS[e]
        opt = [f for f in sp["fields"] if f not in sp["required"] and f not in sp["expected"]]
        extra = "; ".join(f"{s}: {f} {lvl}" for s in srcs for f, lvl in LEVEL_OVERRIDES.get(s, {}).get(e, {}).items())
        lv.append([ENT_NAME[e], ", ".join(sp["required"]) + (f" ({extra})" if extra else ""),
                   ", ".join(sp["expected"]) or "-", ", ".join(opt) or "-"])
    d.table(["Entity", "Required (missing -> rejected)", "Expected (missing -> NULL + flag)", "Optional (NULL)"], lv,
            "Required, expected and optional fields", widths=[16, 40, 20, 34], font_half_pts=15)
    tot_act = lambda a, rule=None: sum(v for (s, a2, r2), v in act.items() if a2 == a and (rule is None or r2 == rule))
    d.table(["Situation", "What happens", "Count"],
            [["Required value missing or invalid (e.g. no admission time, unreadable date, unknown ICD-9 code)",
              "Record **rejected** to the quarantine with the reason", n(sum(v for (s, c), v in reasons.items()
                                                                             if c in ("missing_required", "invalid_date", "ambiguous_date", "unmappable_label", "unknown_icd9_code", "invalid_icd9_format", "invalid_id")))],
             ["Expected value missing (staff name or role, patient life status, test name)",
              "Record **kept**, value NULL, row flagged `missing_expected`", n(tot_act("flagged", "missing_expected"))],
             ["Optional value missing (placeholder)", "Value set to **NULL**", n(tot_act("set_null", "placeholder_to_null"))],
             ["Optional value invalid (pulse 420, `abc`, SpO2 140, unreadable phone)",
              "Value set to **NULL**, row flagged", n(tot_act("set_null") - tot_act("set_null", "placeholder_to_null"))],
             ["Value in another format, unit or case", "Value **corrected**, change logged", n(tot_act("corrected"))]],
            "When a record is corrected, kept with NULL or rejected", widths=[45, 40, 15])

    d.h("3.3 Duplicates", 2)
    d.p("**Exact duplicates** (same id, every field equal after trimming and ignoring case) are removed and the first "
        "copy is kept. **Duplicate entities** have different ids but the same entity key after cleaning (keys in the table below) and "
        "no other field with two different non-empty values: the lowest id is kept, the other record is removed, its "
        "non-empty values fill the gaps of the kept record, and every reference to it is re-pointed to the kept record "
        "(for example an admission of a patient registered twice). If the key matches but another field differs "
        "(two exams of the same type at the same minute for different orders), both are real records: both are kept "
        "and flagged `possible_duplicate`. Staff have no date of birth, so two staff records with the same name, role "
        "and department are only merged if one of the ids is used by fewer than 10 clinical records.")
    d.table(["Entity", "Duplicate key"], [[ENT_NAME[e], " + ".join(ENTITY_SPECS[e]["dup_key"]).replace("_key", "")]
                                          for e in ENT], "Duplicate-entity keys", widths=[30, 70])
    d.table(["Source", "Exact duplicates removed", "Duplicate entities merged", "References re-pointed",
             "Flagged possible duplicates"],
            [[s, n(S[s]["exact_duplicates_removed"]), n(S[s]["near_duplicates_merged"]),
              n(act[(s, "corrected", "repointed_to_kept_duplicate")]), n(act[(s, "flagged", "possible_duplicate")])]
             for s in srcs], "Duplicates found per source")

    d.h("3.4 Text", 2)
    d.bullets([
        "Whitespace is trimmed and runs of spaces are collapsed to one in every text value.",
        "Person names get a capital letter per word (`DUBOIS` -> `Dubois`, `o'neill` -> `O'Neill`), with particles in "
        "lower case (`de`, `van`, `bin`, `binte`, `s/o`, `d/o`). Source D names written `SURNAME, Given` are "
        "reordered to `Given Surname`. `full_name` follows each hospital's naming order.",
        "Short descriptive text (reasons, departments, indications, allergies) takes the spelling used most often for "
        "the same value in its column (`CHEST PAIN`, `cHEST pAIN` -> `Chest pain`).",
        "Clinical free text (notes, findings, instructions) keeps its case unless the whole value is damaged (all "
        "capitals or inverted case) and the same text exists elsewhere with normal case.",
        "Labels are compared without case and spaces and mapped to the common values (section 3.7). Phones become "
        "E.164 (`+256759800807`) and the next of kin is split into name, relationship and phone.",
    ])
    tex = []
    for rule in ["whitespace_trimmed", "case_standardised", "name_reordered", "none_known_standardised"]:
        for s in srcs:
            x = next((r for r in log if r["rule"] == rule and r["source_system"] == s and r["before"]), None)
            if x:
                tex.append([s, ENT_NAME[x["entity"]], x["field"], rule, f"`{vis(x['before'])[:45]}`",
                            f"`{cut(x['after'], 45)}`"])
    d.p("In the examples below, a removed space is shown as \u00b7.")
    d.table(["Source", "Entity", "Field", "Rule", "Before", "After"], tex, "Text standardization examples",
            widths=[6, 14, 14, 18, 24, 24])

    d.h("3.5 Dates and time zones", 2)
    d.p("All timestamps are converted to **UTC** and written in ISO 8601 (`2024-05-08T12:59:00Z`); dates of birth are "
        "written `YYYY-MM-DD`. `admissions.source_timezone` keeps the hospital's zone so local time can be recovered. "
        "The table below shows the time zone of each source and how its timestamps are read.")
    d.table(["Source", "Time zone", "DST", "How raw timestamps are written", "Converted (non-standard format)",
             "Written in UTC (Z)", "Unix time"],
            [[s, SOURCES[s]["timezone"], "yes" if s in ("A", "D") else "no", SOURCES[s]["raw_time"],
              n(act[(s, "corrected", "date_format_standardised")]), n(act[(s, "corrected", "written_in_utc")]),
              n(act[(s, "corrected", "unix_timestamp_converted")])] for s in srcs],
            "Source time zones and how they are converted", widths=[6, 13, 5, 40, 13, 10, 9])
    d.bullets([
        "A value with an explicit offset (`+08:00`, `+11:00`) or `Z` is converted exactly. A value without one is "
        "local time of the source's zone; in C and D, where an offset is normally present, such values are "
        "flagged `no_offset_local_time_assumed`. An unknown time zone is never guessed: it would stop the run.",
        "Europe/Paris and Australia/Sydney have daylight saving time. A local time in the autumn repeated hour is "
        "ambiguous: we take the first occurrence and flag it; a time in the spring gap does not exist: it is moved "
        "forward one hour and flagged. Africa/Kampala (UTC+3) and Asia/Singapore (UTC+8) have no DST.",
        "Slash dates are day-first in every source, except Source B slash dates written with AM/PM, which are "
        "month-first. Dot dates are day-first in A but come in both orders in D. A dash or D dot date `NN-NN-YYYY` is "
        "day-first if the first number is over 12 and month-first if the second is over 12; if both are 12 or less "
        "the date is **ambiguous** and is not guessed.",
        "Impossible dates (`31/02/2024`, month 13, hour 25, years such as `0202` or `20225`, two-digit years, `TBC`) "
        "are invalid. An invalid or ambiguous required date rejects the record; an optional one becomes NULL.",
    ])

    d.h("3.6 Numbers and units", 2)
    rng = {k: f"{a}-{b}" for k, (a, b) in VITAL_RANGES.items()}
    d.table(["Measure", "Raw forms", "Stored as", "Valid range", "Conversions"] + [f"{s} invalid" for s in srcs],
            [["Temperature", "`37,2`, `98.6F`, `99.1 °F`, `{value, unit}`, bare 86-113", "Celsius, 1 decimal",
              rng["temperature_c"], "(F - 32) x 5/9: " + ", ".join(
                  f"{s} {act[(s, 'corrected', 'fahrenheit_converted_to_celsius')] + act[(s, 'corrected', 'fahrenheit_converted_to_celsius_unit_inferred')]}"
                  for s in srcs)],
             ["Oxygen saturation", "`96`, `96%`, `0.96` (C)", "integer percent", rng["spo2_pct"],
              "fraction x 100 (C): " + str(act[("C", "corrected", "fraction_converted_to_percent")])],
             ["Blood pressure", "`120/80`, `120 / 80`, `120-80`, `120/80 mmHg`, `{systolic, diastolic}`",
              "systolic_bp + diastolic_bp", f"{rng['systolic_bp']} / {rng['diastolic_bp']}", "split"],
             ["Heart rate", "`88`, `88 bpm`, `88/min`", "integer per minute", rng["heart_rate"], "unit text removed"],
             ["Respiratory rate", "`18`, `18/min`", "integer per minute", rng["respiratory_rate"], "unit text removed"],
             ["Pain score", "`4`, `4/10`", "integer", rng["pain_score"], "unit text removed"]],
            "Unit conversions and valid ranges", widths=[12, 26, 13, 10, 20], font_half_pts=15)
    d.table(["Source", "Decimal comma fixed", "Unit text removed", "Out of range -> NULL", "Not a number -> NULL"],
            [[s, n(act[(s, "corrected", "decimal_comma")]), n(act[(s, "corrected", "unit_text_removed")]),
              n(act[(s, "set_null", "out_of_range")]), n(act[(s, "set_null", "invalid_number")])] for s in srcs],
            "Numeric corrections per source")
    d.p("An impossible vital sign is set to NULL but the triage record is kept, because the rest of the assessment "
        "(time, priority, other vital signs) is still valid. ICD-9 codes stay text: they are trimmed, upper-cased, the "
        "leading zero and the decimal point are restored (`38.9` -> `038.9`, `4019` -> `401.9`), and a code that is not "
        "in the Phase 1 dictionary rejects the diagnosis.")

    d.h("3.7 Clinical categories", 2)
    d.p("Labels are compared without case and extra spaces, then mapped to the common values below (the values of "
        "the CHECK constraints in our contract). A label that maps to nothing is **unmappable**: the record is "
        "rejected if the field is required, the value is NULL otherwise. We never guess. Every raw label and the "
        "value it was mapped to is counted in `output/cleaning_log/label_mappings.csv`.")
    cat = []
    for key in ["admission_type", "admission_status", "triage_priority", "unit_type", "order_status", "priority",
                "exam_status", "diagnosis_type", "life_status"]:
        for std in sorted({x for s in srcs for x in LABEL_MAPS[s][key]}):
            cat.append([key, f"**{std}**"] + [", ".join(LABEL_MAPS[s][key].get(std, [])) for s in srcs])
    d.table(["Category", "Common value"] + [f"Source {s} labels" for s in srcs], cat,
            "Mapping of source labels to common values", widths=[12, 13, 19, 19, 19, 19], font_half_pts=14)
    un = [r for r in labels if r["standard_value"] == "<unmapped>"]
    d.table(["Source", "Entity", "Field", "Unmappable label", "Count"],
            [[r["source_system"], ENT_NAME[r["entity"]], r["field"], f"`{r['raw_label']}`", r["count"]] for r in un],
            "Labels that could not be mapped (rejected or NULL)", widths=[8, 22, 20, 30, 8])

    d.h("3.8 Relationships", 2)
    d.p("References are checked parent-first. **Orphan reference**: the referenced id does not exist anywhere in the "
        "source (an admission of a patient that does not exist, a note by an unknown author). **Parent quarantined**: "
        "the parent exists but was rejected, so the child cannot be linked any more and is rejected too (cascade). "
        "**Inconsistent reference**: a diagnosis whose patient differs from its admission's patient, or a radiology "
        "exam whose admission differs from its order's admission. A radiology exam without an order is a legitimate "
        "walk-in exam (order_id NULL); one pointing to a non-existent order is rejected, because blanking the "
        "reference would invent the fact that it was a walk-in exam.")
    d.table(["Source", "Orphan reference", "Parent quarantined (cascade)", "Inconsistent reference",
             "Role mismatch flagged"],
            [[s, n(reasons[(s, "orphan_reference")]), n(reasons[(s, "parent_quarantined")]),
              n(reasons[(s, "inconsistent_reference")]), n(act[(s, "flagged", "role_mismatch")])] for s in srcs],
            "Relationship problems per source")

    d.h("3.9 Chronology", 2)
    checks = [("Admission before the patient's date of birth", "before date of birth"),
              ("Discharge before admission", r"discharge \S+ before admission"),
              ("Event after the extract time", "after the extract time"),
              ("Child event before its admission", r"(triage|diagnosis|note|order|exam|procedure|entry)_time \S+ before admission"),
              ("Child event after the admission's discharge", r"_time \S+ after discharge"),
              ("Discharge record before admission", r"discharge_time \S+ before admission"),
              ("Unit exit before unit entry", "unit exit .* before entry"),
              ("Unit exit after the admission ended", "after the admission ended"),
              ("Radiology exam before its order", "before its order"),
              ("Discharge record for an admission that is still active", "still active")]
    chq = [r for r in quar if "chronology" in r["reason_codes"]]
    ch_rows = []
    for label, pat in checks:
        ch_rows.append([label] + [n(sum(1 for r in chq if r["source_system"] == s and re.search(pat, r["reason_details"])))
                                  for s in srcs])
    d.table(["Check (rejected)"] + srcs, ch_rows, "Chronology checks (records rejected)", widths=[52, 12, 12, 12, 12])
    soft = [("Discharge record time differs from the admission's", "discharge_time_differs"),
            ("Overlapping unit stays", "overlapping_unit_stays"), ("Open unit stay after discharge", "open_stay_after_discharge"),
            ("Status inconsistent with discharge time", "status_inconsistent"),
            ("Follow-up before discharge", "chronology_soft"), ("Patient alive after an admission ending in death",
                                                                "life_status_inconsistent")]
    d.table(["Check (kept, flagged only)"] + srcs, [[lbl] + [n(act[(s, "flagged", r)]) for s in srcs] for lbl, r in soft],
            "Soft chronology checks (record kept with a flag)", widths=[52, 12, 12, 12, 12])
    d.p("All comparisons are made in UTC, after the time-zone conversion, so events of a source with daylight saving "
        "time are compared correctly.")

    d.h("3.10 Results", 2)
    res = []
    for s in srcs:
        x = S[s]
        res.append([s, n(x["raw_records_read"]), n(x["malformed"]), n(x["exact_duplicates_removed"]),
                    n(x["near_duplicates_merged"]), n(x["rejected_own_problem"]), n(x["rejected_cascade"]),
                    n(x["clean_records"]), f"{100 * x['clean_records'] / x['raw_records_read']:.1f}%"])
    res.append(["**All**"] + [f"**{n(T[k])}**" for k in ("raw_records_read", "malformed", "exact_duplicates_removed",
                                                         "near_duplicates_merged", "rejected_own_problem",
                                                         "rejected_cascade", "clean_records")]
               + [f"**{100 * T['clean_records'] / T['raw_records_read']:.1f}%**"])
    d.table(["Source", "Raw records", "Malformed", "Exact duplicates", "Entities merged", "Rejected (own problem)",
             "Rejected (cascade)", "Clean", "Kept"], res, "Output of run_all.py: cleaning results per source",
            widths=[8, 10, 10, 10, 10, 12, 11, 9, 8])
    d.p(f"Out of the {n(T['raw_records_read'])} raw records, {n(T['malformed'])} could not be read, "
        f"{n(T['exact_duplicates_removed'])} were exact duplicate copies, {n(T['near_duplicates_merged'])} were duplicate "
        f"entities merged into the kept record, {n(T['rejected_own_problem'] + T['rejected_cascade'])} were quarantined "
        f"({n(T['rejected_cascade'])} of them only because their parent was quarantined), and "
        f"{n(T['clean_records'])} are in the clean tables "
        f"({100 * T['clean_records'] / T['raw_records_read']:.1f}%). Every raw record ends up in exactly one of these "
        f"groups. In total {n(sum(v for (s, a, r), v in act.items() if a in ('corrected', 'set_null', 'flagged')))} "
        "corrections, NULLs and flags were logged.")
    pe = []
    for e in ENT:
        cells = []
        for s in srcs:
            r = next((x for x in summ if x["source_system"] == s and x["entity"] == e), None)
            cells.append(f"{n(r['clean_records'])} / {n(int(r['raw_records_read']) - int(r['clean_records']))}" if r else "")
        pe.append([ENT_NAME[e]] + cells)
    d.table(["Entity"] + [f"{s}: clean / not clean" for s in srcs], pe, "Clean and quarantined records per entity")
    rlabel = {"exact_duplicate": "Exact duplicate (removed)", "near_duplicate": "Duplicate entity (merged)",
              "missing_required": "Missing required value", "invalid_date": "Invalid date",
              "ambiguous_date": "Ambiguous date", "unmappable_label": "Unmappable category",
              "unknown_icd9_code": "Unknown ICD-9 code", "invalid_icd9_format": "Not an ICD-9 code",
              "orphan_reference": "Orphan reference", "parent_quarantined": "Parent quarantined (cascade)",
              "inconsistent_reference": "Inconsistent reference", "chronology": "Chronology",
              "duplicate_id_conflict": "Same id, different values", "invalid_id": "Unreadable identifier"}
    rr = [[lbl] + [n(reasons[(s, k)]) for s in srcs] for k, lbl in rlabel.items() if any(reasons[(s, k)] for s in srcs)]
    rr.append(["Malformed (not loaded)"] + [n(S[s]["malformed"]) for s in srcs])
    d.table(["Quarantine reason (a record can have several)"] + srcs, rr, "Quarantine by reason",
            widths=[52, 12, 12, 12, 12])

    d.p("The table below shows before-and-after examples taken from the cleaning log (one per rule).")
    want = ["whitespace_trimmed", "case_standardised", "name_reordered", "date_format_standardised", "written_in_utc",
            "unix_timestamp_converted", "no_offset_local_time_assumed", "dst_ambiguous_time_assumed_first",
            "decimal_comma", "fahrenheit_converted_to_celsius", "fraction_converted_to_percent", "unit_text_removed",
            "bp_format_normalised", "decimal_point_restored", "leading_zero_restored", "none_known_standardised",
            "datetime_extracted_from_text", "repointed_to_kept_duplicate", "placeholder_to_null", "out_of_range",
            "invalid_number"]
    used = Counter()
    ex = []
    for rule in want:
        cand = [r for r in log if r["rule"] == rule and r["before"]]
        if not cand:
            continue
        by_src = {}
        for r in cand:
            by_src.setdefault(r["source_system"], r)
        s = min(by_src, key=lambda k: (used[k], k))
        used[s] += 1
        r = by_src[s]
        ex.append([s, ENT_NAME[r["entity"]], r["field"], rule, f"`{vis(r['before'])[:40]}`",
                   f"`{cut(r['after'], 40)}`" if r["after"] else "NULL"])
    d.table(["Source", "Entity", "Field", "Rule", "Before", "After"], ex, "Before-and-after examples",
            widths=[6, 15, 14, 21, 22, 22], font_half_pts=15)
    qx = []
    seen = set()
    for r in quar:
        k = (r["reason_codes"].split(";")[0].split(":")[0], r["source_system"])
        if r["disposition"] == "rejected" and k[0] not in {x for x, _ in seen} and len(qx) < 12:
            seen.add(k)
            qx.append([r["source_system"], ENT_NAME[r["entity"]], r["source_record_id"], cut(r["reason_details"], 80),
                       cut(r["raw_record"], 60)])
    d.table(["Source", "Entity", "Id", "Reason", "Raw record (start)"], qx,
            "Examples of quarantined records (one per reason)", widths=[6, 14, 6, 44, 30], font_half_pts=15)
    d.p("The complete results are in `output/cleaning_report.md`, with every rejected record (reason and original raw "
        "text) in `output/quarantine/` and every single change in `output/cleaning_log/cleaning_log.csv`.")

    # =========================================================================
    d.h("4. Notes")
    d.bullets([
        "The raw files in `data/raw/` are never modified; the whole pipeline can be rerun at any time and gives the "
        "same output.",
        "An ambiguous date (`04-07-2025`, or a D dot date `05.06.2022`) is never guessed: if the field is required, "
        "the record is quarantined as an ambiguous date.",
        "A local time in the autumn repeated hour (Paris or Sydney) can be either of two instants; we take the first "
        "one and flag the record, so the choice is visible.",
        "Two staff members with the same name, role and department who are both active in the records are kept apart "
        "(flagged `possible_duplicate`), because merging them would attribute one person's work to the other.",
        "Unmapped test, procedure and body-area names are kept as text, because the contract has no fixed list for "
        "them; unmapped labels of the fixed categories are rejected.",
    ])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    d.save(out_path)
    return out_path


if __name__ == "__main__":
    print(f"Written {build()}")
