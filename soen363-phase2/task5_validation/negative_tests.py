"""
Task 5: negative tests. Proves the integrated schema REFUSES bad data (output/integrated/hospital.db).

    python -m task5_validation.negative_tests          (from the soen363-phase2 folder, after Task 4)
    python -m task5_validation.negative_tests --db other.db --out some/folder

The real database is opened read-only and copied into memory (sqlite3 backup API); every deliberately bad
INSERT/UPDATE runs inside its own savepoint that is always rolled back, so nothing is ever written to disk.
One positive control (a valid insert that IS accepted) shows the rejections are caused by the rules, not by a
generic failure.

Public API
    run_negative_tests(db_path)    -> List[NegativeResult]
    write_results(results, out_dir)  writes negative_tests.csv
Standard library only.
"""

PIPELINE_VERSION = "2026.11.17-tasks"   # run_all.py checks that every file has the same version

import argparse
import csv
import sqlite3
import sys
from pathlib import Path
from typing import Any, List, NamedTuple, Optional, Sequence, Tuple

DEFAULT_DB = Path(__file__).resolve().parents[1] / "output" / "integrated" / "hospital.db"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "output" / "validation"
EARLY = "1900-01-01T00:00:00Z"     # before every admission
NEW_ID = "(SELECT MAX({col}) + 1 FROM {table})"
Case = Tuple[str, str, str, str, str, Sequence[Any], bool]
# ^ id, rule, mechanism, attempt, sql, params, expect_reject


class NegativeResult(NamedTuple):
    id: str
    rule: str
    mechanism: str
    attempted_change: str
    rejected: bool
    error: str
    expected_reject: bool


def _one(conn: sqlite3.Connection, sql: str, params: Sequence[Any] = ()) -> Tuple[Any, ...]:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        raise RuntimeError(f"negative tests need a sample row, none found for: {sql}")
    return row


def _new(table: str, col: str) -> str:
    return NEW_ID.format(col=col, table=table)


def _new_adm_sql() -> str:
    return ("INSERT INTO Admission (source_system, source_record_id, admission_id, patient_id, admit_time,"
            " admission_type, reason, discharge_time, admission_status) SELECT 'A', 'NEG-TEST',"
            f" {_new('Admission', 'admission_id')},"
            " ?, '2020-01-02T00:00:00Z', 'elective', 'test', ?, ?")


def _clone_dx_sql() -> str:
    return ("INSERT INTO Diagnosis (source_system, source_record_id, diagnosis_id, admission_id, patient_id,"
            " icd9_code, professional_id, diagnosis_time, diagnosis_type) SELECT source_system, 'NEG-TEST',"
            f" {_new('Diagnosis', 'diagnosis_id')}, admission_id, ?, ?, professional_id, diagnosis_time,"
            " diagnosis_type FROM Diagnosis WHERE diagnosis_id = ?")


def _clone_stay_sql() -> str:
    return ("INSERT INTO UnitStay (source_system, source_record_id, stay_id, admission_id, professional_id,"
            f" unit_type, entry_time, exit_time) SELECT source_system, 'NEG-TEST', {_new('UnitStay', 'stay_id')},"
            " admission_id, professional_id, unit_type, '2020-01-02T00:00:00Z', '2020-01-01T00:00:00Z'"
            " FROM UnitStay WHERE stay_id = ?")


def _clone_discharge_sql() -> str:
    return ("INSERT INTO DischargeRecord (source_system, source_record_id, discharge_id, admission_id,"
            f" professional_id, discharge_time) SELECT source_system, 'NEG-TEST',"
            f" {_new('DischargeRecord', 'discharge_id')},"
            " ?, professional_id, discharge_time FROM DischargeRecord ORDER BY discharge_id LIMIT 1")


def _key_cases(conn: sqlite3.Connection) -> List[Case]:
    pid, = _one(conn, "SELECT MIN(patient_id) FROM Patient")
    dx_id, dx_pid, dx_code = _one(conn, "SELECT diagnosis_id, patient_id, icd9_code FROM Diagnosis"
                                  " ORDER BY diagnosis_id LIMIT 1")
    other, = _one(conn, "SELECT MIN(patient_id) FROM Patient WHERE patient_id <> ?", (dx_pid,))
    return [
        ("NEG-pk-patient", "Patient id is unique", "PRIMARY KEY", f"INSERT Patient with existing patient_id={pid}",
         "INSERT INTO Patient (patient_id, full_name, date_of_birth) VALUES (?, 'Dup Test', '2000-01-01')",
         (pid,), True),
        ("NEG-fk-admission-patient", "Admission needs an existing patient", "FOREIGN KEY",
         "INSERT Admission with patient_id=-1", _new_adm_sql(), (-1, None, None), True),
        ("NEG-fk-diagnosis-patient-mismatch", "Diagnosis patient must equal its admission's patient",
         "FOREIGN KEY (composite)",
         f"INSERT Diagnosis copy of #{dx_id} with patient_id={other} (admission is of {dx_pid})",
         _clone_dx_sql(), (other, dx_code, dx_id), True),
        ("NEG-fk-diagnosis-icd9", "Diagnosis ICD-9 code must be in the dictionary", "FOREIGN KEY",
         f"INSERT Diagnosis copy of #{dx_id} with icd9_code='NOT-A-CODE'", _clone_dx_sql(),
         (dx_pid, "NOT-A-CODE", dx_id), True),
    ]


