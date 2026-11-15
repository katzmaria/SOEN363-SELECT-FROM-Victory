# Phase 2 - Task 2: Cleaning and Standardisation Report

_Generated automatically by `cleaning/run_cleaning.py`. Re-running the script on the unchanged raw files reproduces this report byte-for-byte._

## 1. Summary of the cleaning results

| Source | Raw records | Same-key duplicates removed | Patients merged (same person) | Quarantined (direct) | Quarantined (cascade) | Clean records | Kept | Logged issues |
|---|---|---|---|---|---|---|---|---|
| A - Europe (TXT) | 8997 | 36 | 4 | 110 | 493 | 8354 | 92.9% | 566 |
| B - North America (CSV) | 9714 | 39 | 5 | 167 | 440 | 9063 | 93.3% | 701 |
| C - Asia (XML) | 9436 | 38 | 5 | 140 | 454 | 8799 | 93.2% | 627 |
| D - Africa (JSON) | 7970 | 32 | 4 | 117 | 335 | 7482 | 93.9% | 928 |
| **Total** | 36117 | 145 | 18 | 534 | 1722 | 33698 | 93.3% | 2822 |

Raw records = duplicates removed + patients merged + quarantined + clean, so every raw record is accounted for. *Direct* = the record itself failed a rule; *cascade* = the record is valid but its parent (patient, admission or order) was quarantined, so it cannot be linked.

### Records per entity (clean / quarantined)

| Entity | A: clean / quar. | B: clean / quar. | C: clean / quar. | D: clean / quar. |
|---|---|---|---|---|
| professionals | 40 / 0 | 40 / 0 | 40 / 0 | 40 / 0 |
| icd9_codes | 27 / 0 | 27 / 0 | 27 / 0 | 27 / 0 |
| patients | 473 / 7 | 492 / 8 | 494 / 6 | 454 / 6 |
| admissions | 840 / 55 | 917 / 53 | 889 / 54 | 765 / 35 |
| triage | 890 / 59 | 961 / 61 | 929 / 59 | 788 / 46 |
| unit_stays | 1372 / 127 | 1405 / 133 | 1406 / 131 | 1215 / 112 |
| diagnoses | 1980 / 170 | 2160 / 154 | 2097 / 150 | 1776 / 113 |
| orders | 569 / 32 | 667 / 43 | 625 / 36 | 478 / 27 |
| radiology | 293 / 25 | 368 / 29 | 322 / 26 | 268 / 21 |
| procedures | 93 / 11 | 98 / 8 | 99 / 10 | 74 / 8 |
| notes | 937 / 62 | 1011 / 65 | 984 / 66 | 833 / 48 |
| discharges | 840 / 55 | 917 / 53 | 887 / 56 | 764 / 36 |

### Actions taken on fields (issue log)

| Issue | Action | A | B | C | D | Total |
|---|---|---|---|---|---|---|
| admission_before_birth | quarantined | 26 | 15 | 22 | 6 | 69 |
| ambiguous_date_mm_dd | corrected | 81 | 0 | 0 | 0 | 81 |
| bp_systolic_not_above_diastolic | flagged | 11 | 19 | 18 | 14 | 62 |
| discharge_before_admission | corrected | 8 | 9 | 9 | 7 | 33 |
| discharge_time_filled_from_admission | corrected | 0 | 6 | 4 | 7 | 17 |
| discharge_time_filled_from_discharge_record | corrected | 0 | 6 | 5 | 9 | 20 |
| dst_nonexistent | flagged | 0 | 6 | 0 | 0 | 6 |
| entity_duplicate_patient | merged | 4 | 5 | 5 | 4 | 18 |
| icd9_leading_zero_lost | corrected | 0 | 55 | 0 | 0 | 55 |
| invalid_heart_rate | nulled | 8 | 6 | 5 | 9 | 28 |
| invalid_oxygen_saturation | nulled | 4 | 11 | 2 | 5 | 22 |
| invalid_pain_level | nulled | 3 | 7 | 3 | 2 | 15 |
| invalid_temperature | nulled | 5 | 4 | 5 | 6 | 20 |
| invalid_timestamp | nulled | 6 | 98 | 58 | 66 | 228 |
| messy_category_label | corrected | 116 | 153 | 185 | 105 | 559 |
| missing_optional_value | retained_null | 221 | 224 | 235 | 245 | 925 |
| missing_required_value | flagged_required | 20 | 21 | 21 | 19 | 81 |
| name_text_standardised | corrected | 26 | 25 | 33 | 22 | 106 |
| non_numeric_value | nulled | 6 | 8 | 2 | 2 | 18 |
| patient_ref_remapped_to_master | corrected | 11 | 12 | 4 | 5 | 32 |
| timestamp_as_epoch_seconds | corrected | 0 | 0 | 0 | 97 | 97 |
| timestamp_without_timezone | flagged | 0 | 0 | 0 | 289 | 289 |
| unknown_icd9_code | quarantined | 10 | 11 | 11 | 9 | 41 |

### Quarantine reasons

