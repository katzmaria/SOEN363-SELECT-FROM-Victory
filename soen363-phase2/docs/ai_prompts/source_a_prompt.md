# Source A: AI prompt disclosure

- **Tool:** Claude Code (Anthropic's agentic coding CLI, used through claude.ai)
- **Model:** Claude Opus 5.5 (model ID `claude-opus-5-5`)
- **Date:** 2026-11-15
- **Used for:** generating the synthetic raw data for Source A only (`data/raw/A_txt/`), through the seeded script
  `source_a_generator.py`. No loading, profiling, cleaning, transformation or import code was generated for this dataset.
- **Outputs:** `docs/ai_prompts/source_a_generator.py`, `data/raw/A_txt/*.txt`, `docs/ai_prompts/source_a_generation_log.md`

The data is entirely fictional, created exclusively for educational and learning purposes, and does not describe
real patients or include any real personal information.

## Exact prompt

The prompt was given in one message (the first sentence of the required statement was cut off when it was pasted, and
the team contract was pasted after it):

```text
I'm working on SOEN 363 Project Phase 2. I need you to generate a synthetic raw dataset for Source A.
Generative AI is allowed ONLY for creating the synthetic source data, so do NOT write any loading,
profiling, cleaning, transformation or import code. Only generate the raw data.

REQUIRED STATEMENT (the course requires this): The data must be entirely fictional, created
exclusively for educational and learning purposes, and must not describe real patients or include. make sure to follow contract.md too:  # Our data contract
[full text of soen363-phase2/docs/contract.md, sections 1 to 8, pasted here]
```

Follow-up message in the same conversation (the handout's data-source requirements, pasted as a reminder):

```text
this helps? 3 Required Data Sources
Create four synthetic datasets representing hospital systems located on four different continents.
[handout sections 3, 3.1 and 3.2 pasted here: sizes 5,000-10,000 records per source, record counting rules,
required hospital content, differences and data-quality problems, "Preserve the original source files unchanged."]
```

Choices confirmed by the team member when asked by the tool: Source A = Europe, time zone Europe/Paris.

## What the tool was told to follow

- `soen363-phase2/docs/contract.md` (sections 1, 6 and 7 apply to raw data; section 7 gives the problem rates)
- `soen363-phase1/db/schema.sql` (the entities and their required columns)
- `soen363-phase1/data/icd9_dictionary.csv` (the only valid ICD-9 codes; read by the generator at run time)
- The conventions already used for Source B (`source_b_generator.py`), so the same cleaning rules apply to both:
  dash dates with an unknown day/month order, Fahrenheit/Celsius temperatures, the same missing-value placeholders,
  `none`/`NKA` meaning "none" in allergies and medications, and ICD-9 codes written without the decimal point.

## Checks the tool ran on the generated data before delivering it

- Every file has a header and the expected number of fields; the 4 malformed lines are the injected ones.
- IDs in every file start at 1.
- Every ICD-9 code is a Phase 1 dictionary code (sometimes written `4019` or `38.9`) or one of the injected fake codes.
- Without injected problems, events are consistent: admissions after the date of birth, unit stays, exams, procedures
  and notes inside the admission, one discharge record per completed admission.
- The data supports the Phase 1 queries: ED to critical-care paths, admissions with several critical-care units,
  discharge summaries containing "recovery" in mixed case, in-hospital deaths, patients without admissions,
  admissions with several distinct ICD-9 codes, surgery before ICU entry.
- Re-running the script produces byte-identical files.
