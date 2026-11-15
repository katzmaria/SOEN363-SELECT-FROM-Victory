"""
Print the tables of the Phase 2 reports in the terminal.

    python show_tables.py          list all tables with their number
    python show_tables.py 3        print table 3
    python show_tables.py 3 7 12   print several tables
    python show_tables.py all      print every table

  Short views made for the README:
    python show_tables.py counts     record counts by entity
    python show_tables.py missingcounts  missing values per entity and source
    python show_tables.py duplicates duplicate counts
    python show_tables.py layout     record layout of the TXT files
    python show_tables.py fields     field profile of source D triage
    python show_tables.py formats    the same information written by each source
    python show_tables.py invalid    invalid values found, one example each
    python show_tables.py malformed  malformed lines that were logged
    python show_tables.py examples   before / after examples of the cleaning
    python show_tables.py missing | timezones | units | categories | chronology   cleaning rules
"""

import csv
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = ["output/profile_report.md", "output/cleaning_report.md", "cleaning/README.md"]
MAX_COL = 40  # wrap cells wider than this

try:
    sys.stdout.reconfigure(errors="replace")
except AttributeError:
    pass


def clean(cell):
    cell = re.sub(r"\\+\|", "|", cell.strip())
    cell = cell.replace("<br>", " / ").replace("`", "").replace("**", "")
    return cell


def find_tables():
    tables = []
    for rel in FILES:
        path = ROOT / rel
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").split("\n")
        title, section, i, in_code = "", "", 0, False
        while i < len(lines):
            line = lines[i]
            if line.startswith("```"):
                in_code = not in_code
                i += 1
                continue
            if in_code:
                i += 1
                continue
            if line.startswith("#"):
                title = section = line.lstrip("#").strip()
            elif re.match(r"^\*\*[^*]+\*\*", line) and not line.startswith("|"):
                bold = re.match(r"^\*\*([^*]+)\*\*", line).group(1)
                # per-entity tables: say which source they belong to
                title = f"{section.split('(')[0].strip()} - {bold}" if section.startswith("Source") else bold
            if line.startswith("|"):
                rows = []
                while i < len(lines) and lines[i].startswith("|"):
                    if not re.fullmatch(r"[|\-: ]+", lines[i].strip()):
                        rows.append([clean(c) for c in re.split(r"(?<!\\)\|", lines[i].strip())[1:-1]])
                    i += 1
                tables.append((rel, title, rows))
                continue
            i += 1
    return tables


def render(rows, max_col=MAX_COL):
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    # width = widest data value (headers wrap onto several lines), capped at MAX_COL
    widths = [min(max_col, max([len(r[c]) for r in rows[1:]] + [max(map(len, rows[0][c].split() or [""]))]))
              for c in range(ncol)]
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    out = [sep]
    for n, r in enumerate(rows):
        cells = [textwrap.wrap(r[c], widths[c]) or [""] for c in range(ncol)]
        for k in range(max(len(x) for x in cells)):
            out.append("| " + " | ".join((cells[c][k] if k < len(cells[c]) else "").ljust(widths[c])
                                         for c in range(ncol)) + " |")
        if n == 0:
            out.append(sep.replace("-", "="))
    out.append(sep)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Short views (compact versions of the report tables, used in the README)
# ---------------------------------------------------------------------------

def get_table(tables, title_start):
    return next((rows for _, t, rows in tables if t.startswith(title_start)), None)


def read_csv(rel):
    path = ROOT / rel
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def view_counts(tables):
    return "Record counts by entity", get_table(tables, "2. Record counts")


def view_duplicates(tables):
    return "Duplicate counts", get_table(tables, "4. Duplicate counts")


