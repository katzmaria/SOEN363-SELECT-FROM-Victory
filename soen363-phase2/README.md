# SOEN 363 Project Phase 2: Multi-Source Hospital Data Integration

Phase 2 takes four independent hospital data sources, one per continent, and turns them into one clean, integrated SQL
database. Each source has its own file format, language, identifiers, date formats, units and data-quality problems.

Report (Google Doc): https://docs.google.com/document/d/1iXljZzHY5cRejdzYDqD--PLoNmUBPs-2YIBLBFgsMjM/edit

## Team and tasks

| Task | Who | Folder | Status |
|---|---|---|---|
| Synthetic source data (A–D) and data contract | Samuel Richard (B, D, contract), Maria-Christine Catiche (A, C) | `data/raw/`, `generator/`, `docs/` | Done |
| Task 1: Inspect and load the data | Maria-Christine Catiche | `task1_load_profile/` | Done |
| Task 2: Clean and standardize the data | Maria-Christine Catiche | `task2_clean/` | Done |
| Task 3a: Schema revisions (tables, keys, types, constraints, ER diagram) | Vanessa Cherbaka | `task3_integration/schema.sql` | Done |
| Task 3b: Identifier management and traceability (global IDs, mapping, patient matching) | Maria Celena Said | `task3_integration/` | Done |
| Task 4: Import into the SQL database | Samuel Richard | `task4_import/` | Done |
| Task 5: Integrity enforcement and validation | Kigham Kerry Kinyuy | `task5_validation/` | Done (code, README and outputs; text for the shared report not yet pasted) |
| Task 6: Demonstration of the integrated database | Kigham Kerry Kinyuy | `task6_demo/` | Drafted (6 demo queries + 20 Phase 1 queries; report text not pasted) |
| Report assembly and submission | Samuel Richard (document format: Maria-Christine Catiche) | Google Doc | In progress (Phase 2 Tasks 1–4 written) |
| Rerunning the Phase 1 queries on the integrated database | Each member reruns their own Phase 1 queries | `task6_demo/` | Drafted for all 20; owners to check their own |

Each task folder for Tasks 3 to 6 has a `README.md` with that task's requirements from the handout; the Task 3, 4 and
5 READMEs also explain how the task was done.

## The four sources

| Source | Continent | Hospital (fictional) | Format | Raw files | Time zone |
|---|---|---|---|---|---|
| A | Europe | CHU de Montclair-sur-Loire | TXT, pipe-delimited, French names | `data/raw/A_txt/` (11 files) | Europe/Paris |
| B | Africa | Uganda National Hospital | CSV | `data/raw/B_csv/` (11 files) | Africa/Kampala |
| C | Asia | Straits Regional Medical Centre | XML | `data/raw/C_xml/hospital_records.xml` | Asia/Singapore |
| D | Oceania | Coral Coast Health Service | JSON (nested) | `data/raw/D_json/` (4 files) | Australia/Sydney |

All data is synthetic and fictional. Every source covers the same 11 entities: professionals, patients, admissions,
triage, diagnoses, clinical notes, orders, radiology, procedures, unit stays and discharges. The shared rules for the
sources are in `docs/contract.md`. How generative AI was used to create the data (the only use the handout allows) is
recorded in `docs/ai_disclosure.md` and `docs/ai_prompts/`.

## How to run

Python 3.10 or newer, **standard library only**: nothing to install (no pandas). Run from the `soen363-phase2` folder.

