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
│   └── generate_data.py      # builds db/hospital.db from schema.sql (Faker, seeded)
├── queries/
│   └── q01.sql … q20.sql     # Task 3 — one file per query
├── scripts/
│   ├── run_queries.py        # runs the queries, saves results to output/
│   └── check_data.py         # checks the dataset against the handout's data rules
├── docs/
│   ├── er-diagram/           # Task 1 — export the diagram here (PNG/PDF + source file)
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
| Rebuild the database from scratch | `python data/generate_data.py` |
| Check data integrity | `python scripts/check_data.py` |
| Run every written query | `python scripts/run_queries.py` |
| Run specific queries | `python scripts/run_queries.py 1 6 14` |

`generate_data.py` deletes and recreates `db/hospital.db`. With `faker==40.39.0`
it reproduces the committed database exactly, so everyone gets the same query
results. If you change the generator, commit the new `hospital.db` with it so the
report outputs stay in sync.

You can also open `db/hospital.db` directly in DB Browser for SQLite or DBeaver.

## Deliverables

| Task | Item | Owner | Status |
|---|---|---|---|
| 1 | ER diagram | TBD | Not started |
| 2 | Schema (`db/schema.sql`) | Person 2 | Draft |
| 2 | Dataset — Patient, Admission, Triage, Professional, UnitStay, SurgicalProcedure | Person 2 | Draft |
| 2 | Dataset — ICD9Dictionary, Diagnosis, ClinicalNote, DiagnosticOrder, RadiologyExamination, DischargeRecord | TBD | Not started |
| 4 | Report (PDF) | TBD | Not started |

## Queries

| # | Topic | Owner | Status |
|---|---|---|---|
| 1 | High-priority emergency patients at triage | Person 2 | Written |
| 2 | Patients with more than three admissions | Person 2 | Written |
| 3 | Discharged without surgery | TBD | — |
| 4 | Radiology + surgery, same admission | TBD | — |
| 5 | ICU/CCU stays over seven days | TBD | — |
| 6 | Admission count per patient (incl. zero) | Person 2 | Written |
| 7 | ED → ICU/CCU, same admission | TBD | — |
| 8 | Most frequent primary ICD-9 with ICU/CCU stay | TBD | — |
| 9 | Average length of stay per critical care unit | TBD | — |
| 10 | Surgery before ICU/CCU entry | Person 2 | Written |
| 11 | Radiology exam count per patient (incl. zero) | TBD | — |
| 12 | Discharge note containing "recovery" | TBD | — |
| 13 | Radiology but no ICU/CCU stay | TBD | — |
| 14 | Longest completed hospital stay | Person 2 | Written |
| 15 | Unit transfers per patient | TBD | — |
| 16 | More than one critical care unit type | TBD | — |
| 17 | More than one distinct ICD-9 per admission | TBD | — |
| 18 | Latest clinical note per patient | TBD | — |
| 19 | Deaths during hospital stay | TBD | — |
| 20 | Surgery and radiology on the same day | TBD | — |

## Conventions

- One query per file, starting with `-- Query N`, the question as a comment, then the SQL.
- Update the tables above when you pick up or finish something.
- Commit schema changes and the regenerated `hospital.db` together.