def view_missingcounts(tables):
    rows = read_csv("output/profile/field_profile.csv")
    if rows is None:
        return None, None
    order, tot = [], {}
    for r in rows:
        key = r["entity"]
        if key not in order:
            order.append(key)
        tot[(key, r["source"])] = tot.get((key, r["source"]), 0) + int(r["missing"])
    out = [["Entity", "A (TXT)", "B (CSV)", "C (XML)", "D (JSON)"]]
    for e in order:
        out.append([e] + [str(tot.get((e, S), 0)) for S in "ABCD"])
    out.append(["Total"] + [str(sum(v for (e, S), v in tot.items() if S == src)) for src in "ABCD"])
    return "Missing values per entity (all fields; details per field in field_profile.csv)", out

def view_missingcounts(tables):
    rows = read_csv("output/profile/field_profile.csv")
    if rows is None:
        return None, None
    order, tot = [], {}
    for r in rows:
        key = r["entity"]
        if key not in order:
            order.append(key)
        tot[(key, r["source"])] = tot.get((key, r["source"]), 0) + int(r["missing"])
    out = [["Entity", "A (TXT)", "B (CSV)", "C (XML)", "D (JSON)"]]
    for e in order:
        out.append([e] + [str(tot.get((e, S), 0)) for S in "ABCD"])
    out.append(["Total"] + [str(sum(v for (e, S), v in tot.items() if S == src)) for src in "ABCD"])
    return "Missing values per entity (all fields; details per field in field_profile.csv)", out

def view_layout(tables):
    rows = get_table(tables, "1.1 Source A")
    out = [["File", "Fields in order (separated by | in the file)"]]
    for r in rows[1:]:
        out.append([r[0], r[2].replace(" | ", ", ")])
    return "Record layout of the source A TXT files", out


def view_fields(tables, source="D", entity="triage"):
    rows = read_csv("output/profile/field_profile.csv")
    out = [["Field", "Inferred type", "Missing", "Other formats in the field"]]
    for r in rows:
        if r["source"] == source and r["entity"] == entity:
            missing = r["missing"] if r["missing"] == "0" else f"{r['missing']} ({r['missing_breakdown']})"
            other = "; ".join(x for x in (r["format_variants"], r["other_types"]) if x)
            other = re.sub(r" \(e\.g\. [^)]*\)", "", other)  # keep only "format: count"
            out.append([r["field"], r["inferred_type"], missing, other])
    return f"Field profile of source {source}, {entity}", out


def view_formats(tables):
    rows = get_table(tables, "5. Formatting differences")
    skip = {"Patient id", "Family name", "Birth date", "Symptoms"}  # values differ between runs
    rename = {"Admitting staff ref": "Staff reference"}
    out = [["Concept", "A (TXT)", "B (CSV)", "C (XML)", "D (JSON)"]]
    for r in rows[1:]:
        if r[0] in skip:
            continue
        # a cell looks like "field = value / inferred type": keep only the value
        out.append([rename.get(r[0], r[0])] + [re.sub(r"^.*? = ", "", c).split(" / ")[0] for c in r[1:]])
    return "The same information written by each source", out


def view_invalid(tables):
    rows = get_table(tables, "6. Invalid and suspicious values")
    found = read_csv("output/profile/invalid_values.csv")
    out = [["Check", "A", "B", "C", "D", "Example"]]
    for r in rows[1:]:
        cands = [x for x in found if x["check"] == r[0]]
        ex = next((x for x in cands if x["entity"] != "patients"), cands[0] if cands else None)
        if ex is None:
            text = ""
        elif ex["entity"] == "patients":  # names differ between runs: show the field only
            text = f"{ex['source']} patients.{ex['field']}"
        else:
            text = f"{ex['source']} {ex['entity']}.{ex['field']} = {ex['value']}"
        out.append(r[:5] + [text])
    return "Invalid and suspicious values in the raw data", out


def view_malformed(tables):
    rows = read_csv("output/profile/malformed_records.csv")
    out = [["Src", "Entity", "Location", "Problem"]]
    for r in rows:
        m = re.search(r"(\d+) fields, header has (\d+)", r["reason"])
        prob = f"{m.group(1)} fields, expected {m.group(2)}" if m else r["reason"]
        out.append([r["source"], r["entity"], r["location"], prob])
    return "Malformed lines (logged, not loaded)", out


