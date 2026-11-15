"""
Writes the cleaned datasets, the quarantine datasets, the cleaning logs and a
Markdown report (summary + before/after examples + check against the
generator's injection manifest).
"""

import csv
import json
import shutil
from collections import Counter, defaultdict

from config import (MANIFEST, OUT_CLEAN, OUT_LOG, OUT_QUARANTINE, REPORT, SCHEMA, SOURCES, ENTITY_ORDER,
                    MISSING_MARKERS, VITAL_RANGES, TEMPERATURE_UNIT, SPO2_UNIT)
from pipeline import fmt_val


def out_columns(E):
    cols = ["source"]
    for f, kind, _ in SCHEMA[E]:
        cols += ["bp_systolic", "bp_diastolic"] if kind == "bp" else [f]
    return cols


def _write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def clean_row(rec):
    row = {"source": rec["_source"]}
    for k, v in rec["_clean"].items():
        row[k] = "" if v is None else fmt_val(v)
    return row


def raw_json(rec):
    return json.dumps(rec["_raw"], ensure_ascii=False, default=str)


def write_outputs(data, rejects, ctx):
    for d in (OUT_CLEAN, OUT_QUARANTINE, OUT_LOG):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    counts = {}
    for E in ENTITY_ORDER:
        rows = []
        for S in SOURCES:
            for r in data[S][E]:
                if not r.get("_quarantined") and not r.get("_removed"):
                    rows.append(clean_row(r))
        rows.sort(key=lambda r: (r["source"], _sortkey(r.get(out_columns(E)[1]))))
        _write(OUT_CLEAN / f"{E}.csv", out_columns(E), rows)
        counts[E] = len(rows)

    q_by_entity = defaultdict(list)
    for r in rejects + ctx.quarantine:
        q_by_entity[r["_entity"]].append({
            "source": r["_source"], "record_id": "" if r.get("_id") is None else r["_id"],
            "location": r["_loc"], "rejection_type": r.get("_qkind", "direct"),
            "reasons": "; ".join(r["_reasons"]), "raw_record": raw_json(r)})
    for E in ENTITY_ORDER:
        rows = sorted(q_by_entity.get(E, []), key=lambda r: (r["source"], _sortkey(r["record_id"])))
        _write(OUT_QUARANTINE / f"{E}_quarantine.csv",
               ["source", "record_id", "location", "rejection_type", "reasons", "raw_record"], rows)

    _write(OUT_LOG / "issues.csv", ["source", "entity", "record_id", "location", "field", "issue", "action",
                                    "before", "after"], ctx.issues)
    _write(OUT_LOG / "duplicates_removed.csv", ["source", "entity", "record_id", "kind", "removed_location",
                                                "kept_location"], ctx.duplicates)
    _write(OUT_LOG / "patient_crosswalk.csv", ["source", "duplicate_patient_id", "master_patient_id", "rule",
                                               "duplicate_location", "master_location"], ctx.crosswalk)
    _write(OUT_LOG / "transformations.csv", ["source", "entity", "field", "transformation", "records"],
           [{"source": s, "entity": e, "field": f, "transformation": t, "records": n}
            for (s, e, f, t), n in sorted(ctx.transforms.items())])
    return counts


def _sortkey(v):
    try:
        return (0, int(v))
    except (TypeError, ValueError):
        return (1, str(v))


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x).replace("|", "\\|").replace("\n", " ") for x in r) + " |")
    return "\n".join(out)


def _distinct(issues, **cond):
    return len({(i["source"], i["entity"], i["record_id"]) for i in issues
                if all(i[k] == v for k, v in cond.items())})


def _rows(issues, **cond):
    return sum(all(i[k] == v for k, v in cond.items()) for i in issues)