| Reason | A | B | C | D | Total |
|---|---|---|---|---|---|
| admission_before_patient_birth | 26 | 15 | 22 | 6 | 69 |
| diagnosis_patient_mismatch | 7 | 7 | 7 | 6 | 27 |
| discharge_record_for_active_admission | 0 | 0 | 2 | 1 | 3 |
| invalid_admit_time_utc | 6 | 5 | 3 | 8 | 22 |
| invalid_assessed_at_utc | 0 | 11 | 4 | 8 | 23 |
| invalid_entry_time_utc | 0 | 17 | 6 | 9 | 32 |
| invalid_exit_time_utc | 0 | 12 | 10 | 6 | 28 |
| invalid_ordered_at_utc | 0 | 8 | 3 | 2 | 13 |
| invalid_performed_at_utc | 0 | 3 | 3 | 1 | 7 |
| invalid_written_at_utc | 0 | 10 | 7 | 8 | 25 |
| malformed_line | 2 | 6 | 0 | 0 | 8 |
| missing_parent_admission | 7 | 7 | 7 | 6 | 27 |
| missing_parent_order | 3 | 3 | 3 | 2 | 11 |
| missing_parent_patient | 8 | 9 | 9 | 8 | 34 |
| missing_required_admit_time_utc | 4 | 4 | 4 | 4 | 16 |
| missing_required_birth_date | 3 | 3 | 3 | 3 | 12 |
| missing_required_family_name | 3 | 3 | 3 | 3 | 12 |
| missing_required_icd9_code | 10 | 11 | 11 | 9 | 41 |
| parent_admission_quarantined | 485 | 425 | 438 | 328 | 1676 |
| parent_order_quarantined | 19 | 20 | 18 | 16 | 73 |
| parent_patient_quarantined | 12 | 16 | 16 | 9 | 53 |
| procedure_before_admission | 4 | 4 | 4 | 3 | 15 |
| radiology_exam_after_discharge | 3 | 3 | 3 | 2 | 11 |
| unit_exit_before_entry | 14 | 15 | 15 | 13 | 57 |
| unknown_icd9_code | 10 | 11 | 11 | 9 | 41 |

A record can carry several reasons, so this table can sum to more than the number of quarantined records.


### Routine conversions applied to every record (not logged individually)

| Conversion | A | B | C | D |
|---|---|---|---|---|
| category_mapped | 14099 | 15431 | 14895 | 12499 |
| fahrenheit_to_celsius | 0 | 1022 | 0 | 0 |
| fraction_to_percent | 0 | 0 | 988 | 0 |
| staff_code_to_integer | 0 | 0 | 9205 | 7722 |
| string_to_number | 0 | 0 | 0 | 623 |
| timestamp_to_utc | 10829 | 11542 | 11280 | 9496 |

## 2. Detection check against the injection manifest

The manifest is **not** used by the cleaning code; it is only compared afterwards to show that the rules find the injected problems. Differences are explained below the table.

| Problem | A inj / det | B inj / det | C inj / det | D inj / det |
|---|---|---|---|---|
| ambiguous_date_mm_dd | 97 / 81 * | 0 / 0 | 0 / 0 | 0 / 0 |
| broken_admission_patient_ref | 8 / 8 | 9 / 9 | 9 / 9 | 8 / 8 |
| broken_diagnosis_icd9_ref | 10 / 10 | 11 / 11 | 11 / 11 | 9 / 9 |
| broken_radiology_order_ref | 3 / 3 | 3 / 3 | 3 / 3 | 2 / 2 |
| broken_unitstay_admission_ref | 7 / 7 | 7 / 7 | 7 / 7 | 6 / 6 |
| diagnosis_patient_mismatch | 7 / 7 | 7 / 7 | 7 / 7 | 6 / 6 |
| discharge_before_admission | 8 / 8 | 9 / 9 | 9 / 9 | 7 / 7 |
| discharge_record_for_active_admission | 0 / 0 | 0 / 0 | 2 / 2 | 1 / 1 |
| entity_duplicate_patient | 4 / 4 | 5 / 5 | 5 / 5 | 4 / 4 |
| exact_duplicate_admission | 8 / 8 | 9 / 9 | 9 / 9 | 8 / 8 |
| exact_duplicate_diagnosis | 21 / 21 | 23 / 23 | 22 / 22 | 18 / 18 |
| exact_duplicate_patient | 7 / 7 | 7 / 7 | 7 / 7 | 6 / 6 |
| exam_outside_admission | 3 / 3 | 3 / 3 | 3 / 3 | 2 / 2 |
| icd9_leading_zero_lost | 0 / 0 | 55 / 55 | 0 / 0 | 0 / 0 |
| invalid_date | 6 / 6 | 98 / 98 | 58 / 58 | 66 / 66 |
| invalid_heart_rate | 8 / 8 | 6 / 6 | 5 / 5 | 9 / 9 |
| invalid_oxygen_saturation | 4 / 4 | 11 / 11 | 2 / 2 | 5 / 5 |
| invalid_pain_level | 3 / 3 | 7 / 7 | 3 / 3 | 2 / 2 |
| invalid_temperature | 5 / 5 | 4 / 4 | 5 / 5 | 6 / 6 |
| malformed_line_extra_fields | 0 / 0 | 6 / 6 | 0 / 0 | 0 / 0 |
| malformed_line_wrong_field_count | 2 / 2 | 0 / 0 | 0 / 0 | 0 / 0 |
| messy_category_label | 172 / 116 * | 153 / 153 | 189 / 185 * | 138 / 105 * |
| messy_name_text | 22 / 22 | 19 / 19 | 28 / 28 | 18 / 18 |
| missing_optional_address | 28 / 28 | 29 / 29 | 31 / 31 | 28 / 28 |
| missing_optional_allergies | 42 / 42 | 51 / 51 | 47 / 47 | 46 / 46 |
| missing_optional_emergency_contact | 21 / 21 | 21 / 21 | 24 / 24 | 26 / 26 |
| missing_optional_insurance | 97 / 97 | 88 / 88 | 90 / 90 | 102 / 102 |
| missing_optional_phone | 32 / 32 | 35 / 35 | 40 / 40 | 40 / 40 |
| missing_required_admission_time | 4 / 4 | 4 / 4 | 4 / 4 | 4 / 4 |
| missing_required_date_of_birth | 3 / 3 | 3 / 3 | 3 / 3 | 3 / 3 |
| missing_required_icd9_code | 10 / 10 | 11 / 11 | 11 / 11 | 9 / 9 |
| missing_required_patient_name | 3 / 3 | 3 / 3 | 3 / 3 | 3 / 3 |
| non_numeric_respiratory_rate | 6 / 6 | 8 / 8 | 2 / 2 | 2 / 2 |
| procedure_outside_admission | 4 / 4 | 4 / 4 | 4 / 4 | 3 / 3 |
| timestamp_as_epoch_seconds | 0 / 0 | 0 / 0 | 0 / 0 | 97 / 97 |
| timestamp_without_timezone | 0 / 0 | 0 / 0 | 0 / 0 | 289 / 289 |
| unit_exit_before_entry | 14 / 14 | 15 / 15 | 15 / 15 | 13 / 13 |

