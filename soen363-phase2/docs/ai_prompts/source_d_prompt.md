# Source D: AI prompt disclosure

- **Tool:** Claude Code (Anthropic's agentic coding CLI, used in the VS Code extension)
- **Model:** Claude Opus 5.5 (model ID `claude-opus-5-5`)
- **Date:** 2026-11-15
- **Used for:** generating the synthetic raw data for Source D only (`data/raw/D_json/`), through the seeded script
  `source_d_generator.py`. No loading, profiling, cleaning, transformation or import code was generated.
- **Outputs:** `docs/ai_prompts/source_d_generator.py`, `data/raw/D_json/*.json`, `docs/ai_prompts/source_d_generation_log.md`

The data is entirely fictional, created exclusively for educational and learning purposes, and does not describe
real patients or include any real personal information.

## Exact prompt

```text
I'm working on SOEN 363 Project Phase 2. I need you to generate a synthetic raw dataset for Source D.
Generative AI is allowed ONLY for creating the synthetic source data, so do NOT write any loading,
profiling, cleaning, transformation or import code. Only generate the raw data.

REQUIRED STATEMENT (the course requires this): The data must be entirely fictional, created
exclusively for educational and learning purposes, and must not describe real patients or include
any real personal information.

Context to read first:
- soen363-phase2/docs/contract.md (our team's data contract: the problem rates in section 7 apply here)
- soen363-phase1/db/schema.sql (the entities the data must cover)
- soen363-phase1/data/icd9_dictionary.csv (the only valid ICD-9 codes)

Source D:
- Format: JSON. Use nesting the way a real hospital API export would: for example, an array of
  patients, each containing its admissions, and each admission containing its triage, diagnoses,
  notes, orders, exams, procedures, unit stays and discharge record. Healthcare professionals can be
  a separate file or top-level array that is referenced by ID. Several JSON files are fine.
- A fictional hospital system called "Coral Coast Health Service", continent Oceania (Australia)
- All timestamps in local time, Australia/Sydney (UTC+10, UTC+11 during daylight saving)
- Total of 7,000-9,000 records, counting every nested entity instance once (one record = one entity
  instance, not one key or container object)
- Cover all Phase 1 entities: HealthcareProfessional, Patient, Admission, TriageAssessment,
  Diagnosis, ClinicalNote, DiagnosticOrder, RadiologyExamination, SurgicalProcedure, UnitStay,
  DischargeRecord. Don't generate an ICD-9 dictionary file; diagnoses reference the shared one.
- Number every entity's IDs from 1, because other sources do the same and the integration step
  has to deal with repeated IDs across sources.

Make the raw data look like a real, independent hospital system, NOT like our cleaned format:
- Use this source's own key names in camelCase (e.g. patientName, dob, admittedAt), not the schema's
  names, and different from the other sources.
- Use its own date formats. Mostly ISO 8601 with a UTC offset (e.g. 2025-03-14T09:30:00+11:00), with
  some day-first strings and a few Unix timestamps mixed in, so some become ambiguous or need
  converting. Include a few local times that fall in the hour skipped or repeated when daylight
  saving starts or ends.
- Use its own category labels (e.g. "ED", "Resus", "Cat 1"..."Cat 5" for triage, "Day Surgery") that
  someone would have to map to our standard values.
- Mix types the way real APIs do: some numbers as strings ("37.2"), some booleans, nulls,
  and missing keys.
- Record some temperatures in Fahrenheit and some in Celsius.
- Use missing-value placeholders: null, missing keys, "", "N/A", "-", "?", -1, "0000-00-00".
- In allergies and medications, use "none", "NKA" or "nil known" for patients who have none.
- Include a few malformed records (e.g. a record missing a required key, or a value of the wrong
  type) so loading has something to log, but keep every file valid JSON so it can still be parsed.
- ICD-9 codes: only use codes from icd9_dictionary.csv, sometimes written without the decimal point
  or with extra spaces, plus about 1% fake codes.

Data-quality problems: inject them on purpose, at roughly the rates in section 7 of contract.md:
exact and near duplicates, missing optional and required values, inconsistent capitalization and
whitespace, non-standard formats, invalid or ambiguous dates, invalid numbers, broken references and
chronologically inconsistent events (e.g. discharge before admission, procedures outside the
admission period). Keep the problems that would reject parent records (patients, admissions) on the
low end, so most records survive cleaning. Everything else should be realistic and internally
consistent: admissions after date of birth, unit stays within the admission, one discharge record
per completed admission, and so on.

How to do it:
1. Write a seeded Python generator script so the data is reproducible. Save it at
   soen363-phase2/docs/ai_prompts/source_d_generator.py (AI disclosure only, NOT part of our pipeline).
2. Run it to write the JSON files to soen363-phase2/data/raw/D_json/.
3. Write soen363-phase2/docs/ai_prompts/source_d_generation_log.md with the record count per entity (nested ones included)
   and the number of each injected problem per entity (nested ones included).
4. Save this exact prompt, and the tool you are (name and model), to
   soen363-phase2/docs/ai_prompts/source_d_prompt.md.
5. Create a branch called source-d, commit only those files with the message
   "Add Source D raw data (synthetic, AI-generated)", and push the branch.

Don't create or change any other files.
```