def detected_counts(S, ctx, rejects):
    I = [i for i in ctx.issues if i["source"] == S]
    Q = [r for r in ctx.quarantine if r["_source"] == S]
    D = [d for d in ctx.duplicates if d["source"] == S]
    qr = lambda ent, prefix: sum(any(x.startswith(prefix) for x in r["_reasons"]) for r in Q if r["_entity"] == ent)
    return {
        "exact_duplicate_patient": sum(d["entity"] == "patients" for d in D),
        "exact_duplicate_admission": sum(d["entity"] == "admissions" for d in D),
        "exact_duplicate_diagnosis": sum(d["entity"] == "diagnoses" for d in D),
        "entity_duplicate_patient": sum(c["source"] == S for c in ctx.crosswalk),
        "missing_required_patient_name": _distinct(I, issue="missing_required_value", field="family_name"),
        "missing_required_date_of_birth": _distinct(I, issue="missing_required_value", field="birth_date"),
        "missing_required_admission_time": _distinct(I, issue="missing_required_value", field="admit_time_utc"),
        "missing_required_icd9_code": _distinct(I, issue="missing_required_value", field="icd9_code"),
        "missing_optional_phone": _distinct(I, issue="missing_optional_value", field="phone"),
        "missing_optional_address": _distinct(I, issue="missing_optional_value", field="address"),
        "missing_optional_emergency_contact": _distinct(I, issue="missing_optional_value", field="emergency_contact"),
        "missing_optional_insurance": _distinct(I, issue="missing_optional_value", field="insurance"),
        "missing_optional_allergies": _distinct(I, issue="missing_optional_value", field="allergies"),
        "messy_name_text": _distinct(I, issue="name_text_standardised", field="family_name"),
        "messy_category_label": _rows(I, issue="messy_category_label"),
        "invalid_date": _rows(I, issue="invalid_timestamp") + _rows(I, issue="invalid_date"),
        "ambiguous_date_mm_dd": _rows(I, issue="ambiguous_date_mm_dd") + _rows(I, issue="date_only_valid_as_mm_dd"),
        "timestamp_without_timezone": _rows(I, issue="timestamp_without_timezone"),
        "timestamp_as_epoch_seconds": _rows(I, issue="timestamp_as_epoch_seconds"),
        "invalid_heart_rate": _rows(I, issue="invalid_heart_rate"),
        "invalid_pain_level": _rows(I, issue="invalid_pain_level"),
        "invalid_temperature": _rows(I, issue="invalid_temperature"),
        "invalid_oxygen_saturation": _rows(I, issue="invalid_oxygen_saturation"),
        "non_numeric_respiratory_rate": _rows(I, issue="non_numeric_value", field="resp_rate_per_min"),
        "icd9_leading_zero_lost": _rows(I, issue="icd9_leading_zero_lost"),
        "broken_admission_patient_ref": qr("admissions", "missing_parent_patient"),
        "broken_diagnosis_icd9_ref": _distinct(I, issue="unknown_icd9_code"),
        "broken_unitstay_admission_ref": qr("unit_stays", "missing_parent_admission"),
        "broken_radiology_order_ref": qr("radiology", "missing_parent_order"),
        "diagnosis_patient_mismatch": qr("diagnoses", "diagnosis_patient_mismatch"),
        "discharge_before_admission": _distinct(I, issue="discharge_before_admission")
                                      + qr("admissions", "discharge_before_admission"),
        "unit_exit_before_entry": qr("unit_stays", "unit_exit_before_entry"),
        "procedure_outside_admission": qr("procedures", "procedure_before_admission"),
        "exam_outside_admission": qr("radiology", "radiology_exam_after_discharge"),
        "discharge_record_for_active_admission": qr("discharges", "discharge_record_for_active_admission"),
        "malformed_line_wrong_field_count": sum(r["_source"] == S for r in rejects) if S == "A" else 0,
        "malformed_line_extra_fields": sum(r["_source"] == S for r in rejects) if S == "B" else 0,
    }


