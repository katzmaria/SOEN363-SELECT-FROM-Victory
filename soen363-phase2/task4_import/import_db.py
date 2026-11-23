"""
Task 4: imports the integrated data (Task 3) into the SQLite database defined by task3_integration/schema.sql.

    python -m task4_import.import_db          (from the soen363-phase2 folder, after Task 2)

How the import works
1. Task 3's integrate() gives the rows of every table with their global keys and rewritten foreign keys.
2. The load order is derived from the schema itself (PRAGMA foreign_key_list): a table is loaded only after
   every table it references. The order is checked again before inserting.
3. Every insert is a parameterized executemany (no values are ever pasted into the SQL text). Empty strings
   become NULL so the schema's NOT NULL / CHECK constraints see real missing values.
4. The whole import is ONE transaction, with PRAGMA foreign_keys = ON, so a bad row fails at once. On any error
   the transaction is rolled back and the error names the table, the source and the original record ID.
5. Before COMMIT: row counts per table must equal what Task 3 produced, and PRAGMA foreign_key_check and
   integrity_check must be empty / 'ok'.

Rerun behaviour: REBUILD, not update. The database is built in output/integrated/hospital.db.tmp and only moved
over hospital.db (os.replace, atomic) once it has passed every check. A failed run leaves the previous database
untouched. Because Task 3's keys are assigned in a fixed order, every rerun gives the same keys and the same rows,
and UNIQUE (source_system, source_record_id) on every table makes an accidental double insert fail loudly instead
of duplicating data. import_log.csv records a checksum per table so two runs can be compared.
Standard library only.
"""

PIPELINE_VERSION = "2026.11.17-tasks"   # run_all.py checks that every file has the same version

import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from common.standards import SOURCES
from common.tabular import read_csv, write_csv
from task3_integration.integrate import CLEAN, OUT, SCHEMA, SOURCE_ORDER, integrate


class ImportError_(Exception):
    """An import failure, with the table and source record that caused it."""


