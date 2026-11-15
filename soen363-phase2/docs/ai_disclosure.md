# Generative AI Disclosure: Synthetic Source Data

The Phase 2 handout (section 2) permits generative AI **only for creating the synthetic source datasets**. This file records how that was done.

## Tool

- **Tool:** Claude (Anthropic), used through Claude Code.
- **Used for:** writing `generator/generate_sources.py` and the source files it produces in `output/raw/`, plus this disclosure and the dataset description in `README.md`.
## Prompts used

All prompts are listed in the order they were given, in one Claude conversation.

1. I asked about what should be a good prompt

   > what should be a good prompt to have the generate sources based on this Phase2?

Claude wrote the used prompt below and generated the four sources and the README.
2. The team then gave the full specification below, verbatim. Claude checked the existing generator and data against every requirement in it and found all of them met, so the files were not regenerated.

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
Claude wrote `generator/generate_sources.py` and generated the four sources and the README.

## How fictional data is guaranteed

- Names, addresses, phone numbers and insurers come from the Faker library with fixed seeds. They are randomly generated and belong to no real person.
- Hospitals are labelled "Fictional … Hospital". Clinical events are random draws from fixed lists.
- ICD-9 codes and titles are real *classification* codes (public reference data), not patient data.

## How the generated data was reviewed

*Your team must complete this section yourselves. The handout makes you responsible for reviewing the generated data. Write down the checks you actually ran.* Suggested checks:

- Count records per source and entity, and compare with `README.md` / `output/injection_manifest.json`.
- Check that every source is within 5,000–10,000 records.
- Spot-check ICD-9 codes and titles against an official ICD-9-CM reference.
- Confirm that the injected problem types appear in the files, and roughly as often as documented.
- Confirm that no real people or organizations appear.