MANIFEST_KEYS = {"A": "A_europe_txt", "B": "B_north_america_csv", "C": "C_asia_xml", "D": "D_africa_json"}


def write_report(data, rejects, ctx, counts, d_codebook_ok):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None
    L = []
    w = L.append
    w("# Phase 2 - Task 2: Cleaning and Standardisation Report\n")
    w("_Generated automatically by `cleaning/run_cleaning.py`. Re-running the script on the unchanged raw files "
      "reproduces this report byte-for-byte._\n")

    # ---- 1. Summary -------------------------------------------------------
    w("## 1. Summary of the cleaning results\n")
    rows, tot = [], Counter()
    for S in SOURCES:
        raw_n = sum(len(data[S][E]) for E in ENTITY_ORDER) + sum(r["_source"] == S for r in rejects)
        dup_n = sum(d["source"] == S for d in ctx.duplicates)
        ent_n = sum(c["source"] == S for c in ctx.crosswalk)
        q = [r for r in ctx.quarantine if r["_source"] == S] + [r for r in rejects if r["_source"] == S]
        qd = sum(r.get("_qkind", "direct") == "direct" for r in q)
        qc = len(q) - qd
        clean_n = sum(1 for E in ENTITY_ORDER for r in data[S][E] if not r.get("_quarantined") and not r.get("_removed"))
        iss = sum(i["source"] == S for i in ctx.issues)
        rows.append([SOURCES[S]["label"], raw_n, dup_n, ent_n, qd, qc, clean_n, f"{clean_n / raw_n:.1%}", iss])
        for k, v in zip(["raw", "dup", "ent", "qd", "qc", "clean", "iss"], [raw_n, dup_n, ent_n, qd, qc, clean_n, iss]):
            tot[k] += v
    rows.append(["**Total**", tot["raw"], tot["dup"], tot["ent"], tot["qd"], tot["qc"], tot["clean"],
                 f"{tot['clean'] / tot['raw']:.1%}", tot["iss"]])
    w(md_table(["Source", "Raw records", "Same-key duplicates removed", "Patients merged (same person)",
                "Quarantined (direct)", "Quarantined (cascade)", "Clean records", "Kept", "Logged issues"], rows))
    w("\nRaw records = duplicates removed + patients merged + quarantined + clean, so every raw record is accounted for. "
      "*Direct* = the record itself failed a rule; *cascade* = the record is valid but its parent "
      "(patient, admission or order) was quarantined, so it cannot be linked.\n")

    w("### Records per entity (clean / quarantined)\n")
    rows = []
    for E in ENTITY_ORDER:
        r = [E]
        for S in SOURCES:
            c = sum(1 for x in data[S][E] if not x.get("_quarantined") and not x.get("_removed"))
            q = sum(1 for x in ctx.quarantine + rejects if x["_source"] == S and x["_entity"] == E)
            r.append(f"{c} / {q}")
        rows.append(r)
    w(md_table(["Entity"] + [f"{S}: clean / quar." for S in SOURCES], rows))

    w("\n### Actions taken on fields (issue log)\n")
    by = Counter((i["issue"], i["action"], i["source"]) for i in ctx.issues)
    codes = sorted({(c, a) for c, a, _ in by})
    rows = [[c, a] + [by.get((c, a, S), 0) for S in SOURCES] + [sum(by.get((c, a, S), 0) for S in SOURCES)]
            for c, a in codes]
    w(md_table(["Issue", "Action", "A", "B", "C", "D", "Total"], rows))

    w("\n### Quarantine reasons\n")
    rc = Counter()
    for r in ctx.quarantine + rejects:
        for x in r["_reasons"]:
            rc[(x.split("(")[0].split(":")[0], r["_source"])] += 1
    reasons = sorted({k for k, _ in rc})
    w(md_table(["Reason", "A", "B", "C", "D", "Total"],
               [[k] + [rc.get((k, S), 0) for S in SOURCES] + [sum(rc.get((k, S), 0) for S in SOURCES)] for k in reasons]))
    w("\nA record can carry several reasons, so this table can sum to more than the number of quarantined records.\n")

    w("\n### Routine conversions applied to every record (not logged individually)\n")
    tc = Counter()
    for (S, E, f, t), n in ctx.transforms.items():
        tc[(t, S)] += n
    ts = sorted({t for t, _ in tc})
    w(md_table(["Conversion", "A", "B", "C", "D"], [[t] + [tc.get((t, S), 0) for S in SOURCES] for t in ts]))

    # ---- 2. Manifest check ------------------------------------------------
    if manifest:
        w("\n## 2. Detection check against the injection manifest\n")
        w("The manifest is **not** used by the cleaning code; it is only compared afterwards to show that the rules "
          "find the injected problems. Differences are explained below the table.\n")
        det = {S: detected_counts(S, ctx, rejects) for S in SOURCES}
        keys = sorted({k for S in SOURCES for k in manifest[MANIFEST_KEYS[S]]["injected_problems"]} | set(det["A"]))
        rows = []
        for k in keys:
            row = [k]
            for S in SOURCES:
                inj = manifest[MANIFEST_KEYS[S]]["injected_problems"].get(k, 0)
                got = det[S].get(k, "n/a")
                mark = "" if got == inj or got == "n/a" else " *"
                row.append(f"{inj} / {got}{mark}")
            rows.append(row)
        w(md_table(["Problem", "A inj / det", "B inj / det", "C inj / det", "D inj / det"], rows))
        w("""
`*` = detected count differs from injected count. The remaining differences are expected:

* **messy_category_label**: the generator picks one of `label.upper()`, `label.lower()`, `" label "`, `"label  "`. When the source label is already upper case (A: `EMER`, `REA`; C: `ICU`; D: `P1`) or a digit (A triage `1`/`2`/`3`), `upper()` / `lower()` return the **identical** string, so there is nothing wrong in the data and nothing to detect. Every label that actually differs from the codebook is detected and mapped.
* **ambiguous_date_mm_dd**: a date written MM/DD in a DD/MM source is only detectable when the documented DD/MM reading contradicts related events (triage / unit entry minutes after admission, the discharge record, the admission window) and the MM/DD reading agrees with them. When both readings are consistent with every related event, the documented DD/MM reading is kept; no method can tell these apart.
* Detected counts for duplicates and missing values are on distinct record ids; invalid dates and labels are counted per written value (duplicate copies included), which is how the generator counts them.
""")
        w(f"Source D's embedded `facility.codebook` agrees with the codebook used here: **{d_codebook_ok}**.\n")

    # ---- 3. Examples ------------------------------------------------------
    w("\n## 3. Representative before-and-after examples\n")
    w("### 3.1 Field-level examples (one per issue and source)\n")
    seen, rows = set(), []
    for i in ctx.issues:
        k = (i["issue"], i["source"])
        if k in seen:
            continue
        seen.add(k)
        rows.append([i["issue"], i["source"], i["entity"], i["record_id"], i["field"], f"`{i['before']}`",
                     f"`{i['after']}`" if i["after"] else "", i["action"]])
    rows.sort()
    w(md_table(["Issue", "Src", "Entity", "Id", "Field", "Before (raw)", "After (clean)", "Action"], rows))

    w("\n### 3.2 Whole-record examples\n")
    for title, S, E, issue in [
        ("Source A admission: ambiguous date resolved, label normalised", "A", "admissions", "ambiguous_date_mm_dd"),
        ("Source A triage: decimal comma, numeric codes, Paris time to UTC", "A", "triage", None),
        ("Source B patient: 'Last, First' split, US date, missing marker", "B", "patients", "missing_optional_value"),
        ("Source B triage: Fahrenheit to Celsius, messy acuity label", "B", "triage", "messy_category_label"),
        ("Source B diagnosis: ICD-9 leading zero restored", "B", "diagnoses", "icd9_leading_zero_lost"),
        ("Source C triage: SpO2 fraction to percent, +08:00 to UTC", "C", "triage", None),
        ("Source D encounter: epoch seconds converted", "D", "admissions", "timestamp_as_epoch_seconds"),
        ("Source D triage: numbers stored as strings, invalid heart rate nulled", "D", "triage", "invalid_heart_rate"),
    ]:
        rec = _pick(data, ctx, S, E, issue)
        if rec is None:
            continue
        w(f"**{title}** (`{rec['_loc']}`)\n")
        w("Raw:\n```json\n" + json.dumps(rec["_raw"], ensure_ascii=False, indent=1, default=str) + "\n```")
        w("Clean:\n```json\n" + json.dumps(clean_row(rec), ensure_ascii=False, indent=1) + "\n```\n")

    w("### 3.3 Duplicate and entity-resolution examples\n")
    for d in ctx.duplicates[:1] + [x for x in ctx.duplicates if x["kind"] == "duplicate_merged_complementary"][:1]:
        w(f"* `{d['source']}` {d['entity']} id {d['record_id']}: **{d['kind']}** - removed `{d['removed_location']}`, "
          f"kept `{d['kept_location']}`.")
    for c in ctx.crosswalk[:3]:
        dup = _find_loc(data, c["source"], "patients", c["duplicate_location"])
        mas = _find_loc(data, c["source"], "patients", c["master_location"])
        w(f"* `{c['source']}` patient {c['duplicate_patient_id']} merged into master {c['master_patient_id']}:")
        w(f"  * duplicate raw: `{json.dumps(dup['_raw'], ensure_ascii=False, default=str)}`")
        w(f"  * master raw: `{json.dumps(mas['_raw'], ensure_ascii=False, default=str)}`")
        w(f"  * master clean: `{json.dumps(clean_row(mas), ensure_ascii=False)}`")

    w("\n### 3.4 Quarantine examples\n")
    shown = set()
    rows = []
    for r in rejects + ctx.quarantine:
        key = (r["_reasons"][0].split("(")[0].split(":")[0])
        if key in shown:
            continue
        shown.add(key)
        rows.append([r["_source"], r["_entity"], r.get("_id", ""), r.get("_qkind", "direct"), "; ".join(r["_reasons"]),
                     "`" + raw_json(r)[:160] + ("…" if len(raw_json(r)) > 160 else "") + "`"])
    w(md_table(["Src", "Entity", "Id", "Type", "Reasons", "Raw record (truncated)"], rows))

    w("\n## 4. Output files\n")
    w("""* `output/clean/<entity>.csv` - cleaned, standardised records of all four sources (column `source` + local id form the key).
* `output/quarantine/<entity>_quarantine.csv` - rejected records with `rejection_type`, `reasons` and the untouched raw record.
* `output/cleaning_log/issues.csv` - every field-level correction, nulling, flag and missing value (before/after).
* `output/cleaning_log/duplicates_removed.csv` - every removed same-key duplicate copy and the copy that was kept.
* `output/cleaning_log/patient_crosswalk.csv` - duplicate patient registrations mapped to their master patient.
* `output/cleaning_log/transformations.csv` - counts of routine conversions (UTC, units, codes, categories).
""")
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")


def _find_loc(data, S, E, loc):
    return next(r for r in data[S][E] if r["_loc"] == loc)


def _pick(data, ctx, S, E, issue):
    ok = [r for r in data[S][E] if not r.get("_quarantined") and not r.get("_removed")]
    if issue is None:
        return ok[0] if ok else None
    locs = {i["location"] for i in ctx.issues if i["source"] == S and i["entity"] == E and i["issue"] == issue}
    for r in ok:
        if r["_loc"] in locs:
            return r
    return None
