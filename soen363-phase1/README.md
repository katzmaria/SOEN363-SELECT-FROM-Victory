# SOEN 363 — Project Phase 1: Hospital Management System

Relational database (SQLite) for the Phase 1 hospital scenario: schema, synthetic
dataset, and the 20 Task 3 queries.

> Keep this repository **private**. It contains the course handout and graded work.

## Layout

```
.
├── db/
│   ├── schema.sql            # Task 2 — all CREATE TABLE statements
│   └── hospital.db           # the dataset the report's query outputs come from
├── data/
│   ├── build_db.py           # rebuilds db/hospital.db: runs both generators in order
│   ├── generate_data.py      # schema + core data (patients, admissions, triage, unit stays)
│   ├── generate_clinical_data.py  # ICD-9, diagnoses, orders, radiology, surgery, notes, discharges
│   └── icd9_dictionary.csv   # ICD-9 codes loaded into ICD9Dictionary
├── queries/
│   └── q01.sql … q20.sql     # Task 3 — one file per query
├── scripts/
│   ├── run_queries.py        # runs the queries, saves results to output/
│   └── check_data.py         # checks the dataset against the handout's data rules
├── docs/
│   └── er-diagram/           # Task 1 — diagram export (PNG) + .drawio source
└── output/                   # generated query results (git-ignored)
```

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Common commands

All commands are run from the repo root.

| What | Command |
|---|---|
| Rebuild the database from scratch | `python data/build_db.py` |
| Check data integrity | `python scripts/check_data.py` |
| Run every written query | `python scripts/run_queries.py` |
| Run specific queries | `python scripts/run_queries.py 1 6 14` |

`build_db.py` deletes and recreates `db/hospital.db`. With `faker==40.39.0`
it reproduces the committed database exactly, so everyone gets the same query
results. If you change either generator, commit the new `hospital.db` with it so
the report outputs stay in sync.

You can also open `db/hospital.db` directly in DB Browser for SQLite or DBeaver.

## Deliverables

| Task | Item | Owner | Status |
|---|---|---|---|
| 1 | ER diagram | Sam (P1) | PNG exported; `.drawio` source missing |
| 2 | Schema (`db/schema.sql`) | Kerry (P2) | Done |
| 2 | Dataset — Patient, Admission, Triage, Professional, UnitStay | Kerry (P2) | Done |
| 2 | Dataset — ICD9Dictionary, Diagnosis, ClinicalNote, DiagnosticOrder, RadiologyExamination, SurgicalProcedure, DischargeRecord | Maria-Christine (P3) | Done |
| 4 | Report (PDF) | Maria Celena (P5) | Done |

## Queries

| # | Topic | Owner | Status |
|---|---|---|---|
| 1 | High-priority emergency patients at triage | Kerry (P2) | Written |
| 2 | Patients with more than three admissions | Kerry (P2) | Written |
| 3 | Discharged without surgery | Maria-Christine (P3) | Written |
| 4 | Radiology + surgery, same admission | Maria-Christine (P3) | Written |
| 5 | ICU/CCU stays over seven days | Vanessa (P4) | Written |
| 6 | Admission count per patient (incl. zero) | Kerry (P2) | Written |
| 7 | ED → ICU/CCU, same admission | Vanessa (P4) | Written |
| 8 | Most frequent primary ICD-9 with ICU/CCU stay | Maria Celena (P5) | Written |
| 9 | Average length of stay per critical care unit | Vanessa (P4) | Written |
| 10 | Surgery before ICU/CCU entry | Kerry (P2) | Written |
| 11 | Radiology exam count per patient (incl. zero) | Maria Celena (P5) | Written |
| 12 | Discharge note containing "recovery" | Maria-Christine (P3) | Written |
| 13 | Radiology but no ICU/CCU stay | Maria Celena (P5) | Written |
| 14 | Longest completed hospital stay | Kerry (P2) | Written |
| 15 | Unit transfers per patient | Vanessa (P4) | Written |
| 16 | More than one critical care unit type | Vanessa (P4) | Written |
| 17 | More than one distinct ICD-9 per admission | Maria-Christine (P3) | Written |
| 18 | Latest clinical note per patient | Maria Celena (P5) | Written |
| 19 | Deaths during hospital stay | Maria-Christine (P3) | Written |
| 20 | Surgery and radiology on the same day | Maria Celena (P5) | Written |

## Conventions

- One query per file, starting with `-- Query N`, the question as a comment, then the SQL.
- Update the tables above when you pick up or finish something.
- Commit schema changes and the regenerated `hospital.db` together.
