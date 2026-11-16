# SOEN 363 Project Phase 2: Multi-Source Hospital Data Integration

Team **SELECT \* FROM Victory**. Due November 30, 2026 at 11:59 PM (Moodle).

Report (Google Doc): https://docs.google.com/document/d/1_8G-2PNgWdFukLguN9jDbjHN7lLbCaVB2wM0P9N4pjw/edit

All paths below are relative to this `soen363-phase2/` folder. Phase 1 work stays in `../soen363-phase1/`: the revised schema starts from `../soen363-phase1/db/schema.sql`, the shared ICD-9 dictionary is `../soen363-phase1/data/icd9_dictionary.csv`, and the Phase 1 queries to rerun are in `../soen363-phase1/queries/`.

## Sources

| Source | Format | Continent | Hospital system | Time zone |
|---|---|---|---|---|
| A | TXT | Europe | CHU de Montclair-sur-Loire | Europe/Paris |
| B | CSV | Africa | Uganda National Hospital | Africa/Kampala |
| C | XML | Asia | Straits Regional Medical Centre | Asia/Singapore |
| D | JSON | Oceania | Coral Coast Health Service | Australia/Sydney |

## Status

Tasks 1 and 2 are done: all four sources are generated, loaded, profiled and cleaned. Task 3 is assigned to Samuel. Everything under "Remaining work" is still open.

| Done | By |
|---|---|
| Data contract (`docs/contract.md`), report section 8.1 (common cleaning rules) | Samuel Richard |
| Source B and Source D raw data | Samuel Richard |
| Source A and Source C raw data | Maria-Christine Catiche |
| Task 1 and Task 2 code for all four sources: loading, profiling, cleaning (`profiling/`, `cleaning/`, `run_all.py`) | Maria-Christine Catiche |
| Report sections 7 (Task 1) and 8.2–8.3 (Task 2 results) | Maria-Christine Catiche |

## Remaining work

| Task | Owner | Covers | Report sections |
|---|---|---|---|
| Task 3: Integration and schema refinement | Samuel Richard | Revised schema: source table (source, continent, time zone), ID-mapping and traceability tables, global surrogate keys, how the columns in `output/clean/` map onto the schema. Updated ER diagram and SQL schema file. | 9 |
| Task 4: Import | Kigham Kerry Kinyuy | Python import pipeline: loads the ICD-9 dictionary and everything in `output/clean/` into Samuel's schema, parents before children, parameterized statements, transactions, safe to rerun. Fills the mapping and traceability tables. | 10 |
| Task 5: Integrity and validation | Vanessa Cherbaka | Constraints (CHECK, FOREIGN KEY, UNIQUE) added to Samuel's schema **before** the import, triggers, the handout's validation queries with their outputs (orphans, chronology, duplicate identifiers, required fields, category values), unresolved limitations | 11 |
| Task 6 and report | Maria Celena Said | The six Task 6 queries with outputs, changes in results after integration, record counts by source and entity, the data-quality frequency table, the AI disclosure, the Phase 2 overview, the final PDF and zip, and the Moodle submission | 5, 6, 12.1, 12.3 |

The split follows what each person did in Phase 1. Swap in the group chat if you prefer.

Everyone who wrote Phase 1 queries reruns their own five on the integrated database and adds them to section 12.2: Kerry (Q1, Q2, Q6, Q10, Q14), Maria-Christine (Q3, Q4, Q12, Q17, Q19), Vanessa (Q5, Q7, Q9, Q15, Q16) and Maria Celena (Q8, Q11, Q13, Q18, Q20).

### Order of work

1. **Samuel** shares the revised schema and the column mapping: by **Nov 19**. Kerry can start the import code against a draft before then.
2. **Vanessa** adds the constraints to that schema: by **Nov 20**. (SQLite can't add CHECK, FOREIGN KEY or UNIQUE constraints to an existing table, so they have to be in the `CREATE TABLE` statements before the import.)
3. **Kerry** runs the full import: **Nov 21–24**. The cleaned data is already in `output/clean/`.
4. **In parallel, once the database exists:** validation queries (Vanessa), Task 6 queries (Maria Celena), Phase 1 reruns (everyone above). All of these can be written against the schema before the import and just run afterwards.
5. **All report sections done:** **Nov 27**.
6. **Maria Celena** assembles the PDF and zip and submits: **Nov 29**.

Before the demo, the whole team walks through every part together, since the handout says every member has to understand the entire project.

## Folder layout

```
soen363-phase2/
├── run_all.py               runs Task 1 and Task 2 for all four sources
├── show_tables.py           prints the Task 1 and Task 2 tables in the terminal
├── data/raw/<source>/       original source files (A_txt, B_csv, C_xml, D_json); never edited
├── profiling/               Task 1: loading and profiling
├── cleaning/                Task 2: cleaning and standardization
├── reporting/               builds the Task 1-2 Word write-up from the last run
├── output/
│   ├── profile/             Task 1 results (record counts, field profile, duplicates, invalid values, malformed records)
│   ├── clean/               cleaned records, one CSV per entity for all sources (input for the import)
│   ├── quarantine/          rejected records, each with its reason codes
│   └── cleaning_log/        every change made during cleaning, label mappings, summary
├── docs/
│   ├── contract.md          shared cleaning conventions
│   ├── ai_disclosure.md     AI disclosure for the synthetic data
│   └── ai_prompts/          prompts, generators and generation logs for each source
├── generator/               data generator
├── sql/                     (to add) schema (Samuel), constraints and triggers, validation and demo queries
└── integrate/               (to add) import pipeline (Kerry)
```

## Working rules

- The import reads `output/clean/`. Where the cleaned files differ from the format in `docs/contract.md`, the cleaned files are what the import has to handle.
- Work on your own branch (`schema`, `import`, `validation`, `demo-report`) and open a pull request into `main`.
- Stay inside your own folders, so merges don't conflict. The schema file is shared: Samuel writes it, Vanessa adds the constraints after. Agree on who edits it when.
- Never edit a file in `data/raw/`. The handout requires the originals to stay unchanged.
- No passwords or credentials in the repo. Put them in a local `.env` file, which is ignored.
- Generative AI may only be used to generate the synthetic datasets. It may not be used for code, SQL, schema design or the report (handout section 2).
- The database file and the source data are not part of the Moodle zip. Markers ask for them at the demo.

## Running it

Tasks 1 and 2 (standard library only, nothing to install):

```bash
python run_all.py --icd9 ../soen363-phase1/data/icd9_dictionary.csv
```

This writes everything under `output/`. Rerunning on the same raw files gives the same output.

Import and validation: to be filled in by Kerry once the pipeline exists (the command, and whether a rerun rebuilds the database or updates it).
