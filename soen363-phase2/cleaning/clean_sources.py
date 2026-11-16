"""
Task 2 - Clean and standardise the raw sources (reproducible: same input -> same output).

    python cleaning/clean_sources.py                    (run from soen363-phase2/)
    python cleaning/clean_sources.py --icd9 ../soen363-phase1/data/icd9_dictionary.csv

Writes
    output/clean/<entity>.csv              clean records of all sources (key = source_system + <entity>_id)
    output/clean/icd9_codes.csv            the ICD-9 dictionary (normalised codes)
    output/quarantine/<entity>.csv         rejected records and removed duplicates, with the reason(s)
    output/quarantine/malformed_records.csv  records that could not be read at all
    output/cleaning_log/cleaning_log.csv   every correction / NULL / flag / rejection, field by field
    output/cleaning_log/label_mappings.csv every raw label -> standard value, with counts
    output/cleaning_log/summary.csv        counts per source and entity
    output/cleaning_report.md              rules, results and before/after examples

Pipeline per source (in this order):
    1. load (malformed records are logged by the loader)
    2. exact duplicates: same ID and every field equal after trimming and ignoring case -> removed
       same ID but different content -> the later copy is rejected (duplicate_id_conflict)
    3. field cleaning: placeholders -> missing, IDs, text, dates/time zones, numbers/units, labels, ICD-9
       missing REQUIRED or invalid REQUIRED value -> rejected; EXPECTED -> NULL + flag; OPTIONAL -> NULL
    4. text case standardisation (majority spelling of each value inside its column)
    5. entities in dependency order (professionals, patients, admissions, orders, radiology, children):
       a. re-point references to near-duplicates onto the kept record
       b. references: missing parent -> rejected (orphan_reference); parent quarantined -> rejected
          (parent_quarantined); inconsistent references (diagnosis patient vs admission patient,
          radiology admission vs its order's admission) -> rejected
       c. near duplicates (same entity key, no conflicting value in any other field) -> the lowest ID is
          kept, the others are removed and their missing values are filled from the duplicate; same key
          but a conflicting value -> both kept and flagged possible_duplicate
       d. chronology checks -> rejected (or flagged when it is only a soft inconsistency)
    6. write outputs
"""

from __future__ import annotations

PIPELINE_VERSION = "2026.11.15-abcd"   # run_all.py checks that every file has the same version

import argparse
import datetime as dt
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PHASE2 = Path(__file__).resolve().parents[1]
if str(PHASE2) not in sys.path:
    sys.path.insert(0, str(PHASE2))

from cleaning import parsers as P
from cleaning.tabular import md_table, read_csv, write_csv
from cleaning.standards import (COLUMN_MAP, ENTITY_SPECS, EVENT_TIME, LABEL_LOOKUP, LEVEL_OVERRIDES, OUTPUT_COLUMNS,
                                PROCESS_ORDER,
                                SOURCES, VITAL_RANGES)
from profiling.load_sources import ENTITIES, load_all

OUT = PHASE2 / "output"
ICD_DEFAULT = PHASE2.parent / "soen363-phase1" / "data" / "icd9_dictionary.csv"
# Categories with no fixed list in the contract: an unknown value is kept as text (with a flag), not rejected.
LABEL_KEEP_TEXT = {"procedure", "exam_type", "body_area"}
# Two staff with the same name, role and department are kept apart (flagged) only if BOTH IDs are used by at
# least this many clinical records: then they are most likely two real people with the same name.
STAFF_IN_USE = 10


# =============================================================================
# Records and the cleaning log
# =============================================================================
class Rec:
    __slots__ = ("entity", "src", "raw", "sid", "id", "val", "flags", "rejects", "loc", "raw_record", "status",
                 "dup_of")

    def __init__(self, entity, src, raw, loc, raw_record):
        self.entity, self.src, self.raw, self.loc, self.raw_record = entity, src, raw, loc, raw_record
        self.sid = None if raw.get(ENTITY_SPECS[entity]["pk"]) is None else str(raw[ENTITY_SPECS[entity]["pk"]])
        self.id = None
        self.val = {}
        self.flags = []
        self.rejects = []                  # (reason_code, detail)
        self.status = "ok"                 # ok | rejected | duplicate
        self.dup_of = None


LOG = []
LABEL_COUNTS = Counter()


def log(rec, field, rule, action, before=None, after=None, detail=""):
    LOG.append({"source_system": rec.src, "entity": rec.entity, "source_record_id": rec.sid,
                "source_row": rec.loc, "field": field, "rule": rule, "action": action,
                "before": "" if before is None else str(before), "after": "" if after is None else _show(after),
                "detail": detail})


