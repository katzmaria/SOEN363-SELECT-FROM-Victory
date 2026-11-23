# Task 6: Demonstrate the integrated database

Handout section 9. Rubric: part of the demonstration and documentation criteria.

- SQL queries and results: patient and admission counts by source and continent; admissions by standardized type
  across continents; most frequent primary ICD-9 by continent; average completed stay by continent; evidence that
  duplicate source IDs were resolved; integrity checks for orphans and invalid chronology.
- Distinguish source-record counts from integrated-entity counts.
- Rerun the 20 Phase 1 queries on the integrated database (adapt only where the schema changed); explain empty
  results or big changes.

## How to run

    python -m task6_demo.run_demo        # or: python show_tables.py --task 6   (Figures 49 onward)

Needs `output/integrated/hospital.db` (Task 4, or `python run_all.py`). The database is opened read-only. Every query
is one file in `queries/`; the full result of each one is written to `output/demo/<id>.csv`, and
`output/demo/summary.csv` lists the Phase 1 row count, the new row count and the explanation of each Phase 1 query.

## The six demonstration queries (`queries/demo_*.sql`)

| Handout item | File | What it shows |
|---|---|---|
| 1. Patient and admission counts by source and continent | `demo_1.sql` | Source records and integrated entities side by side: A 475 / B 653 / C 475 / D 648 patients (2,251 integrated) and 3,007 admissions. They are equal because no cross-source patient merged (see below) |
| 2. Admissions by standardized admission type | `demo_2.sql` | The five common types by continent |
| 3. Most frequent primary ICD-9 by continent | `demo_3.sql` | Top 3 per continent, with the official title; ties broken by code |
| 4. Average completed admission duration | `demo_4.sql` | Days, by continent (completed = discharged or deceased with a discharge time) |
| 5. Duplicate source identifiers resolved | `demo_5a.sql`, `demo_5b.sql` | Local patient 1, 2, 3 in the four sources get different integrated IDs; 651 patient local IDs and 826 admission local IDs are used by more than one source; 0 admissions point at a patient of another source |
| 6. Orphans and invalid chronology | `demo_6.sql` | 16 checks, all PASS (0 violations) |

Source-record counts and integrated counts are the same here because the Task 3 matching rules found no cross-source
patient pair (0 merged, 0 uncertain). The queries still count them separately, so they would differ if a merge occurred.

## The 20 Phase 1 queries (`queries/q01.sql` to `q20.sql`)

Each file keeps the Phase 1 question and logic and only renames columns. The first two comment lines say what was
renamed. The Phase 1 database had 60 patients and 124 admissions, the integrated one has 2,251 patients and 3,007
admissions, so most results are larger. That alone is not an error.

| Phase 1 column | Integrated column |
|---|---|
| `admission_date_time`, `discharge_date_time` | `admit_time`, `discharge_time` |
| `final_admission_status` | `admission_status` |
| `triage_priority_level` | `triage_priority` |
| `contents`, `creation_date_time` (ClinicalNote) | `note_text`, `note_time` |
| `examination_id`, `examination_date_time`, `examination_type` | `exam_id`, `exam_time`, `exam_type` |
| `procedure_type`, `procedure_date_time` | `procedure_name`, `procedure_time` |
| `unit_stay_id`, `entry_date_time`, `exit_date_time` | `stay_id`, `entry_time`, `exit_time` |
| `condition_at_discharge` | `discharge_condition` |

Timestamps are now ISO 8601 UTC text (`2025-03-14T16:11:00Z`); `JULIANDAY` and `DATE` accept this format, so no query
needed another change.

### Results that changed notably (full list with every query: Figure 56 or `output/demo/summary.csv`)

- **Q5 is empty (14 rows in Phase 1).** No critical-care stay in the integrated database lasts more than 6.2 days
  (CCU 6.2, ICU 5.9, MICU 5.9, SICU 6.0), while Phase 1 had stays up to 16.5 days. The synthetic Phase 2 sources
  contain shorter critical-care stays, and no Task 2 rejection reason concerns stay length.
- **Q6, Q11, Q15 return 2,251 rows**: one per integrated patient, including 167 patients with no admission (shown
  with 0 where the query keeps them).
- **Q14 returns 3 patients** instead of 1: three admissions tie at 432 hours (18 days) and the query keeps ties.
- **Q19 returns 63 rows**: 73 deceased admissions have a discharge record, and the query also needs a primary
  diagnosis, which 10 of them lack (the Task 5 limitation).
- **Q8** gives the same top diagnosis (410.9); admissions without a primary diagnosis cannot be counted.
- **Q9** gives averages of 2.0 to 2.4 days (2.5 to 4.2 in Phase 1).

Owners from Phase 1 (each member checks the output of their own queries): Kerry Q1, Q2, Q6, Q10, Q14;
Maria-Christine Q3, Q4, Q12, Q17, Q19; Vanessa Q5, Q7, Q9, Q15, Q16; Maria Celena Q8, Q11, Q13, Q18, Q20.

## Output files

| Path | Content |
|---|---|
| `output/demo/demo_*.csv`, `output/demo/qNN.csv` | Full result of each query |
| `output/demo/summary.csv` | Query, owner, rows in Phase 1, rows now, explanation |
| `output/tables/task6_tables.txt` | The tables printed by `show_tables.py --task 6` |
