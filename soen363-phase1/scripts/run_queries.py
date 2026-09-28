"""
Run the Task 3 queries against db/hospital.db.

Usage (from the repo root):
    python scripts/run_queries.py          # run every query that has SQL in it
    python scripts/run_queries.py 1 6 14   # run only these queries

Each result is printed to the terminal and also written to
output/qNN.txt so it can be pasted or screenshotted into the report.
Files that only contain comments (not written yet) are skipped.
"""

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "db" / "hospital.db"
QUERY_DIR = REPO_ROOT / "queries"
OUT_DIR = REPO_ROOT / "output"


def has_sql(text: str) -> bool:
    return any(line.strip() and not line.strip().startswith("--") for line in text.splitlines())


def format_table(headers, rows, max_width=40):
    def cell(v):
        s = "NULL" if v is None else str(v)
        return s if len(s) <= max_width else s[: max_width - 3] + "..."

    body = [[cell(v) for v in r] for r in rows]
    widths = [max([len(h)] + [len(r[i]) for r in body]) for i, h in enumerate(headers)]
    line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    out = [line, "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |", line]
    out += ["| " + " | ".join(v.ljust(w) for v, w in zip(r, widths)) + " |" for r in body]
    out.append(line)
    out.append(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")
    return "\n".join(out)


def main():
    if not DB_PATH.exists():
        sys.exit(f"Database not found at {DB_PATH}. Run: python data/generate_data.py")

    wanted = {int(a) for a in sys.argv[1:]}
    OUT_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    for path in sorted(QUERY_DIR.glob("q*.sql")):
        n = int(path.stem[1:])
        if wanted and n not in wanted:
            continue
        sql = path.read_text()
        if not has_sql(sql):
            print(f"Q{n:02d}: not written yet, skipped")
            continue
        try:
            cur = conn.execute(sql)
            headers = [d[0] for d in cur.description]
            result = format_table(headers, cur.fetchall())
        except sqlite3.Error as e:
            result = f"ERROR: {e}"
        (OUT_DIR / f"q{n:02d}.txt").write_text(result + "\n")
        print(f"\n=== Q{n:02d} ===\n{result}")

    conn.close()


if __name__ == "__main__":
    main()