def _show(v):
    if isinstance(v, dt.datetime):
        return P.iso_utc(v)
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, tuple):
        return "/".join(map(str, v))
    return str(v)


def reject(rec, code, detail=""):
    rec.rejects.append((code, detail))
    if rec.status == "ok":
        rec.status = "rejected"
    log(rec, code.split(":", 1)[1] if ":" in code else "", code.split(":", 1)[0], "rejected", detail=detail)


def flag(rec, code, field="", before=None, detail=""):
    if code not in rec.flags:
        rec.flags.append(code)
    log(rec, field, code.split(":", 1)[0], "flagged", before, None, detail)


# =============================================================================
# Field cleaning
# =============================================================================
class Out:
    __slots__ = ("value", "problem", "detail", "fixes")

    def __init__(self, value=None, problem=None, detail="", fixes=()):
        self.value, self.problem, self.detail, self.fixes = value, problem, detail, list(fixes)


MISSING = object()


def clean_value(rec, f, kind, ctx):
    raw = rec.raw.get(f)
    numeric = kind in ("bp", "temperature", "spo2") or kind.startswith("vital:")
    if P.is_missing(raw, numeric=numeric):
        return MISSING
    s = P.collapse_ws(str(raw))
    ws_fix = ["whitespace_trimmed"] if s != str(raw) else []
    src = rec.src
    cfg = SOURCES[src]

    if kind == "id" or kind.startswith("fk:"):
        v = P.parse_id(s)
        return Out(v, None if v is not None else "invalid_id", f"{s!r} is not an identifier")

    if kind == "name":
        fixes = list(ws_fix)
        m = re.fullmatch(r"([^,]+),\s*([^,]+)", s)               # 'SURNAME, Given' -> 'Given Surname'
        if m:
            s = f"{m.group(2)} {m.group(1)}"
            fixes.append("name_reordered")
        v = P.smart_title(s)
        return Out(v, fixes=fixes + (["case_standardised"] if v.casefold() == s.casefold() and v != s else []))

    if kind in ("text", "free_text"):
        return Out(s, fixes=ws_fix)

    if kind == "room":                                     # 'SIC-03' is a code (upper case); 'Ward 6B' is text
        if re.fullmatch(r"[A-Za-z]{2,5}-?\d+[A-Za-z]?", s):
            return Out(s.upper(), fixes=ws_fix + (["case_standardised"] if s.upper() != s else []))
        return Out(s, fixes=ws_fix)

    if kind == "code":
        return Out(s.upper(), fixes=ws_fix + (["case_standardised"] if s.upper() != s else []))

    if kind == "lower_list":
        v = ", ".join(p.strip() for p in s.lower().split(",") if p.strip())
        return Out(v, fixes=ws_fix + (["case_standardised"] if v != s else []))

    if kind == "none_or_text":
        if P.none_known(s):
            return Out("none", fixes=["none_known_standardised"] if s != "none" else [])
        return Out(s, fixes=ws_fix)

    if kind.startswith("label:"):
        key = kind.split(":", 1)[1]
        std = LABEL_LOOKUP[src][key].get(s.lower())
        LABEL_COUNTS[(src, rec.entity, f, s, std or ("<kept as text>" if key in LABEL_KEEP_TEXT else "<unmapped>"))] += 1
        if std is None:
            if key in LABEL_KEEP_TEXT:
                return Out(s, fixes=["not_in_standard_list"])
            return Out(None, "unmappable_label", f"{s!r} has no standard {key} value")
        return Out(std, fixes=ws_fix + (["label_mapped"] if std != s else []))

    if kind in ("datetime", "date"):
        r = P.parse_temporal(s, ctx["tz"], want_time=kind == "datetime", opts=cfg["dates"])
        fixes = []
        if r.status == "invalid" and f == "follow_up_time":
            # 'Specialist clinic 21/01/2022 10:00': the appointment time written inside a sentence
            m = re.search(r"\d{1,2}/\d{1,2}/\d{4}(?:\s+\d{1,2}:\d{2}(?:\s?[AaPp][Mm])?)?", s)
            if m:
                r = P.parse_temporal(m.group(0), ctx["tz"], want_time=True, opts=cfg["dates"])
                if r.status == "invalid" and ":" not in m.group(0):
                    r = P.parse_temporal(m.group(0) + " 00:00", ctx["tz"], want_time=True, opts=cfg["dates"])
                fixes.append("datetime_extracted_from_text")
        if r.status == "ambiguous":
            return Out(None, "ambiguous_date", r.detail)
        if r.status != "ok":
            return Out(None, "invalid_date", r.detail)
        fixes += r.flags
        usual = cfg["usual_ts"] if kind == "datetime" else cfg["usual_date"]
        if r.fmt not in usual and not r.fmt.startswith("epoch"):
            fixes.append(f"date_format_standardised:{r.fmt}")
        if (kind == "datetime" and cfg["ts_offset"] and "+offset" not in r.fmt and not r.fmt.startswith("epoch")):
            fixes.append("no_offset_local_time_assumed")
        return Out(r.value, fixes=fixes)

    if kind == "phone":
        v = P.normalize_phone(s, cfg["phone_country"], cfg["phone_national_len"], cfg["phone_trunk"])
        if v is None:
            return Out(None, "invalid_phone", f"{s!r} is not a phone number")
        return Out(v, fixes=["phone_e164"])

    if kind == "contact":
        name, rel, phone = P.split_contact(s)
        ph = P.normalize_phone(phone, cfg["phone_country"], cfg["phone_national_len"], cfg["phone_trunk"]) \
            if phone else None
        return Out((P.smart_title(name) if name else None, rel.capitalize() if rel else None, ph),
                   fixes=["contact_split"])

    if kind == "bp":
        r = P.parse_bp(s)
        if r.status != "ok":
            return Out(None, "invalid_number", r.detail)
        sy, di = r.value
        lo_s, hi_s = VITAL_RANGES["systolic_bp"]
        lo_d, hi_d = VITAL_RANGES["diastolic_bp"]
        if not (lo_s <= sy <= hi_s and lo_d <= di <= hi_d and sy > di):
            return Out(None, "out_of_range", f"{s!r}: blood pressure outside {lo_s}-{hi_s} / {lo_d}-{hi_d}")
        return Out((sy, di), fixes=r.flags)

    if kind.startswith("vital:") or kind in ("temperature", "spo2"):
        if kind == "temperature":
            r = P.parse_temperature(s, rec.raw.get("temperature_unit"))
            rng_key = "temperature_c"
        elif kind == "spo2":
            r = P.parse_spo2(s, cfg["spo2_scale"])
            rng_key = "spo2_pct"
        else:
            r = P.parse_number(s)
            rng_key = kind.split(":", 1)[1]
        if r.status != "ok":
            return Out(None, "invalid_number", r.detail)
        lo, hi = VITAL_RANGES[rng_key]
        if not lo <= r.value <= hi:
            return Out(None, "out_of_range", f"{s!r} -> {r.value:g} outside {lo}-{hi}")
        v = r.value
        if kind.startswith("vital:"):
            if v != int(v):
                return Out(None, "invalid_number", f"{s!r} is not a whole number")
            v = int(v)
        return Out(v, fixes=r.flags)

    if kind == "icd9":
        code, fixes = P.normalize_icd9(raw)
        if code.startswith("INVALID:"):
            return Out(None, "invalid_icd9_format", f"{s!r} is not an ICD-9 code")
        if ctx["icd9"] is not None and code not in ctx["icd9"]:
            return Out(None, "unknown_icd9_code", f"{code!r} is not in the ICD-9 dictionary")
        return Out(code, fixes=fixes)

    raise ValueError(kind)


