"""
Task 3: integrates the four clean sources into one SQLite database with global surrogate keys.

    python -m task3_integration.integrate          (from the soen363-phase2 folder, after Task 2)

1. matches patients across sources (rules below) and decides which ones are merged
2. gives every record a new global key, in a fixed order (sources A, B, C, D; parents before children)
3. records every (entity, source, local key, original ID) -> global key in IdMapping
4. rewrites every foreign key through IdMapping, always with the row's own source
5. loads everything into output/integrated/hospital.db (schema: task3_integration/schema.sql) and also writes
   output/integrated/id_mapping.csv and patient_match_candidates.csv

Patient matching (cross-source only; Task 2 already removed duplicates within a source). Names are compared after
lowercasing, removing accents and punctuation; phones as digits only, without the country code or trunk 0.
  MERGE      same first + last name, same date of birth, same sex, and the same phone or the same address
  UNCERTAIN  same first + last name and date of birth, nothing else agreeing      (NAME_DOB)
             same last name and date of birth, different first name               (LASTNAME_DOB)
             same first + last name, date of birth one day apart or day/month swapped (NAME_DOB_NEAR)
             -> kept as separate patients, the pair is stored in PatientMatchCandidate
  MERGED_TRANSITIVE  an uncertain pair whose two records still end up as one patient because each was merged
             with the same other record; the pair keeps its rule and evidence, only the decision changes
  Anything else (including the same name alone) is not a match.
Healthcare professionals are never merged across sources: the hospitals are on different continents.
Standard library only.
"""

PIPELINE_VERSION = "2026.11.17-tasks"   # run_all.py checks that every file has the same version

import re
import sqlite3
import unicodedata
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from common.standards import SOURCES
from common.tabular import read_csv, write_csv

PHASE2 = Path(__file__).resolve().parents[1]
CLEAN = PHASE2 / "output" / "clean"
OUT = PHASE2 / "output" / "integrated"
SCHEMA = Path(__file__).resolve().parent / "schema.sql"
SOURCE_ORDER = ["A", "B", "C", "D"]

# file, table, primary key column, {foreign key column: parent table} - in load order (parents first)
ENTITIES = [
    ("professionals", "HealthcareProfessional", "professional_id", {}),
    ("patients", "Patient", "patient_id", {}),
    ("admissions", "Admission", "admission_id",
     {"patient_id": "Patient", "admitting_professional_id": "HealthcareProfessional"}),
    ("orders", "DiagnosticOrder", "order_id",
     {"admission_id": "Admission", "professional_id": "HealthcareProfessional"}),
    ("triage", "TriageAssessment", "triage_id",
     {"admission_id": "Admission", "nurse_id": "HealthcareProfessional"}),
    ("diagnoses", "Diagnosis", "diagnosis_id",
     {"admission_id": "Admission", "patient_id": "Patient", "professional_id": "HealthcareProfessional"}),
    ("notes", "ClinicalNote", "note_id",
     {"admission_id": "Admission", "author_id": "HealthcareProfessional"}),
    ("radiology", "RadiologyExamination", "exam_id",
     {"admission_id": "Admission", "order_id": "DiagnosticOrder",
      "referring_professional_id": "HealthcareProfessional", "technician_id": "HealthcareProfessional"}),
    ("procedures", "SurgicalProcedure", "procedure_id",
     {"admission_id": "Admission", "surgeon_id": "HealthcareProfessional"}),
    ("unit_stays", "UnitStay", "stay_id",
     {"admission_id": "Admission", "professional_id": "HealthcareProfessional"}),
    ("discharges", "DischargeRecord", "discharge_id",
     {"admission_id": "Admission", "professional_id": "HealthcareProfessional"}),
]
PATIENT_FIELDS = ["first_name", "last_name", "full_name", "date_of_birth", "sex", "address", "phone",
                  "emergency_contact_name", "emergency_contact_relationship", "emergency_contact_phone",
                  "life_status", "quality_flags"]