EXAMPLES = [  # (issue code, preferred source, readable name)
    ("messy_category_label", "A", "Messy category label"),
    ("messy_category_label", "C", "Messy category label"),
    ("ambiguous_date_mm_dd", "A", "Ambiguous DD/MM date"),
    ("timestamp_as_epoch_seconds", "D", "Epoch timestamp"),
    ("timestamp_without_timezone", "D", "Timestamp without zone"),
    ("icd9_leading_zero_lost", "B", "ICD-9 leading zero lost"),
    ("invalid_temperature", "B", "Temperature out of range"),
    ("invalid_oxygen_saturation", "C", "SpO2 out of range"),
    ("invalid_heart_rate", "D", "Heart rate out of range"),
    ("non_numeric_value", "A", "Not a number"),
    ("invalid_timestamp", "B", "Impossible date"),
    ("discharge_before_admission", "C", "Discharge before admit"),
]


def view_examples(tables):
    issues = read_csv("output/cleaning_log/issues.csv")
    if issues is None:
        return None, None
    cut = lambda v: re.sub(r"\s*\(.*$", "", v) if v else "NULL"
    out = [["Problem", "Src", "Field", "Before", "After", "Action"]]
    for code, src, name in EXAMPLES:
        i = next((x for x in issues if x["issue"] == code and x["source"] == src), None) \
            or next((x for x in issues if x["issue"] == code), None)
        if i:
            out.append([name, i["source"], i["field"], cut(i["before"]), cut(i["after"]), i["action"]])
    return "Before and after cleaning", out


# Cleaning rules (Task 2). Written here so they can be shown without other files.
RULES = {
    "missing": ("When a record is corrected, kept with NULL or quarantined", [
        ["Situation", "What we do"],
        ["Optional value missing (phone, insurance, allergies...)", "Kept as NULL and logged"],
        ["Optional value invalid (heart rate 420, pain 15...)", "Value set to NULL, record kept"],
        ["Required value missing in one copy but present in another copy", "Filled from the other copy"],
        ["Discharge time missing, but the discharge record has it (or the reverse)", "Filled from the record of the same discharge"],
        ["Required value missing or invalid, no evidence anywhere", "Record quarantined with the reason"],
        ["Invalid unit exit or discharge time (NULL would mean 'still there')", "Record quarantined"],
    ]),
    "timezones": ("Time zones and how timestamps are converted to UTC", [
        ["Source", "Written as", "Source time zone", "What we do"],
        ["A", "DD/MM/YYYY HH:MM", "Europe/Paris, no offset", "Local time -> UTC (DST aware)"],
        ["B", "MM/DD/YYYY hh:mm AM/PM", "America/Toronto, no offset", "Local time -> UTC (DST aware)"],
        ["C", "ISO 8601 with +08:00", "Asia/Singapore", "Written offset used"],
        ["D", "ISO 8601 with Z", "UTC", "Used as written"],
        ["D", "ISO 8601 without zone", "unknown", "Assumed Africa/Johannesburg, flagged"],
        ["D", "Unix epoch seconds", "UTC", "Converted"],
    ]),
    "units": ("Unit conversions and valid ranges", [
        ["Field", "Conversion", "Valid range"],
        ["Temperature", "B: Fahrenheit -> Celsius; A: 37,2 -> 37.2", "25 - 45 C"],
        ["SpO2", "C: fraction -> percent (0.97 -> 97)", "50 - 100 %"],
        ["Heart rate", "-", "20 - 300 bpm"],
        ["Respiratory rate", "text like 'abc' -> NULL", "4 - 80 per min"],
        ["Pain score", "must be a whole number", "0 - 10"],
        ["Blood pressure", "'120/80' -> systolic 120, diastolic 80", "50-300 / 20-200"],
        ["ICD-9 code", "kept as text; B: '38.9' -> '038.9'", "must exist in the dictionary"],
    ]),
    "categories": ("Source labels mapped to common values", [
        ["Common value", "A", "B", "C", "D"],
        ["emergency", "EMER", "Emergency", "ER", "1"],
        ["urgent", "URG", "Urgent", "Urgent Care", "2"],
        ["elective", "ELEC", "Elective", "Scheduled", "3"],
        ["outpatient", "AMB", "Outpatient", "Ambulatory", "4"],
        ["newborn", "NN", "Newborn", "Birth", "5"],
        ["high / medium / low", "1 / 2 / 3", "High / Medium / Low", "Red / Yellow / Green", "P1 / P2 / P3"],
        ["Emergency Department", "URGENCES", "Emergency Department", "Emergency Room", "emergency"],
        ["ICU", "REA", "Intensive Care Unit", "ICU", "icu"],
        ["CCU", "USIC", "Coronary Care Unit", "CCU", "ccu"],
        ["MICU", "REA-MED", "Medical ICU", "Medical ICU", "micu"],
        ["SICU", "REA-CHIR", "Surgical ICU", "Surgical ICU", "sicu"],
        ["General Ward", "MED", "General Ward", "Ward", "ward"],
        ["discharged", "SORTI", "Discharged", "Discharged", "discharged"],
        ["deceased", "DECEDE", "Expired", "Died", "died"],
        ["active", "EN COURS", "In House", "Admitted", "inpatient"],
        ["female / male / unspecified", "F / H / I", "Female / Male / Unknown", "female / male / unspecified", "f / m / o"],
    ]),
    "chronology": ("Chronology checks", [
        ["Rule", "If it fails"],
        ["discharge time >= admission time", "Corrected from the discharge record if it has a valid time, otherwise quarantined"],
        ["admission date >= patient birth date", "Admission quarantined"],
        ["unit exit >= unit entry", "Unit stay quarantined"],
        ["triage, unit stay, order, exam, procedure, note and discharge record inside the admission", "Record quarantined"],
        ["diagnosis time >= admission time", "Diagnosis quarantined"],
        ["radiology exam >= its order time", "Exam quarantined"],
        ["unit stays of one admission do not overlap", "Only flagged"],
    ]),
}


