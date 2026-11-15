# Data contract (fill in together before writing cleaning code)

Every source owner's cleaned output in `data/clean/` must follow this file, so the integration step can load all four sources the same way.

## 1. Sources

| Source | Format | Continent | Hospital system name | Source time zone | Owner |
|---|---|---|---|---|---|
| A | TXT | | | | to be chosen |
| B | CSV | | | | Samuel |
| C | XML | | | | to be chosen |
| D | JSON | | | | to be chosen |

## 2. Cleaned output files

For each entity: file name, columns, types, required or optional.

## 3. Formats

- Dates and timestamps:
- Missing values:
- Text casing and whitespace:
- Units (temperature, weight, etc.):

## 4. Standard category values

- Admission type:
- Triage priority:
- Unit type:
- Admission status:
- Examination / order status:
- Diagnosis type:

## 5. Identifiers

How source identifiers are written in the cleaned files, so they can't collide across sources.

## 6. ICD-9 dictionary

Location of the single shared dictionary file and how codes are stored (as strings, keeping leading zeros).

## 7. Data-quality problems every source must include

Duplicates, missing required and optional values, inconsistent capitalization and whitespace, invalid or ambiguous dates, invalid numbers, broken references, chronologically inconsistent events, and local IDs repeated across sources. Target frequency for each:

## 8. Rejection file format

Columns every rejection file must have (for example: source, entity, source record id, reason).