# -----------------------------------------------------------------------------------------------------------
# Patient matching
# -----------------------------------------------------------------------------------------------------------
def norm_text(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def norm_phone(s, src):
    digits = re.sub(r"\D", "", s or "")
    cc, trunk = SOURCES[src]["phone_country"], SOURCES[src]["phone_trunk"]
    if digits.startswith(cc):
        digits = digits[len(cc):]
    if trunk and digits.startswith(trunk):
        digits = digits[len(trunk):]
    return digits


def name_parts(p):
    first, last = norm_text(p["first_name"]), norm_text(p["last_name"])
    if not (first and last):                       # fall back on the full name: first token / last token
        toks = norm_text(p["full_name"]).split()
        first, last = (toks[0], toks[-1]) if len(toks) > 1 else ("", toks[0] if toks else "")
    return first, last


def near_dates(a, b):
    """One day apart, or the same date with day and month swapped."""
    try:
        da, db = date.fromisoformat(a), date.fromisoformat(b)
    except ValueError:
        return False
    return abs(da - db) == timedelta(days=1) or (da.year == db.year and da.month == db.day and da.day == db.month
                                                  and da != db)


def classify(p, q):
    """(decision, rule_code, evidence) for two patients from different sources, or None if no match."""
    pf, pl = name_parts(p)
    qf, ql = name_parts(q)
    same_name, same_last = bool(pl) and (pf, pl) == (qf, ql), bool(pl) and pl == ql
    same_dob = p["date_of_birth"] == q["date_of_birth"]
    if same_name and same_dob:
        same_sex = p["sex"] == q["sex"] and p["sex"] not in ("", "unknown")
        pp, qp = norm_phone(p["phone"], p["source_system"]), norm_phone(q["phone"], q["source_system"])
        same_phone = bool(pp) and pp == qp
        same_addr = bool(norm_text(p["address"])) and norm_text(p["address"]) == norm_text(q["address"])
        ev = (f"name+dob equal; sex {'equal' if same_sex else 'differs'}; phone {'equal' if same_phone else 'differs'}"
              f"; address {'equal' if same_addr else 'differs'}")
        if same_sex and (same_phone or same_addr):
            return "merged", "NAME_DOB_SEX_CONTACT", ev
        return "uncertain", "NAME_DOB", ev
    if same_last and same_dob:
        return "uncertain", "LASTNAME_DOB", f"last name + dob equal; first names '{pf}' / '{qf}'"
    if same_name and near_dates(p["date_of_birth"], q["date_of_birth"]):
        return "uncertain", "NAME_DOB_NEAR", f"name equal; dob {p['date_of_birth']} / {q['date_of_birth']}"
    return None


def match_patients(patients):
    """Candidate pairs, compared only within blocks (same dob, or same name) to avoid comparing everyone."""
    blocks = defaultdict(list)
    for p in patients:
        blocks["dob:" + p["date_of_birth"]].append(p)
        blocks["name:" + " ".join(name_parts(p))].append(p)
    seen, pairs = set(), []
    for members in blocks.values():
        for i, p in enumerate(members):
            for q in members[i + 1:]:
                if p["source_system"] == q["source_system"]:
                    continue
                if p["source_system"] > q["source_system"]:
                    p, q = q, p
                key = (p["source_system"], p["patient_id"], q["source_system"], q["patient_id"])
                if key in seen:
                    continue
                seen.add(key)
                c = classify(p, q)
                if c:
                    pairs.append((p, q) + c)
    return sorted(pairs, key=lambda t: (t[0]["source_system"], int(t[0]["patient_id"]),
                                        t[1]["source_system"], int(t[1]["patient_id"])))


def merge_groups(patients, pairs):
    """Union-find over the 'merged' pairs. Returns {(src, local id): survivor (src, local id)}."""
    order = {(p["source_system"], p["patient_id"]): (SOURCE_ORDER.index(p["source_system"]), int(p["patient_id"]))
             for p in patients}
    parent = {k: k for k in order}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for p, q, decision, *_ in pairs:
        if decision == "merged":
            a, b = find((p["source_system"], p["patient_id"])), find((q["source_system"], q["patient_id"]))
            if a != b:                                           # the earliest source record survives
                parent[max(a, b, key=order.get)] = min(a, b, key=order.get)
    return {k: find(k) for k in order}


# -----------------------------------------------------------------------------------------------------------
# Integration
# -----------------------------------------------------------------------------------------------------------
def load_clean(name):
    _, rows = read_csv(CLEAN / f"{name}.csv")
    return sorted(rows, key=lambda r: (SOURCE_ORDER.index(r["source_system"]), int(list(r.values())[2])))


def fix_admission_status(admissions):
    """Task 2 flags admissions marked discharged/deceased with no discharge time (status_inconsistent) but keeps
    them, and the schema's status CHECK rejects them. If the same source has a discharge record for the admission,
    its discharge time is used; otherwise the status is set to unknown (NULL). The flag stays on the row."""
    disch = {(d["source_system"], d["admission_id"]): d["discharge_time"] for d in load_clean("discharges")}
    for a in admissions:
        if a["admission_status"] in ("discharged", "deceased") and not a["discharge_time"]:
            t = disch.get((a["source_system"], a["admission_id"]))
            if t:
                a["discharge_time"] = t
                a["quality_flags"] += ";discharge_time_from_discharge_record"
            else:
                a["admission_status"] = ""
                a["quality_flags"] += ";admission_status_set_unknown"
    return admissions


def integrate():
    mapping = {}            # (table, src, local id) -> global id
    id_rows = []            # IdMapping rows
    out = {}                # table -> rows ready to insert

    # Patients first: decide merges, then number one Patient per merge group
    patients = load_clean("patients")
    pairs = match_patients(patients)
    survivor = merge_groups(patients, pairs)
    by_key = {(p["source_system"], p["patient_id"]): p for p in patients}
    group_id, patient_rows = {}, []
    for p in patients:                                           # already in A..D, local id order
        k = (p["source_system"], p["patient_id"])
        s = survivor[k]
        if s not in group_id:
            group_id[s] = len(group_id) + 1
            members = [by_key[m] for m in by_key if survivor[m] == s]
            row = {"patient_id": group_id[s]}
            for f in PATIENT_FIELDS:                             # survivor's value, else the first non-empty one
                row[f] = next((m[f] for m in members if m[f]), "")
            if len(members) > 1:
                row["quality_flags"] = ";".join(filter(None, [row["quality_flags"], "merged:" + ",".join(
                    f"{m['source_system']}{m['patient_id']}" for m in members)]))
            patient_rows.append(row)
        mapping[("Patient",) + k] = group_id[s]
        id_rows.append(dict(entity_type="Patient", source_system=k[0], source_local_id=k[1],
                            source_record_id=p["source_record_id"], integrated_id=group_id[s]))
    out["Patient"] = patient_rows

    candidates = []
    for i, (p, q, decision, rule, ev) in enumerate(pairs, 1):
        pid1 = mapping[("Patient", p["source_system"], p["patient_id"])]
        pid2 = mapping[("Patient", q["source_system"], q["patient_id"])]
        # an 'uncertain' pair can still end up as one patient if both sides got merged with the same third record
        # (A1~B1 merged, B1~C1 merged, A1~C1 uncertain). union-find already joined them, so relabel the pair
        # instead of letting the CHECK on PatientMatchCandidate blow up. rule + evidence stay as they were
        if decision == "uncertain" and pid1 == pid2:
            decision = "merged_transitive"
            ev += "; same patient through other merged pairs"
        candidates.append(dict(
            candidate_id=i,
            source_system_1=p["source_system"], source_local_id_1=p["patient_id"], patient_id_1=pid1,
            source_system_2=q["source_system"], source_local_id_2=q["patient_id"], patient_id_2=pid2,
            rule_code=rule, evidence=ev, decision=decision))
    out["PatientMatchCandidate"] = candidates

    # Every other entity: new sequential key, then rewrite its foreign keys with the row's own source
    for name, table, pk, fks in ENTITIES:
        if table == "Patient":
            continue
        rows = []
        for r in (fix_admission_status(load_clean(name)) if table == "Admission" else load_clean(name)):
            src, local = r["source_system"], r[pk]
            new = len(rows) + 1
            mapping[(table, src, local)] = new
            id_rows.append(dict(entity_type=table, source_system=src, source_local_id=local,
                                source_record_id=r["source_record_id"], integrated_id=new))
            r = dict(r, **{pk: new})
            for col, parent in fks.items():
                if r[col] == "":
                    continue                                     # nullable FK (e.g. radiology.order_id)
                try:
                    r[col] = mapping[(parent, src, r[col])]
                except KeyError:
                    raise SystemExit(f"{table} {src}:{local}: {col}={r[col]} has no {parent} in source {src}")
            rows.append(r)
        out[table] = rows
    return out, id_rows


def build_db(out, id_rows, db_path):
    db_path.unlink(missing_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.executemany("INSERT INTO SourceSystem VALUES (?, ?, ?, ?, ?)",
                    [(s, SOURCES[s]["continent"], SOURCES[s]["name"], SOURCES[s]["format"], SOURCES[s]["timezone"])
                     for s in SOURCE_ORDER])
    _, icd = read_csv(CLEAN / "icd9_codes.csv")
    tables = {"ICD9Dictionary": icd, "IdMapping": id_rows, **out}
    for table, rows in tables.items():
        cols = [c[1] for c in con.execute(f"PRAGMA table_info({table})")]
        con.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                        [[None if r.get(c) in ("", None) else r[c] for c in cols] for r in rows])
    con.commit()
    bad = con.execute("PRAGMA foreign_key_check").fetchall()
    con.close()
    if bad:
        raise SystemExit(f"Foreign key check failed: {bad[:5]}")


def run(out_dir=OUT, quiet=False):
    out_dir.mkdir(parents=True, exist_ok=True)
    out, id_rows = integrate()
    build_db(out, id_rows, out_dir / "hospital.db")
    write_csv(out_dir / "id_mapping.csv", id_rows,
              ["entity_type", "source_system", "source_local_id", "source_record_id", "integrated_id"])
    cand = out["PatientMatchCandidate"]
    write_csv(out_dir / "patient_match_candidates.csv", cand, list(cand[0]) if cand else ["candidate_id"])
    if not quiet:
        merged = sum(c["decision"] in ("merged", "merged_transitive") for c in cand)   # both mean same patient
        print(f"  {len(id_rows)} source records mapped; {len(out['Patient'])} patients "
              f"({merged} merged pairs, {len(cand) - merged} uncertain pairs kept separate)")
        print(f"  -> {out_dir / 'hospital.db'}")
    return out, id_rows


if __name__ == "__main__":
    run()
