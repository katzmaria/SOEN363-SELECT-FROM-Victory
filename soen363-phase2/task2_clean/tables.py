"""
Task 2 result tables, built from output/cleaning_log/ and output/quarantine/ (printed by show_tables.py).

    python show_tables.py --task 2
"""

PIPELINE_VERSION = "2026.11.17-tasks"   # run_all.py checks that every file has the same version

import re
from collections import Counter
from pathlib import Path

from common.standards import ENTITY_SPECS, LABEL_MAPS, LEVEL_OVERRIDES, SOURCES, VITAL_RANGES
from common.tabular import ENT, ENT_NAME, cut, n, rows, vis

OUT = Path(__file__).resolve().parents[1] / "output"


def tables(d):
    """Adds the Task 2 tables to `d` (show_tables.TerminalDoc): d.h(...) for section titles, d.table(...)."""
    summ = rows(OUT / "cleaning_log" / "summary.csv")
    if not summ:
        raise SystemExit("No Task 2 results yet: run  python show_tables.py --task 2")
    srcs = list(dict.fromkeys(r["source_system"] for r in summ))
    log = rows(OUT / "cleaning_log" / "cleaning_log.csv")
    labels = rows(OUT / "cleaning_log" / "label_mappings.csv")
    quar = [r for e in ENT for r in rows(OUT / "quarantine" / f"{e}.csv")]
    S = {s: {k: sum(int(r[k]) for r in summ if r["source_system"] == s) for k in summ[0]
             if k not in ("source_system", "entity")} for s in srcs}
    T = {k: sum(S[s][k] for s in srcs) for k in S[srcs[0]]}
    act = Counter((r["source_system"], r["action"], r["rule"]) for r in log)
    reasons = Counter((r["source_system"], c.split(":")[0]) for r in quar for c in r["reason_codes"].split(";"))

    d.h("Task 2: Clean and Standardize the Data")
    d.h("2.1 Missing values", 2)
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
    d.h("2.2 Duplicates", 2)
    d.table(["Entity", "Duplicate key"], [[ENT_NAME[e], " + ".join(ENTITY_SPECS[e]["dup_key"]).replace("_key", "")]
                                          for e in ENT], "Duplicate-entity keys", widths=[30, 70])
    d.table(["Source", "Exact duplicates removed", "Duplicate entities merged", "References re-pointed",
             "Flagged possible duplicates"],
            [[s, n(S[s]["exact_duplicates_removed"]), n(S[s]["near_duplicates_merged"]),
              n(act[(s, "corrected", "repointed_to_kept_duplicate")]), n(act[(s, "flagged", "possible_duplicate")])]
             for s in srcs], "Duplicates found per source")
    d.h("2.3 Text", 2)
    tex = []
    for rule in ["whitespace_trimmed", "case_standardised", "name_reordered", "none_known_standardised"]:
        for s in srcs:
            x = next((r for r in log if r["rule"] == rule and r["source_system"] == s and r["before"]), None)
            if x:
                tex.append([s, ENT_NAME[x["entity"]], x["field"], rule, f"`{vis(x['before'])[:45]}`",
                            f"`{cut(x['after'], 45)}`"])
    d.table(["Source", "Entity", "Field", "Rule", "Before", "After"], tex, "Text standardization examples",
            widths=[6, 14, 14, 18, 24, 24])
    d.h("2.4 Dates and time zones", 2)
    d.table(["Source", "Time zone", "DST", "How raw timestamps are written", "Converted (non-standard format)",
             "Written in UTC (Z)", "Unix time"],
            [[s, SOURCES[s]["timezone"], "yes" if s in ("A", "D") else "no", SOURCES[s]["raw_time"],
              n(act[(s, "corrected", "date_format_standardised")]), n(act[(s, "corrected", "written_in_utc")]),
              n(act[(s, "corrected", "unix_timestamp_converted")])] for s in srcs],
            "Source time zones and how they are converted", widths=[6, 13, 5, 40, 13, 10, 9])
    d.h("2.5 Numbers and units", 2)
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
    d.h("2.6 Clinical categories", 2)
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
    d.h("2.7 Relationships", 2)
    d.table(["Source", "Orphan reference", "Parent quarantined (cascade)", "Inconsistent reference",
             "Role mismatch flagged"],
            [[s, n(reasons[(s, "orphan_reference")]), n(reasons[(s, "parent_quarantined")]),
              n(reasons[(s, "inconsistent_reference")]), n(act[(s, "flagged", "role_mismatch")])] for s in srcs],
            "Relationship problems per source")
    d.h("2.8 Chronology", 2)
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
    d.h("2.9 Results", 2)
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
