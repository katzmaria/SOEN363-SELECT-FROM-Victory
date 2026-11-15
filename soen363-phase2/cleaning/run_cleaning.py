"""
Entry point. Usage (from the phase2_sources folder):

    python cleaning/run_cleaning.py

Reads output/raw/ (never modified) and writes output/clean/, output/quarantine/,
output/cleaning_log/ and output/cleaning_report.md. Standard library only
(Python >= 3.9 for zoneinfo; the IANA tz database must be available - on
Windows install it with `pip install tzdata`).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import SOURCE_CODEBOOKS  # noqa: E402
from pipeline import (Context, deduplicate, integrity_checks, normalise_all, reconcile_discharge,  # noqa: E402
                      required_checks, resolve_ambiguous_a, resolve_patients)
from readers import read_all  # noqa: E402
from report import write_outputs, write_report  # noqa: E402


def check_d_codebook(cb):
    """Source D ships its own codebook; make sure ours agrees with it."""
    ours_type = SOURCE_CODEBOOKS["admission_type"]["D"]
    ours_tri = SOURCE_CODEBOOKS["triage_priority"]["D"]
    return (all(ours_type.get(k) == v for k, v in cb["encounter_type"].items())
            and all(ours_tri.get(k.lower()) == v for k, v in cb["triage_category"].items()))


def main():
    data, rejects, d_codebook = read_all()
    ctx = Context()
    normalise_all(data, ctx)
    resolve_ambiguous_a(data, ctx)
    deduplicate(data, ctx)
    reconcile_discharge(data, ctx)
    master = resolve_patients(data, ctx)
    required_checks(data, ctx)
    integrity_checks(data, ctx, master, rejects)
    counts = write_outputs(data, rejects, ctx)
    write_report(data, rejects, ctx, counts, check_d_codebook(d_codebook))

    print(f"{'entity':16s} clean rows")
    for e, n in counts.items():
        print(f"{e:16s} {n:>6d}")
    print(f"quarantined: {len(ctx.quarantine) + len(rejects)}   duplicates removed: {len(ctx.duplicates)}   "
          f"patients merged: {len(ctx.crosswalk)}   issues logged: {len(ctx.issues)}")


if __name__ == "__main__":
    main()