| Command | What it does |
|---|---|
| `python run_all.py` | Runs Tasks 1 to 5 and writes every result to `output/` (about 10 seconds) |
| `python show_tables.py --task 1` | Runs Task 1 and prints its result tables (Figures 1–17) in the terminal |
| `python show_tables.py --task 2` | Runs Task 2 and prints its result tables (Figures 18–35) |
| `python show_tables.py --task 3` | Runs Task 3 and prints its tables (Figures 36–39) |
| `python show_tables.py --task 4` | Runs Task 4 and prints its tables (Figures 40–41) |
| `python show_tables.py --task 5` | Runs Task 5 (validation checks and negative tests) and prints its tables (Figures 42–48) |
| `python show_tables.py --task 6` | Runs the demonstration and Phase 1 queries and prints their tables (Figures 49 onward) |
| `python show_tables.py --task 2 --no-run` | Prints the Task 2 tables of the last run, without running again |
| `python show_tables.py --list` | Lists every figure and the task it belongs to |
| `python show_tables.py 12 13 --no-run` | Prints only Figures 12 and 13 |

The ICD-9 dictionary is read from `../soen363-phase1/data/icd9_dictionary.csv` (change it with `--icd9 <path>`).
`--sources A B` runs only some sources.

Both scripts first check that every code file is the current version. If one is outdated or missing, or a raw data
file is not where it should be, they name the file and stop. The tables are also saved to
`output/tables/task<N>_tables.txt`, which is easier to read than a long terminal.

## Folder structure

```
soen363-phase2/
├── run_all.py                  runs Tasks 1 to 5
├── show_tables.py              runs a task and prints its result tables
├── common/                     code shared by every task
│   ├── standards.py            the target model: source settings, column mappings, field levels, label maps
│   ├── parsers.py              dates and time zones, numbers, units, ICD-9 codes, phone numbers, names
│   └── tabular.py              reading and writing CSV tables
├── task1_load_profile/         Task 1: inspect and load the data
│   ├── load_sources.py         one loader per format (TXT, CSV, XML, JSON)
│   ├── profile_sources.py      record counts, field profile, format differences, invalid values, duplicates
│   └── tables.py               the Task 1 result tables
├── task2_clean/                Task 2: clean and standardize the data
│   ├── clean_sources.py        the cleaning rules, duplicates, relationships, quarantine
│   ├── cleaning_report.py      writes output/cleaning_report.md
│   └── tables.py               the Task 2 result tables
├── task3_integration/          Task 3: integrate the sources and refine the schema
│   ├── schema.sql              the integrated schema (15 tables, 8 triggers)
│   ├── integrate.py            global keys, IdMapping, foreign-key rewriting, patient matching
│   └── tables.py               the Task 3 result tables
├── task4_import/               Task 4: import into the SQL database
│   ├── import_db.py            parents-first load in one transaction, checks, atomic rebuild
│   └── tables.py               the Task 4 result tables
├── task5_validation/           Task 5: enforce and validate data integrity
│   ├── validate.py             the 118 validation checks on hospital.db (read-only)
│   ├── negative_tests.py       16 attempts to break the rules, on a copy of the database
│   └── tables.py               the Task 5 result tables
├── task6_demo/                 Task 6: demonstrate the integrated database
│   ├── run_demo.py             runs the queries read-only, writes output/demo/
│   ├── queries/                demo_1 to demo_6 (handout) and q01 to q20 (Phase 1, adapted)
│   └── tables.py               the Task 6 result tables
├── data/raw/                   the four raw sources (A_txt, B_csv, C_xml, D_json)
├── generator/                  the script that generated the synthetic data
├── docs/                       data contract and generative AI disclosure
└── output/                     everything the pipeline writes (rebuilt on every run)
```

## What Tasks 1 and 2 do

**Task 1, inspect and load.** Each source is read with its own loader into the same in-memory structure, keeping the
original text of every value. Records that cannot be read (broken lines, wrong field count, invalid XML or JSON
elements) are counted as malformed and kept for review, not dropped silently. The profile then compares the sources:
record counts per entity, field types and missing values, format differences (dates, units, codes, labels), invalid
values and duplicates.

**Task 2, clean and standardize.** Every record is mapped to one common target model:

- **Field levels:** a missing required field rejects the record, a missing expected field becomes NULL and is flagged,
  and a missing optional field becomes NULL.
- **Dates:** every date and time is parsed with that source's conventions and converted to UTC. Ambiguous dates (for
  example `03-04-2025` where both orders are possible) and years outside 1900–2100 are rejected.