def field_level(src, entity, f):
    spec = ENTITY_SPECS[entity]
    over = LEVEL_OVERRIDES.get(src, {}).get(entity, {})
    if f in over:
        return over[f]
    return "required" if f in spec["required"] else "expected" if f in spec["expected"] else "optional"


def compose_full_name(src, given, family):
    """Full name in the hospital's own order: A given + family; C family + given (Chinese names), except
    Malay/Indian names ('.. bin', '.. d/o') which are given + family."""
    if SOURCES[src]["name_order"] == "given_first" or (given or "").endswith(("bin", "binte", "d/o", "s/o")):
        return " ".join(x for x in (given, family) if x) or None
    return " ".join(x for x in (family, given) if x) or None


def clean_fields(rec, ctx):
    spec = ENTITY_SPECS[rec.entity]
    for f, kind in spec["fields"].items():
        level = field_level(rec.src, rec.entity, f)
        out = clean_value(rec, f, kind, ctx)
        raw = rec.raw.get(f)
        if out is MISSING:
            rec.val[f] = None
            if level == "required":
                reject(rec, f"missing_required:{f}", f"raw value {raw!r}")
            elif level == "expected":
                flag(rec, f"missing_expected:{f}", f, raw)
            elif raw is not None and P.collapse_ws(str(raw)) != "":
                log(rec, f, "placeholder_to_null", "set_null", raw, None)
            continue
        if out.problem:
            rec.val[f] = None
            if level == "required":
                reject(rec, f"{out.problem}:{f}", out.detail)
            else:
                rec.flags.append(f"{out.problem}:{f}")
                log(rec, f, out.problem, "set_null", raw, None, out.detail)
            continue
        rec.val[f] = out.value
        for fx in out.fixes:
            if fx.startswith("dst_"):
                rec.flags.append(f"{fx}:{f}")
                log(rec, f, fx, "flagged", raw, out.value, "local time ambiguous/non-existent at a DST change")
            elif fx not in ("label_mapped", "phone_e164", "contact_split"):
                log(rec, f, fx.split(":")[0], "corrected", raw, out.value, fx)


