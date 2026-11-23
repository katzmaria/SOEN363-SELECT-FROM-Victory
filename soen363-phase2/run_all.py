"""
Runs the Phase 2 pipeline, from the soen363-phase2 folder:

    python run_all.py --icd9 ../soen363-phase1/data/icd9_dictionary.csv

1. checks that every code file is the current version (and names any outdated or missing file)
2. Task 1: loads and profiles the four raw sources   -> output/profile/, output/profile_report.md
3. Task 2: cleans and standardizes them              -> output/clean/, output/quarantine/, output/cleaning_log/,
                                                        output/cleaning_report.md
4. Task 3: integrates the clean sources             -> output/integrated/hospital.db, id_mapping.csv,
                                                        patient_match_candidates.csv
5. Task 4: rebuilds hospital.db in one transaction  -> output/integrated/hospital.db, import_log.csv
   (rerun check: import_log.csv says whether every table is identical to the previous import)
6. Task 5: validates hospital.db and runs the negative tests -> output/validation/
To see the result tables in the terminal, use show_tables.py instead (it runs the same steps).
Standard library only: nothing to install.
"""

import argparse
import importlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

PIPELINE_VERSION = "2026.11.17-tasks"
MODULES = ["common.tabular", "common.standards", "common.parsers",
           "task1_load_profile.load_sources", "task1_load_profile.profile_sources", "task1_load_profile.tables",
           "task2_clean.clean_sources", "task2_clean.cleaning_report", "task2_clean.tables",
           "task3_integration.integrate", "task3_integration.tables",
           "task4_import.import_db", "task4_import.tables",
           "task5_validation.validate", "task5_validation.negative_tests", "task5_validation.tables"]
OLD_FOLDERS = ["cleaning", "profiling", "reporting"]          # replaced by common/ and the task folders
RAW = {"A": "data/raw/A_txt/sejours.txt", "B": "data/raw/B_csv/admissions.csv",
       "C": "data/raw/C_xml/hospital_records.xml", "D": "data/raw/D_json/patients_p1.json"}


def check_files(sources):
    bad = []
    for m in MODULES:
        path = ROOT / (m.replace(".", "/") + ".py")
        if not path.exists():
            bad.append(f"  MISSING   {path.relative_to(ROOT)}")
            continue
        if f'PIPELINE_VERSION = "{PIPELINE_VERSION}"' not in path.read_text(encoding="utf-8", errors="replace"):
            bad.append(f"  OUTDATED  {path.relative_to(ROOT)}")
    for s in sources:
        if not (ROOT / RAW[s]).exists():
            bad.append(f"  NO DATA   {RAW[s]}  (source {s}: put its raw files in {Path(RAW[s]).parent}/, with these "
                       f"exact file names)")
    if bad:
        print("Cannot run - fix these files first (close them in your editor, then copy the new version in):")
        print("\n".join(bad))
        sys.exit(1)
    for m in MODULES:
        mod = importlib.import_module(m)
        if Path(mod.__file__).resolve().parent.parent != ROOT:
            print(f"Cannot run - {m} is imported from {mod.__file__}, not from this folder.")
            sys.exit(1)
    old = [f for f in OLD_FOLDERS if any((ROOT / f).glob("*.py"))]
    if old:
        print("Note: old folder(s) " + ", ".join(f"{f}/" for f in old) + " are no longer used and can be deleted "
              "(the code is now in common/ and the task folders).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", nargs="+", default=["A", "B", "C", "D"])
    ap.add_argument("--icd9", default=str(ROOT.parent / "soen363-phase1" / "data" / "icd9_dictionary.csv"))
    a = ap.parse_args()
    t0 = time.time()
    check_files(a.sources)
    print(f"Code files OK (version {PIPELINE_VERSION}).")

    from task1_load_profile.profile_sources import profile
    from task2_clean.clean_sources import OUT, run

    print("Task 1 - loading and profiling the raw sources ...")
    profile(tuple(a.sources), Path(a.icd9), OUT)
    print(f"  -> {OUT / 'profile_report.md'}")
    print("Task 2 - cleaning and standardizing ...")
    run(tuple(a.sources), Path(a.icd9), OUT)
    # task 3 reads what task 2 just wrote to output/clean/, so it has to come after it.
    # imported under another name so it doesn't shadow task 2's run()
    from task3_integration.integrate import run as integrate
    print("Task 3 - integrating the sources ...")
    integrate()
    from task4_import.import_db import run as import_db
    print("Task 4 - importing into the SQL database ...")
    import_db()
    from task5_validation import negative_tests, validate
    print("Task 5 - validating data integrity ...")
    validate.write_results(validate.run_checks(), OUT / "validation")
    negative_tests.write_results(negative_tests.run_negative_tests(), OUT / "validation")
    print(f"Done in {time.time() - t0:.1f} s. To see the tables: python show_tables.py --task 1  (or --task 2, 3, 4, 5)")