`*` = detected count differs from injected count. The remaining differences are expected:

* **messy_category_label**: the generator picks one of `label.upper()`, `label.lower()`, `" label "`, `"label  "`. When the source label is already upper case (A: `EMER`, `REA`; C: `ICU`; D: `P1`) or a digit (A triage `1`/`2`/`3`), `upper()` / `lower()` return the **identical** string, so there is nothing wrong in the data and nothing to detect. Every label that actually differs from the codebook is detected and mapped.
* **ambiguous_date_mm_dd**: a date written MM/DD in a DD/MM source is only detectable when the documented DD/MM reading contradicts related events (triage / unit entry minutes after admission, the discharge record, the admission window) and the MM/DD reading agrees with them. When both readings are consistent with every related event, the documented DD/MM reading is kept; no method can tell these apart.
* Detected counts for duplicates and missing values are on distinct record ids; invalid dates and labels are counted per written value (duplicate copies included), which is how the generator counts them.

Source D's embedded `facility.codebook` agrees with the codebook used here: **True**.


## 3. Representative before-and-after examples

### 3.1 Field-level examples (one per issue and source)

| Issue | Src | Entity | Id | Field | Before (raw) | After (clean) | Action |
|---|---|---|---|---|---|---|---|
| admission_before_birth | A | admissions | 1 | admit_time_utc | `admitted 2024-05-08 (local)` | `patient 1 born 2026-09-27` | quarantined |
| admission_before_birth | B | admissions | 97 | admit_time_utc | `admitted 2024-09-15 (local)` | `patient 53 born 2026-02-04` | quarantined |
| admission_before_birth | C | admissions | 171 | admit_time_utc | `admitted 2023-06-14 (local)` | `patient 91 born 2024-12-19` | quarantined |
| admission_before_birth | D | admissions | 369 | admit_time_utc | `admitted 2024-03-30 (local)` | `patient 213 born 2024-08-18` | quarantined |
| ambiguous_date_mm_dd | A | admissions | 229 | discharge_time_utc | `2025-01-02T07:16:00Z (read as DD/MM)` | `2025-02-01T07:16:00Z (read as MM/DD: matches discharge record / summary)` | corrected |
| bp_systolic_not_above_diastolic | A | triage | 2 | blood_pressure | `'98/99'` | `kept as recorded (physiologically implausible, needs review)` | flagged |
| bp_systolic_not_above_diastolic | B | triage | 22 | blood_pressure | `'100/105'` | `kept as recorded (physiologically implausible, needs review)` | flagged |
| bp_systolic_not_above_diastolic | C | triage | 36 | blood_pressure | `'98/99'` | `kept as recorded (physiologically implausible, needs review)` | flagged |
| bp_systolic_not_above_diastolic | D | triage | 73 | blood_pressure | `'100/104'` | `kept as recorded (physiologically implausible, needs review)` | flagged |
| discharge_before_admission | A | admissions | 17 | discharge_time_utc | `2025-05-08T15:19:00Z (before admit 2025-05-09T10:19:00Z)` | `2025-05-23T10:19:00Z (from discharge record)` | corrected |
| discharge_before_admission | B | admissions | 206 | discharge_time_utc | `2025-01-25T01:47:00Z (before admit 2025-01-26T05:47:00Z)` | `2025-02-08T04:47:00Z (from discharge record)` | corrected |
| discharge_before_admission | C | admissions | 219 | discharge_time_utc | `2025-09-12T09:26:14Z (before admit 2025-09-12T14:26:14Z)` | `2025-09-12T18:26:14Z (from discharge record)` | corrected |
| discharge_before_admission | D | admissions | 3 | discharge_time_utc | `2025-12-25T19:28:29Z (before admit 2025-12-27T19:28:29Z)` | `2026-01-14T06:28:29Z (from discharge record)` | corrected |
| discharge_time_filled_from_admission | B | discharges | 168 | discharge_time_utc | `NULL / invalid` | `2026-09-03T02:36:00Z` | corrected |
| discharge_time_filled_from_admission | C | discharges | 98 | discharge_time_utc | `NULL / invalid` | `2024-02-07T16:33:29Z` | corrected |
| discharge_time_filled_from_admission | D | discharges | 70 | discharge_time_utc | `NULL / invalid` | `2023-04-24T05:18:36Z` | corrected |
| discharge_time_filled_from_discharge_record | B | admissions | 442 | discharge_time_utc | `NULL / invalid` | `2023-12-22T04:33:00Z` | corrected |
| discharge_time_filled_from_discharge_record | C | admissions | 101 | discharge_time_utc | `NULL / invalid` | `2023-03-06T08:41:24Z` | corrected |
| discharge_time_filled_from_discharge_record | D | admissions | 64 | discharge_time_utc | `NULL / invalid` | `2025-03-09T20:28:15Z` | corrected |
| dst_nonexistent | B | admissions | 189 | discharge_time_utc | `'03/10/2024 02:51 AM'` | `2024-03-10T07:51:00Z` | flagged |
| entity_duplicate_patient | A | patients | 481 | patient_id | `481` | `master patient 49` | merged |
| entity_duplicate_patient | B | patients | 501 | patient_id | `501` | `master patient 130` | merged |
| entity_duplicate_patient | C | patients | 501 | patient_id | `501` | `master patient 44` | merged |
| entity_duplicate_patient | D | patients | 461 | patient_id | `461` | `master patient 250` | merged |
| icd9_leading_zero_lost | B | diagnoses | 45 | icd9_code | `'38.9'` | `038.9` | corrected |
| invalid_heart_rate | A | triage | 56 | heart_rate_bpm | `'0'` | `NULL (allowed 20-300 bpm)` | nulled |
| invalid_heart_rate | B | triage | 75 | heart_rate_bpm | `'-5'` | `NULL (allowed 20-300 bpm)` | nulled |
| invalid_heart_rate | C | triage | 23 | heart_rate_bpm | `'420'` | `NULL (allowed 20-300 bpm)` | nulled |
| invalid_heart_rate | D | triage | 34 | heart_rate_bpm | `-5` | `NULL (allowed 20-300 bpm)` | nulled |
| invalid_oxygen_saturation | A | triage | 226 | spo2_pct | `'140'` | `NULL (allowed 50-100 %)` | nulled |
| invalid_oxygen_saturation | B | triage | 93 | spo2_pct | `'-3'` | `NULL (allowed 50-100 %)` | nulled |
| invalid_oxygen_saturation | C | triage | 694 | spo2_pct | `'1.05' (= 105 %)` | `NULL (allowed 50-100 %)` | nulled |
| invalid_oxygen_saturation | D | triage | 49 | spo2_pct | `140` | `NULL (allowed 50-100 %)` | nulled |
| invalid_pain_level | A | triage | 208 | pain_score | `'-1'` | `NULL (allowed 0-10 (pain scale))` | nulled |
| invalid_pain_level | B | triage | 182 | pain_score | `'11'` | `NULL (allowed 0-10 (pain scale))` | nulled |
| invalid_pain_level | C | triage | 105 | pain_score | `'-1'` | `NULL (allowed 0-10 (pain scale))` | nulled |
| invalid_pain_level | D | triage | 579 | pain_score | `'15' (= 15 (pain scale))` | `NULL (allowed 0-10 (pain scale))` | nulled |
| invalid_temperature | A | triage | 384 | temperature_c | `'410,0'` | `NULL (allowed 25.0-45.0 degC)` | nulled |
| invalid_temperature | B | triage | 426 | temperature_c | `'208.4' (= 98 degC)` | `NULL (allowed 25.0-45.0 degC)` | nulled |
| invalid_temperature | C | triage | 35 | temperature_c | `'98.0'` | `NULL (allowed 25.0-45.0 degC)` | nulled |
| invalid_temperature | D | triage | 68 | temperature_c | `410.0` | `NULL (allowed 25.0-45.0 degC)` | nulled |
| invalid_timestamp | A | admissions | 82 | admit_time_utc | `'00/13/2024 08:30'` |  | nulled |
| invalid_timestamp | B | admissions | 2 | admit_time_utc | `'13/45/2024 09:15 PM'` |  | nulled |
| invalid_timestamp | C | admissions | 101 | discharge_time_utc | `'unknown'` |  | nulled |
| invalid_timestamp | D | admissions | 64 | discharge_time_utc | `'2025-02-30T10:00:00Z'` |  | nulled |
| messy_category_label | A | admissions | 8 | admission_type | `' URG '` | `urgent` | corrected |
| messy_category_label | B | admissions | 5 | admission_type | `'URGENT'` | `urgent` | corrected |
| messy_category_label | C | admissions | 23 | admission_type | `'Scheduled  '` | `elective` | corrected |
| messy_category_label | D | admissions | 53 | status | `'inpatient  '` | `active` | corrected |
| missing_optional_value | A | patients | 145 | emergency_contact | `'N/A'` | `NULL` | retained_null |
| missing_optional_value | B | patients | 32 | address | `'NULL'` | `NULL` | retained_null |
| missing_optional_value | C | patients | 384 | phone | `''` | `NULL` | retained_null |
| missing_optional_value | D | patients | 209 | address | `<absent/null>` | `NULL` | retained_null |
| missing_required_value | A | patients | 323 | birth_date | `''` | `NULL -> record quarantined unless a duplicate copy supplies it` | flagged_required |
| missing_required_value | B | patients | 221 | birth_date | `'unknown'` | `NULL -> record quarantined unless a duplicate copy supplies it` | flagged_required |
| missing_required_value | C | patients | 286 | family_name | `''` | `NULL -> record quarantined unless a duplicate copy supplies it` | flagged_required |
| missing_required_value | D | patients | 335 | family_name | `<absent/null>` | `NULL -> record quarantined unless a duplicate copy supplies it` | flagged_required |
| name_text_standardised | A | patients | 22 | family_name | `'ARNAUD'` | `Arnaud` | corrected |
| name_text_standardised | B | patients | 291 | family_name | `'  Ortiz '` | `Ortiz` | corrected |
| name_text_standardised | C | patients | 384 | family_name | `'bora'` | `Bora` | corrected |
| name_text_standardised | D | patients | 142 | family_name | `'dludlu'` | `Dludlu` | corrected |
| non_numeric_value | A | triage | 27 | resp_rate_per_min | `'abc'` |  | nulled |
| non_numeric_value | B | triage | 231 | resp_rate_per_min | `'abc'` |  | nulled |
| non_numeric_value | C | triage | 383 | resp_rate_per_min | `'--'` |  | nulled |
| non_numeric_value | D | triage | 246 | resp_rate_per_min | `'--'` |  | nulled |
| patient_ref_remapped_to_master | A | admissions | 512 | patient_id | `483` | `275` | corrected |
| patient_ref_remapped_to_master | B | admissions | 255 | patient_id | `501` | `130` | corrected |
| patient_ref_remapped_to_master | C | admissions | 675 | patient_id | `505` | `357` | corrected |
| patient_ref_remapped_to_master | D | admissions | 434 | patient_id | `461` | `250` | corrected |
| timestamp_as_epoch_seconds | D | admissions | 17 | admit_time_utc | `1685187524` | `2023-05-27T11:38:44Z` | corrected |
| timestamp_without_timezone | D | admissions | 18 | admit_time_utc | `'2024-06-07T18:06:13'` | `2024-06-07T16:06:13Z (assumed Africa/Johannesburg)` | flagged |
| unknown_icd9_code | A | diagnoses | 221 | icd9_code | `'123.45'` |  | quarantined |
| unknown_icd9_code | B | diagnoses | 166 | icd9_code | `'E000'` |  | quarantined |
| unknown_icd9_code | C | diagnoses | 64 | icd9_code | `'999.99'` |  | quarantined |
| unknown_icd9_code | D | diagnoses | 58 | icd9_code | `'999.99'` |  | quarantined |