- **Units and codes:** Fahrenheit becomes Celsius, SpO2 fractions become percentages, ICD-9 codes are normalized and
  checked against the dictionary, and phone numbers are converted to E.164.
- **Labels and text:** local labels (French, abbreviations, other spellings) are mapped to one vocabulary, and names
  with broken capitalization are fixed.
- **Duplicates:** exact copies are removed, and near-duplicates (same entity key, no conflicting values) are merged.
  Records whose values conflict are kept apart and flagged.
- **Relationships:** entities are processed parents first. A child whose parent was rejected is rejected too (cascade),
  and events outside their admission's dates fail the chronology checks.

Every rejected record goes to `output/quarantine/` with its original values and the reason. Every change is written to
`output/cleaning_log/`.

## What Tasks 3 to 5 do

**Task 3, integrate.** Every clean record gets a global surrogate key, recorded in `IdMapping` with its source and
original ID, and every foreign key is rewritten through that mapping. Patients are matched across sources with fixed
rules and uncertain matches are kept apart. Details: `task3_integration/README.md`.

**Task 4, import.** The integrated rows are loaded into `output/integrated/hospital.db`, parents first, with
parameterized inserts in one transaction. A rerun rebuilds the database and swaps it in only after every check
passed. Details: `task4_import/README.md`.

**Task 5, enforce and validate.** The schema gets NOT NULL on the two text primary keys and 8 triggers for the rules a CHECK
cannot express (radiology and procedures inside the admission, discharge record only on a completed admission).
`validate.py` then runs 118 checks on the imported database (106 PASS, 0 FAIL, 4 WARNING, 8 LIMITATION) and
`negative_tests.py` tries 16 changes on a copy of it (15 must be rejected, 1 valid control accepted). Unresolved
limitations, such as 295 completed admissions without a primary diagnosis, are reported, not repaired. Details:
`task5_validation/README.md`.

## Output files

| Path | Task | Content |
|---|---|---|
| `output/profile/*.csv` | 1 | Record counts, field profile, format differences, invalid values, duplicates, malformed records |
| `output/profile_report.md` | 1 | The profile as a readable report |
| `output/clean/*.csv` | 2 | The clean records, one file per entity, all sources together (`source_system` and `source_record_id` on every row) |
| `output/quarantine/*.csv` | 2 | Rejected records with their raw values and the reason |
| `output/cleaning_log/summary.csv` | 2 | Per source and entity: read, malformed, duplicates removed and merged, rejected, clean |
| `output/cleaning_log/cleaning_log.csv` | 2 | Every individual change made to a value |
| `output/cleaning_log/label_mappings.csv` | 2 | Every label mapping used (local value to standard value) |
| `output/cleaning_report.md` | 2 | The cleaning rules and results as a readable report |
| `output/integrated/hospital.db` | 3, 4 | The integrated SQLite database (git-ignored; rebuilt by every run) |
| `output/integrated/id_mapping.csv` | 3 | Every source record and the integrated ID it was given |
| `output/integrated/patient_match_candidates.csv` | 3 | Cross-source patient match candidates and their decision |
| `output/integrated/import_log.csv` | 4 | Rows and checksum per table, compared with the previous run |
| `output/validation/validation_results.csv` | 5 | One row per validation check: rule, enforced by, severity, violations, status |
| `output/validation/violations_sample.csv` | 5 | The first 20 offending rows of every check that is not PASS |
| `output/validation/negative_tests.csv` | 5 | Each attempt to break a rule, and the error the database returned |
| `output/tables/task<N>_tables.txt` | 1–5 | The result tables printed by `show_tables.py` |

Task 3 starts from `output/clean/`; Task 5 starts from `output/integrated/hospital.db`.

## Adding Task 6

Put the task's code in its folder, then add it to `TASKS` in `show_tables.py` (the comment there explains the three
steps). `python show_tables.py --task K` then runs it and prints its tables the same way as Tasks 1 and 2.
