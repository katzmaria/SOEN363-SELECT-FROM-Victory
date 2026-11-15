# Source B: AI prompt disclosure

- **Tool:** Claude Code (Anthropic's agentic coding CLI, used in the VS Code extension)
- **Model:** Claude Opus 5.5 (model ID `claude-opus-5-5`)
- **Date:** 2026-11-15
- **Used for:** generating the synthetic raw data for Source B only (`data/raw/B_csv/`), through the seeded script
  `source_b_generator.py`. No loading, profiling, cleaning, transformation or import code was generated.
- **Outputs:** `docs/ai_prompts/source_b_generator.py`, `data/raw/B_csv/*.csv`, `docs/ai_prompts/source_b_generation_log.md`

The data is entirely fictional, created exclusively for educational and learning purposes, and does not describe
real patients or include any real personal information.

## Exact prompt

```text
I'm working on SOEN 363 Project Phase 2. I need you to generate a synthetic raw dataset for Source B.
Generative AI is allowed ONLY for creating the synthetic source data, so do NOT write any loading,
profiling, cleaning, transformation or import code. Only generate the raw data.

REQUIRED STATEMENT (the course requires this): The data must be entirely fictional, created
exclusively for educational and learning purposes, and must not describe real patients or include
any real personal information.

Context to read first:
- soen363-phase2/docs/contract.md (our team's data contract: the problem rates in section 7 apply here)
- soen363-phase1/db/schema.sql (the 12 entities the data must cover)
- soen363-phase1/data/icd9_dictionary.csv (the only valid ICD-9 codes)

Source B:
- Format: CSV, one file per entity
- A fictional hospital system called "Uganda National Hospital", continent Africa
- All timestamps in local time, Africa/Kampala (UTC+3, no DST)
- Total of 7,000-9,000 records across all files (one record = one entity instance)
- Cover all Phase 1 entities: HealthcareProfessional, Patient, Admission, TriageAssessment,
  Diagnosis, ClinicalNote, DiagnosticOrder, RadiologyExamination, SurgicalProcedure, UnitStay,
  DischargeRecord. Don't generate an ICD-9 dictionary file; diagnoses reference the shared one.
- Number every entity's IDs from 1 (patient 1, 2, 3...), because other sources do the same and the
  integration step has to deal with repeated IDs across sources.

Make the raw data look like a real, independent hospital system, NOT like our cleaned format:
- Use this source's own column names (e.g. PatientName, DOB, AdmitDateTime), not the schema's names.
- Use its own date formats. Mostly day-first (DD/MM/YYYY HH:MM), but mix in some ISO and
  some month-first dates so a few become genuinely ambiguous.
- Use its own category labels (e.g. "Emergency Dept", "A&E", "Casualty", "HIGH", "Hi", "Routine")
  that someone would have to map to our standard values.
- Record some temperatures in Fahrenheit and some in Celsius.
- Use local missing-value placeholders: empty, "N/A", "null", "-", "?", "-1", "0000-00-00".
- In allergies and medications, use "none", "NKA" or "no known allergies" for patients who have none.
- ICD-9 codes: only use codes from icd9_dictionary.csv, sometimes written without the decimal point
  or with extra spaces (e.g. "4019", " 428.0"), plus about 1% fake codes.

Data-quality problems: inject them on purpose, at roughly the rates in section 7 of contract.md:
exact and near duplicates, missing optional values, missing required values, inconsistent
capitalization and whitespace, non-standard formats, invalid or ambiguous dates, invalid numbers
(e.g. temperature 300, pain level 14, negative heart rate), broken references (child rows pointing to
parents that don't exist) and chronologically inconsistent events (e.g. discharge before admission,
procedures outside the admission period). Keep the problems that would reject parent records
(patients, admissions) on the low end, so most records survive cleaning. Everything else should be
realistic and internally consistent: admissions after date of birth, unit stays within the admission,
one discharge record per completed admission, and so on.

How to do it:
1. Write a seeded Python generator script so the data is reproducible. Save it at
   soen363-phase2/docs/ai_prompts/source_b_generator.py. It's part of the AI disclosure, NOT part of our
   pipeline, so don't put it in src/.
2. Run it to write the CSV files to soen363-phase2/data/raw/B_csv/.
3. Write soen363-phase2/docs/ai_prompts/source_b_generation_log.md with the record count per file
   and the number of each injected problem per file, so I can check them against my own profiling.
4. Save this exact prompt, and the tool you are (name and model), to
   soen363-phase2/docs/ai_prompts/source_b_prompt.md.
5. Commit only those files, with the message "Add Source B raw data (synthetic, AI-generated)".
   Do NOT add any Co-Authored-By line or any other AI attribution to the commit.
   Push to main.

Don't create or change any other files.
```