### 3.2 Whole-record examples

**Source A admission: ambiguous date resolved, label normalised** (`admissions.txt:line 230`)

Raw:
```json
{
 "sejour_no": "229",
 "pat_no": "128",
 "medecin_admission": "5",
 "date_entree": "18/01/2025 15:16",
 "type_sejour": "EMER",
 "motif": "Abdominal pain",
 "provenance": "physician referral",
 "assurance": "Alexandre #800766",
 "date_sortie": "02/01/2025 08:16",
 "statut": "SORTI"
}
```
Clean:
```json
{
 "source": "A",
 "admission_id": "229",
 "patient_id": "128",
 "admitting_professional_id": "5",
 "admit_time_utc": "2025-01-18T14:16:00Z",
 "admission_type": "emergency",
 "reason": "Abdominal pain",
 "arrival_mode": "physician referral",
 "insurance": "Alexandre #800766",
 "discharge_time_utc": "2025-02-01T07:16:00Z",
 "status": "discharged"
}
```

**Source A triage: decimal comma, numeric codes, Paris time to UTC** (`triage.txt:line 6`)

Raw:
```json
{
 "triage_no": "5",
 "sejour_no": "5",
 "infirmier": "36",
 "date_heure": "16/09/2023 18:07",
 "tension": "138/94",
 "fc": "129",
 "fr": "24",
 "temp_c": "36,0",
 "spo2_pct": "88",
 "douleur": "7",
 "symptomes": "weakness, abdominal pain",
 "allergies": "Sulfa drugs",
 "traitement": "Amoxicillin 500 mg",
 "priorite": "1"
}
```
Clean:
```json
{
 "source": "A",
 "triage_id": "5",
 "admission_id": "5",
 "nurse_id": "36",
 "assessed_at_utc": "2023-09-16T16:07:00Z",
 "bp_systolic": "138",
 "bp_diastolic": "94",
 "heart_rate_bpm": "129",
 "resp_rate_per_min": "24",
 "temperature_c": "36",
 "spo2_pct": "88",
 "pain_score": "7",
 "symptoms": "weakness, abdominal pain",
 "allergies": "Sulfa drugs",
 "home_medications": "Amoxicillin 500 mg",
 "priority": "high"
}
```

