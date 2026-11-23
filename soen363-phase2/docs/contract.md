# Our data contract

This was the plan the team agreed before the pipeline was written. Sections 1 and 4 to 7 still hold. Where the final
pipeline differs from sections 2, 3, 5 and 8, the differences are listed here, and the code and its output are the
reference.

## 0. What the final pipeline does differently

| Topic | In this plan | In the final pipeline |
|---|---|---|
| Clean files | `data/clean/<source>_<table>.csv`, one file per source and table | `output/clean/<entity>.csv`, one file per entity with all four sources together (`admissions.csv`, `patients.csv`, ...) |
| Source columns | `source_id`, `source_record_id` at the end | `source_system`, `source_record_id` at the start of every row, plus a `quality_flags` column |
| Column names | Same as the Phase 1 schema | The names of the integrated schema (`task3_integration/schema.sql`), for example `admit_time`, `discharge_time`, `admission_status`, `triage_priority`, `exam_status`, `note_text` |
| Timestamps | `YYYY-MM-DD HH:MM:SS` in UTC | ISO 8601 in UTC with a `T` and a `Z`, for example `2024-05-08T12:59:00Z`; the source time zone is kept in `source_timezone` |
| Rejected records | `data/rejected/<source>_rejected.csv`, reason codes such as `BROKEN_REFERENCE` | `output/quarantine/<entity>.csv` with `source_system`, `entity`, `source_record_id`, `source_row`, `disposition`, `duplicate_of`, `reason_codes`, `reason_details`, `raw_record`; reason codes are lower case, for example `orphan_reference`, `chronology`, `near_duplicate`, `unknown_icd9_code`, `unmappable_label` |
| Unreadable records | Rejected as `MALFORMED` | Logged in `output/profile/malformed_records.csv` and `output/quarantine/malformed_records.csv` |
| Duplicates | The first record is kept, the rest are rejected as `DUPLICATE` | The lowest id is kept, its empty fields are filled from the duplicate, references are re-pointed, and the removed copy is logged with `duplicate_of` |
| Identifiers | Source owners keep local IDs | Task 3 assigns global IDs and records every source ID in `IdMapping` (see `task3_integration/README.md`) |

## 1. Sources

| Source | Format | Continent | Hospital system name | Source time zone | Owner |
|---|---|---|---|---|---|
| A | TXT | Europe | CHU de Montclair-sur-Loire | Europe/Paris | Maria-Christine |
| B | CSV | Africa | Uganda National Hospital | Africa/Kampala (UTC+3, no DST) | Samuel |
| C | XML | Asia | Straits Regional Medical Centre | Asia/Singapore (UTC+8, no DST) | Maria-Christine |
| D | JSON | Oceania | Coral Coast Health Service | Australia/Sydney (UTC+10/+11, has DST) | Samuel |

## 2. Cleaned output files

- One CSV per entity per source, named `data/clean/<source>_<table>.csv` with the table name in snake_case (e.g. `B_admission.csv`, `B_unit_stay.csv`).
- UTF-8, comma-delimited, with a header row. Quote a value if it has a comma, quote or newline in it.
- Use the same column names and order as the matching table in `../soen363-phase1/db/schema.sql`, then add `source_id` and `source_record_id` at the end (see section 5).
- A column is required if it's `NOT NULL` in the schema, otherwise it's optional. If a record is missing a required value, it goes in the rejection file (section 8). Don't make up a value to get it through.
- Nobody makes their own ICD-9 dictionary. All diagnoses use codes from the shared one in section 6.

