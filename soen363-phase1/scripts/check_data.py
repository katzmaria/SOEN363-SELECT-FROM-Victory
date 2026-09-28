"""
Sanity-check db/hospital.db against the data rules in the handout's
"Data sources" section: foreign keys valid, timestamps in order, events
inside their admission, a primary diagnosis on every completed admission,
and every table populated. Also checks that the core data is consistent
with the scenario: no overlapping admissions for one patient, no admission
before birth, newborn admissions only for newborns, and triage by nurses.

Usage (from the repo root):
    python scripts/check_data.py

Exits with code 1 if any check fails.
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "hospital.db"

TABLES = [
    "HealthcareProfessional", "ICD9Dictionary", "Patient", "Admission",
    "TriageAssessment", "Diagnosis", "ClinicalNote", "DiagnosticOrder",
    "RadiologyExamination", "SurgicalProcedure", "UnitStay", "DischargeRecord",
]


def outside_admission(table, time_col):
    """Rows of `table` whose `time_col` falls before admission or after discharge."""
    return f"""SELECT COUNT(*) FROM {table} x JOIN Admission a ON a.admission_id = x.admission_id
               WHERE x.{time_col} < a.admission_date_time
                  OR (a.discharge_date_time IS NOT NULL AND x.{time_col} > a.discharge_date_time)"""


# (description, SQL returning the number of violating rows)
CHECKS = {
    "Core data (patients, admissions, unit stays)": [
        ("Discharge time is after admission time",
         "SELECT COUNT(*) FROM Admission WHERE discharge_date_time < admission_date_time"),
        ("Unit exit time is after unit entry time (no zero-length stays)",
         "SELECT COUNT(*) FROM UnitStay WHERE exit_date_time <= entry_date_time"),
        ("Unit stays start at or after admission",
         """SELECT COUNT(*) FROM UnitStay u JOIN Admission a USING (admission_id)
            WHERE u.entry_date_time < a.admission_date_time"""),
        ("Unit stays end at or before discharge",
         """SELECT COUNT(*) FROM UnitStay u JOIN Admission a USING (admission_id)
            WHERE a.discharge_date_time IS NOT NULL
              AND (u.exit_date_time IS NULL OR u.exit_date_time > a.discharge_date_time)"""),
        ("A patient has at most one open (active) admission",
         """SELECT COUNT(*) FROM (SELECT patient_id FROM Admission
                                WHERE discharge_date_time IS NULL
                                GROUP BY patient_id HAVING COUNT(*) > 1)"""),
        # Counts pairs of admissions. An open admission counts as lasting forever,
        # so a patient re-admitted while still admitted is caught here too.
        # julianday() is used because DATETIME columns have NUMERIC affinity in SQLite,
        # which can make a plain text comparison against a sentinel like '9999' misbehave.
        ("A patient's admissions do not overlap in time",
         """SELECT COUNT(*) FROM Admission a JOIN Admission b
              ON b.patient_id = a.patient_id AND a.admission_id < b.admission_id
            WHERE julianday(a.admission_date_time) < julianday(COALESCE(b.discharge_date_time, '9999-12-31'))
              AND julianday(b.admission_date_time) < julianday(COALESCE(a.discharge_date_time, '9999-12-31'))"""),
        ("No admission starts before the patient was born",
         """SELECT COUNT(*) FROM Admission a JOIN Patient p USING (patient_id)
            WHERE julianday(a.admission_date_time) < julianday(p.date_of_birth)"""),
        ("'newborn' admissions are within 28 days of birth",
         """SELECT COUNT(*) FROM Admission a JOIN Patient p USING (patient_id)
            WHERE a.admission_type = 'newborn'
              AND julianday(a.admission_date_time) - julianday(p.date_of_birth) > 28"""),
        # Handout, Step 3: "A triage nurse performs an initial assessment"
        ("Triage is performed by nursing staff",
         """SELECT COUNT(*) FROM TriageAssessment t
            JOIN HealthcareProfessional h ON h.professional_id = t.performing_professional_id
            WHERE h.role NOT IN ('Nurse', 'Triage Nurse')"""),
    ],
    "Clinical data (diagnoses, orders, exams, surgery, notes, discharge)": [
        ("Every completed admission has a primary diagnosis",
         """SELECT COUNT(*) FROM Admission a
            WHERE a.discharge_date_time IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM Diagnosis d
                              WHERE d.admission_id = a.admission_id
                                AND d.diagnosis_type = 'primary')"""),
        ("Diagnosis patient matches its admission's patient",
         """SELECT COUNT(*) FROM Diagnosis d JOIN Admission a USING (admission_id)
            WHERE d.patient_id <> a.patient_id"""),
        ("Diagnoses are dated during the admission", outside_admission("Diagnosis", "diagnosis_date_time")),
        ("Diagnostic orders are placed during the admission", outside_admission("DiagnosticOrder", "request_date_time")),
        ("Radiology exams happen during the admission",
         outside_admission("RadiologyExamination", "examination_date_time")),
        ("Radiology exams belong to the same admission as their order",
         """SELECT COUNT(*) FROM RadiologyExamination r JOIN DiagnosticOrder o USING (order_id)
            WHERE r.admission_id <> o.admission_id"""),
        ("Radiology exams happen after their order was placed",
         """SELECT COUNT(*) FROM RadiologyExamination r JOIN DiagnosticOrder o USING (order_id)
            WHERE r.examination_date_time < o.request_date_time"""),
        ("Surgical procedures happen during the admission",
         outside_admission("SurgicalProcedure", "procedure_date_time")),
        ("Clinical notes are written during the admission", outside_admission("ClinicalNote", "creation_date_time")),
        ("Every completed admission has a discharge record",
         """SELECT COUNT(*) FROM Admission a
            WHERE a.discharge_date_time IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM DischargeRecord r WHERE r.admission_id = a.admission_id)"""),
        ("Discharge records only exist for completed admissions, at the same time",
         """SELECT COUNT(*) FROM DischargeRecord r JOIN Admission a USING (admission_id)
            WHERE a.discharge_date_time IS NULL OR r.discharge_date_time <> a.discharge_date_time"""),
        ("Deaths are recorded only for deceased patients",
         """SELECT COUNT(*) FROM Admission a JOIN Patient p USING (patient_id)
            WHERE a.final_admission_status = 'deceased' AND p.life_status <> 'deceased'"""),
        ("No admission starts after the patient's death",
         """SELECT COUNT(*) FROM Admission d JOIN Admission later
              ON later.patient_id = d.patient_id AND later.admission_date_time > d.discharge_date_time
            WHERE d.final_admission_status = 'deceased'"""),
    ],
}


def main():
    if not DB_PATH.exists():
        sys.exit(f"Database not found at {DB_PATH}. Run: python data/build_db.py")
    conn = sqlite3.connect(DB_PATH)
    failures = 0

    print("Row counts")
    for t in TABLES:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        failures += 0 if n else 1
        print(f"  {t:<24}{n:>6}" + ("" if n else "   <-- EMPTY"))

    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    failures += bool(fk)
    print(f"\n[{'PASS' if not fk else 'FAIL'}] Foreign keys reference existing rows"
          + (f" ({len(fk)} bad rows)" if fk else ""))

    for section, checks in CHECKS.items():
        print(f"\n{section}")
        for desc, sql in checks:
            bad = conn.execute(sql).fetchone()[0]
            failures += bool(bad)
            print(f"  [{'PASS' if not bad else 'FAIL'}] {desc}" + (f" ({bad} violations)" if bad else ""))

    conn.close()
    print(f"\n{failures} issue(s) found." if failures else "\nAll checks passed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