**Source B patient: 'Last, First' split, US date, missing marker** (`patients.csv:row 2`)

Raw:
```json
{
 "PatientID": "32",
 "FullName": "Arnold, Robert",
 "DOB": "12/16/1995",
 "Sex": "Unknown",
 "HomeAddress": "NULL",
 "Phone": "859-519-9327 x857",
 "EmergencyContact": "Jim Steele (954) 052-8433 x966",
 "Deceased": "N"
}
```
Clean:
```json
{
 "source": "B",
 "patient_id": "32",
 "family_name": "Arnold",
 "given_name": "Robert",
 "birth_date": "1995-12-16",
 "sex": "unspecified",
 "address": "",
 "phone": "859-519-9327 x857",
 "emergency_contact": "Jim Steele (954) 052-8433 x966",
 "life_status": "alive"
}
```

**Source B triage: Fahrenheit to Celsius, messy acuity label** (`triage.csv:row 24`)

Raw:
```json
{
 "TriageID": "23",
 "EncounterID": "23",
 "NurseID": "31",
 "AssessedAt": "04/20/2025 11:12 PM",
 "BloodPressure": "96/66",
 "HeartRate": "56",
 "RespRate": "11",
 "TempF": "101.1",
 "SpO2": "92",
 "PainScore": "9",
 "Symptoms": "fall injury, nausea",
 "Allergies": "Penicillin",
 "HomeMeds": "Furosemide 40 mg",
 "Acuity": "HIGH"
}
```
Clean:
```json
{
 "source": "B",
 "triage_id": "23",
 "admission_id": "23",
 "nurse_id": "31",
 "assessed_at_utc": "2025-04-21T03:12:00Z",
 "bp_systolic": "96",
 "bp_diastolic": "66",
 "heart_rate_bpm": "56",
 "resp_rate_per_min": "11",
 "temperature_c": "38.4",
 "spo2_pct": "92",
 "pain_score": "9",
 "symptoms": "fall injury, nausea",
 "allergies": "Penicillin",
 "home_medications": "Furosemide 40 mg",
 "priority": "high"
}
```

