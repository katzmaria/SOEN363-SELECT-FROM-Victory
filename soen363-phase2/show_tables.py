"""
Runs the Phase 2 tasks and prints their result tables in the terminal, one task at a time if you want.

    python show_tables.py --task 1            run Task 1 (load + profile), print its tables
    python show_tables.py --task 2            run Task 2 (clean + standardize), print its tables
    python show_tables.py                     run Tasks 1 and 2, print all tables
    python show_tables.py --task 2 --no-run   print the Task 2 tables of the last run (no re-run)
    python show_tables.py --list              list the figures of every task
    python show_tables.py 12 13               print only Figures 12 and 13 (add --no-run to skip the run)
    python show_tables.py --width 120         table width in characters (default: terminal width)

Every task's tables are also saved to output/tables/task<N>_tables.txt, to open in VS Code instead of scrolling.
Options for the run: --icd9 <path> (default ../soen363-phase1/data/icd9_dictionary.csv), --sources A B C D.
Standard library only. No Word document is created.

Tasks 3 to 6: add an entry to TASKS below (a function that runs the task) and give their tables a heading
"N. Task K: ..." in reporting/make_report.py; they are then split out the same way.
"""

import argparse
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


def run_task1(a):
    from cleaning.clean_sources import OUT
    from profiling.profile_sources import profile
    print("Task 1 - loading and profiling the raw sources ...")
    profile(tuple(a.sources), Path(a.icd9), OUT)


def run_task2(a):
    from cleaning.clean_sources import OUT, run
    print("Task 2 - cleaning and standardizing ...")
    run(tuple(a.sources), Path(a.icd9), OUT, quiet=True)

# -----------------------------------------------------------------------------------------------------------
# Tasks 3 to 6 - not written yet. When a task's code exists:
#   1. uncomment its function below and point it to the real code,
#   2. add it to TASKS (e.g. 3: run_task3),
#   3. give its tables a section heading "N. Task K: ..." in reporting/make_report.py, so that
#      `python show_tables.py --task K` prints only that task's tables.
# -----------------------------------------------------------------------------------------------------------

# Task 3 - Integration and schema refinement (integration lead, report section 9):
#   revise the Phase 1 schema, build the identifier-mapping table (source, continent, original id ->
#   integrated id) and the source-traceability columns. Tables to show: schema changes, id mapping counts.
# def run_task3(a):
#     from integration.integrate import integrate          # hypothetical module: src/integrate/
#     print("Task 3 - integrating the four clean sources ...")
#     integrate()

# Task 4 - Import into the SQL database (integration lead, report section 10):
#   load the clean tables into SQLite in parent-first order, with parameterized statements and transactions.
#   Tables to show: rows imported per table and source, rerun behaviour.
# def run_task4(a):
#     from integration.import_db import import_all         # hypothetical module
#     print("Task 4 - importing into the database ...")
#     import_all()

# Task 5 - Integrity enforcement and validation (Source A owner, report section 11):
#   constraints and triggers, then validation queries (orphans, chronology, duplicate ids).
#   Tables to show: each validation query and its result (expected: 0 problems).
# def run_task5(a):
#     from validation.validate import run_validation        # hypothetical module: sql/ + a small runner
#     print("Task 5 - running the validation queries ...")
#     run_validation()

# Task 6 - Demonstration of the integrated database (Source C owner, report section 12):
#   integration queries (counts by source/continent, admission types, top ICD-9 by continent, average stay)
#   and the Phase 1 queries rerun on the integrated database. Tables to show: each query's result.
# def run_task6(a):
#     from demo.queries import run_demo_queries              # hypothetical module
#     print("Task 6 - running the demonstration queries ...")
#     run_demo_queries()

TASKS = {1: run_task1, 2: run_task2}        # later: {1: run_task1, 2: run_task2, 3: run_task3, 4: run_task4, ...}


def plain(s):
    """Remove the **bold** and `code` markers used by the report."""
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
    """Same interface as the report writer, but prints the tables instead (and keeps them per task)."""

    def __init__(self, tasks=None, figures=None, listing=False, width=120):
        self.tasks, self.figures, self.listing, self.width = tasks, figures, listing, width
        self.table_no, self.task, self.section, self.printed = 0, 1, "", None
        self.saved = defaultdict(list)                      # task -> text lines

    def h(self, text, level=1):
        text = plain(text)
        if level == 1:
            m = re.search(r"Task (\d+)", text)
            self.task = int(m.group(1)) if m else (1 if self.table_no == 0 else 0)   # introduction -> Task 1
        self.section = text

    def table(self, header, rows, caption=None, **_):
        if not caption:
            return
        self.table_no += 1
        title = f"Figure {self.table_no}: {plain(caption)}"
        if self.listing:
            print(f"  Task {self.task}  {title}   [{self.section}]")
            return
        if self.tasks and self.task not in self.tasks:
            return
        if self.figures and self.table_no not in self.figures:
            return
        lines = []
        if self.section != self.printed:
            bar = "#" * min(self.width, 100)
            lines += ["", bar, f"# {self.section}", bar]
            self.printed = self.section
        lines += ["", title] + box(header, rows or [["(no rows)"] + [""] * (len(header) - 1)], self.width)
        print("\n".join(lines))
        self.saved[self.task] += lines

    # everything else the report writes (text, lists, captions) is not printed
    def p(self, *a, **k): pass
    def title(self, *a, **k): pass
    def bullets(self, *a, **k): pass
    def code(self, *a, **k): pass
    def caption(self, *a, **k): pass
    def page_break(self, *a, **k): pass
    def save(self, *a, **k): pass


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
        todo = sorted(a.task or TASKS)
        # the tables read the results of both tasks: run the other one too if it has never been run
        if 1 not in todo and not (out / "profile" / "record_counts.csv").exists():
            todo.insert(0, 1)
        if 2 not in todo and not (out / "cleaning_log" / "summary.csv").exists():
            todo.append(2)
        for t in todo:
            TASKS[t](a)
        print(f"Results written to {out}")

    import reporting.make_report as mr
    doc = TerminalDoc(tasks=set(a.task or []), figures=set(a.figures), listing=a.list, width=a.width)
    mr.Docx = lambda: doc                         # the report code fills the terminal instead of a Word file
    mr.build(out_path=out / ".unused.docx")
    if not a.list:
        (out / "tables").mkdir(parents=True, exist_ok=True)
        for t, lines in sorted(doc.saved.items()):
            path = out / "tables" / f"task{t}_tables.txt"
            path.write_text("\n".join(lines).lstrip("\n") + "\n", encoding="utf-8")
            print(f"\nTask {t} tables also saved to {path.relative_to(ROOT)}")