| Table | File | Primary key | Foreign keys | Notable constraints |
|---|---|---|---|---|
| HealthcareProfessional | `<source>_healthcare_professional.csv` | professional_id | none | name, role NOT NULL |
| Patient | `<source>_patient.csv` | patient_id | none | full_name, date_of_birth NOT NULL; life_status is alive or deceased (default alive) |
| Admission | `<source>_admission.csv` | admission_id | patient_id, admitting_professional_id | admission_type, reason_for_admission NOT NULL; discharge after admission |
| TriageAssessment | `<source>_triage_assessment.csv` | assessment_id | admission_id, performing_professional_id | pain_level 0-10; triage_priority_level NOT NULL |
| Diagnosis | `<source>_diagnosis.csv` | diagnosis_id | patient_id, admission_id, icd9_code, diagnosing_professional_id | patient_id has to match the admission's patient; if it doesn't, reject as `BROKEN_REFERENCE` |
| ClinicalNote | `<source>_clinical_note.csv` | note_id | admission_id, authoring_professional_id | note_type, contents NOT NULL |
| DiagnosticOrder | `<source>_diagnostic_order.csv` | order_id | admission_id, requesting_professional_id | clinical_reason, order_status, priority NOT NULL |
| RadiologyExamination | `<source>_radiology_examination.csv` | examination_id | admission_id, order_id (nullable), referring_professional_id, technician_professional_id | examination_type NOT NULL; during the admission |
| SurgicalProcedure | `<source>_surgical_procedure.csv` | procedure_id | admission_id, performing_professional_id | procedure_type, procedure_date_time NOT NULL; during the admission |
| UnitStay | `<source>_unit_stay.csv` | unit_stay_id | admission_id, responsible_professional_id | exit after entry |
| DischargeRecord | `<source>_discharge_record.csv` | discharge_id | admission_id (UNIQUE), authorizing_professional_id | one per admission; has to agree with the admission status; if it doesn't, reject as `CHRONOLOGY` |

## 3. Formats

- Timestamps: `YYYY-MM-DD HH:MM:SS` in UTC. Convert from the source's time zone (section 1). We went with UTC because two sources (Europe/Paris and Australia/Sydney) have daylight saving time, which repeats an hour once a year.
- Dates with no time (date_of_birth): `YYYY-MM-DD`, no conversion.
- Ambiguous dates: if a date could be read two ways (e.g. `03/04/2025` in a source that mixes day-first and month-first), reject it as `AMBIGUOUS_DATE` instead of guessing.
- Missing values: leave the field empty so it loads as NULL. Placeholders like `N/A`, `null`, `-`, `?`, `none`, `0000-00-00` or `-1` should be turned into empty fields too. Don't write the word `NULL`.
  - Exception: in `known_allergies` and `current_medications`, "none" (or "no known allergies", "NKA", etc.) is real information, meaning the patient has none. Keep it as `none`. Only leave those fields empty when the value is actually unknown.
- Whitespace: trim both ends and collapse multiple spaces into one.
- Capitalization:
  - Names in title case (`mary o'neil` → `Mary O'neil`). Handle any special cases in the cleaning code, not by editing the output by hand, because the cleaning has to be rerunnable.
  - Category values exactly as listed in section 4.
  - Free text (notes, findings, reasons) stays as is, just trimmed.
- Units:
  - Temperature in Celsius, 1 decimal. From Fahrenheit: `(F - 32) * 5/9`.
  - Heart rate and respiratory rate per minute, as integers.
  - Oxygen saturation as an integer percent, 0-100.
  - Blood pressure as `systolic/diastolic` in mmHg, e.g. `120/80`.
  - Pain level as an integer, 0-10.
- Invalid numbers (temperature of 300, pain level 14, negative heart rate, etc.): blank it out if the column is optional, reject the record if it's required.

## 4. Standard category values

These have to match the CHECK constraints in the schema exactly. Map your source's labels to these.

| Column | Allowed values |
|---|---|
| Admission.admission_type | emergency, urgent, elective, outpatient, newborn |
| Admission.final_admission_status | active, discharged, deceased |
| Patient.life_status | alive, deceased |
| TriageAssessment.triage_priority_level | low, medium, high |
| UnitStay.unit_type | Emergency Department, ICU, CCU, MICU, SICU, General Ward |
| DiagnosticOrder.order_status | pending, in_progress, completed, cancelled |
| DiagnosticOrder.priority | routine, urgent, stat |
| RadiologyExamination.examination_status | scheduled, completed, cancelled |
| Diagnosis.diagnosis_type | primary, secondary |

If you can't tell which value a label should map to, reject it as `UNMAPPED_CATEGORY`.

## 5. Identifiers

