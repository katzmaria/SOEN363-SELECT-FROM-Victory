# Task 5: Enforce and validate data integrity

Handout section 8 - part of 20 points (SQL import, integrity enforcement and validation).

- Database constraints wherever possible; triggers or checks for the rest.
- Check at least: unique non-null primary keys; foreign keys exist; every admission has a patient; every diagnosis
  has an admission and an ICD-9 code; diagnosis patient = admission patient; discharge after admission; unit exit
  after entry; exams and procedures inside their admission; every completed admission has a primary diagnosis;
  discharge agrees with admission status; required values and categories follow the rules.
- Deliver: the validation queries, their outputs, and every unresolved limitation.

Code for this task goes in this folder. To show its results like Tasks 1 and 2, add it to `TASKS` in `show_tables.py`.
