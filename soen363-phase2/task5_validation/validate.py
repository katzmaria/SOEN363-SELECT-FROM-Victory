"""
Task 5: validates the integrity of the integrated database (output/integrated/hospital.db).

    python -m task5_validation.validate          (from the soen363-phase2 folder, after Task 4)
    python -m task5_validation.validate --db other.db --out some/folder

Every check is ONE SQL query that returns the rows BREAKING the rule: 0 rows = PASS. The database is opened
read-only, so the script can be rerun at any time and never changes the data.

Severity of a check
    FAIL         the rule must hold; any offending row is an integrity error (exit code 1).
    WARNING      the rule is expected to hold but the source data is known to break it a little; reported, kept.
    LIMITATION   a known gap in the integrated data that cannot be repaired (documented, never hidden).
Enforcement: "constraint" = the schema (PK / FK / CHECK / NOT NULL / composite FK) already refuses violations,
so the query proves it; "trigger" = a trigger refuses violations; "query" = only this validation query finds them.

Public API (for later phases)
    run_checks(db_path)            -> List[CheckResult]
    write_results(results, out_dir)  writes validation_results.csv and violations_sample.csv
Standard library only.
"""

PIPELINE_VERSION = "2026.11.17-tasks"   # run_all.py checks that every file has the same version

import argparse
import csv
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple, Union

from common.standards import SOURCES as SOURCE_CONFIG

DEFAULT_DB = Path(__file__).resolve().parents[1] / "output" / "integrated" / "hospital.db"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "output" / "validation"
SAMPLE_SIZE = 20
SOURCES = tuple(SOURCE_CONFIG)
TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"          # ISO 8601, UTC
COMPLETED = "('discharged', 'deceased')"


class Check(NamedTuple):
    id: str
    name: str
    rule: str
    handout: str
    enforcement: str          # constraint | trigger | query
    severity: str             # FAIL | WARNING | LIMITATION
    sql: str
    params: Tuple[Any, ...] = ()


class CheckResult(NamedTuple):
    id: str
    name: str
    rule: str
    handout: str
    enforcement: str
    severity: str
    violations: int
    status: str               # PASS | FAIL | WARNING | LIMITATION
    sample: Tuple[Dict[str, Any], ...]   # first SAMPLE_SIZE offending rows, each a dict {column: value}


