"""
Task 4 result tables, built from output/integrated/ (printed by show_tables.py).

    python show_tables.py --task 4
"""

PIPELINE_VERSION = "2026.11.17-tasks"   # run_all.py checks that every file has the same version

import sqlite3
from pathlib import Path

from common.tabular import read_csv

OUT = Path(__file__).resolve().parents[1] / "output" / "integrated"


def tables(d):
    db, log_path = OUT / "hospital.db", OUT / "import_log.csv"
    if not (db.exists() and log_path.exists()):
        raise SystemExit("No Task 4 results yet: run  python show_tables.py --task 4")
    con = sqlite3.connect(db)
    _, log = read_csv(log_path)

    d.h("Task 4: Import into the SQL Database")
    d.h("4.1 Import order and row counts", 2)
    d.table(["#", "Table", "References", "Rows expected", "Rows in DB", "Checksum", "Same as previous run"],
            [[i, e["table"],
              ", ".join(sorted({r[2] for r in con.execute(f"PRAGMA foreign_key_list({e['table']})")}
                               - {e["table"]})) or "-",
              e["expected_rows"], e["db_rows"], e["checksum"], e["same_as_previous_run"] or "(first run)"]
             for i, e in enumerate(log, 1)],
            caption="Tables in load order: each one after every table it references; one transaction")
    d.h("4.2 Relationships after identifier conversion", 2)
    d.table(["Source", "Continent", "Patients", "Admissions", "Diagnoses", "Admissions with a wrong patient"],
            [list(r) for r in con.execute("""
        SELECT s.source_system, s.continent,
               (SELECT COUNT(*) FROM IdMapping m WHERE m.entity_type = 'Patient' AND m.source_system = s.source_system),
               (SELECT COUNT(*) FROM Admission a WHERE a.source_system = s.source_system),
               (SELECT COUNT(*) FROM Diagnosis g WHERE g.source_system = s.source_system),
               (SELECT COUNT(*) FROM Admission a
                 WHERE a.source_system = s.source_system
                   AND NOT EXISTS (SELECT 1 FROM IdMapping mp
                                    WHERE mp.entity_type = 'Patient' AND mp.integrated_id = a.patient_id
                                      AND mp.source_system = a.source_system))
        FROM SourceSystem s ORDER BY s.source_system""")],
            caption="Every admission still points at a patient from its own source after the keys were rewritten")
    con.close()
