"""
Task 3 result tables, built from output/integrated/ (printed by show_tables.py).

    python show_tables.py --task 3
"""

PIPELINE_VERSION = "2026.11.17-tasks"   # run_all.py checks that every file has the same version

import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "output" / "integrated" / "hospital.db"


def tables(d):
    if not DB.exists():
        raise SystemExit("No Task 3 results yet: run  python show_tables.py --task 3")
    con = sqlite3.connect(DB)
    q = lambda sql: [list(r) for r in con.execute(sql)]

    d.h("Task 3: Integrate the Sources")
    d.h("3.1 Identifier mapping", 2)
    d.table(["Entity", "A", "B", "C", "D", "Source records", "Integrated IDs"], q("""
        SELECT entity_type, SUM(source_system='A'), SUM(source_system='B'), SUM(source_system='C'),
               SUM(source_system='D'), COUNT(*), COUNT(DISTINCT integrated_id)
        FROM IdMapping GROUP BY entity_type ORDER BY entity_type"""),
        caption="Source records per entity and the global keys they were given")
    d.table(["Source", "Continent", "Original ID", "Local key", "Integrated patient_id", "Admissions"], q("""
        SELECT m.source_system, s.continent, m.source_record_id, m.source_local_id, m.integrated_id,
               (SELECT COUNT(*) FROM Admission a WHERE a.patient_id = m.integrated_id)
        FROM IdMapping m JOIN SourceSystem s USING (source_system)
        WHERE m.entity_type = 'Patient' AND m.source_local_id = 1 ORDER BY m.source_system"""),
        caption="Local patient 1 in each source becomes a different integrated patient")
    d.h("3.2 Patient matching", 2)
    rows = q("""SELECT rule_code, decision, COUNT(*) FROM PatientMatchCandidate GROUP BY 1, 2 ORDER BY 1, 2""")
    d.table(["Rule", "Decision", "Pairs"], rows or [["(none)", "-", 0]],
            caption="Cross-source patient match candidates (rules in task3_integration/README.md)")
    d.table(["Fix", "Admissions"], q("""
        SELECT CASE WHEN quality_flags LIKE '%discharge_time_from_discharge_record%'
                    THEN 'discharge_time taken from the discharge record' ELSE 'admission_status set to unknown' END,
               COUNT(*)
        FROM Admission WHERE quality_flags LIKE '%discharge_time_from_discharge_record%'
                          OR quality_flags LIKE '%admission_status_set_unknown%' GROUP BY 1"""),
        caption="Admissions marked discharged/deceased without a discharge time (Task 2 flag status_inconsistent)")
    con.close()