# =============================================================================
# Text case: the majority spelling of a value inside its column
# =============================================================================
def standardise_case(recs):
    """Short descriptive text ('text', 'none_or_text'): every value takes the spelling used most often for it
    in its column. Clinical free text ('free_text'): changed ONLY when the whole value is case-damaged
    (all capitals, all lower case or inverted case) and the same text exists elsewhere with normal case;
    an inverted value with no such twin is swapped back. Anything else a clinician wrote stays as written."""
    by_field = defaultdict(list)
    kinds = {}
    for r in recs:
        if r.status == "duplicate":
            continue
        for f, kind in ENTITY_SPECS[r.entity]["fields"].items():
            keep_text_label = kind.startswith("label:") and kind.split(":", 1)[1] in LABEL_KEEP_TEXT
            if (kind in ("text", "none_or_text", "free_text", "room") or keep_text_label) and isinstance(r.val.get(f), str):
                by_field[f].append(r)
                kinds[f] = "text" if keep_text_label or kind == "room" else kind
    for f, rows in by_field.items():
        forms = defaultdict(Counter)
        for r in rows:
            forms[r.val[f].casefold()][r.val[f]] += 1
        free = kinds[f] == "free_text"
        for r in rows:
            v = r.val[f]
            good = [(n, s) for s, n in forms[v.casefold()].items() if not P.case_damaged(s)
                    and not (free and P.all_lower(s))]
            if free:
                if not (P.case_damaged(v) or P.all_lower(v)) or (not good and not P.case_inverted(v)):
                    continue
                new = max(good, key=lambda t: (t[0], t[1]))[1] if good else v.swapcase()
            else:
                ranked = sorted(forms[v.casefold()].items(), key=lambda kv: (-kv[1], P.case_damaged(kv[0]), kv[0]))
                new = ranked[0][0]
                if P.case_inverted(new):               # no good spelling seen anywhere: swap it back
                    new = new.swapcase()
            if new != v:
                log(r, f, "case_standardised", "corrected", v, new)
                r.val[f] = new


# =============================================================================
# Exact duplicates
# =============================================================================
def norm_raw(rec):
    return tuple(P.collapse_ws(str(v)).casefold() if v is not None else "" for k, v in sorted(rec.raw.items()))


def exact_duplicates(recs):
    first = {}
    for r in recs:
        if r.sid is None or P.is_missing(r.sid):
            continue
        key = P.collapse_ws(r.sid).casefold()
        if key not in first:
            first[key] = r
            continue
        f0 = first[key]
        if norm_raw(r) == norm_raw(f0):
            r.status, r.dup_of = "duplicate", f0.sid
            r.rejects.append(("exact_duplicate", f"same ID and same values as {f0.loc}"))
            log(r, "", "exact_duplicate", "removed_duplicate", detail=f"duplicate of {f0.loc}")
        else:
            reject(r, "duplicate_id_conflict", f"ID already used by {f0.loc} with different values")


# =============================================================================
# Entity processing: references, near duplicates, chronology
# =============================================================================
def dup_key(r):
    v = r.val
    e = r.entity
    if e == "professionals":
        k = ((v["full_name"] or "").casefold() or None, v["role"], (v["department"] or "").casefold() or None)
    elif e == "patients":
        k = ((v["full_name"] or "").casefold() or None, v["date_of_birth"])
    else:
        k = tuple(v.get(f) for f in ENTITY_SPECS[e]["dup_key"])
    # admission + timestamp must be known; the 'type' part of a child key may be empty (e.g. no test name)
    need = k if e in ("professionals", "patients", "admissions") else k[:2]
    return None if any(x is None for x in need) else k


