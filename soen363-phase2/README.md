# SOEN 363 Project Phase 2: Multi-Source Hospital Data Integration

Team **SELECT \* FROM Victory**. Due November 30, 2026 at 11:59 PM (Moodle).

Report (Google Doc): https://docs.google.com/document/d/1_8G-2PNgWdFukLguN9jDbjHN7lLbCaVB2wM0P9N4pjw/edit

All paths below are relative to this `soen363-phase2/` folder. Phase 1 work stays in `../soen363-phase1/`: start the revised schema from `../soen363-phase1/db/schema.sql`, the shared ICD-9 dictionary from `../soen363-phase1/data/icd9_dictionary.csv`, and the Phase 1 query reruns from `../soen363-phase1/queries/`.

## Roles

| Role | Owner | Covers | Folders |
|---|---|---|---|
| Data contract + Source B (CSV) | Samuel Richard | `docs/contract.md`, shared ICD-9 dictionary, common cleaning rules, Source B | `docs/contract.md`, `data/raw/B_csv/`, `src/sources/b/` |
| Source A (TXT) | to be chosen | Source A + constraints written into the schema in week 1 (before import) + triggers and integrity validation queries (after import) | `data/raw/A_txt/`, `src/sources/a/`, `sql/` (constraints, validation) |
| Integration lead | to be chosen | Schema revisions, ID mapping and traceability, import pipeline; receives the contract from Samuel and shares the revised schema in week 1 | `src/integrate/`, `sql/` (schema) |
| Source C (XML) | to be chosen | Source C + Task 6 demonstration queries | `data/raw/C_xml/`, `src/sources/c/` |
| Source D (JSON) | to be chosen | Source D + report assembly and submission | `data/raw/D_json/`, `src/sources/d/` |

Everyone also reruns their own Phase 1 queries against the integrated database.

## Folder layout

```
soen363-phase2/
data/raw/<source>/   original source files, never edited after they are committed
data/clean/          cleaned output for each source, in the format set by docs/contract.md
data/rejected/       quarantined records, each with a rejection reason
src/sources/<x>/     loading, profiling and cleaning code for one source
src/integrate/       identifier mapping and database import
sql/                 schema, constraints, validation and demonstration queries
docs/contract.md     shared conventions everyone codes against
docs/ai_prompts/     prompts used to generate each synthetic dataset (AI disclosure)
docs/profiles/       initial profiling output for each source
```

Folders are created as people add their first file to them.

## Working rules

- `docs/contract.md` comes first: Samuel writes it and hands it to the integration lead. Changes go through the group chat.
- SQLite can't add CHECK, FOREIGN KEY or UNIQUE constraints to an existing table, so constraints go into the `CREATE TABLE` statements in the schema file. The Source A owner adds them in a pull request in week 1, before the import, so two people aren't editing the schema at the same time later.
- Work on your own branch (`source-a`, `source-b`, `source-c`, `source-d`, `integration`) and open a pull request into `main`.
- Stay inside your own folders, so merges don't conflict.
- Never edit a file in `data/raw/` after it is committed. The handout requires the originals to stay unchanged.
- No passwords or credentials in the repo. Put them in a local `.env` file, which is ignored.
- Generative AI may only be used to generate the synthetic datasets. It may not be used for code, SQL, schema design or the report (handout section 2). Save every data-generation prompt in `docs/ai_prompts/`.
- The database file and the source data are not part of the Moodle zip. Markers ask for them at the demo.

## Rebuilding the database

To be filled in once the pipeline exists: requirements, the command that runs the full pipeline, and whether a rerun rebuilds the database or updates it.
