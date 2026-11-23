"""
Runs the Phase 2 tasks and prints their result tables in the terminal, one task at a time if you want.

    python show_tables.py --task 1            run Task 1 (load + profile), print its tables
    python show_tables.py --task 2            run Task 2 (clean + standardize), print its tables
    python show_tables.py                     run every task, print all tables
    python show_tables.py --task 2 --no-run   print the Task 2 tables of the last run (no re-run)
    python show_tables.py --list              list the figures of every task
    python show_tables.py 12 13 --no-run      print only Figures 12 and 13
    python show_tables.py --width 120         table width in characters (default: terminal width)

Every task's tables are also saved to output/tables/task<N>_tables.txt, to open in VS Code instead of scrolling.
Options for the run: --icd9 <path> (default ../soen363-phase1/data/icd9_dictionary.csv), --sources A B C D.
Standard library only.
"""

import argparse
import importlib
import re
import shutil
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(errors="replace")      # Windows consoles: never crash on a special character
except Exception:
    pass


# -----------------------------------------------------------------------------------------------------------
# The tasks: how to run each one, and where its tables are (a module with a tables(d) function)
# -----------------------------------------------------------------------------------------------------------
def run_task1(a):
    from task1_load_profile.profile_sources import profile
    print("Task 1 - loading and profiling the raw sources ...")
    profile(tuple(a.sources), Path(a.icd9), ROOT / "output")


def run_task2(a):
    from task2_clean.clean_sources import run
    print("Task 2 - cleaning and standardizing ...")
    run(tuple(a.sources), Path(a.icd9), ROOT / "output", quiet=True)


def run_task3(a):
    from task3_integration.integrate import run
    print("Task 3 - integrating the sources ...")
    run(quiet=True)


def run_task4(a):
    from task4_import.import_db import run
    print("Task 4 - importing into the SQL database ...")
    run(quiet=True)


def run_task5(a: argparse.Namespace) -> None:
    from task5_validation import negative_tests, validate
    db = ROOT / "output" / "integrated" / "hospital.db"
    if not db.exists():
        raise SystemExit("No database to validate: run Task 4 first (python show_tables.py --task 4)")
    print("Task 5 - validating data integrity ...")
    out = ROOT / "output" / "validation"
    validate.write_results(validate.run_checks(db), out)
    negative_tests.write_results(negative_tests.run_negative_tests(db), out)


TASKS = {
    1: (run_task1, "task1_load_profile.tables"),
    2: (run_task2, "task2_clean.tables"),
    3: (run_task3, "task3_integration.tables"),
    4: (run_task4, "task4_import.tables"),
    5: (run_task5, "task5_validation.tables"),
    # Task 6 - not written yet. When a task's code exists in its folder (see the README.md there):
    #   1. write a run_taskK(a) function above that runs it,
    #   2. write taskK_.../tables.py with a tables(d) function: d.h("Task K: ...") then d.table(...) per result,
    #   3. add it here, e.g.  5: (run_task5, "task5_validation.tables"),
    # Then `python show_tables.py --task K` runs it and prints its tables like Tasks 1 and 2.
}


# -----------------------------------------------------------------------------------------------------------
# Printing
# -----------------------------------------------------------------------------------------------------------
def plain(s):
    """Remove the **bold** and `code` markers used in the table cells."""
    return re.sub(r"\*\*(.+?)\*\*", r"\1", str("" if s is None else s)).replace("`", "")


def fit(natural, avail):
    """Column widths: natural widths if they fit, else cap the widest columns (water-filling)."""
    if sum(natural) <= avail:
        return natural
    lo, hi = 1, max(natural)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if sum(min(w, mid) for w in natural) <= avail:
            lo = mid
        else:
            hi = mid - 1
    return [min(w, lo) for w in natural]


