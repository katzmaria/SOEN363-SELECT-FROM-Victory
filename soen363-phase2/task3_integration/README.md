# Task 3: Integrate the sources and refine the schema

Handout section 6 - rubric: 20 points (integration, identifier mapping, justified schema revisions).

- Map the clean data of all four sources (`output/clean/`) onto one schema based on the Phase 1 database.
- Revise tables, keys, data types and constraints where needed; explain the problem each change solves.
- Identifier management: global surrogate keys + a mapping from the source IDs (patient 125 in A is not patient 125
  in B); update every foreign key; never merge patients only by name; keep uncertain matches separate.
- Traceability: for every record keep the source, the continent, the original ID and the integrated ID
  (every clean row already has `source_system` and `source_record_id`).
- Deliver: the updated SQL schema and a written description of the changes (ER diagram optional, handout section 10).

Code for this task goes in this folder. To show its results like Tasks 1 and 2, add it to `TASKS` in `show_tables.py`.

## How to run

    python -m task3_integration.integrate      # or: python show_tables.py --task 3

Reads `output/clean/`, writes `output/integrated/hospital.db`, `id_mapping.csv` and `patient_match_candidates.csv`.

## Schema changes (`schema.sql`) and the problem each one solves

| Change | Integration problem | How it resolves it |
|---|---|---|
| Global surrogate keys on every table, assigned in a fixed order (sources A→D, parents before children) | Every source numbers its records from 1, so `patient_id = 1` is four different people | One key space for the whole database; rerunning gives the same keys |
| `IdMapping(entity_type, source_system, source_local_id, source_record_id, integrated_id)` | Need to trace each record back to its source and rewrite foreign keys | `source_local_id` is what the clean files' FKs use, so every FK is rewritten by looking up `(parent, row's own source, local id)`; `source_record_id` keeps the raw ID (e.g. `P000001`); the continent comes from joining `SourceSystem` |
| `integrated_id` not unique in `IdMapping` | A merged patient comes from several source records | Each source record keeps its own mapping row pointing at the same patient |
| `source_system` / `source_record_id` removed from `Patient` | A merged patient has more than one source | The sources live in `IdMapping`; the other tables keep the columns because their records are never merged (1:1) |
| New `PatientMatchCandidate` | Uncertain matches must be kept separately, not merged | Each candidate pair is stored with its rule, evidence and decision; a CHECK ensures `merged` pairs share one patient and `uncertain` pairs do not |
| `SourceSystem` rows loaded from `common/standards.py` | Continent of origin required | Stored once per source instead of on every row |

## Patient matching rules

Cross-source only (Task 2 already removed duplicates within a source). Comparison after lowercasing, removing
accents and punctuation; phones as digits without country code or trunk 0.

| Rule | Condition | Decision |
|---|---|---|
| `NAME_DOB_SEX_CONTACT` | same first + last name, date of birth, sex, **and** same phone or address | merged (the record from the earliest source survives; empty fields filled from the others) |
| `NAME_DOB` | same first + last name and date of birth, nothing else agrees | uncertain, kept separate |
| `LASTNAME_DOB` | same last name and date of birth, different first name | uncertain, kept separate |
| `NAME_DOB_NEAR` | same first + last name, date of birth one day apart or day/month swapped | uncertain, kept separate |
| — | anything else, including the same name alone | not a match |

Healthcare professionals are never merged across sources: the hospitals are on different continents.

Result on the current data: no pairs meet any rule, so 0 merges and 0 uncertain candidates (2,251 patients).

## Admission status fix

Task 2 keeps 95 admissions marked `discharged`/`deceased` with no discharge time (flag `status_inconsistent`), which
the schema's status CHECK rejects. If the same source has a discharge record for the admission (88), its time is
used; otherwise (7) the status is set to unknown (NULL). Both are noted in `quality_flags`.