# -----------------------------------------------------------------------------------------------------------
# Load order, derived from the schema
# -----------------------------------------------------------------------------------------------------------
def schema_tables(con):
    return [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid")]


def dependencies(con):
    """{table: set of tables it references}, read from the schema (self-references ignored)."""
    return {t: {r[2] for r in con.execute(f"PRAGMA foreign_key_list({t})")} - {t} for t in schema_tables(con)}


def load_order(con):
    """Topological order: every table after all the tables it references. Ties keep the schema's order."""
    deps, order, done = dependencies(con), [], set()
    while len(order) < len(deps):
        ready = [t for t in deps if t not in done and deps[t] <= done]
        if not ready:
            raise ImportError_(f"Foreign key cycle between: {sorted(set(deps) - done)}")
        order.append(ready[0])
        done.add(ready[0])
    return order


# -----------------------------------------------------------------------------------------------------------
# Rows to insert
# -----------------------------------------------------------------------------------------------------------
def collect_rows(out=None, id_rows=None):
    """{table: list of dict rows} for every table in the schema, from Task 3's integrate() (run here if the
    caller did not pass its result)."""
    if out is None:
        out, id_rows = integrate()
    _, icd = read_csv(CLEAN / "icd9_codes.csv")
    source_rows = [dict(source_system=s, continent=SOURCES[s]["continent"], hospital_name=SOURCES[s]["name"],
                        file_format=SOURCES[s]["format"], source_timezone=SOURCES[s]["timezone"])
                   for s in SOURCE_ORDER]
    return {"SourceSystem": source_rows, "ICD9Dictionary": icd, "IdMapping": id_rows, **out}


def to_param(v):
    """Value for a ? placeholder: empty / whitespace-only text is a missing value (NULL)."""
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None
    return v


def describe(table, row):
    """Where a row comes from, for error messages: 'Admission B:ADM00042' or 'ICD9Dictionary 250.00'."""
    if row.get("source_system") and row.get("source_record_id"):
        return f"{table} {row['source_system']}:{row['source_record_id']}"
    return f"{table} {next(iter(row.values()), '?')}"


def insert_table(con, table, rows):
    cols = [c[1] for c in con.execute(f"PRAGMA table_info({table})")]
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"
    params = [[to_param(r.get(c)) for c in cols] for r in rows]
    con.execute("SAVEPOINT tbl")
    try:
        con.executemany(sql, params)
    except sqlite3.DatabaseError as e:
        con.execute("ROLLBACK TO tbl")
        # executemany only says e.g. "FOREIGN KEY constraint failed", not which row. Retry the rows one by one
        # inside the still-open savepoint to name them (up to 5, so one systematic problem shows as a pattern),
        # then undo the retry: the import is all-or-nothing either way.
        bad = []
        for row, p in zip(rows, params):
            try:
                con.execute(sql, p)
            except sqlite3.DatabaseError as row_err:
                bad.append(f"{describe(table, row)}: {row_err}")
                if len(bad) == 5:
                    break
        con.execute("ROLLBACK TO tbl")
        con.execute("RELEASE tbl")
        raise ImportError_(f"{table}: import stopped, nothing was committed. "
                           + ("; ".join(bad) or f"no single row fails on its own ({e})")) from e
    con.execute("RELEASE tbl")
    return len(rows)


def table_checksum(con, table):
    """SHA-256 of every row in primary key order: equal checksums on two runs = identical table contents."""
    h = hashlib.sha256()
    for row in con.execute(f"SELECT * FROM {table} ORDER BY 1, 2, 3"):
        h.update(repr(row).encode())
    return h.hexdigest()[:16]


# -----------------------------------------------------------------------------------------------------------
# The import
# -----------------------------------------------------------------------------------------------------------
def import_all(db_path=OUT / "hospital.db", rows_by_table=None):
    """Builds db_path from scratch in one transaction; returns the import log (one dict per table)."""
    rows_by_table = rows_by_table if rows_by_table is not None else collect_rows()
    tmp = db_path.with_suffix(db_path.suffix + ".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp, isolation_level=None)            # autocommit off only where we say BEGIN
    try:
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        con.execute("PRAGMA foreign_keys = ON")
        order = load_order(con)
        missing = set(rows_by_table) - set(order)
        if missing:
            raise ImportError_(f"No table in the schema for: {sorted(missing)}")

        con.execute("BEGIN")
        log, loaded = [], set()
        for table in order:
            assert dependencies(con)[table] <= loaded, f"{table} would be loaded before its parents"
            n = insert_table(con, table, rows_by_table.get(table, []))
            loaded.add(table)
            log.append({"table": table, "expected_rows": n})

        # checks before COMMIT: nothing lost, nothing dangling
        for entry in log:
            entry["db_rows"] = con.execute(f"SELECT COUNT(*) FROM {entry['table']}").fetchone()[0]
            if entry["db_rows"] != entry["expected_rows"]:
                raise ImportError_(f"{entry['table']}: {entry['db_rows']} rows in the database, "
                                   f"{entry['expected_rows']} expected")
        bad_fk = con.execute("PRAGMA foreign_key_check").fetchall()
        if bad_fk:
            raise ImportError_(f"Foreign key check failed: {bad_fk[:5]}")
        ok = con.execute("PRAGMA integrity_check").fetchone()[0]
        if ok != "ok":
            raise ImportError_(f"Integrity check failed: {ok}")
        con.execute("COMMIT")

        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for entry in log:
            entry.update(checksum=table_checksum(con, entry["table"]), imported_at=stamp)
    except BaseException:
        if con.in_transaction:
            con.execute("ROLLBACK")
        con.close()
        tmp.unlink(missing_ok=True)                              # the previous hospital.db is untouched
        raise
    con.close()
    os.replace(tmp, db_path)                                     # atomic swap: old DB until this line
    return log


def run(out_dir=OUT, quiet=False):
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "import_log.csv"
    previous = {}
    if log_path.exists():
        previous = {r["table"]: r["checksum"] for r in read_csv(log_path)[1]}
    log = import_all(out_dir / "hospital.db")
    for entry in log:
        entry["same_as_previous_run"] = ("" if entry["table"] not in previous
                                         else "yes" if previous[entry["table"]] == entry["checksum"] else "no")
    write_csv(log_path, log, ["table", "expected_rows", "db_rows", "checksum", "same_as_previous_run",
                              "imported_at"])
    if not quiet:
        total = sum(e["db_rows"] for e in log)
        print(f"  {total} rows imported into {len(log)} tables (one transaction, parents first)")
        if previous:
            changed = [e["table"] for e in log if e["same_as_previous_run"] == "no"]
            print("  rerun: identical to the previous import" if not changed
                  else f"  rerun: contents changed in {', '.join(changed)}")
        print(f"  -> {out_dir / 'hospital.db'}, {log_path.name}")
    return log


if __name__ == "__main__":
    run()
