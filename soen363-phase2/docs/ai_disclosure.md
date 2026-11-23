# Generative AI Disclosure: Synthetic Source Data

The Phase 2 handout (section 2) permits generative AI **only for creating the synthetic source datasets**. This file records how that was done.
## Scope

Generative AI was used only to create the four synthetic source datasets in `data/raw/`. It was not used for the Python loading, profiling, cleaning, integration or import code, the database schema, the SQL, or the report.

## Tool

- **Tool:** Claude Code (Anthropic's agentic coding CLI), used in the VS Code extension for Sources B and D and through claude.ai for Sources A and C (as stated in their prompt files).
- **Model and date:** Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-15, for all four sources (stated in each source's prompt file).

## What produced each source

| Source | Hospital (fictional), continent | Format, time zone | Generator script | Seed | Prompt and log |
|---|---|---|---|---|---|
| A | CHU de Montclair-sur-Loire, Europe | TXT (pipe-delimited, French), Europe/Paris | `docs/ai_prompts/source_a_generator.py` | 2025 | `source_a_prompt.md`, `source_a_generation_log.md` |
| B | Uganda National Hospital, Africa | CSV, Africa/Kampala | `docs/ai_prompts/source_b_generator.py` | 363 | `source_b_prompt.md`, `source_b_generation_log.md` |
| C | Straits Regional Medical Centre, Asia | XML (nested), Asia/Singapore | `docs/ai_prompts/source_c_generator.py` | 2026 | `source_c_prompt.md`, `source_c_generation_log.md` |
| D | Coral Coast Health Service, Oceania | JSON (nested), Australia/Sydney | `docs/ai_prompts/source_d_generator.py` | 2061 | `source_d_prompt.md`, `source_d_generation_log.md` |

Every generator is seeded, so running it again reproduces its files exactly. The generators only write raw data; none of them is part of the loading, cleaning or import pipeline. The raw files are never modified by the pipeline.

## Prompts used

- **Source B:** the exact prompt, tool, model, date and outputs are in `docs/ai_prompts/source_b_prompt.md`.
- **Source D:** the same, in `docs/ai_prompts/source_d_prompt.md`.
- **Source A:** `docs/ai_prompts/source_a_prompt.md`. One message, with the team contract pasted in, then a follow-up message pasting the handout's data-source requirements. The tool asked which continent and time zone, and the team member chose Europe and Europe/Paris.
- **Source C:** `docs/ai_prompts/source_c_prompt.md`. One message, with the team contract and the handout's data-source sections pasted in; the continent chosen in the prompt was Asia, and the tool chose Asia/Singapore and the hospital name.

All four prompts tell the tool that the data must be entirely fictional and created only for educational purposes, to generate data only (no loading, profiling, cleaning or import code), and to follow the team's data contract, the Phase 1 schema and the Phase 1 ICD-9 dictionary. The A and C prompt files also list the checks the tool ran on its own output.

An earlier attempt at one script for all four sources was also written with Claude. Its prompt is kept in the appendix below. It was removed from the repository because its output is not the committed data (its file names, hospital names and, for B and D, continents differ from the committed files).

## How fictional data is guaranteed

- Names, addresses, phone numbers and identifiers are random. The generators build names from lists of common first names and surnames, and the data contains no real person.
- Hospitals are fictional. Source D's phone numbers come from the ranges reserved for fiction and its URLs use the reserved `.example` domain.
- ICD-9 codes and titles are real *classification* codes taken from the Phase 1 dictionary (public reference data), not patient data.

## How the generated data was reviewed

The checks concern the generated sources (A to D). The evidence comes from the Task 1 profile and the Task 2 quarantine.

| # | Check | Evidence | Done by |
|---|---|---|---|
| 1 | Each source has 5,000-10,000 records | `output/profile/record_counts.csv`: A 8,030, B 7,923, C 8,136, D 8,506 records (duplicates and malformed records included; 32,595 in total) | Maria-Christine (Task 1 profile) |
| 2 | The loader counts agree with the generators' own logs | each generation log's total equals the profile total: A 8,030, B 7,923, C 8,136, D 8,506 (for D, 8,484 loaded plus 22 malformed). Running each of the four generators again reproduces its committed `data/raw` files and its generation log byte for byte. | Kigham Kerry Kinyuy, run with Claude Code's help (comparison of log totals with the profile and byte-for-byte rerun of the four generators, 2026-11-23) |
| 3 | The injected problems are present | the four generation logs count, per file or entity, duplicates, missing values, bad dates, invalid numbers, broken references and chronology errors; Task 1 found them (`output/profile_report.md`: duplicates, missing values, formatting differences, invalid values, malformed records) | Maria-Christine (Task 1 profile) |
| 4 | ICD-9 codes are valid and the injected fake codes are caught | Codes come from the Phase 1 dictionary; Task 2 quarantines unknown codes (`output/quarantine/diagnoses.csv`, reason `unknown_icd9_code`) | Maria-Christine (Task 2 cleaning) |
| 5 | No real person appears | Names are random combinations; Source D uses fictional phone ranges | Kigham Kerry Kinyuy, 2026-11-23: sampled 6 patients and 3 staff per source; names are common-name combinations with no recognizable public figures; no emails in the raw data; image links use fictional or reserved domains; phone numbers are random, and only Source D's are from reserved ranges |

## Appendix: prompt for the earlier all-in-one attempt (not used for the committed data)

```text
You are helping with a university database course project (SOEN 363, Phase 2).
Generate synthetic hospital data. IMPORTANT: all data must be ENTIRELY
FICTIONAL, created exclusively for educational and learning purposes, and must
not describe real patients or include any real personal information.

Write a deterministic Python script (fixed random seed, Faker allowed) that
creates four independent hospital data sources, one per continent:

  Source A - Europe        - TXT (pipe-delimited, one file per entity, header line)
  Source B - North America - CSV (one file per entity)
  Source C - Asia          - XML (nested: admission children inside <admission>)
  Source D - Africa        - JSON (nested: encounter children inside arrays)

Size: each source must contain 5,000-10,000 records in total (one record =
one entity instance; nested XML/JSON instances count once; headers, tags and
containers do not count).

Content: each source must contain related records for healthcare
professionals, ICD-9 dictionary entries, patients, admissions, triage
assessments, unit stays (Emergency Department, ICU, CCU, MICU, SICU, General
Ward), diagnoses (one primary per completed admission plus secondaries),
diagnostic orders, radiology examinations with reports, surgical procedures,
clinical notes (including discharge summaries) and discharge records. Use only
real ICD-9-CM codes and official titles, stored as strings so leading zeros
(e.g. 038.9) are preserved. Include enough variation for these cases: ED to
ICU/CCU transfers, surgery before ICU entry, several critical care unit types
in one admission, discharge summaries mentioning "recovery" in mixed case,
in-hospital deaths, patients with no admissions, and admissions with several
distinct ICD-9 codes.

Differences between sources: use different field names, date/time formats,
time zones, category labels (admission type, triage priority, unit type,
status), units (e.g. Celsius vs Fahrenheit, oxygen saturation as % vs
fraction) and missing-value representations (empty, NULL, N/A, null, absent).

Data-quality problems: inject controlled, counted examples of
  - exact duplicate records and the same person registered twice
  - missing required and missing optional values
  - inconsistent capitalization and whitespace
  - invalid and ambiguous dates
  - invalid numeric values (e.g. impossible vital signs)
  - broken references between related records
  - chronologically inconsistent events (discharge before admission, unit
    exit before entry, procedure outside the admission)
  - repeated local identifiers across sources (each source numbers from 1)
Keep the majority of records clean and usable.

Also produce: a manifest with record counts by source and entity and the
count of each injected problem; and a README documenting each source's file
layout, the TXT delimiter and record layout, time zones, and a codebook that
maps each source's category labels to common values.
```
