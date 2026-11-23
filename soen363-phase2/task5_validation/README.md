# Task 5: Enforce and validate data integrity

Handout section 8 - part of 20 points (SQL import, integrity enforcement and validation).

- Database constraints wherever possible; triggers or checks for the rest.
- Check at least: unique non-null primary keys; foreign keys exist; every admission has a patient; every diagnosis
  has an admission and an ICD-9 code; diagnosis patient = admission patient; discharge after admission; unit exit
  after entry; exams and procedures inside their admission; every completed admission has a primary diagnosis;
  discharge agrees with admission status; required values and categories follow the rules.
- Deliver: the validation queries, their outputs, and every unresolved limitation.

## How to run

    python -m task5_validation.validate          # the 118 validation checks
    python -m task5_validation.negative_tests    # 16 attempts to break the rules, on a copy of the database
    python show_tables.py --task 5               # runs both and prints Figures 42-48

All three need `output/integrated/hospital.db` (Tasks 1 to 4, or `python run_all.py`). Both scripts open the database
read-only: `validate.py` opens it with `mode=ro`, and `negative_tests.py` works on an in-memory copy of it
(the real file is opened read-only and copied with the sqlite3 backup API; nothing is written to disk). They can be re-run any number of times. `--db <path>` and `--out <dir>`
change the database and the output folder.

| Output | Content |
|---|---|
| `output/validation/validation_results.csv` | One row per check: id, rule, handout bullet, enforced by, severity, violations, status |
| `output/validation/violations_sample.csv` | The first 20 offending rows of every check that is not PASS |
| `output/validation/negative_tests.csv` | One row per negative test: the change tried, whether it was rejected, the error |
| `output/tables/task5_tables.txt` | The tables printed by `show_tables.py --task 5` |

## What is checked

A check has a severity. `FAIL` severity: any violation is an error. `WARNING`: the data is kept and reported.
`LIMITATION`: information missing from the integrated database, reported, never invented. Result of the last run
on the current data: **118 checks, 106 PASS, 0 FAIL, 4 WARNING, 8 LIMITATION**.

| Rule | Handout bullet | Enforced by | Checks | Result |
|---|---|---|---|---|
| Primary key unique and not NULL, every table | Primary keys unique and non-null | PRIMARY KEY (+ NOT NULL) | 15 | 15 PASS |
| Every foreign key points to a row (34 foreign-key checks) + `PRAGMA foreign_key_check` | Foreign keys exist | FOREIGN KEY | 35 | 35 PASS |
| Admission has a patient; diagnosis has an admission; diagnosis has a dictionary ICD-9 code | Admission has patient; diagnosis has admission and ICD-9 | FOREIGN KEY | 3 | 3 PASS |
| Diagnosis patient = patient of its admission | Diagnosis patient = admission patient | composite FOREIGN KEY `Diagnosis(admission_id, patient_id)` to `Admission UNIQUE(admission_id, patient_id)` | 1 | 1 PASS |
| Discharge not before admission; unit exit not before entry | Discharge after admission; unit exit after entry | CHECK | 2 | 2 PASS |
| Discharge record not before admission | Discharge after admission | query | 1 | 1 PASS |
| Radiology exam and surgical procedure inside the admission | Exams and procedures inside their admission | trigger | 2 | 2 PASS |
| Unit stay and triage inside the admission | (events inside the stay) | query | 2 | 2 PASS |
| Order, diagnosis and clinical note inside the admission | (events inside the stay) | query | 3 | 3 WARNING (1, 3, 1 rows) |
| Admission status agrees with discharge time (active has none, discharged/deceased has one) | Discharge agrees with admission status | CHECK | 1 | 1 PASS |
| A DischargeRecord exists only for a discharged/deceased admission | Discharge agrees with admission status | trigger | 1 | 1 PASS |
| Discharge time of the record equals the admission's; deceased admission has a deceased patient | Discharge agrees with admission status | query | 2 | 2 PASS |
| Every completed admission has a DischargeRecord | Discharge agrees with admission status | query | 1 | 1 WARNING (229) |
| Required columns are not NULL, every table | Required values | query | 15 | 15 PASS |
| Category columns hold allowed values (sex, status, type, priority, unit, source) | Categories follow the rules | CHECK | 11 | 11 PASS |
| Timestamps are ISO 8601 UTC text, every time column | Required values (format) | query | 13 | 13 PASS |
| Every completed admission has a primary diagnosis (with split by kind and by source) | Completed admission has a primary diagnosis | query | 7 | 7 LIMITATION |
| Admission with NULL status | Required values | query | 1 | 1 LIMITATION |
| Multiple admissions per patient and diagnoses per admission were kept | (evidence, not a rule) | query | 2 | 2 PASS |

Every check lists its rule text in `validation_results.csv`, and the SQL is in `validate.py`.

## Schema changes made for Task 5 (`task3_integration/schema.sql`)

The table count stays at 15; only constraints and triggers were added.

**NOT NULL on `ICD9Dictionary.icd9_code` and `SourceSystem.source_system`.** SQLite lets a primary key hold NULL
unless the column is an `INTEGER PRIMARY KEY` (checked: a row with a NULL text key is accepted). These two keys are
text, so "primary key non-null" was not enforced by the database. Adding NOT NULL fixes it. The other tables have
integer keys or already declared NOT NULL.

**Eight triggers.** A CHECK sees one row only, so it cannot compare an event with its admission or a discharge record
with its admission's status. These rules need a lookup in another table:

