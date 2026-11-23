"""
Task 6: runs the demonstration queries and the 20 Phase 1 queries on the integrated database.

    python -m task6_demo.run_demo          (from the soen363-phase2 folder, after Task 4)

Every query is one .sql file in task6_demo/queries/ (demo_*.sql = the six demonstration queries of the handout,
qNN.sql = the Phase 1 queries adapted to the integrated schema). The database is opened read-only. For each query
the full result is written to output/demo/<id>.csv and one line to output/demo/summary.csv, which also shows how
many rows the original Phase 1 query returns on the Phase 1 database, so a change in size can be explained.
Standard library only.
"""

PIPELINE_VERSION = "2026.11.17-tasks"   # run_all.py checks that every file has the same version

import csv
import sqlite3
from pathlib import Path

PHASE2 = Path(__file__).resolve().parents[1]
DB = PHASE2 / "output" / "integrated" / "hospital.db"
QUERIES = Path(__file__).resolve().parent / "queries"
OUT = PHASE2 / "output" / "demo"
PHASE1_DB = PHASE2.parent / "soen363-phase1" / "db" / "hospital.db"
PHASE1_QUERIES = PHASE2.parent / "soen363-phase1" / "queries"

DEMO = [
    ("demo_1", "Patient and admission counts by source and continent"),
    ("demo_2", "Admissions by standardized admission type across continents"),
    ("demo_3", "Top 3 primary ICD-9 diagnoses by continent"),
    ("demo_4", "Average completed admission duration by continent"),
    ("demo_5a", "Same local patient ID in each source maps to a different integrated patient"),
    ("demo_5b", "Duplicate source identifiers: how they were resolved"),
    ("demo_6", "Integrity checks: orphaned records and invalid chronology"),
]
PHASE1 = [
    (1, "High-priority emergency patients at triage", "Kerry"),
    (2, "Patients with more than three admissions", "Kerry"),
    (3, "Discharged without surgery", "Maria-Christine"),
    (4, "Radiology and surgery in the same admission", "Maria-Christine"),
    (5, "ICU/CCU stays over seven days", "Vanessa"),
    (6, "Admission count per patient (including zero)", "Kerry"),
    (7, "ED then ICU/CCU in the same admission", "Vanessa"),
    (8, "Most frequent primary ICD-9 with an ICU/CCU stay", "Maria Celena"),
    (9, "Average length of stay per critical care unit", "Vanessa"),
    (10, "Surgery before ICU/CCU entry", "Kerry"),
    (11, "Radiology exam count per patient (including zero)", "Maria Celena"),
    (12, 'Discharge note containing "recovery"', "Maria-Christine"),
    (13, "Radiology but no ICU/CCU stay", "Maria Celena"),
    (14, "Longest completed hospital stay", "Kerry"),
    (15, "Unit transfers per patient", "Vanessa"),
    (16, "More than one critical care unit type", "Vanessa"),
    (17, "More than one distinct ICD-9 per admission", "Maria-Christine"),
    (18, "Latest clinical note per patient", "Maria Celena"),
    (19, "Deaths during the hospital stay", "Maria-Christine"),
    (20, "Surgery and radiology on the same day", "Maria Celena"),
]