Different sources can use the same local IDs (patient 125 in A isn't patient 125 in B), so the cleaned files keep the local IDs and add two columns to every row:

- `source_id`: `A`, `B`, `C` or `D`.
- `source_record_id`: the original ID from the raw file, as text, unchanged.

Other rules:

- Primary and foreign key columns keep the local IDs. Source owners don't create global IDs.
- The schema's keys are INTEGER. If a raw ID isn't just a number (e.g. `UG-0125`), put the numeric part in the key column (`125`) and the full ID in `source_record_id`. Same for foreign keys. If that makes two IDs in the same file collide, use some other rule (in code) and write down what you did.
- `(source_id, source_record_id)` has to be unique in each file.
- During integration, the integration lead assigns global surrogate keys, updates the foreign keys to match, and keeps a mapping table (source, continent, original ID, integrated ID). The integration lead can change this design if needed.
- Patients from different sources aren't merged just because the names match. If we do any cross-source matching, the integration lead documents the rules and keeps uncertain matches separate.

## 6. ICD-9 dictionary

- Shared file: `../soen363-phase1/data/icd9_dictionary.csv` (columns `icd9_code, official_title, description, disease_category`).
- Codes are text, written exactly like in the dictionary, including leading zeros and the decimal point (e.g. `038.9`, `250.00`). Don't load them as numbers or `038.9` turns into `38.9` and won't match.
- When generating your data, only use codes from the dictionary, plus a few fake ones on purpose (around 1% of diagnoses) to test rejection. Paste the list of codes into the prompt, otherwise the AI will make up codes and most of them will get rejected.
- When cleaning, get the source code into the dictionary's format before looking it up (trim, uppercase any V/E prefix, add back the decimal point and leading zeros). Only accept the result if exactly one dictionary code matches. For example `4019` can only be `401.9`, but a bare `389` could be `038.9` or something else, so reject it. If there's no match or more than one, reject it as `UNKNOWN_ICD9`.

## 7. Data-quality problems every source must include

Most records need to survive cleaning, so we're keeping the problems that cause rejections low. Percentages are out of each source's total records, and they can overlap.

| Problem | Target | What happens in cleaning |
|---|---|---|
| Exact and near duplicates | ~5% | Removed (keep the first one), logged |
| Missing optional values | ~10% | Kept as empty |
| Missing required values | ~2% | Rejected |
| Inconsistent capitalization and whitespace | ~15% | Fixed |
| Non-standard formats (dates, units, category labels) | ~15% | Fixed |
| Invalid or ambiguous dates | ~2% | Rejected |
| Invalid numbers (out of range, not a number) | ~5% | Blanked if optional, rejected if required |
| Broken references (parent record missing) | ~2% | Rejected |
| Events out of order in time | ~2% | Rejected |
| Local IDs repeated across sources | Everyone starts IDs at 1 | Handled in integration (section 5) |

Altogether, rejected records should come to about 10-15% of each source, counted after cascading. Rejections cascade: if an admission is rejected, all its diagnoses, notes, unit stays, etc. get rejected too as broken references. So keep the problems that reject parent records (patients, admissions) on the low end of the table, and check your actual total once your cleaning runs.

Duplicate rules (only within your own source; matching across sources is part of integration):

- Exact duplicate: every field is the same after trimming and ignoring case.
- Duplicate entity:
  - Patient: same full_name and date_of_birth.
  - HealthcareProfessional: same name and role.
  - Admission: same patient and same admission_date_time.
  - Anything else: same admission, same timestamp and same type (note_type, examination_type, unit_type, etc.).
- Keep the first record. The rest go in the rejection file as `DUPLICATE`, with the kept record's ID in `reason_detail`. You can add stricter rules for your source as long as you note them in your profiling notes.
- Child records of a removed duplicate get re-pointed to the record you kept. For example, if patient 125 is a duplicate of patient 12, change every admission with `patient_id` 125 to 12 instead of rejecting them as broken references. Do this before checking references.

## 8. Rejection file format

One file per source: `data/rejected/<source>_rejected.csv`, UTF-8 with a header row. If a record fails more than one rule, give it one row per reason.

| Column | Content |
|---|---|
| source_id | `A`, `B`, `C` or `D` |
| entity | Table it was meant for, e.g. `Admission` |
| source_record_id | Original ID (empty if the ID is missing) |
| reason_code | `DUPLICATE`, `MISSING_REQUIRED`, `INVALID_DATE`, `AMBIGUOUS_DATE`, `INVALID_NUMBER`, `UNMAPPED_CATEGORY`, `UNKNOWN_ICD9`, `BROKEN_REFERENCE`, `CHRONOLOGY` or `MALFORMED` |
| reason_detail | Short explanation, e.g. `discharge 2025-03-01 before admission 2025-03-04` |
| raw_record | The original record exactly as it was in the source file |

Records that can't be read at all (Task 1) go here too, as `MALFORMED`.

Since one record can have several rows, count rejections in the report by distinct `(source_id, entity, source_record_id)`, not by row. Malformed rows with no ID count once each. That way raw = clean + rejected adds up.