def conflicts(a, b):
    """Fields (other than the ID) where both records have a value and the values differ."""
    out = []
    for f in ENTITY_SPECS[a.entity]["fields"]:
        if f == ENTITY_SPECS[a.entity]["pk"]:
            continue
        x, y = a.val.get(f), b.val.get(f)
        if x is None or y is None:
            continue
        if isinstance(x, str) and isinstance(y, str):
            x, y = re.sub(r"[\W_]+", "", x.casefold()), re.sub(r"[\W_]+", "", y.casefold())
        if x != y:
            out.append(f)
    return out


def process_source(code, recs, ctx):
    extract = ctx["extract_utc"]
    all_ids = {e: {r.id for r in recs[e] if r.id is not None} for e in ENTITIES}
    remap = defaultdict(dict)
    kept = {}
    prof_refs = Counter(r.val.get(f) for e2 in ENTITIES for r in recs[e2] if r.status != "duplicate"
                        for f, k in ENTITY_SPECS[e2]["fields"].items() if k == "fk:professionals")
    for e in PROCESS_ORDER:
        spec = ENTITY_SPECS[e]
        rows = [r for r in recs[e] if r.status != "duplicate"]
        fks = {f: k.split(":", 1)[1] for f, k in spec["fields"].items() if k.startswith("fk:")}

        # a. re-point references to near duplicates
        for r in rows:
            for f, target in fks.items():
                v = r.val.get(f)
                if v is not None and v in remap[target]:
                    r.val[f] = remap[target][v]
                    log(r, f, "repointed_to_kept_duplicate", "corrected", v, r.val[f],
                        f"{target} {v} is a duplicate of {r.val[f]}")

        # b. references
        for r in rows:
            if r.status != "ok":
                continue
            for f, target in fks.items():
                v = r.val.get(f)
                if v is None:
                    continue
                if v not in all_ids[target]:
                    reject(r, f"orphan_reference:{f}", f"{target} {v} does not exist in source {code}")
                elif v not in kept[target]:
                    reject(r, f"parent_quarantined:{f}", f"{target} {v} is in the quarantine")
            if r.status != "ok":
                continue
            if e == "diagnoses":
                adm = kept["admissions"][r.val["admission_id"]]
                if r.val["patient_id"] is None:
                    r.val["patient_id"] = adm.val["patient_id"]
                    log(r, "patient_id", "derived_from_admission", "corrected", None, r.val["patient_id"])
                elif r.val["patient_id"] != adm.val["patient_id"]:
                    reject(r, "inconsistent_reference:patient_id",
                           f"diagnosis patient {r.val['patient_id']} but admission {adm.id} belongs to patient "
                           f"{adm.val['patient_id']}")
            if e == "radiology" and r.val.get("order_id") is not None and r.status == "ok":
                o = kept["orders"][r.val["order_id"]]
                if o.val["admission_id"] != r.val["admission_id"]:
                    reject(r, "inconsistent_reference:order_id",
                           f"order {o.id} belongs to admission {o.val['admission_id']}")
            role_need = {"nurse_id": "nurse", "surgeon_id": "surgeon", "technician_id": "radiology_technician"}
            for f, need in role_need.items():
                if f in fks and r.val.get(f) is not None and r.status == "ok":
                    role = kept["professionals"][r.val[f]].val.get("role")
                    if role is not None and role != need:
                        flag(r, f"role_mismatch:{f}", f, r.val[f], f"professional is a {role}, expected {need}")

        # c. near duplicates. Children are grouped on admission + timestamp; inside a group two records match
        #    when their 'type' parts are equal or one of them is empty (e.g. an order with no test name).
        child = e not in ("professionals", "patients", "admissions")
        groups = defaultdict(list)
        for r in rows:
            if r.status == "ok":
                k = dup_key(r)
                if k is not None:
                    groups[k[:2] if child else k].append(r)

        def compatible(a, b):
            ka, kb = dup_key(a), dup_key(b)
            return all(x is None or y is None or x == y for x, y in zip(ka[2:], kb[2:])) if child else True

        for k, grp in groups.items():
            if len(grp) < 2:
                continue
            grp.sort(key=lambda x: x.id)
            survivors = [grp[0]]
            for d in grp[1:]:
                keep = next((x for x in survivors if compatible(x, d)), None)
                if keep is None:
                    survivors.append(d)
                    continue
                clash = conflicts(keep, d)
                if clash:
                    # same key but a different fact elsewhere (e.g. another order): two real records
                    for a, b in ((keep, d), (d, keep)):
                        flag(a, f"possible_duplicate:{spec['pk']}", spec["pk"], a.id,
                             f"same {' + '.join(spec['dup_key'])} as {b.id} but different {', '.join(clash)}")
                    survivors.append(d)
                    continue
                if e == "professionals" and prof_refs[d.id] >= STAFF_IN_USE and prof_refs[keep.id] >= STAFF_IN_USE:
                    # Staff have no date of birth: name + role + department is a weak key. When BOTH IDs are
                    # used by clinical records they are most likely two people with the same name -> keep both.
                    for a, b in ((keep, d), (d, keep)):
                        flag(a, "possible_duplicate:professional_id", "professional_id", a.id,
                             f"same name, role and department as professional {b.id}; both IDs are used by "
                             f"{STAFF_IN_USE}+ clinical records")
                    survivors.append(d)
                    continue
                d.status, d.dup_of = "duplicate", keep.sid
                d.rejects.append(("near_duplicate", f"same {', '.join(spec['dup_key'])} as {spec['pk']} {keep.id}"))
                log(d, "", "near_duplicate", "removed_duplicate", detail=f"kept {spec['pk']} {keep.id}")
                remap[e][d.id] = keep.id
                for f in spec["fields"]:
                    if keep.val.get(f) is None and d.val.get(f) is not None:
                        keep.val[f] = d.val[f]
                        log(keep, f, "filled_from_duplicate", "corrected", None, d.val[f],
                            f"value taken from duplicate {spec['pk']} {d.id}")
        rows = [r for r in rows if r.status != "duplicate"]

        # d. chronology
        for r in rows:
            if r.status != "ok":
                continue
            v = r.val
            if e == "patients":
                if v["date_of_birth"] > extract.date():
                    reject(r, "chronology:date_of_birth", "date of birth after the extract date")
                elif (extract.date() - v["date_of_birth"]).days > 120 * 365.25:
                    flag(r, "implausible_age:date_of_birth", "date_of_birth", v["date_of_birth"])
            elif e == "admissions":
                pat = kept["patients"][v["patient_id"]]
                admit_local = v["admit_time"].astimezone(ctx["tz"]).date()
                if admit_local < pat.val["date_of_birth"]:
                    reject(r, "chronology:admit_time", f"admission {P.iso_utc(v['admit_time'])} before date of "
                                                       f"birth {pat.val['date_of_birth']}")
                if v["admit_time"] > extract:
                    reject(r, "chronology:admit_time", "admission after the extract time")
                if v["discharge_time"] is not None:
                    if v["discharge_time"] < v["admit_time"]:
                        reject(r, "chronology:discharge_time", f"discharge {P.iso_utc(v['discharge_time'])} before "
                                                               f"admission {P.iso_utc(v['admit_time'])}")
                    elif v["discharge_time"] > extract:
                        reject(r, "chronology:discharge_time", "discharge after the extract time")
                if r.status == "ok":
                    st, dis = v["admission_status"], v["discharge_time"]
                    if st == "active" and dis is not None:
                        flag(r, "status_inconsistent:admission_status", "admission_status", st,
                             "status active but a discharge time is recorded")
                    if st in ("discharged", "deceased") and dis is None:
                        flag(r, "status_inconsistent:admission_status", "admission_status", st,
                             "discharged/deceased but no discharge time")
            elif e in EVENT_TIME:
                tf = EVENT_TIME[e]
                t = v.get(tf)
                adm = kept["admissions"][v["admission_id"]]
                start, end = adm.val["admit_time"], adm.val["discharge_time"]
                if e == "discharges" and end is None and adm.val["admission_status"] not in ("discharged", "deceased"):
                    reject(r, "chronology:discharge_time", f"discharge record for admission {adm.id}, which is "
                                                           f"still active (status {adm.val['admission_status']}, "
                                                           f"no discharge time)")
                    continue
                if t is not None:
                    if t < start:
                        reject(r, f"chronology:{tf}", f"{tf} {P.iso_utc(t)} before admission {P.iso_utc(start)}")
                    elif t > (end or extract):
                        reject(r, f"chronology:{tf}", f"{tf} {P.iso_utc(t)} after "
                               + (f"discharge {P.iso_utc(end)}" if end else "the extract time"))
                if r.status != "ok":
                    continue
                if e == "discharges" and end is not None and t != end:
                    flag(r, "discharge_time_differs:discharge_time", "discharge_time", P.iso_utc(t),
                         f"admission discharge time is {P.iso_utc(end)}")
                if e == "discharges" and v["follow_up_time"] is not None and v["follow_up_time"] < t:
                    flag(r, "chronology_soft:follow_up_time", "follow_up_time", P.iso_utc(v["follow_up_time"]),
                         "follow-up appointment before discharge")
                if e == "unit_stays":
                    x = v["exit_time"]
                    if x is not None and x < t:
                        reject(r, "chronology:exit_time", f"unit exit {P.iso_utc(x)} before entry {P.iso_utc(t)}")
                    elif x is not None and x > (end or extract):
                        reject(r, "chronology:exit_time", f"unit exit {P.iso_utc(x)} after the admission ended")
                    elif x is None and end is not None:
                        flag(r, "open_stay_after_discharge:exit_time", "exit_time", None,
                             "no exit time although the admission is discharged")
                if e == "radiology" and v.get("order_id") is not None and r.status == "ok":
                    o = kept["orders"][v["order_id"]]
                    if t is not None and t < o.val["order_time"]:
                        reject(r, "chronology:exam_time", f"exam {P.iso_utc(t)} before its order "
                                                          f"{P.iso_utc(o.val['order_time'])}")
        kept[e] = {r.id: r for r in rows if r.status == "ok"}

    # soft cross-record checks
    stays = defaultdict(list)
    for r in kept["unit_stays"].values():
        stays[r.val["admission_id"]].append(r)
    for lst in stays.values():
        lst.sort(key=lambda x: x.val["entry_time"])
        for a, b in zip(lst, lst[1:]):
            if a.val["exit_time"] is not None and b.val["entry_time"] < a.val["exit_time"]:
                flag(b, "overlapping_unit_stays:entry_time", "entry_time", P.iso_utc(b.val["entry_time"]),
                     f"starts before stay {a.id} ends")
    died = {a.val["patient_id"] for a in kept["admissions"].values() if a.val["admission_status"] == "deceased"}
    for p in kept["patients"].values():
        if p.id in died and p.val["life_status"] == "alive":
            flag(p, "life_status_inconsistent:life_status", "life_status", "alive", "an admission ended in death")
    return kept