# -----------------------------------------------------------------------------------------------------------
# Checks generated from the schema itself (so a new table or foreign key is covered without editing this file)
# -----------------------------------------------------------------------------------------------------------
def table_names(con: sqlite3.Connection) -> List[str]:
    return [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid")]


def columns(con: sqlite3.Connection, table: str) -> List[sqlite3.Row]:
    return list(con.execute(f"PRAGMA table_info({table})"))      # cid, name, type, notnull, dflt, pk


def pk_checks(con: sqlite3.Connection) -> List[Check]:
    """Primary keys unique and non-null. SQLite lets TEXT / composite PKs hold NULL, so NULL is tested too."""
    out: List[Check] = []
    for t in table_names(con):
        pk = [c["name"] for c in sorted(columns(con, t), key=lambda c: c["pk"]) if c["pk"]]
        if not pk:
            continue
        cols = ", ".join(pk)
        nulls = " OR ".join(f"{c} IS NULL" for c in pk)
        out.append(Check(
            f"PK-{t}", f"{t}: primary key unique and not null",
            f"({cols}) identifies one row of {t} and is never NULL.", "Primary keys unique and non-null",
            "constraint", "FAIL",
            f"SELECT {cols}, COUNT(*) AS n FROM {t} GROUP BY {cols} HAVING COUNT(*) > 1 OR {nulls}"))
    return out


HANDOUT_FK = {
    ("Admission", "Patient"): "Every admission has an existing patient",
    ("Diagnosis", "Admission"): "Every diagnosis has an existing admission (and the same patient)",
    ("Diagnosis", "ICD9Dictionary"): "Every diagnosis has an ICD-9 code from the dictionary",
}


def fk_checks(con: sqlite3.Connection) -> List[Check]:
    """One check per foreign key declared in the schema: child rows whose parent row does not exist."""
    out: List[Check] = []
    for t in table_names(con):
        groups: Dict[int, List[sqlite3.Row]] = {}
        for r in con.execute(f"PRAGMA foreign_key_list({t})"):
            groups.setdefault(r["id"], []).append(r)
        for rows in groups.values():
            rows.sort(key=lambda r: r["seq"])
            parent = rows[0]["table"]
            child_cols = [r["from"] for r in rows]
            parent_cols = [r["to"] for r in rows] if rows[0]["to"] else \
                [c["name"] for c in columns(con, parent) if c["pk"]]
            present = " AND ".join(f"c.{c} IS NOT NULL" for c in child_cols)
            match = " AND ".join(f"p.{p} = c.{c}" for c, p in zip(child_cols, parent_cols))
            label = ", ".join(child_cols)
            out.append(Check(
                f"FK-{t}-{parent}-{'+'.join(child_cols)}", f"{t}({label}) -> {parent}",
                f"Every non-NULL {t}({label}) matches a row of {parent}({', '.join(parent_cols)}).",
                HANDOUT_FK.get((t, parent), "Foreign keys point to existing rows"), "constraint", "FAIL",
                f"SELECT c.rowid AS row_id, {', '.join('c.' + x for x in child_cols)} FROM {t} c "
                f"WHERE {present} AND NOT EXISTS (SELECT 1 FROM {parent} p WHERE {match})"))
    return out


def required_checks(con: sqlite3.Connection) -> List[Check]:
    """Required values: NOT NULL / PK columns are never NULL, and no TEXT column holds an empty string."""
    out: List[Check] = []
    for t in table_names(con):
        cols = columns(con, t)
        tests = [f"{c['name']} IS NULL" for c in cols if c["notnull"] or c["pk"]]
        tests += [f"TRIM({c['name']}) = ''" for c in cols if (c["type"] or "").upper() == "TEXT"]
        if tests:
            out.append(Check(
                f"REQ-{t}", f"{t}: required values present, no empty text",
                f"Required columns of {t} are never NULL and no text column is an empty string "
                "(the import turns empty strings into NULL).", "Required values", "query", "FAIL",
                f"SELECT rowid AS row_id FROM {t} WHERE {' OR '.join(tests)}"))
    return out


def format_checks(con: sqlite3.Connection) -> List[Check]:
    """Every timestamp is a real ISO 8601 UTC value 'YYYY-MM-DDTHH:MM:SSZ'; dates of birth are 'YYYY-MM-DD'."""
    out: List[Check] = []
    for t in table_names(con):
        for c in columns(con, t):
            name, kind = c["name"], (c["type"] or "").upper()
            if kind == "DATETIME" or name == "follow_up_time":
                fn, fmt, shape = "strftime", f"'{TS_FORMAT}', ", "YYYY-MM-DDTHH:MM:SSZ (UTC)"
            elif kind == "DATE":
                fn, fmt, shape = "date", "", "YYYY-MM-DD"
            else:
                continue
            out.append(Check(
                f"FMT-{t}.{name}", f"{t}.{name}: format {shape}",
                f"{t}.{name} is NULL or a valid calendar value written exactly as {shape}.",
                "Timestamps in ISO 8601 UTC", "query", "FAIL",
                f"SELECT rowid AS row_id, {name} FROM {t} "
                f"WHERE {name} IS NOT NULL AND {fn}({fmt}{name}) IS NOT {name}"))
    return out


# -----------------------------------------------------------------------------------------------------------
# Hand-written checks
# -----------------------------------------------------------------------------------------------------------
DOMAINS: List[Tuple[str, str, Tuple[str, ...]]] = [   # (table, column, allowed values): independent of the schema's CHECKs, NULL is allowed where the column is
    ("Patient", "sex", ("female", "male", "unknown")),
    ("Patient", "life_status", ("alive", "deceased")),
    ("Admission", "admission_status", ("active", "discharged", "deceased")),
    ("Admission", "admission_type", ("emergency", "urgent", "elective", "outpatient", "newborn")),
    ("Diagnosis", "diagnosis_type", ("primary", "secondary")),
    ("TriageAssessment", "triage_priority", ("low", "medium", "high")),
    ("DiagnosticOrder", "order_status", ("pending", "in_progress", "completed", "cancelled")),
    ("DiagnosticOrder", "priority", ("routine", "urgent", "stat")),
    ("RadiologyExamination", "exam_status", ("scheduled", "completed", "cancelled")),
    ("UnitStay", "unit_type", ("Emergency Department", "ICU", "CCU", "MICU", "SICU", "General Ward")),
    ("SourceSystem", "source_system", SOURCES),
]


def domain_checks() -> List[Check]:
    return [Check(
        f"DOM-{t}.{c}", f"{t}.{c}: allowed categories",
        f"{t}.{c} is NULL or one of: {', '.join(vals)}.", "Categories follow the rules", "constraint", "FAIL",
        f"SELECT rowid AS row_id, {c} FROM {t} WHERE {c} IS NOT NULL AND {c} NOT IN ({', '.join('?' * len(vals))})",
        tuple(vals)) for t, c, vals in DOMAINS]


OUTSIDE_STAY = "a few records have a timestamp outside the admission period (the offending rows are days before admit or after discharge); they are kept and reported as a warning, not rejected"
# (table, time column, why it is only a warning or None)
EVENTS: List[Tuple[str, str, Optional[str]]] = [
    ("RadiologyExamination", "exam_time", None),
    ("SurgicalProcedure", "procedure_time", None),
    ("TriageAssessment", "triage_time", None),
    ("DiagnosticOrder", "order_time", OUTSIDE_STAY),
    ("Diagnosis", "diagnosis_time", OUTSIDE_STAY),
    ("ClinicalNote", "note_time", OUTSIDE_STAY),
]


TRIGGERED = {"RadiologyExamination", "SurgicalProcedure"}   # schema.sql triggers refuse these


def event_checks() -> List[Check]:
    out: List[Check] = []
    for t, col, why in EVENTS:
        warn = why is not None
        out.append(Check(
            f"TIME-{t}-in-admission", f"{t}.{col} inside the admission period",
            f"{t}.{col} is not before the admission's admit_time and, when the admission has a "
            f"discharge_time, not after it." + (f" Known: {why}." if warn else ""),
            "Events inside the admission period",
            "trigger" if t in TRIGGERED else "query", "WARNING" if warn else "FAIL",
            f"SELECT e.rowid AS row_id, e.admission_id, e.{col}, a.admit_time, a.discharge_time "
            f"FROM {t} e JOIN Admission a ON a.admission_id = e.admission_id "
            f"WHERE e.{col} < a.admit_time OR (a.discharge_time IS NOT NULL AND e.{col} > a.discharge_time)"))
    return out


def time_order_checks() -> List[Check]:
    h = "Discharge after admission, unit exit after entry"
    return [
        Check("TIME-discharge-after-admit", "Admission: discharge_time not before admit_time",
              "When discharge_time is set, discharge_time >= admit_time.", h, "constraint", "FAIL",
              "SELECT admission_id, admit_time, discharge_time FROM Admission WHERE discharge_time < admit_time"),
        Check("TIME-unit-exit-after-entry", "UnitStay: exit_time not before entry_time",
              "When exit_time is set, exit_time >= entry_time.", h, "constraint", "FAIL",
              "SELECT stay_id, entry_time, exit_time FROM UnitStay WHERE exit_time < entry_time"),
        Check("TIME-unitstay-in-admission", "UnitStay inside the admission period",
              "A unit stay enters at or after admit_time and, when the admission is discharged, enters and "
              "exits at or before its discharge_time.", "Events inside the admission period", "query", "FAIL",
              "SELECT s.stay_id, s.admission_id, s.entry_time, s.exit_time, a.admit_time, a.discharge_time "
              "FROM UnitStay s JOIN Admission a ON a.admission_id = s.admission_id "
              "WHERE s.entry_time < a.admit_time OR (a.discharge_time IS NOT NULL "
              "AND (s.entry_time > a.discharge_time OR s.exit_time > a.discharge_time))"),
        Check("TIME-dischargerecord-after-admit", "DischargeRecord: discharge_time not before admit_time",
              "A discharge record is never earlier than its admission's admit_time.", h, "query", "FAIL",
              "SELECT d.discharge_id, d.admission_id, d.discharge_time, a.admit_time FROM DischargeRecord d "
              "JOIN Admission a ON a.admission_id = d.admission_id WHERE d.discharge_time < a.admit_time"),
    ]


def consistency_checks() -> List[Check]:
    h = "Discharge agrees with admission status"
    return [
        Check("PAT-diagnosis-patient", "Diagnosis.patient_id equals its admission's patient",
              "Diagnosis is the only child table that stores both patient_id and admission_id; the two must "
              "agree (the composite foreign key enforces it).", "Diagnosis patient = admission patient",
              "constraint", "FAIL",
              "SELECT d.diagnosis_id, d.admission_id, d.patient_id, a.patient_id AS admission_patient_id "
              "FROM Diagnosis d JOIN Admission a ON a.admission_id = d.admission_id "
              "WHERE a.patient_id <> d.patient_id"),
        Check("STAT-status-vs-discharge-time", "Admission: status agrees with discharge_time",
              "discharged / deceased admissions have a discharge_time; active admissions do not.", h,
              "constraint", "FAIL",
              "SELECT admission_id, admission_status, discharge_time FROM Admission WHERE "
              f"(admission_status IN {COMPLETED} AND discharge_time IS NULL) "
              "OR (admission_status = 'active' AND discharge_time IS NOT NULL)"),
        Check("STAT-discharge-record-on-open-admission", "No discharge record on an active / unknown-status admission",
              "An admission that is not completed (active or NULL status) has no DischargeRecord.", h,
              "trigger", "FAIL",
              "SELECT d.discharge_id, d.admission_id, a.admission_status FROM DischargeRecord d "
              f"JOIN Admission a ON a.admission_id = d.admission_id "
              f"WHERE a.admission_status IS NULL OR a.admission_status NOT IN {COMPLETED}"),
        Check("STAT-discharge-time-differs", "Discharge record time equals the admission's discharge_time",
              "DischargeRecord.discharge_time = Admission.discharge_time. WARNING: the two come from different "
              "source files, so a difference is reported, not rejected.", h, "query", "WARNING",
              "SELECT d.discharge_id, d.admission_id, d.discharge_time, a.discharge_time AS admission_discharge_time "
              "FROM DischargeRecord d JOIN Admission a ON a.admission_id = d.admission_id "
              "WHERE d.discharge_time IS NOT a.discharge_time"),
        Check("STAT-completed-without-discharge-record", "Completed admission has a discharge record",
              "Every discharged / deceased admission has a DischargeRecord. WARNING: no DischargeRecord was "
              "imported for this admission (it may have been quarantined in Task 2); the admission is kept and reported.", h, "query", "WARNING",
              f"SELECT a.admission_id, a.source_system, a.admission_status FROM Admission a "
              f"WHERE a.admission_status IN {COMPLETED} AND NOT EXISTS "
              "(SELECT 1 FROM DischargeRecord d WHERE d.admission_id = a.admission_id)"),
        Check("STAT-deceased-admission-living-patient", "Deceased admission: patient not marked alive",
              "An admission with status 'deceased' belongs to a patient whose life_status is not 'alive'. "
              "WARNING: the status comes from the admission source, life_status from the patient source.", h,
              "query", "WARNING",
              "SELECT a.admission_id, a.patient_id, p.life_status FROM Admission a "
              "JOIN Patient p ON p.patient_id = a.patient_id "
              "WHERE a.admission_status = 'deceased' AND p.life_status = 'alive'"),
    ]


NO_PRIMARY = (f"FROM Admission a WHERE a.admission_status IN {COMPLETED} AND NOT EXISTS "
              "(SELECT 1 FROM Diagnosis d WHERE d.admission_id = a.admission_id AND d.diagnosis_type = 'primary')")
NO_DIAG = "AND NOT EXISTS (SELECT 1 FROM Diagnosis d WHERE d.admission_id = a.admission_id)"
H_PRIMARY = "Every completed admission has a primary diagnosis"


def limitation_checks() -> List[Check]:
    """Known source gaps. Sub-measurements: by source system, and no diagnosis at all vs secondary only."""
    sel = "SELECT a.admission_id, a.source_system, a.admission_status "
    out = [
        Check("LIM-no-primary-diagnosis", "Completed admission without a primary ICD-9 diagnosis",
              "Every discharged / deceased admission has at least one primary diagnosis. No primary ICD-9 diagnosis was imported "
              "for this completed admission. Its diagnoses may have been quarantined in Task 2 (duplicates, chronology, "
              "invalid dates, unknown ICD-9 codes, orphan professionals, parent quarantined) or none was recorded as "
              "primary. LIMITATION: it is never invented.",
              H_PRIMARY, "query", "LIMITATION", sel + NO_PRIMARY),
        Check("LIM-no-primary-none-at-all", "  of which: no diagnosis of any kind",
              "Completed admission with no Diagnosis row at all.", H_PRIMARY, "query", "LIMITATION",
              sel + NO_PRIMARY + " " + NO_DIAG),
        Check("LIM-no-primary-secondary-only", "  of which: secondary diagnoses only",
              "Completed admission with Diagnosis rows, all of them secondary.", H_PRIMARY, "query",
              "LIMITATION", sel + NO_PRIMARY + " AND EXISTS (SELECT 1 FROM Diagnosis d "
              "WHERE d.admission_id = a.admission_id)"),
    ]
    for s in SOURCES:
        out.append(Check(
            f"LIM-no-primary-source-{s}", f"  of which: source system {s}",
            f"Completed admission without a primary diagnosis, from source {s}.", H_PRIMARY, "query",
            "LIMITATION", sel + NO_PRIMARY + " AND a.source_system = ?", (s,)))
    out.append(Check(
        "LIM-null-admission-status", "Admission with unknown (NULL) status",
        "admission_status is not NULL. LIMITATION: Task 2 flagged their status as inconsistent "
        "(status_inconsistent); Task 3 set it to unknown (flag admission_status_set_unknown) because no discharge "
        "time could be recovered; these admissions are kept, "
        "excluded from the completed-admission checks (a discharge record on one is still a FAIL), and never "
        "guessed.", "Required values / status", "query",
        "LIMITATION", "SELECT admission_id, source_system, admit_time, discharge_time FROM Admission "
                      "WHERE admission_status IS NULL"))
    return out


def evidence_checks() -> List[Check]:
    """'Evidence' checks: they fail when the data does NOT contain the thing that must be preserved."""
    h = "Multiple admissions and diagnoses per patient preserved"
    return [
        Check("EVID-multiple-admissions", "Patients with more than one admission exist",
              "At least one patient has 2+ admissions (history kept, not collapsed to one).", h, "query", "FAIL",
              "SELECT 'no patient has more than one admission' AS problem WHERE NOT EXISTS "
              "(SELECT 1 FROM Admission GROUP BY patient_id HAVING COUNT(*) > 1)"),
        Check("EVID-multiple-diagnoses", "Admissions with more than one diagnosis exist",
              "At least one admission has 2+ diagnoses (all kept, not collapsed to one).", h, "query", "FAIL",
              "SELECT 'no admission has more than one diagnosis' AS problem WHERE NOT EXISTS "
              "(SELECT 1 FROM Diagnosis GROUP BY admission_id HAVING COUNT(*) > 1)"),
    ]


def build_checks(con: sqlite3.Connection) -> List[Check]:
    return (pk_checks(con) + fk_checks(con) + required_checks(con) + domain_checks() + format_checks(con)
            + consistency_checks() + time_order_checks() + event_checks() + limitation_checks()
            + evidence_checks())


# -----------------------------------------------------------------------------------------------------------
# Running
# -----------------------------------------------------------------------------------------------------------
def connect_readonly(db_path: Union[str, Path]) -> sqlite3.Connection:
    path = Path(db_path)
    if not path.is_file():
        raise SystemExit(f"Database not found: {path}\nBuild it first with:  python -m task4_import.import_db")
    con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def run_one(con: sqlite3.Connection, check: Check) -> CheckResult:
    try:
        rows = con.execute(check.sql, check.params).fetchall()
    except sqlite3.Error as err:
        raise SystemExit(f"Check {check.id} could not run: {err}")
    count = len(rows)
    sample = tuple(dict(r) for r in rows[:SAMPLE_SIZE])
    status = "PASS" if count == 0 else check.severity
    return CheckResult(check.id, check.name, check.rule, check.handout, check.enforcement, check.severity,
                       count, status, sample)


def run_checks(db_path: Union[str, Path] = DEFAULT_DB) -> List[CheckResult]:
    """Runs every check (read-only) and returns one CheckResult per check, in a fixed order."""
    con = connect_readonly(db_path)
    try:
        results = [run_one(con, c) for c in build_checks(con)]
        fk = [tuple(r) for r in con.execute("PRAGMA foreign_key_check")]
    except sqlite3.DatabaseError as err:        # e.g. --db README.md: not a SQLite file
        raise SystemExit(f"{db_path} is not a usable SQLite database: {err}")
    finally:
        con.close()
    pragma = CheckResult(
        "FK-pragma-foreign_key_check", "PRAGMA foreign_key_check", "SQLite's own check of every foreign key "
        "returns no row.", "Foreign keys point to existing rows", "constraint", "FAIL", len(fk),
        "PASS" if not fk else "FAIL",
        tuple(dict(zip(("table", "rowid", "parent", "fk_index"), r)) for r in fk[:SAMPLE_SIZE]))
    return [pragma] + results


# -----------------------------------------------------------------------------------------------------------
# Output
# -----------------------------------------------------------------------------------------------------------
RESULT_FIELDS = ["id", "name", "rule", "handout", "enforcement", "severity", "violations", "status"]


def write_results(results: List[CheckResult], out_dir: Union[str, Path] = DEFAULT_OUT) -> Tuple[Path, Path]:
    """validation_results.csv (one row per check) and violations_sample.csv (first rows of each non-passing check)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    res_path, sample_path = out / "validation_results.csv", out / "violations_sample.csv"
    with open(res_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(RESULT_FIELDS)
        w.writerows([getattr(r, k) for k in RESULT_FIELDS] for r in results)
    with open(sample_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["check_id", "status", "row_number", "offending_row"])
        for r in results:
            for i, row in enumerate(r.sample, 1):
                w.writerow([r.id, r.status, i, "; ".join(f"{k}={v}" for k, v in row.items())])
    return res_path, sample_path


def print_report(results: List[CheckResult]) -> None:
    print(f"{'ID':<46} {'SEVERITY':<10} {'STATUS':<10} VIOLATIONS")
    for r in results:
        print(f"{r.id:<46} {r.severity:<10} {r.status:<10} {r.violations}")
    counts = {s: sum(r.status == s for r in results) for s in ("PASS", "FAIL", "WARNING", "LIMITATION")}
    print("\n" + "  ".join(f"{k}: {v}" for k, v in counts.items()))


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Task 5: validate the integrity of the integrated database.")
    ap.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database (default output/integrated/hospital.db)")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="folder for the CSV results (default output/validation)")
    args = ap.parse_args(argv)
    results = run_checks(args.db)
    res_path, sample_path = write_results(results, args.out)
    print_report(results)
    print(f"\nWrote {res_path}\nWrote {sample_path}")
    return 1 if any(r.status == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
