"""
Runs EVERYTHING for Phase 2 Tasks 1 and 2, from the soen363-phase2 folder:

    python run_all.py --icd9 ../soen363-phase1/data/icd9_dictionary.csv

1. checks that every code file is the current version (and names any outdated file)
2. Task 1: loads and profiles the four raw sources      -> output/profile/, output/profile_report.md
3. Task 2: cleans and standardizes them                 -> output/clean/, output/quarantine/, output/cleaning_log/,
                                                           output/cleaning_report.md
4. writes the report with every table                   -> output/Phase2_Tasks1-2_report.docx

Standard library only: nothing to install.
"""

import argparse
import importlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

PIPELINE_VERSION = "2026.11.15-abcd"
MODULES = ["cleaning.tabular", "cleaning.standards", "cleaning.parsers", "cleaning.clean_sources", "cleaning.report",
           "profiling.load_sources", "profiling.profile_sources", "reporting.docx_writer", "reporting.make_report"]
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


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", nargs="+", default=["A", "B", "C", "D"])
    ap.add_argument("--icd9", default=str(ROOT.parent / "soen363-phase1" / "data" / "icd9_dictionary.csv"))
    ap.add_argument("--no-report", action="store_true", help="skip the Word report")
    a = ap.parse_args()
    t0 = time.time()
    check_files(a.sources)
    print(f"Code files OK (version {PIPELINE_VERSION}).")

    from cleaning.clean_sources import OUT, run
    from profiling.profile_sources import profile

    print("Task 1 - loading and profiling the raw sources ...")
    profile(tuple(a.sources), Path(a.icd9), OUT)
    print(f"  -> {OUT / 'profile_report.md'}")
    print("Task 2 - cleaning and standardizing ...")
    run(tuple(a.sources), Path(a.icd9), OUT)
    if not a.no_report:
        from reporting.make_report import build
        print(f"Report -> {build()}")
    print(f"Done in {time.time() - t0:.1f} s.")
