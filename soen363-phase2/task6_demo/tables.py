"""
Task 6 result tables, built by running the queries in task6_demo/queries/ on output/integrated/hospital.db
(printed by show_tables.py).

    python show_tables.py --task 6
"""

PIPELINE_VERSION = "2026.11.17-tasks"   # run_all.py checks that every file has the same version

from task6_demo.run_demo import DB, NOTES, run_all_queries

PREVIEW_ROWS = 8


def _cells(rows):
    return [["NULL" if v is None else v for v in r] for r in rows]


def tables(d):
    if not DB.exists():
        raise SystemExit("No Task 6 results yet: run  python show_tables.py --task 6")
    results = run_all_queries(DB)
    demo = [r for r in results if r["kind"] == "demo"]
    phase1 = [r for r in results if r["kind"] == "phase1"]

    d.h("Task 6: Demonstration of the Integrated Database")
    d.h("6.1 Demonstration queries", 2)
    for r in demo:
        d.table(r["headers"], _cells(r["rows"]), caption=f"{r['id']}: {r['title']}")

    d.h("6.2 Phase 1 queries rerun on the integrated database", 2)
    d.table(["Query", "Topic", "Owner", "Rows in Phase 1", "Rows now", "Why the result changed"],
            [[r["id"].upper(), r["title"], r["owner"], r["phase1_rows"], len(r["rows"]), NOTES.get(r["id"], "")]
             for r in phase1],
            caption="The 20 Phase 1 queries: result size before and after integration")
    d.h("6.3 Results of the Phase 1 queries (first rows)", 2)
    for r in phase1:
        shown = min(PREVIEW_ROWS, len(r["rows"]))
        d.table(r["headers"], _cells(r["rows"][:PREVIEW_ROWS]),
                caption=f"{r['id'].upper()}: {r['title']} ({len(r['rows'])} rows, first {shown} shown)")