**Source B diagnosis: ICD-9 leading zero restored** (`diagnoses.csv:row 46`)

Raw:
```json
{
 "DxID": "45",
 "PatientID": "10",
 "EncounterID": "19",
 "ICD9": "38.9",
 "ProviderID": "30",
 "DxDateTime": "02/22/2025 10:27 PM",
 "DxRank": "Secondary"
}
```
Clean:
```json
{
 "source": "B",
 "diagnosis_id": "45",
 "patient_id": "10",
 "admission_id": "19",
 "icd9_code": "038.9",
 "professional_id": "30",
 "diagnosed_at_utc": "2025-02-23T03:27:00Z",
 "rank": "secondary"
}
```

**Source C triage: SpO2 fraction to percent, +08:00 to UTC** (`admissions/admission[1][@admissionNo=1]/triage[@id=1]`)

Raw:
```json
{
 "id": "1",
 "nurse": "S031",
 "at": "2023-06-23T20:20:42+08:00",
 "bp": "158/64",
 "pulse": "111",
 "respiration": "25",
 "temperatureC": "37.7",
 "oxygenSaturation": "0.96",
 "pain": "9",
 "symptoms": "dizziness, cough",
 "allergies": "None known",
 "medications": "Atorvastatin 40 mg",
 "level": "Green",
 "admissionNo": "1"
}
```
Clean:
```json
{
 "source": "C",
 "triage_id": "1",
 "admission_id": "1",
 "nurse_id": "31",
 "assessed_at_utc": "2023-06-23T12:20:42Z",
 "bp_systolic": "158",
 "bp_diastolic": "64",
 "heart_rate_bpm": "111",
 "resp_rate_per_min": "25",
 "temperature_c": "37.7",
 "spo2_pct": "96",
 "pain_score": "9",
 "symptoms": "dizziness, cough",
 "allergies": "None known",
 "home_medications": "Atorvastatin 40 mg",
 "priority": "low"
}
```

**Source D encounter: epoch seconds converted** (`encounters[16](encounter_id=17)`)

Raw:
```json
{
 "encounter_id": 17,
 "patient_mrn": 8,
 "admitted_by": "PR-1",
 "start": 1685187524,
 "encounter_type": 2,
 "reason": "Cough",
 "referral_source": "physician referral",
 "medical_aid": "Mkhokeleleki, Sikobi and Masilela #611092",
 "end": "2023-06-11T18:38:44Z",
 "outcome": "discharged"
}
```
Clean:
```json
{
 "source": "D",
 "admission_id": "17",
 "patient_id": "8",
 "admitting_professional_id": "1",
 "admit_time_utc": "2023-05-27T11:38:44Z",
 "admission_type": "urgent",
 "reason": "Cough",
 "arrival_mode": "physician referral",
 "insurance": "Mkhokeleleki, Sikobi and Masilela #611092",
 "discharge_time_utc": "2023-06-11T18:38:44Z",
 "status": "discharged"
}
```

**Source D triage: numbers stored as strings, invalid heart rate nulled** (`encounters[29](encounter_id=30).triage[0]`)

Raw:
```json
{
 "triage_id": 34,
 "nurse": "PR-11",
 "at": "2024-08-05T23:16:37Z",
 "bp": "149/94",
 "pulse": -5,
 "resp_rate": 14,
 "temp_c": "38.3",
 "spo2": 97,
 "pain_score": 3,
 "complaints": [
  "dizziness",
  "chest pain"
 ],
 "allergies": "None known",
 "current_meds": "Lisinopril 10 mg",
 "category": "P3",
 "encounter_id": 30
}
```
Clean:
```json
{
 "source": "D",
 "triage_id": "34",
 "admission_id": "30",
 "nurse_id": "11",
 "assessed_at_utc": "2024-08-05T23:16:37Z",
 "bp_systolic": "149",
 "bp_diastolic": "94",
 "heart_rate_bpm": "",
 "resp_rate_per_min": "14",
 "temperature_c": "38.3",
 "spo2_pct": "97",
 "pain_score": "3",
 "symptoms": "dizziness, chest pain",
 "allergies": "None known",
 "home_medications": "Lisinopril 10 mg",
 "priority": "low"
}
```

### 3.3 Duplicate and entity-resolution examples

