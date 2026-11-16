"""
Runs Tasks 1 and 2 and prints EVERY report table in the terminal (numbered Figure 1, 2, ... like the report).

    python show_tables.py                     run everything, then print all tables
    python show_tables.py 7 12                run everything, then print only Figures 7 and 12
    python show_tables.py --no-run            print the tables of the last run (no re-run)
    python show_tables.py --no-run --list     list the figures
    python show_tables.py --width 160         table width in characters (default: terminal width)

Options for the run: --icd9 <path> (default ../soen363-phase1/data/icd9_dictionary.csv), --sources A B C D.
Standard library only. No Word document is created.
"""

import argparse
import re
import shutil
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(errors="replace")      # Windows consoles: never crash on a special character
except Exception:
    pass


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
    header = [plain(h) for h in header]
    rows = [[plain(c) for c in r] + [""] * (len(header) - len(r)) for r in rows]
    n = len(header)
    natural = [max([len(header[i])] + [len(r[i]) for r in rows]) for i in range(n)]
    widths = [max(3, w) for w in fit(natural, max(n * 6, width - (3 * n + 1)))]
    line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    head_line = "+" + "+".join("=" * (w + 2) for w in widths) + "+"

    def emit(cells):
        parts = [textwrap.wrap(c, w, break_long_words=True, break_on_hyphens=False) or [""]
                 for c, w in zip(cells, widths)]
        for k in range(max(len(p) for p in parts)):
            print("| " + " | ".join((p[k] if k < len(p) else "").ljust(w) for p, w in zip(parts, widths)) + " |")

    print(line)
    emit(header)
    print(head_line)
    for r in rows:
        emit(r)
        print(line)


class TerminalDoc:
    """Same interface as the Word writer, but prints the tables (and section titles) instead."""

    def __init__(self, only=None, listing=False, width=120):
        self.only, self.listing, self.width = only, listing, width
        self.table_no, self.section, self.printed_section = 0, "", None

    def h(self, text, level=1):
        self.section = plain(text)

    def table(self, header, rows, caption=None, **_):
        if not caption:
            return
        self.table_no += 1
        title = f"Figure {self.table_no}: {plain(caption)}"
        if self.listing:
            print(f"{title}   [{self.section}]")
            return
        if self.only and self.table_no not in self.only:
            return
        if self.section != self.printed_section and not self.only:
            print("\n" + "#" * min(self.width, 100) + f"\n# {self.section}\n" + "#" * min(self.width, 100))
            self.printed_section = self.section
        print(f"\n{title}")
        box(header, rows or [["(no rows)"] + [""] * (len(header) - 1)], self.width)

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
    ap.add_argument("--no-run", action="store_true", help="do not re-run Tasks 1 and 2, use the last results")
    ap.add_argument("--list", action="store_true", help="only list the figures")
    ap.add_argument("--width", type=int, default=max(80, shutil.get_terminal_size((140, 40)).columns - 1))
    ap.add_argument("--sources", nargs="+", default=["A", "B", "C", "D"])
    ap.add_argument("--icd9", default=str(ROOT.parent / "soen363-phase1" / "data" / "icd9_dictionary.csv"))
    a = ap.parse_args()

    import run_all
    run_all.check_files(a.sources)
    if not a.no_run:
        from cleaning.clean_sources import OUT, run
        from profiling.profile_sources import profile
        print("Task 1 - loading and profiling the raw sources ...")
        profile(tuple(a.sources), Path(a.icd9), OUT)
        print("Task 2 - cleaning and standardizing ...")
        run(tuple(a.sources), Path(a.icd9), OUT, quiet=True)
        print(f"Results written to {OUT}")

    import reporting.make_report as mr
    doc = TerminalDoc(only=set(a.figures), listing=a.list, width=a.width)
    mr.Docx = lambda: doc                         # the report code fills the terminal instead of a Word file
    mr.build(out_path=ROOT / "output" / ".unused.docx")
    if not a.list:
        print(f"\n{doc.table_no} figures. Print one again with:  python show_tables.py --no-run <number>")