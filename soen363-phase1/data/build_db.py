"""
Rebuild db/hospital.db from scratch, in order:
  1. generate_data.py           - schema + core data (patients, admissions, triage, unit stays)
  2. generate_clinical_data.py  - ICD-9, diagnoses, orders, radiology, surgery, notes, discharges

Usage (from the repo root):
    python data/build_db.py
"""

import generate_clinical_data
import generate_data

if __name__ == "__main__":
    generate_data.main()
    generate_clinical_data.main()