* `A` patients id 464: **exact_duplicate_raw** - removed `patients.txt:line 408`, kept `patients.txt:line 2`.
* `A` patient 481 merged into master 49:
  * duplicate raw: `{"pat_no": "481", "nom": "Pelletier", "prenom": " Michelle  ", "date_naissance": "07/12/1933", "sexe": "I", "adresse": "24, rue Baron, 11548 Gilles", "telephone": "06 31 04 91 82", "contact_urgence": "Élise Pruvost +33 2 99 72 69 13", "statut_vital": "VIVANT"}`
  * master raw: `{"pat_no": "49", "nom": "Pelletier", "prenom": "Michelle", "date_naissance": "07/12/1933", "sexe": "I", "adresse": "24, rue Baron, 11548 Gilles", "telephone": "06 31 04 91 82", "contact_urgence": "Élise Pruvost +33 2 99 72 69 13", "statut_vital": "VIVANT"}`
  * master clean: `{"source": "A", "patient_id": "49", "family_name": "Pelletier", "given_name": "Michelle", "birth_date": "1933-12-07", "sex": "unspecified", "address": "24, rue Baron, 11548 Gilles", "phone": "06 31 04 91 82", "emergency_contact": "Élise Pruvost +33 2 99 72 69 13", "life_status": "alive"}`
* `A` patient 482 merged into master 332:
  * duplicate raw: `{"pat_no": "482", "nom": "Rivière", "prenom": "AMÉLIE", "date_naissance": "13/03/2010", "sexe": "F", "adresse": "rue de Valette, 44379 Delaunay-sur-Lévêque", "telephone": "+33 4 73 81 96 21", "contact_urgence": "Luc Marques 02 55 36 10 41", "statut_vital": "VIVANT"}`
  * master raw: `{"pat_no": "332", "nom": "Rivière", "prenom": "Amélie", "date_naissance": "13/03/2010", "sexe": "F", "adresse": "rue de Valette, 44379 Delaunay-sur-Lévêque", "telephone": "+33 4 73 81 96 21", "contact_urgence": "Luc Marques 02 55 36 10 41", "statut_vital": "VIVANT"}`
  * master clean: `{"source": "A", "patient_id": "332", "family_name": "Rivière", "given_name": "Amélie", "birth_date": "2010-03-13", "sex": "female", "address": "rue de Valette, 44379 Delaunay-sur-Lévêque", "phone": "+33 4 73 81 96 21", "emergency_contact": "Luc Marques 02 55 36 10 41", "life_status": "alive"}`
* `A` patient 483 merged into master 275:
  * duplicate raw: `{"pat_no": "483", "nom": "De Oliveira", "prenom": " Bernadette  ", "date_naissance": "15/06/2020", "sexe": "F", "adresse": "799, rue Jacques Briand, 28329 Collet", "telephone": "01 76 00 23 22", "contact_urgence": "Chantal Guillon +33 (0)5 24 82 53 52", "statut_vital": "VIVANT"}`
  * master raw: `{"pat_no": "275", "nom": "De Oliveira", "prenom": "Bernadette", "date_naissance": "15/06/2020", "sexe": "F", "adresse": "799, rue Jacques Briand, 28329 Collet", "telephone": "01 76 00 23 22", "contact_urgence": "Chantal Guillon +33 (0)5 24 82 53 52", "statut_vital": "VIVANT"}`
  * master clean: `{"source": "A", "patient_id": "275", "family_name": "De Oliveira", "given_name": "Bernadette", "birth_date": "2020-06-15", "sex": "female", "address": "799, rue Jacques Briand, 28329 Collet", "phone": "01 76 00 23 22", "emergency_contact": "Chantal Guillon +33 (0)5 24 82 53 52", "life_status": "alive"}`

### 3.4 Quarantine examples