# =============================================================================
# Output
# =============================================================================
def to_output(r):
    v = dict(r.val)
    o = {"source_system": r.src, "source_record_id": r.sid}
    e = r.entity
    for c in OUTPUT_COLUMNS[e]:
        o[c] = v.get(c)
    if e == "patients":
        contact = v.get("emergency_contact") or (None, None, None)
        (o["emergency_contact_name"], o["emergency_contact_relationship"],
         o["emergency_contact_phone"]) = contact
    if e == "admissions":
        o["source_timezone"] = SOURCES[r.src]["timezone"]
    if e == "triage":
        bp = v.get("blood_pressure") or (None, None)
        o["systolic_bp"], o["diastolic_bp"] = bp
        sp = v.get("spo2")
        o["temperature_c"], o["spo2_pct"] = v.get("temperature"), int(sp) if sp is not None and sp == int(sp) else sp
    for c, x in o.items():
        if isinstance(x, dt.datetime):
            o[c] = P.iso_utc(x)
        elif isinstance(x, dt.date):
            o[c] = x.isoformat()
    o["quality_flags"] = ";".join(r.flags)
    return o


def load_icd9(path):
    """-> (set of normalised codes, (columns, rows)) or (None, None) when the file is missing."""
    if path is None or not Path(path).exists():
        return None, None
    cols, rows = read_csv(path)
    col = next((c for c in cols if c.strip().lower() in ("icd9_code", "code", "icd9")), cols[0])
    out, seen = [], set()
    for r in rows:
        code = P.normalize_icd9(r.get(col))[0]
        if code is None or code.startswith("INVALID:") or code in seen:
            continue
        seen.add(code)
        r = dict(r)
        r[col] = code
        out.append({("icd9_code" if k == col else k): v for k, v in r.items()})
    return seen, (["icd9_code" if c == col else c for c in cols], out)