def rule_view(name):
    return lambda tables: RULES[name]


VIEWS = {"counts": view_counts, "missingcounts": view_missingcounts, "duplicates": view_duplicates, "layout": view_layout, "fields": view_fields, "formats": view_formats, "invalid": view_invalid,
         "malformed": view_malformed, "examples": view_examples,
         **{k: rule_view(k) for k in RULES}}


def main():
    tables = find_tables()
    if sys.argv[1:2] and sys.argv[1] in VIEWS:
        title, rows = VIEWS[sys.argv[1]](tables)
        if rows is None:
            print("Run the profiling and cleaning scripts first.")
            return
        print(f"\n{title}")
        print(render(rows, max_col=44 if sys.argv[1] in RULES else 32))
        return
    if not tables:
        print("No reports found. Run profiling/profile_sources.py and cleaning/run_cleaning.py first.")
        return
    args = sys.argv[1:]
    if not args:
        current = None
        for n, (rel, title, rows) in enumerate(tables, start=1):
            if rel != current:
                print(f"\n{rel}")
                current = rel
            print(f"  {n:3d}  {title}  ({len(rows) - 1} rows)")
        print("\nShow a table with:  python show_tables.py <number>   (or: all)")
        print("Short views:  counts, missingcounts, duplicates, layout, fields, formats, invalid, malformed, examples")
        print("Cleaning rules: missing, timezones, units, categories, chronology")
        return
    picks = range(1, len(tables) + 1) if args == ["all"] else [int(a) for a in args]
    for n in picks:
        if not 1 <= n <= len(tables):
            print(f"No table {n} (there are {len(tables)}).")
            continue
        rel, title, rows = tables[n - 1]
        print(f"\nTable {n} - {title}   [{rel}]")
        print(render(rows))


if __name__ == "__main__":
    main()