| Src | Entity | Id | Type | Reasons | Raw record (truncated) |
|---|---|---|---|---|---|
| A | patients | 64 | direct | malformed_line: 7 fields, expected 9 | `{"line": "64\|Guilbert\|Élodie\|22/09/1954\|H\|85, boulevard de Moulin, 55116 Pasquier\|0375623246"}` |
| A | patients | 323 | direct | missing_required_birth_date | `{"pat_no": "323", "nom": "Gomes", "prenom": "Adèle", "date_naissance": "", "sexe": "F", "adresse": "95, rue Eugène Colin, 37862 Bouvet", "telephone": "025365252…` |
| A | patients | 175 | direct | missing_required_family_name | `{"pat_no": "175", "nom": "", "prenom": "Frédéric", "date_naissance": "02/07/2026", "sexe": "I", "adresse": "89, chemin de Fernandez, 83144 Thierry", "telephone"…` |
| A | admissions | 82 | direct | invalid_admit_time_utc | `{"sejour_no": "82", "pat_no": "36", "medecin_admission": "35", "date_entree": "00/13/2024 08:30", "type_sejour": "URG", "motif": "Dizziness", "provenance": "phy…` |
| A | admissions | 125 | direct | missing_required_admit_time_utc | `{"sejour_no": "125", "pat_no": "61", "medecin_admission": "1", "date_entree": "N/A", "type_sejour": "ELEC", "motif": "Weakness", "provenance": "ambulance", "ass…` |
| A | diagnoses | 128 | direct | missing_required_icd9_code | `{"diag_no": "128", "pat_no": "25", "sejour_no": "50", "code_cim9": "", "medecin": "5", "date_heure": "04/07/2024 01:03", "rang": "S"}` |
| A | diagnoses | 221 | direct | unknown_icd9_code | `{"diag_no": "221", "pat_no": "43", "sejour_no": "93", "code_cim9": "123.45", "medecin": "2", "date_heure": "05/01/2025 05:03", "rang": "S"}` |
| B | triage | 100 | direct | invalid_assessed_at_utc | `{"TriageID": "100", "EncounterID": "96", "NurseID": "16", "AssessedAt": "13/45/2024 09:15 PM", "BloodPressure": "118/70", "HeartRate": "96", "RespRate": "17", "…` |
| B | unit_stays | 72 | direct | invalid_exit_time_utc | `{"StayID": "72", "EncounterID": "44", "AttendingID": "3", "Unit": "General Ward", "Room": "GEN-34", "Bed": "1", "InTime": "06/10/2024 10:01 PM", "OutTime": "02/…` |
| B | unit_stays | 197 | direct | invalid_entry_time_utc | `{"StayID": "197", "EncounterID": "112", "AttendingID": "4", "Unit": "General Ward", "Room": "GEN-33", "Bed": "2", "InTime": "02/30/2025 10:00 AM", "OutTime": "0…` |
| B | orders | 216 | direct | invalid_ordered_at_utc | `{"OrderID": "216", "EncounterID": "282", "OrderingProviderID": "4", "OrderedAt": "13/45/2024 09:15 PM", "Test": "Blood panel", "Indication": "Rule out infection…` |
| B | radiology | 52 | direct | invalid_performed_at_utc | `{"ImagingID": "52", "EncounterID": "111", "OrderID": "92", "ReferringProviderID": "15", "TechID": "19", "Modality": "MRI", "PerformedAt": "TBD", "BodyPart": "He…` |
| B | notes | 1 | direct | invalid_written_at_utc | `{"NoteID": "1", "EncounterID": "1", "AuthorID": "17", "NoteType": "Operative Note", "WrittenAt": "TBD", "NoteText": "Operative note. Coronary artery bypass graf…` |
| A | admissions | 1 | direct | admission_before_patient_birth | `{"sejour_no": "1", "pat_no": "1", "medecin_admission": "15", "date_entree": "08/05/2024 14:59", "type_sejour": "EMER", "motif": "Shortness of breath", "provenan…` |
| A | admissions | 54 | cascade | parent_patient_quarantined | `{"sejour_no": "54", "pat_no": "26", "medecin_admission": "2", "date_entree": "22/04/2024 00:47", "type_sejour": "ELEC", "motif": "Dizziness", "provenance": "amb…` |
| A | admissions | 89 | direct | missing_parent_patient | `{"sejour_no": "89", "pat_no": "6351", "medecin_admission": "35", "date_entree": "03/09/2025 17:55", "type_sejour": "URG", "motif": "Chest pain", "provenance": "…` |
| A | triage | 1 | cascade | parent_admission_quarantined | `{"triage_no": "1", "sejour_no": "1", "infirmier": "11", "date_heure": "08/05/2024 15:04", "tension": "113/57", "fc": "56", "fr": "18", "temp_c": "37,7", "spo2_p…` |
| A | unit_stays | 66 | direct | unit_exit_before_entry | `{"mvt_no": "66", "sejour_no": "35", "medecin_resp": "10", "unite": "MED", "chambre": "GEN-32", "lit": "3", "entree": "06/01/2024 14:36", "sortie": "05/01/2024 0…` |
| A | unit_stays | 89 | direct | missing_parent_admission | `{"mvt_no": "89", "sejour_no": "6562", "medecin_resp": "40", "unite": "MED", "chambre": "GEN-05", "lit": "1", "entree": "18/01/2024 16:33", "sortie": "19/01/2024…` |
| A | diagnoses | 250 | direct | diagnosis_patient_mismatch(diagnosis=304,admission=52) | `{"diag_no": "250", "pat_no": "304", "sejour_no": "108", "code_cim9": "584.9", "medecin": "5", "date_heure": "16/08/2025 23:51", "rang": "P"}` |
| A | radiology | 123 | direct | missing_parent_order | `{"examen_no": "123", "sejour_no": "347", "demande_no": "90859", "medecin_ref": "5", "manipulateur": "34", "type_examen": "Ultrasound", "date_heure": "23/10/2024…` |
| A | radiology | 162 | direct | radiology_exam_after_discharge | `{"examen_no": "162", "sejour_no": "477", "demande_no": "311", "medecin_ref": "25", "manipulateur": "29", "type_examen": "Ultrasound", "date_heure": "23/07/2025 …` |
| A | procedures | 32 | direct | procedure_before_admission | `{"acte_no": "32", "sejour_no": "364", "chirurgien": "22", "intervention": "Cardiac catheterization", "date_heure": "20/04/2023 03:00", "resultat": "successful"}` |
| B | radiology | 328 | cascade | parent_order_quarantined | `{"ImagingID": "328", "EncounterID": "801", "OrderID": "584", "ReferringProviderID": "4", "TechID": "24", "Modality": "CT scan", "PerformedAt": "09/20/2024 04:48…` |
| C | discharges | 943 | direct | discharge_record_for_active_admission | `{"id": "943", "at": "2026-10-15T09:16:06+08:00", "destination": "home", "condition": "stable", "followUp": "", "appointment": "", "authorizedBy": "S001", "admis…` |

## 4. Output files

* `output/clean/<entity>.csv` - cleaned, standardised records of all four sources (column `source` + local id form the key).
* `output/quarantine/<entity>_quarantine.csv` - rejected records with `rejection_type`, `reasons` and the untouched raw record.
* `output/cleaning_log/issues.csv` - every field-level correction, nulling, flag and missing value (before/after).
* `output/cleaning_log/duplicates_removed.csv` - every removed same-key duplicate copy and the copy that was kept.
* `output/cleaning_log/patient_crosswalk.csv` - duplicate patient registrations mapped to their master patient.
* `output/cleaning_log/transformations.csv` - counts of routine conversions (UTC, units, codes, categories).

