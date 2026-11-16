"""
Minimal table helpers (standard library only - no pandas needed).

`Table` is the data structure the loaders return: the column names in order plus one dict per record.
"""

from __future__ import annotations

PIPELINE_VERSION = "2026.11.15-abcd"   # run_all.py checks that every file has the same version

import csv
from collections import Counter


class Table:
    def __init__(self, columns=(), rows=()):
        self.columns = list(columns)
        self.rows = list(rows)

    def __len__(self):
        return len(self.rows)

    def column(self, name):
        return [r.get(name) for r in self.rows]

    def head(self, n=5):
        return Table(self.columns, self.rows[:n])

    def __repr__(self):
        return f"Table({len(self.rows)} rows x {len(self.columns)} columns)"


def write_csv(path, rows, columns):
    """None is written as an empty field; UTF-8, '\\n' line endings."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(columns)
        for r in rows:
            w.writerow(["" if r.get(c) is None else r.get(c) for c in columns])


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        return list(rd.fieldnames or []), list(rd)


def count_by(rows, *keys):
    return Counter(tuple(r[k] for k in keys) for r in rows)


def md_table(rows, columns=None, max_rows=None, max_len=140):
    """Markdown table from a list of dicts."""
    if not rows:
        return "_none_\n"
    columns = columns or list(rows[0])
    if max_rows is not None:
        rows = rows[:max_rows]
    out = ["| " + " | ".join(str(c) for c in columns) + " |", "|" + "---|" * len(columns)]
    for r in rows:
        cells = []
        for c in columns:
            x = r.get(c)
            s = "" if x is None else str(x).replace("|", "\\|").replace("\n", " ")
            cells.append(s if len(s) <= max_len else s[:max_len - 3] + "...")
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"