| Trigger | Fires on | Enforces |
|---|---|---|
| `trg_radiology_in_admission_insert` / `_update` | INSERT / UPDATE of RadiologyExamination | `exam_time` between the admission's `admit_time` and `discharge_time` (no upper bound while the admission is open) |
| `trg_procedure_in_admission_insert` / `_update` | INSERT / UPDATE of SurgicalProcedure | the same for `procedure_time` |
| `trg_discharge_record_completed_insert` / `_update` | INSERT / UPDATE of DischargeRecord | its admission has status `discharged` or `deceased` |
| `trg_admission_keep_completed` | UPDATE of `Admission.admission_status` | status cannot leave discharged/deceased while a DischargeRecord exists |
| `trg_admission_keep_window` | UPDATE of `admit_time` / `discharge_time` | the new period cannot exclude an existing radiology exam or procedure |

The last two close the other direction: without them a rule enforced when the child row is written could be broken
afterwards by changing the parent. The triggers live in `schema.sql`, not in the Task 5 code, because the database is
rebuilt on every run from that file; a trigger there exists in every rebuilt database and applies to every
connection, whichever script opens it. The time rules are limited to radiology and procedures because
those are the two the handout names; the existing data has 0 violations of these rules and of the discharge-record
rule (checks PASS).

## Negative tests (`negative_tests.py`)

16 cases run on a copy of the database in memory with `PRAGMA foreign_keys = ON`: 15 changes that break a rule
(all 15 rejected) and 1 positive control (a valid exam is accepted, so a rejection is not just a broken test). The
real file is opened read-only and copied into memory with the sqlite3 backup API; each case runs in a savepoint that
is rolled back, so nothing is written to disk.

Every case, its mechanism and the error returned are in Figure 47 and `output/validation/negative_tests.csv`.
Mechanisms covered: PRIMARY KEY, FOREIGN KEY (including the composite diagnosis-to-admission key), CHECK, NOT NULL,
UNIQUE, and triggers. Representative lines:

- Admission for patient -1 (FOREIGN KEY): `FOREIGN KEY constraint failed`
- Admission with discharge before admit (CHECK): `CHECK constraint failed: discharge_time IS NULL OR discharge_time >= admit_time`
- Radiology exam dated 1900 (trigger): `exam_time must be inside its admission period (admit_time to discharge_time)`
- Control: exam at exactly `admit_time`: accepted

## Warnings (kept and reported)

- **229 completed admissions have no DischargeRecord.** The four sources all export discharge records, and no
  DischargeRecord was imported for these admissions. The cause is not established here; Task 2 may have
  quarantined some of them (`output/quarantine/discharges.csv`). The admissions are kept.
- **5 event rows lie outside their admission period:** 1 diagnostic order, 3 diagnoses and 1 clinical note. All five are after the
  admission's discharge, by about 7 to 35 days, so this is not rounding. The cause is not established. The rows are kept and
  reported; no trigger enforces these three, so they could be imported. Radiology, procedures, triage
  and unit stays have 0 such rows.

## Known limitations

**(a) 295 completed admissions have no primary ICD-9 diagnosis** (discharged or deceased, 3,007 admissions in
total). By source: A 60, B 79, C 54, D 102. By kind: 178 have no diagnosis row at all, 117 have secondary diagnoses
only. The cause is one of two things, as far as the data shows: the diagnosis was quarantined in Task 2 (duplicates,
chronology, invalid dates, unknown ICD-9 codes, orphan professionals, parent quarantined; `output/quarantine/diagnoses.csv`),
or none was recorded as primary. Tracing the raw rows: for source A, 54 of the 60 admissions have a quarantined
diagnosis row; for source B, 47 of the 79 do, and 29 have no diagnosis row in the raw file at all. For C and D the
quarantine files do not allow tracing a diagnosis to an admission, so no split is given.

Why it is not repaired: the handout forbids inventing clinical facts. Promoting a secondary diagnosis to primary, or
restoring a quarantined row, would invent or change clinical data. Why no constraint or trigger: a rule "completed
admission needs a primary diagnosis" would fail on the 295 existing admissions, and would block valid inserts, since
a primary diagnosis can legitimately be added after the admission row. It is therefore a query check with severity
LIMITATION; `violations_sample.csv` holds the first 20 of them.

**(b) 7 admissions have a NULL `admission_status`.** Task 2 flagged their status as inconsistent
(`status_inconsistent`); Task 3 set it to unknown (flag `admission_status_set_unknown`) because no discharge time could be recovered. They are kept, reported separately,
and not counted as completed. A DischargeRecord on one of them is still rejected by the trigger.

**(c) What the database does not enforce.**
- Timestamp format (ISO 8601 UTC text) is verified by query only; there is no CHECK on it.
- Order, diagnosis, clinical note, triage and unit-stay times inside the admission are verified by query only (3 of
  them show warnings, see above). Only radiology and procedures have triggers.
- Required values are enforced by NOT NULL where the schema declares it; the REQ checks verify the result by query.
- Foreign keys are enforced only on connections that run `PRAGMA foreign_keys = ON` (SQLite default is off;
  `import_db.py` and `negative_tests.py` turn it on). Triggers fire whether or not that setting is on;
  foreign keys are enforced only when it is.
- A trigger checks rows written after it exists. It does not re-check rows already in the table; that is what the
  validation queries are for.
- The validation describes the current data and must be re-run after any change to it.
