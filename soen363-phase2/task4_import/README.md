# Task 4: Import into the SQL database

Handout section 7 - part of 20 points (SQL import, integrity enforcement and validation).

- Python script that loads the clean data into the revised database (Task 3's schema).
- Parents before children, parameterized statements, transactions and error handling.
- Keep relationships intact when IDs are converted; no duplicates when the script is rerun.
- Document whether a rerun rebuilds the database or updates it.
- Result: real, populated tables (not the raw files stored as text or JSON).

Code for this task goes in this folder. To show its results like Tasks 1 and 2, add it to `TASKS` in `show_tables.py`.

## How to run

    python -m task4_import.import_db          # or: python show_tables.py --task 4   (both after Task 2)

Reads Task 3's integrated rows (`task3_integration.integrate.integrate()`), writes `output/integrated/hospital.db`
and `output/integrated/import_log.csv`. Task 3's own `run()` also builds the database through this importer, so
there is a single loading path.

## How each requirement is met (`import_db.py`)

| Requirement (handout 7) | How |
|---|---|
| Referenced records before dependent records | `load_order()` reads every table's foreign keys from the schema (`PRAGMA foreign_key_list`) and sorts the tables topologically; before each table is inserted, an assert checks its parents are already loaded. Order used: SourceSystem, IdMapping, HealthcareProfessional, ICD9Dictionary, Patient, PatientMatchCandidate, Admission, TriageAssessment, Diagnosis, ClinicalNote, DiagnosticOrder, RadiologyExamination, SurgicalProcedure, UnitStay, DischargeRecord |
| Parameterized statements | `INSERT INTO t (cols) VALUES (?, ?, ...)` with `executemany`; column names come from the schema (`PRAGMA table_info`), values are never formatted into the SQL. Empty text becomes NULL |
| Errors and transactions | One transaction for the whole import with `PRAGMA foreign_keys = ON` (bad references fail on insert, not later) and a SAVEPOINT per table. Before COMMIT: row count per table = rows produced by Task 3, `PRAGMA foreign_key_check` empty, `PRAGMA integrity_check` = ok. Any failure rolls everything back |
| Relationships kept through identifier conversion | Task 3 rewrites every FK through IdMapping using the row's own source; the import keeps those keys as-is (no AUTOINCREMENT re-numbering). Figure "Relationships after identifier conversion" shows 0 admissions pointing at a patient from another source |
| No duplicates on rerun | See below |

## Rerun behaviour: the pipeline **rebuilds**, it does not update

- The new database is built in `hospital.db.tmp` and moved over `hospital.db` with `os.replace` (atomic) only after
  every check passed. A failed run deletes the temp file; the previous `hospital.db` is left exactly as it was.
- The keys are deterministic (Task 3 numbers records in a fixed order), so rerunning on the same clean data gives
  the same database. `import_log.csv` stores a checksum per table and a `same_as_previous_run` column; two runs in a
  row show `yes` for all 15 tables.
- Second guard: every table has `UNIQUE (source_system, source_record_id)` (IdMapping: its primary key), so even
  inserting the same rows twice into one database fails instead of creating duplicates.
- Why rebuild rather than update (upsert): the sources are static files and the whole pipeline takes seconds;
  a rebuild cannot leave stale rows behind when Task 2 rejects a record it accepted before, which an upsert would.

## Result on the current data

56,445 rows in 15 tables (28,204 source records in IdMapping, 2,251 patients, 3,007 admissions, 4,832 diagnoses).
