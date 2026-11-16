# SOEN 363 Project Phase 2: Multi-Source Hospital Data Integration

Phase 2 takes four independent hospital data sources, one per continent, and turns them into one clean, integrated SQL
database. Each source has its own file format, language, identifiers, date formats, units and data-quality problems.

## Team and tasks

| Task | Who | Folder | Status |
|---|---|---|---|
| Synthetic source data (A–D) and data contract | Samuel Richard (B, D, contract), Maria-Christine Catiche (A, C) | `data/raw/`, `generator/`, `docs/` | Done |
| Task 1: Inspect and load the data | Maria-Christine Catiche | `task1_load_profile/` | Done |
| Task 2: Clean and standardize the data | Maria-Christine Catiche | `task2_clean/` | Done |
| Task 3: Integration and schema refinement | To be decided | `task3_integration/` | Not started |
| Task 4: Import into the SQL database | To be decided | `task4_import/` | Not started |
| Task 5: Integrity enforcement and validation | To be decided | `task5_validation/` | Not started |
| Task 6: Demonstration of the integrated database | To be decided | `task6_demo/` | Not started |
| Report assembly and submission | To be decided | Google Doc | Not started |

Each task folder for Tasks 3 to 6 has a `README.md` with that task's requirements from the handout.

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

Python 3.9 or newer, **standard library only**: nothing to install (no pandas). Run from the `soen363-phase2` folder.

| Command | What it does |
|---|---|
| `python run_all.py` | Runs Task 1 and Task 2 and writes every result to `output/` |
| `python show_tables.py --task 1` | Runs Task 1 and prints its result tables (Figures 1–17) in the terminal |
| `python show_tables.py --task 2` | Runs Task 2 and prints its result tables (Figures 18–35) |
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
├── run_all.py                  runs Task 1 and Task 2
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
├── task3_integration/          Task 3 (README.md with the requirements)
├── task4_import/               Task 4
├── task5_validation/           Task 5
├── task6_demo/                 Task 6
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
| `output/tables/task<N>_tables.txt` | 1, 2 | The result tables printed by `show_tables.py` |

Task 3 starts from `output/clean/`.

## Adding Tasks 3 to 6

Put the task's code in its folder, then add it to `TASKS` in `show_tables.py` (the comment there explains the three
steps). `python show_tables.py --task K` then runs it and prints its tables the same way as Tasks 1 and 2.