def box(header, rows, width):
    """The table as text lines (ASCII borders, long cells wrapped)."""
    header = [plain(h) for h in header]
    rows = [[plain(c) for c in r] + [""] * (len(header) - len(r)) for r in rows]
    n = len(header)
    natural = [max([len(header[i])] + [len(r[i]) for r in rows]) for i in range(n)]
    widths = [max(3, w) for w in fit(natural, max(n * 6, width - (3 * n + 1)))]
    line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    out = [line]

    def emit(cells):
        parts = [textwrap.wrap(c, w, break_long_words=True, break_on_hyphens=False) or [""]
                 for c, w in zip(cells, widths)]
        for k in range(max(len(p) for p in parts)):
            out.append("| " + " | ".join((p[k] if k < len(p) else "").ljust(w) for p, w in zip(parts, widths)) + " |")

    emit(header)
    out.append("+" + "+".join("=" * (w + 2) for w in widths) + "+")
    for r in rows:
        emit(r)
        out.append(line)
    return out


class TerminalDoc:
    """Receives the section titles and tables of each task and prints the selected ones."""

    def __init__(self, tasks=None, figures=None, listing=False, width=120):
        self.tasks, self.figures, self.listing, self.width = tasks, figures, listing, width
        self.table_no, self.task, self.section, self.printed = 0, 0, "", None
        self.saved = defaultdict(list)                      # task -> text lines

    def h(self, text, level=1):
        text = plain(text)
        if level == 1:
            m = re.search(r"Task (\d+)", text)
            self.task = int(m.group(1)) if m else 0
        self.section = text

    def table(self, header, rows, caption=None, **_):
        if not caption:
            return
        self.table_no += 1
        title = f"Figure {self.table_no}: {plain(caption)}"
        if self.listing:
            print(f"  Task {self.task}  {title}   [{self.section}]")
            return
        if (self.tasks and self.task not in self.tasks) or (self.figures and self.table_no not in self.figures):
            return
        lines = []
        if self.section != self.printed:
            bar = "#" * min(self.width, 100)
            lines += ["", bar, f"# {self.section}", bar]
            self.printed = self.section
        lines += ["", title] + box(header, rows or [["(no rows)"] + [""] * (len(header) - 1)], self.width)
        print("\n".join(lines))
        self.saved[self.task] += lines


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("figures", nargs="*", type=int, help="figure numbers to print (default: all)")
    ap.add_argument("--task", type=int, nargs="+", help="task number(s) to run and print, e.g. --task 1")
    ap.add_argument("--no-run", action="store_true", help="do not re-run the tasks, use the last results")
    ap.add_argument("--list", action="store_true", help="only list the figures")
    ap.add_argument("--width", type=int, default=max(80, shutil.get_terminal_size((140, 40)).columns - 1))
    ap.add_argument("--sources", nargs="+", default=["A", "B", "C", "D"])
    ap.add_argument("--icd9", default=str(ROOT.parent / "soen363-phase1" / "data" / "icd9_dictionary.csv"))
    a = ap.parse_args()
    unknown = [t for t in (a.task or []) if t not in TASKS]
    if unknown:
        raise SystemExit(f"Task(s) {unknown} have no code yet. Available: {sorted(TASKS)}")

    import run_all
    run_all.check_files(a.sources)
    out = ROOT / "output"
    if not (a.no_run or a.list):
        for t in sorted(a.task or TASKS):
            TASKS[t][0](a)
        print(f"Results written to {out}")

    doc = TerminalDoc(tasks=set(a.task or []), figures=set(a.figures), listing=a.list, width=a.width)
    for t in sorted(TASKS):                     # every task, so the figure numbers stay the same
        try:
            importlib.import_module(TASKS[t][1]).tables(doc)
        except SystemExit as exc:               # this task has no results yet
            if not a.task or t in a.task:
                raise
            print(f"(Task {t} has no results yet; its figures are not numbered: {exc})")
    if not a.list:
        (out / "tables").mkdir(parents=True, exist_ok=True)
        for t, lines in sorted(doc.saved.items()):
            path = out / "tables" / f"task{t}_tables.txt"
            path.write_text("\n".join(lines).lstrip("\n") + "\n", encoding="utf-8")
            print(f"\nTask {t} tables also saved to {path.relative_to(ROOT)}")