def run(codes=("A", "B", "C", "D"), icd9_path=ICD_DEFAULT, out_dir=OUT, quiet=False):
    LOG.clear()
    LABEL_COUNTS.clear()
    icd9, icd9_df = load_icd9(icd9_path)
    if icd9 is None and not quiet:
        print(f"WARNING: ICD-9 dictionary not found at {icd9_path}; codes are only format-checked.")
    loaded = load_all(codes)
    clean, quarantine, summary = defaultdict(list), defaultdict(list), []
    malformed = []
    all_recs = {}
    for code in codes:
        src = loaded[code]
        cfg = SOURCES[code]
        tz = P.get_tz(cfg["timezone"])
        ext = src.meta.get("extractTime")
        extract = (P.parse_temporal(ext, tz).value if ext else
                   P.parse_temporal(cfg["extract_time_local"], tz).value)
        ctx = {"tz": tz, "icd9": icd9, "extract_utc": extract}
        malformed += src.malformed
        recs = {}
        for e in ENTITIES:
            df = src.entities[e]
            cmap = COLUMN_MAP[code][e]
            lst = []
            for row in df.rows:
                raw = {common: row.get(rawcol) for rawcol, common in cmap.items()}
                lst.append(Rec(e, code, raw, row["_source_row"], row["_raw_record"]))
            exact_duplicates(lst)
            for r in lst:
                if r.status == "duplicate":
                    continue
                clean_fields(r, ctx)
                r.id = r.val.get(ENTITY_SPECS[e]["pk"])
                if e == "patients" and r.val.get("full_name") is None:
                    r.val["full_name"] = compose_full_name(code, r.val.get("first_name"), r.val.get("last_name"))
            standardise_case(lst)
            recs[e] = lst
        process_source(code, recs, ctx)
        all_recs[code] = recs
        mal_by_entity = Counter(m["entity"] for m in src.malformed)
        for e in ENTITIES:
            lst = recs[e]
            for r in lst:
                if r.status == "ok":
                    clean[e].append(to_output(r))
                else:
                    codes_ = [c for c, _ in r.rejects]
                    quarantine[e].append({
                        "source_system": code, "entity": e, "source_record_id": r.sid, "source_row": r.loc,
                        "disposition": "duplicate_removed" if r.status == "duplicate" else "rejected",
                        "duplicate_of": r.dup_of,
                        "reason_codes": ";".join(dict.fromkeys(codes_)),
                        "reason_details": " | ".join(f"{c}: {d}" if d else c for c, d in r.rejects),
                        "raw_record": r.raw_record})
            st = Counter(r.status for r in lst)
            casc = sum(1 for r in lst if r.status == "rejected"
                       and all(c.startswith("parent_quarantined") for c, _ in r.rejects))
            summary.append({"source_system": code, "entity": e,
                            "raw_records_read": len(lst) + mal_by_entity.get(e, 0),
                            "malformed": mal_by_entity.get(e, 0),
                            "exact_duplicates_removed": sum(1 for r in lst if r.rejects[:1] and
                                                            r.rejects[0][0] == "exact_duplicate"),
                            "near_duplicates_merged": sum(1 for r in lst if r.status == "duplicate" and
                                                          r.rejects[0][0] == "near_duplicate"),
                            "rejected_own_problem": st["rejected"] - casc, "rejected_cascade": casc,
                            "clean_records": st["ok"],
                            "clean_with_flags": sum(1 for r in lst if r.status == "ok" and r.flags)})

    # ---- write ----
    for sub in ("clean", "quarantine", "cleaning_log"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)
    for e in ENTITIES:
        cols = ["source_system", "source_record_id"] + OUTPUT_COLUMNS[e] + ["quality_flags"]
        write_csv(out_dir / "clean" / f"{e}.csv", clean[e], cols)
        qcols = ["source_system", "entity", "source_record_id", "source_row", "disposition", "duplicate_of",
                 "reason_codes", "reason_details", "raw_record"]
        write_csv(out_dir / "quarantine" / f"{e}.csv", quarantine[e], qcols)
    write_csv(out_dir / "quarantine" / "malformed_records.csv", malformed,
              ["source_system", "entity", "source_row", "reason", "raw_record"])
    if icd9_df is not None:
        write_csv(out_dir / "clean" / "icd9_codes.csv", icd9_df[1], icd9_df[0])
    write_csv(out_dir / "cleaning_log" / "cleaning_log.csv", LOG,
              ["source_system", "entity", "source_record_id", "source_row", "field", "rule", "action", "before",
               "after", "detail"])
    lab = [{"source_system": s, "entity": e, "field": f, "raw_label": raw, "standard_value": std, "count": n}
           for (s, e, f, raw, std), n in sorted(LABEL_COUNTS.items())]
    write_csv(out_dir / "cleaning_log" / "label_mappings.csv", lab,
              ["source_system", "entity", "field", "raw_label", "standard_value", "count"])
    write_csv(out_dir / "cleaning_log" / "summary.csv", summary, list(summary[0]))

    from cleaning.report import write_report
    write_report(out_dir, summary, LOG, lab, quarantine, malformed, all_recs, icd9_path if icd9 else None)
    if not quiet:
        print(md_table(summary))
        print(f"Written to {out_dir}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", nargs="+", default=["A", "B", "C", "D"])
    ap.add_argument("--icd9", default=str(ICD_DEFAULT), help="ICD-9 dictionary CSV (column icd9_code)")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    run(tuple(a.sources), Path(a.icd9), Path(a.out))