# Why a result differs from Phase 1 (checked against the data). Row counts are larger almost everywhere because
# the Phase 1 database has 60 patients and 124 admissions and the integrated one has 2,251 patients and 3,007
# admissions from four sources; that alone is not an error.
NOTES = {
    "q01": "More patients: all four sources are included.",
    "q02": "More patients with 4+ admissions at the larger size.",
    "q03": "Almost every discharged admission has no surgery (358 procedures for 3,007 admissions).",
    "q04": "Admissions with both a radiology exam and a surgery, at the larger size.",
    "q05": "EMPTY: no critical-care stay in the integrated database lasts more than 6.2 days (longest: CCU 6.2, "
           "ICU 5.9, MICU 5.9, SICU 6.0). The Phase 1 database had stays up to 16.5 days. The synthetic Phase 2 "
           "sources contain shorter critical-care stays; no Task 2 rejection reason concerns stay length.",
    "q06": "One row per integrated patient: 2,251, of which 167 have no admission (shown with 0).",
    "q07": "More admissions with an ED stay followed by a critical-care stay.",
    "q08": "Same question; the top primary diagnosis is 410.9. Admissions without a primary diagnosis (limitation of "
           "Task 5) are not counted.",
    "q09": "Same four unit types; averages are 2.0 to 2.4 days (2.5 to 4.2 in Phase 1).",
    "q10": "More admissions with surgery before critical-care entry.",
    "q11": "One row per integrated patient (2,251), including patients with no exam (0).",
    "q12": "More discharge summaries mentioning 'recovery'; note text is column note_text.",
    "q13": "Admissions with a radiology exam and no critical-care stay, at the larger size.",
    "q14": "3 patients tie at 432 hours (18 days); the query keeps all ties by design (Phase 1 had 1).",
    "q15": "One row per integrated patient (2,251).",
    "q16": "More admissions with two or more critical-care unit types.",
    "q17": "More admissions with 2+ distinct ICD-9 codes at the larger size.",
    "q18": "1,861 patients have at least one clinical note, so one latest note each.",
    "q19": "73 deceased admissions have a discharge record; 63 are listed because the query also needs a primary "
           "diagnosis (the 10 others are part of the Task 5 limitation of admissions without one).",
    "q20": "Same-day surgery and radiology pairs, at the larger size.",
}


def connect_readonly(path: Path) -> sqlite3.Connection:
    """Opens a database that cannot be changed by the queries."""
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def run_sql(con: sqlite3.Connection, sql: str) -> tuple:
    cur = con.execute(sql)
    return [d[0] for d in cur.description], cur.fetchall()


def phase1_row_count(con, number: int):
    """Rows the original Phase 1 query returns on the Phase 1 database (None if that database is missing)."""
    path = PHASE1_QUERIES / f"q{number:02d}.sql"
    if con is None or not path.exists():
        return None
    return len(con.execute(path.read_text(encoding="utf-8")).fetchall())


def run_all_queries(db_path: Path = DB) -> list:
    """One dict per query: id, kind, title, owner, sql, headers, rows, phase1_rows."""
    if not db_path.exists():
        raise SystemExit("No database: run Task 4 first (python show_tables.py --task 4)")
    old = connect_readonly(PHASE1_DB) if PHASE1_DB.exists() else None
    con = connect_readonly(db_path)
    try:
        results = []
        for qid, title in DEMO:
            sql = (QUERIES / f"{qid}.sql").read_text(encoding="utf-8")
            headers, rows = run_sql(con, sql)
            results.append(dict(id=qid, kind="demo", title=title, owner="", sql=sql, headers=headers, rows=rows,
                                phase1_rows=None))
        for number, title, owner in PHASE1:
            sql = (QUERIES / f"q{number:02d}.sql").read_text(encoding="utf-8")
            headers, rows = run_sql(con, sql)
            results.append(dict(id=f"q{number:02d}", kind="phase1", title=title, owner=owner, sql=sql,
                                headers=headers, rows=rows, phase1_rows=phase1_row_count(old, number)))
        return results
    finally:
        con.close()
        if old is not None:
            old.close()


def _write(path: Path, headers: list, rows: list) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(headers)
        w.writerows([["" if v is None else v for v in r] for r in rows])


def write_results(results: list, out_dir: Path = OUT) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for r in results:
        _write(out_dir / f"{r['id']}.csv", r["headers"], r["rows"])
    _write(out_dir / "summary.csv", ["id", "kind", "owner", "title", "phase1_rows", "integrated_rows", "note"],
           [[r["id"], r["kind"], r["owner"], r["title"], r["phase1_rows"], len(r["rows"]), NOTES.get(r["id"], "")]
            for r in results])


def run(out_dir: Path = OUT, db_path: Path = DB, quiet: bool = False) -> list:
    results = run_all_queries(db_path)
    write_results(results, out_dir)
    if not quiet:
        print(f"  {len(results)} queries run on {db_path.name} (read-only) -> {out_dir}")
    return results


if __name__ == "__main__":
    run()
