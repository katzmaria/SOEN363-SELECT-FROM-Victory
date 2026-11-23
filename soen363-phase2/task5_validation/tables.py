"""
Task 5 result tables, built from output/validation/ and output/integrated/ (printed by show_tables.py).

    python show_tables.py --task 5
"""

PIPELINE_VERSION = "2026.11.17-tasks"   # run_all.py checks that every file has the same version

import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from common.tabular import read_csv

OUT = Path(__file__).resolve().parents[1] / "output"
STATUSES = ["PASS", "FAIL", "WARNING", "LIMITATION"]
PREFIXES = ["PK", "FK", "REQ", "DOM", "FMT", "TIME", "STAT", "PAT", "LIM", "EVID"]


def _summary_rows(results: List[Dict[str, str]]) -> List[List[Any]]:
    count = Counter((r["id"].split("-")[0], r["enforcement"], r["status"]) for r in results)
    kinds = sorted({(p, k) for p, k, _ in count}, key=lambda t: (PREFIXES.index(t[0]), t[1]))
    rows = [[p, k] + [count[(p, k, s)] for s in STATUSES] + [sum(count[(p, k, s)] for s in STATUSES)]
            for p, k in kinds]
    return rows + [["Total", ""] + [sum(r[2 + i] for r in rows) for i in range(len(STATUSES) + 1)]]


def _trigger_rows(con: sqlite3.Connection) -> List[List[str]]:
    rows = []
    for name, table, sql in con.execute("SELECT name, tbl_name, sql FROM sqlite_master "
                                        "WHERE type = 'trigger' ORDER BY tbl_name, name"):
        m = re.search(r"\b(BEFORE|AFTER)\s+(INSERT|UPDATE|DELETE)", sql, re.I)
        rows.append([name, table, " ".join(m.groups()).upper() if m else "?"])
    return rows


def _primary_diagnosis_rows(by_id: Dict[str, Dict[str, str]]) -> Any:
    def v(i: str) -> str:
        return by_id[i]["violations"]

    sources = [[f"Source {s}", v(f"LIM-no-primary-source-{s}")] for s in "ABCD"]
    return sources + [["Total", v("LIM-no-primary-diagnosis")]], [
        ["No diagnosis of any kind", v("LIM-no-primary-none-at-all")],
        ["Secondary diagnoses only", v("LIM-no-primary-secondary-only")],
        ["Total", v("LIM-no-primary-diagnosis")]]


def _preservation_rows(con: sqlite3.Connection) -> list:
    def one(sql: str) -> Any:
        return con.execute(sql).fetchone()[0]

    return [
        ["Patients", one("SELECT COUNT(*) FROM Patient")],
        ["Admissions", one("SELECT COUNT(*) FROM Admission")],
        ["Diagnoses", one("SELECT COUNT(*) FROM Diagnosis")],
        ["Patients with more than one admission",
         one("SELECT COUNT(*) FROM (SELECT 1 FROM Admission GROUP BY patient_id HAVING COUNT(*) > 1)")],
        ["Admissions with more than one diagnosis",
         one("SELECT COUNT(*) FROM (SELECT 1 FROM Diagnosis GROUP BY admission_id HAVING COUNT(*) > 1)")]]


def tables(d: Any) -> None:
    db = OUT / "integrated" / "hospital.db"
    files = [OUT / "validation" / f for f in ("validation_results.csv", "negative_tests.csv")]
    if not (db.exists() and all(f.exists() for f in files)):
        raise SystemExit("No Task 5 results yet: run  python show_tables.py --task 5")
    results, negatives = read_csv(files[0])[1], read_csv(files[1])[1]
    by_id = {r["id"]: r for r in results}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)

    d.h("Task 5: Data Integrity Validation")
    d.h("5.1 Summary of all checks", 2)
    d.table(["Check group", "Enforced by"] + STATUSES + ["Checks"], _summary_rows(results),
            caption="Checks by group (PK, FK, REQ, DOM, FMT, TIME, STAT, PAT, LIM, EVID) and result")
    d.h("5.2 Checks that are not PASS", 2)
    d.table(["Check", "Severity", "Result", "Violations", "Rule"],
            [[r["id"], r["severity"], r["status"], r["violations"], r["rule"]]
             for r in results if r["status"] != "PASS"],
            caption="Warnings (data kept, reported) and limitations (information missing from the integrated database; see each rule)")
    d.h("5.3 Completed admissions without a primary diagnosis", 2)
    by_source, by_kind = _primary_diagnosis_rows(by_id)
    d.table(["Source system", "Admissions"], by_source,
            caption="Completed admissions with no primary ICD-9 diagnosis, by source system")
    d.table(["Kind", "Admissions"], by_kind,
            caption="Same admissions by kind. Cause: the diagnoses of these stays were quarantined in Task 2 "
                    "(see output/quarantine/diagnoses.csv), or none was recorded as primary. "
                    f"{by_id['LIM-null-admission-status']['violations']} further admissions have an unknown (NULL) "
                    "status because Task 2 flagged their status as inconsistent and set it to unknown, so they "
                    "are not counted as completed")
    d.h("5.4 Multiple admissions and diagnoses are preserved", 2)
    d.table(["Measure", "Count"], _preservation_rows(con),
            caption="Nothing was collapsed to one row per patient or per admission")
    d.h("5.5 Negative tests", 2)
    d.table(["Test", "Rule", "Mechanism", "Attempted change", "Rejected", "Database error"],
            [[n["id"], n["rule"], n["mechanism"], n["attempted_change"],
              "yes" if n["rejected"] == "True" else "no", n["error"] or "(accepted)"] for n in negatives],
            caption="Invalid changes the database must refuse (the last test is a valid change that must be accepted)")
    d.h("5.6 Database enforcement inventory", 2)
    d.table(["Trigger", "Table", "Event"], _trigger_rows(con),
            caption="Triggers in the database (keys, NOT NULL, UNIQUE and CHECK rules are in the table definitions)")
    con.close()