def _check_cases(conn: sqlite3.Connection) -> List[Case]:
    pid, = _one(conn, "SELECT MIN(patient_id) FROM Patient")
    stay, = _one(conn, "SELECT MIN(stay_id) FROM UnitStay")
    return [
        ("NEG-check-admission-times", "Discharge must not be before admission", "CHECK",
         "INSERT Admission with discharge_time 2020-01-01 < admit_time 2020-01-02", _new_adm_sql(),
         (pid, "2020-01-01T00:00:00Z", "discharged"), True),
        ("NEG-check-unitstay-times", "Unit exit must not be before entry", "CHECK",
         f"INSERT UnitStay copy of #{stay} with exit 2020-01-01 < entry 2020-01-02", _clone_stay_sql(),
         (stay,), True),
        ("NEG-check-sex", "sex is female / male / unknown", "CHECK", f"UPDATE Patient #{pid} SET sex='other'",
         "UPDATE Patient SET sex = 'other' WHERE patient_id = ?", (pid,), True),
    ]


def _null_unique_cases(conn: sqlite3.Connection) -> List[Case]:
    ss, rec = _one(conn, "SELECT source_system, source_record_id FROM HealthcareProfessional ORDER BY professional_id")
    dup_adm, = _one(conn, "SELECT MIN(admission_id) FROM DischargeRecord")
    return [
        ("NEG-notnull-patient-name", "Patient full_name is required", "NOT NULL",
         "INSERT Patient with full_name NULL",
         f"INSERT INTO Patient (patient_id, full_name, date_of_birth) VALUES ({_new('Patient', 'patient_id')}, NULL,"
         " '2000-01-01')", (), True),
        ("NEG-notnull-icd9-key", "ICD9Dictionary key is never NULL", "NOT NULL",
         "INSERT ICD9Dictionary with icd9_code NULL",
         "INSERT INTO ICD9Dictionary (icd9_code, official_title) VALUES (NULL, 'No code')", (), True),
        ("NEG-unique-professional-source", "One professional row per source record", "UNIQUE",
         f"INSERT HealthcareProfessional with existing ({ss}, {rec}) and a new id",
         "INSERT INTO HealthcareProfessional (source_system, source_record_id, professional_id)"
         f" VALUES (?, ?, {_new('HealthcareProfessional', 'professional_id')})", (ss, rec), True),
        ("NEG-unique-discharge-per-admission", "At most one discharge record per admission", "UNIQUE",
         f"INSERT DischargeRecord for admission {dup_adm} that already has one",
         _clone_discharge_sql(), (dup_adm,), True),
    ]


def _integrity_cases(conn: sqlite3.Connection) -> List[Case]:
    return _key_cases(conn) + _check_cases(conn) + _null_unique_cases(conn)


