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