def _trigger_cases(conn: sqlite3.Connection) -> List[Case]:
    exam, exam_adm = _one(conn, "SELECT exam_id, admission_id FROM RadiologyExamination ORDER BY exam_id LIMIT 1")
    proc, proc_adm = _one(conn, "SELECT procedure_id, admission_id FROM SurgicalProcedure"
                              " ORDER BY procedure_id LIMIT 1")
    active, = _one(conn, "SELECT MIN(admission_id) FROM Admission WHERE admission_status = 'active'")
    clone_exam = ("INSERT INTO RadiologyExamination (source_system, source_record_id, exam_id, admission_id,"
                  " referring_professional_id, technician_id, exam_type, exam_time, exam_status) SELECT source_system,"
                  f" 'NEG-TEST', {_new('RadiologyExamination', 'exam_id')}, admission_id, referring_professional_id,"
                  " technician_id, exam_type, {when}, exam_status FROM RadiologyExamination WHERE exam_id = ?")
    clone_proc = ("INSERT INTO SurgicalProcedure (source_system, source_record_id, procedure_id, admission_id,"
                  f" surgeon_id, procedure_name, procedure_time) SELECT source_system, 'NEG-TEST',"
                  f" {_new('SurgicalProcedure', 'procedure_id')}, admission_id, surgeon_id, procedure_name, ?"
                  " FROM SurgicalProcedure WHERE procedure_id = ?")
    at_admit = ("(SELECT a.admit_time FROM Admission a"
                " WHERE a.admission_id = RadiologyExamination.admission_id)")
    return [
        ("NEG-trg-radiology-window", "Radiology exam inside its admission window", "trigger",
         f"INSERT RadiologyExamination copy of #{exam} (admission {exam_adm}) with exam_time {EARLY}",
         clone_exam.replace("{when}", "?"), (EARLY, exam), True),
        ("NEG-trg-procedure-window", "Surgical procedure inside its admission window", "trigger",
         f"INSERT SurgicalProcedure copy of #{proc} (admission {proc_adm}) with procedure_time {EARLY}",
         clone_proc, (EARLY, proc), True),
        ("NEG-trg-discharge-active", "Discharge record only for a discharged/deceased admission", "trigger",
         f"INSERT DischargeRecord for active admission {active}", _clone_discharge_sql(), (active,), True),
        ("NEG-trg-shrink-window", "Admission window cannot exclude its radiology exams", "trigger",
         f"UPDATE Admission {exam_adm} SET admit_time = 1 day after exam #{exam}",
         "UPDATE Admission SET admit_time = (SELECT strftime('%Y-%m-%dT%H:%M:%SZ', datetime(exam_time, '+1 day'))"
         " FROM RadiologyExamination WHERE exam_id = ?) WHERE admission_id = ?", (exam, exam_adm), True),
        ("POS-control-radiology-valid", "Valid exam (exam_time = admit_time) is accepted", "none (positive control)",
         f"INSERT RadiologyExamination copy of #{exam} with exam_time = its admission's admit_time",
         clone_exam.replace("{when}", at_admit), (exam,), False),
    ]


def _attempt(conn: sqlite3.Connection, sql: str, params: Sequence[Any]) -> Optional[str]:
    """Run one statement in a savepoint and always roll it back. Returns the sqlite error text, None if accepted."""
    conn.execute("SAVEPOINT neg")
    try:
        conn.execute(sql, params)
        return None
    except sqlite3.Error as exc:
        return str(exc)
    finally:
        conn.execute("ROLLBACK TO neg")
        conn.execute("RELEASE neg")


def run_negative_tests(db_path: Path = DEFAULT_DB) -> List[NegativeResult]:
    path = Path(db_path)
    if not path.is_file():
        raise SystemExit(f"Database not found: {path}\nBuild it first with:  python -m task4_import.import_db")
    conn = sqlite3.connect(":memory:", isolation_level=None)
    try:
        source = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            source.backup(conn)
        finally:
            source.close()
        conn.execute("PRAGMA foreign_keys = ON")
        results = []
        for cid, rule, mech, attempt, sql, params, expect in _integrity_cases(conn) + _trigger_cases(conn):
            err = _attempt(conn, sql, params)
            results.append(NegativeResult(cid, rule, mech, attempt, err is not None, err or "", expect))
        return results
    except sqlite3.Error as err:
        raise SystemExit(f"{path} is not a usable SQLite database: {err}")
    finally:
        conn.close()


def failures(results: Sequence[NegativeResult]) -> List[NegativeResult]:
    """Rejections that did not happen and a positive control that was refused."""
    return [r for r in results if r.rejected != r.expected_reject]


def write_results(results: Sequence[NegativeResult], out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "negative_tests.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(NegativeResult._fields)
        writer.writerows(results)
    return path


def _print_table(results: Sequence[NegativeResult]) -> None:
    for r in results:
        if r.rejected == r.expected_reject:
            verdict = "REJECTED" if r.rejected else "ACCEPTED (control)"
        else:
            verdict = "NOT REJECTED" if r.expected_reject else "UNEXPECTED REJECT"
        print(f"{r.id}\n    rule:      {r.rule}\n    mechanism: {r.mechanism}\n    attempt:   {r.attempted_change}"
              f"\n    result:    {verdict}\n    error:     {r.error or '-'}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run deliberately bad statements against the integrated DB.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    results = run_negative_tests(args.db)
    path = write_results(results, args.out)
    _print_table(results)
    bad = failures(results)
    print(f"\n{len(results)} cases, {len(bad)} unexpected outcome(s). Wrote {path}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
