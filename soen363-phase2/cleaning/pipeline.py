"""
Cleaning pipeline. Steps (run in this order by run_cleaning.py):

  1. normalise_all        field-level standardisation of every staged record
  2. resolve_ambiguous_a  choose DD/MM vs MM/DD for source A using related events
  3. deduplicate          same-key duplicates: drop identical copies, merge
                          complementary copies, quarantine conflicting copies
  4. reconcile_discharge  admission discharge time <-> discharge record time
                          (two records of the same event)
  5. resolve_patients     same person registered twice -> one master patient
  6. required_checks      quarantine records missing required information
  7. integrity_checks     references (parents, ICD-9, staff) + chronology,
                          with cascade quarantine of children of rejected parents

Every decision is written to ctx.issues (field-level log) or ctx.quarantine
(record-level rejection with reasons). Nothing is guessed: a value is only
changed when the source itself provides the evidence.
"""

import json
from collections import Counter, defaultdict
from datetime import timedelta

from zoneinfo import ZoneInfo

from config import (ADMISSION_BEFORE_BIRTH_POLICY, CHILD_ENTITIES, DST_SLACK_SECONDS, KEY, NULL_HAS_MEANING, SCHEMA, SOURCES,
                    TRACK_MISSING_OPTIONAL, TRIAGE_WINDOW_SECONDS)
from normalize import (INVALID, MISSING, clean_ws, fmt_utc, is_missing, map_category, norm_bp, norm_icd9,
                       norm_name, norm_vital, parse_date, parse_id, parse_ts, show, DOB_FORMATS)


class Context:
    def __init__(self):
        self.issues = []                 # field-level log
        self.quarantine = []             # rejected records
        self.duplicates = []             # removed / merged duplicate copies
        self.crosswalk = []              # patient entity-resolution mapping
        self.transforms = Counter()      # routine conversions (source, entity, field, what)
        self.examples = {}               # (source, entity, id) -> raw/clean snapshot

    def log(self, rec, field, code, action, before=None, after=None):
        self.issues.append({
            "source": rec["_source"], "entity": rec["_entity"], "record_id": rec.get("_id"),
            "location": rec["_loc"], "field": field, "issue": code, "action": action,
            "before": "" if before is None else str(before), "after": "" if after is None else str(after),
        })

    def reject(self, rec, reasons, kind="direct"):
        rec["_quarantined"] = True
        rec.setdefault("_reasons", [])
        for r in reasons:
            if r not in rec["_reasons"]:
                rec["_reasons"].append(r)
        rec["_qkind"] = rec.get("_qkind") or kind
        if not rec.get("_in_q"):
            rec["_in_q"] = True
            self.quarantine.append(rec)


def live(records):
    return [r for r in records if not r.get("_quarantined") and not r.get("_removed")]


def fmt_val(v):
    if v is None:
        return "NULL"
    if hasattr(v, "tzinfo") and hasattr(v, "hour"):
        return fmt_utc(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


# ---------------------------------------------------------------------------
# 1. Field-level normalisation
# ---------------------------------------------------------------------------

def normalise_record(rec, ctx, icd9_dict):
    S, E = rec["_source"], rec["_entity"]
    clean, fail, alt, dst = {}, {}, {}, set()
    rec["_id"] = parse_id(rec.get(KEY[E])) if E != "icd9_codes" else clean_ws(str(rec.get("icd9_code")))
    if rec["_id"] is INVALID:
        rec["_id"] = None

    for field, kind, required in SCHEMA[E]:
        v = rec.get(field)
        out = None

        if kind in ("id", "prof"):
            if not is_missing(v, S):
                out = parse_id(v)
                if out is INVALID:
                    fail[field] = f"invalid_identifier_{field}"
                    ctx.log(rec, field, "invalid_identifier", "nulled", show(v))
                    out = None
                elif kind == "prof" and isinstance(v, str) and not v.strip().isdigit():
                    ctx.transforms[(S, E, field, "staff_code_to_integer")] += 1

        elif kind == "name":
            if not is_missing(v, S):
                out = norm_name(str(v))
                if out != v:
                    ctx.log(rec, field, "name_text_standardised", "corrected", show(v), out)

        elif kind == "text":
            if not is_missing(v, S):
                out = clean_ws(str(v))
                if out != v:
                    ctx.log(rec, field, "whitespace_standardised", "corrected", show(v), out)

        elif kind.startswith("cat:"):
            if not is_missing(v, S):
                mapped, messy = map_category(kind[4:], v, S)
                if mapped is INVALID:
                    fail[field] = f"unmapped_category_{field}"
                    ctx.log(rec, field, "unmapped_category", "nulled", show(v))
                else:
                    out = mapped
                    if messy:
                        ctx.log(rec, field, "messy_category_label", "corrected", show(v), out)
                    ctx.transforms[(S, E, field, "category_mapped")] += 1

        elif kind == "ts":
            r = parse_ts(v, S)
            if r["value"] is INVALID:
                fail[field] = f"invalid_{field}"
                ctx.log(rec, field, "invalid_timestamp", "nulled", show(v))
            elif r["value"] is not MISSING:
                out = r["value"]
                if r["alt"] is not None:
                    alt[field] = r["alt"]
                for fl in r["flags"]:
                    if fl in ("dst_ambiguous", "dst_nonexistent"):
                        dst.add(field)
                        ctx.log(rec, field, fl, "flagged", show(v), fmt_utc(out))
                    elif fl == "timezone_assumed_local":
                        ctx.log(rec, field, "timestamp_without_timezone", "flagged", show(v),
                                f"{fmt_utc(out)} (assumed {SOURCES[S]['tz']})")
                    elif fl == "timestamp_from_epoch_seconds":
                        ctx.log(rec, field, "timestamp_as_epoch_seconds", "corrected", show(v), fmt_utc(out))
                    elif fl == "date_written_mm_dd":
                        ctx.log(rec, field, "date_only_valid_as_mm_dd", "corrected", show(v), fmt_utc(out))
                ctx.transforms[(S, E, field, "timestamp_to_utc")] += 1

        elif kind == "dob":
            d = parse_date(v, S, DOB_FORMATS[S])
            if d is INVALID:
                fail[field] = f"invalid_{field}"
                ctx.log(rec, field, "invalid_date", "nulled", show(v))
            elif d is not MISSING:
                out = d

        elif kind == "date":
            d = parse_date(v, S)
            if d is INVALID:
                fail[field] = f"invalid_{field}"
                ctx.log(rec, field, "invalid_date", "nulled", show(v))
            elif d is not MISSING:
                out = d

        elif kind == "icd9":
            if E == "icd9_codes":
                out = clean_ws(str(v)).upper()
            else:
                code, iss = norm_icd9(v, S, icd9_dict[S])
                for i in iss:
                    ctx.log(rec, *i)
                if code is INVALID:
                    fail[field] = "unknown_icd9_code"
                elif code is not MISSING:
                    out = code

        elif kind == "bp":
            s, d, iss = norm_bp(v, S, field)
            for i in iss:
                ctx.log(rec, *i)
            clean["bp_systolic"], clean["bp_diastolic"] = s, d
            continue

        elif kind.startswith("vital:"):
            out, iss, note = norm_vital(kind[6:], v, S, field)
            for i in iss:
                ctx.log(rec, *i)
            if note:
                ctx.transforms[(S, E, field, note)] += 1

        clean[field] = out
        if out is None and field not in fail:
            if required:
                fail[field] = f"missing_required_{field}"
                ctx.log(rec, field, "missing_required_value", "flagged_required", show(v),
                        "NULL -> record quarantined unless a duplicate copy supplies it")
            elif field in TRACK_MISSING_OPTIONAL.get(E, ()):
                ctx.log(rec, field, "missing_optional_value", "retained_null", show(v), "NULL")

    rec["_clean"], rec["_fail"], rec["_alt"], rec["_dst"] = clean, fail, alt, dst


def normalise_all(data, ctx):
    # ICD-9 dictionary per source (the code list each source ships with).
    icd9 = {S: {clean_ws(str(r["icd9_code"])).upper() for r in ents["icd9_codes"]} for S, ents in data.items()}
    for S, ents in data.items():
        for E in SCHEMA:
            for rec in ents[E]:
                normalise_record(rec, ctx, icd9)
    return icd9


# ---------------------------------------------------------------------------
# 2. Source A: DD/MM vs MM/DD
# ---------------------------------------------------------------------------

def _readings(rec, field):
    v = rec["_clean"].get(field)
    out = [v] if v is not None else []
    if field in rec["_alt"]:
        out.append(rec["_alt"][field])
    return out


def _swap(rec, field, ctx, why):
    old = rec["_clean"][field]
    rec["_clean"][field] = rec["_alt"].pop(field)
    ctx.log(rec, field, "ambiguous_date_mm_dd", "corrected", fmt_utc(old) + " (read as DD/MM)",
            f"{fmt_utc(rec['_clean'][field])} (read as MM/DD: {why})")


def resolve_ambiguous_a(data, ctx):
    ents = data["A"]
    kids = {E: defaultdict(list) for E in CHILD_ENTITIES}
    for E in CHILD_ENTITIES:
        for r in ents[E]:
            kids[E][r["_clean"].get("admission_id")].append(r)

    window = timedelta(seconds=TRIAGE_WINDOW_SECONDS)
    adm_window = {}
    for a in ents["admissions"]:
        aid, c = a["_clean"]["admission_id"], a["_clean"]
        # Admission time: triage happens minutes after arrival and the first
        # unit stay starts shortly after. Pick the reading they support.
        if "admit_time_utc" in a["_alt"]:
            refs = [_readings(t, "assessed_at_utc") for t in kids["triage"][aid]] + \
                   [_readings(s, "entry_time_utc") for s in kids["unit_stays"][aid]]
            dis = _readings(a, "discharge_time_utc")
            def score(x):
                # 1) how many related events start shortly after this reading,
                # 2) how many of them match in their own documented DD/MM reading,
                # 3) is it compatible with (some reading of) the discharge time.
                # Ties keep the documented reading (score must be strictly better).
                hits = sum(any(timedelta(0) <= y - x <= window for y in rs) for rs in refs)
                primary_hits = sum(bool(rs) and timedelta(0) <= rs[0] - x <= window for rs in refs)
                compatible = not dis or any(d >= x for d in dis)
                return (hits, primary_hits, compatible)
            alt_s = score(a["_alt"]["admit_time_utc"])
            if alt_s[0] >= 1 and alt_s > score(c["admit_time_utc"]):
                _swap(a, "admit_time_utc", ctx, "matches triage / unit-stay times")
        # Discharge time: the discharge record and discharge summary describe the same moment.
        if "discharge_time_utc" in a["_alt"]:
            refs = [_readings(d, "discharge_time_utc") for d in kids["discharges"][aid]] + \
                   [_readings(n, "written_at_utc") for n in kids["notes"][aid]
                    if n["_clean"].get("note_type") == "discharge_summary"]
            adm = c.get("admit_time_utc")
            def score(x):
                ev = sum(any(abs((y - x).total_seconds()) <= 60 for y in rs) for rs in refs)
                return (ev, adm is None or x >= adm)
            alt_s = score(a["_alt"]["discharge_time_utc"])
            if alt_s[0] >= 1 and alt_s > score(c["discharge_time_utc"]):
                _swap(a, "discharge_time_utc", ctx, "matches discharge record / summary")
        if aid not in adm_window and c.get("admit_time_utc"):
            adm_window[aid] = (c["admit_time_utc"], c.get("discharge_time_utc"))

    # Child events must lie inside their admission. Swap only if the documented
    # reading is outside and the alternative reading is inside.
    child_ts = {"triage": ["assessed_at_utc"], "unit_stays": ["entry_time_utc", "exit_time_utc"],
                "diagnoses": ["diagnosed_at_utc"], "orders": ["ordered_at_utc"],
                "radiology": ["performed_at_utc"], "procedures": ["performed_at_utc"],
                "notes": ["written_at_utc"], "discharges": ["discharge_time_utc"]}
    for E, fields in child_ts.items():
        for r in ents[E]:
            w = adm_window.get(r["_clean"].get("admission_id"))
            if not w:
                continue
            for f in fields:
                if f not in r["_alt"]:
                    continue
                lo, hi = w
                if f == "exit_time_utc" and r["_clean"].get("entry_time_utc"):
                    lo = r["_clean"]["entry_time_utc"]
                if E == "diagnoses":
                    hi = None
                inside = lambda x: x >= lo and (hi is None or x <= hi)
                same_event = E == "discharges" or (E == "notes" and r["_clean"].get("note_type") == "discharge_summary")
                if same_event and hi is not None:
                    # discharge record / discharge summary = the admission's discharge moment
                    near = lambda x: abs((x - hi).total_seconds()) <= 60
                    if not near(r["_clean"][f]) and near(r["_alt"][f]):
                        _swap(r, f, ctx, "matches the admission discharge time")
                    continue
                if not inside(r["_clean"][f]) and inside(r["_alt"][f]):
                    _swap(r, f, ctx, "the DD/MM reading is outside the admission, the MM/DD reading is inside")


    # Unit-stay entry/exit pair: if exit < entry under the documented reading,
    # use the alternative reading of ONE of them when that makes the stay
    # consistent (and keeps it inside the admission when the window is known).
    for r in ents["unit_stays"]:
        c = r["_clean"]
        en, ex = c.get("entry_time_utc"), c.get("exit_time_utc")
        if en is None or ex is None or ex >= en:
            continue
        w = adm_window.get(c.get("admission_id"))
        fits = lambda a, b: a <= b and (w is None or (a >= w[0] and (w[1] is None or b <= w[1])))
        if "entry_time_utc" in r["_alt"] and fits(r["_alt"]["entry_time_utc"], ex):
            _swap(r, "entry_time_utc", ctx, "only this reading puts the unit entry before its exit")
        elif "exit_time_utc" in r["_alt"] and fits(en, r["_alt"]["exit_time_utc"]):
            _swap(r, "exit_time_utc", ctx, "only this reading puts the unit exit after its entry")


# ---------------------------------------------------------------------------
# 3. Same-key duplicates
# ---------------------------------------------------------------------------

def deduplicate(data, ctx):
    for S, ents in data.items():
        for E in SCHEMA:
            groups = defaultdict(list)
            for r in ents[E]:
                if r["_id"] is not None:
                    groups[r["_id"]].append(r)
            for key, copies in groups.items():
                if len(copies) < 2:
                    continue
                first = copies[0]
                same = all(c["_clean"] == first["_clean"] for c in copies[1:])
                if same:
                    for c in copies[1:]:
                        kind = "exact_duplicate_raw" if c["_raw"] == first["_raw"] else "duplicate_identical_after_cleaning"
                        _remove_dup(c, first, kind, ctx)
                    continue
                merged, conflicts = {}, []
                for f in first["_clean"]:
                    vals = []
                    for c in copies:
                        x = c["_clean"].get(f)
                        if x is not None and x not in vals:
                            vals.append(x)
                    if len(vals) > 1:
                        conflicts.append(f)
                    merged[f] = vals[0] if vals else None
                if conflicts:
                    for c in copies:
                        ctx.log(c, ",".join(conflicts), "conflicting_duplicate_key", "quarantined",
                                "; ".join(fmt_val(x["_clean"].get(conflicts[0])) for x in copies))
                        ctx.reject(c, [f"conflicting_duplicate_key({','.join(conflicts)})"])
                    continue
                # Copies differ only where one copy has NULL: combine them.
                for f, v in merged.items():
                    if first["_clean"].get(f) is None and v is not None:
                        ctx.log(first, f, "filled_from_duplicate_copy", "corrected", "NULL", fmt_val(v))
                        first["_fail"].pop(f, None)
                first["_clean"] = merged
                for c in copies[1:]:
                    _remove_dup(c, first, "duplicate_merged_complementary", ctx)


def _remove_dup(dup, kept, kind, ctx):
    dup["_removed"] = True
    ctx.duplicates.append({"source": dup["_source"], "entity": dup["_entity"], "record_id": dup["_id"],
                           "removed_location": dup["_loc"], "kept_location": kept["_loc"], "kind": kind})


# ---------------------------------------------------------------------------
# 4. Same-event reconciliation: admission discharge time <-> discharge record
# ---------------------------------------------------------------------------

def reconcile_discharge(data, ctx):
    for S, ents in data.items():
        dis = defaultdict(list)
        for d in live(ents["discharges"]):
            dis[d["_clean"]["admission_id"]].append(d)
        for a in live(ents["admissions"]):
            c = a["_clean"]
            if c.get("status") not in ("discharged", "deceased"):
                continue
            times = {d["_clean"]["discharge_time_utc"] for d in dis[c["admission_id"]]
                     if d["_clean"].get("discharge_time_utc")}
            if len(times) != 1:
                continue
            t = next(iter(times))
            adm = c.get("admit_time_utc")
            if c.get("discharge_time_utc") is None:
                c["discharge_time_utc"] = t
                a["_fail"].pop("discharge_time_utc", None)
                ctx.log(a, "discharge_time_utc", "discharge_time_filled_from_discharge_record", "corrected",
                        "NULL / invalid", fmt_utc(t))
            elif adm and c["discharge_time_utc"] < adm and t >= adm:
                ctx.log(a, "discharge_time_utc", "discharge_before_admission", "corrected",
                        f"{fmt_utc(c['discharge_time_utc'])} (before admit {fmt_utc(adm)})",
                        f"{fmt_utc(t)} (from discharge record)")
                c["discharge_time_utc"] = t
        adm_by_id = {a["_clean"]["admission_id"]: a for a in live(ents["admissions"])}
        for d in live(ents["discharges"]):
            a = adm_by_id.get(d["_clean"]["admission_id"])
            if d["_clean"].get("discharge_time_utc") is None and a and a["_clean"].get("discharge_time_utc") \
                    and a["_clean"].get("status") in ("discharged", "deceased"):
                d["_clean"]["discharge_time_utc"] = a["_clean"]["discharge_time_utc"]
                d["_fail"].pop("discharge_time_utc", None)
                ctx.log(d, "discharge_time_utc", "discharge_time_filled_from_admission", "corrected",
                        "NULL / invalid", fmt_utc(d["_clean"]["discharge_time_utc"]))


# ---------------------------------------------------------------------------
# 5. Entity resolution: same person registered twice under different ids
# ---------------------------------------------------------------------------

def _k(v):
    return None if v is None else (clean_ws(v).casefold() if isinstance(v, str) else v)


def is_same_person(p, q):
    """Deterministic rule (documented in README):
       - same sex and same given name (case/space-insensitive), and
       - no contradiction on family name or date of birth, and
       - at least 3 of {family name, date of birth, phone, address} agree."""
    a, b = p["_clean"], q["_clean"]
    if a.get("sex") is None or a.get("sex") != b.get("sex"):
        return False
    if _k(a.get("given_name")) is None or _k(a.get("given_name")) != _k(b.get("given_name")):
        return False
    for f in ("family_name", "birth_date"):
        if _k(a.get(f)) is not None and _k(b.get(f)) is not None and _k(a.get(f)) != _k(b.get(f)):
            return False
    agree = sum(_k(a.get(f)) is not None and _k(a.get(f)) == _k(b.get(f))
                for f in ("family_name", "birth_date", "phone", "address"))
    return agree >= 3


def resolve_patients(data, ctx):
    master = {}
    for S, ents in data.items():
        pts = sorted((p for p in live(ents["patients"]) if p["_id"] is not None), key=lambda p: p["_id"])
        parent = {p["_id"]: p["_id"] for p in pts}

        def find(x):
            while parent[x] != x:
                x = parent[x]
            return x
        by_given = defaultdict(list)   # blocking key keeps the comparison cheap
        for p in pts:
            by_given[_k(p["_clean"].get("given_name"))].append(p)
        for block in by_given.values():
            for i, p in enumerate(block):
                for q in block[i + 1:]:
                    if is_same_person(p, q):
                        ra, rb = find(p["_id"]), find(q["_id"])
                        parent[max(ra, rb)] = min(ra, rb)
        by_id = {p["_id"]: p for p in pts}
        m = {}
        for p in pts:
            root = find(p["_id"])
            if root == p["_id"]:
                continue
            keep = by_id[root]
            m[p["_id"]] = root
            for f, v in p["_clean"].items():
                if keep["_clean"].get(f) is None and v is not None and f != "patient_id":
                    keep["_clean"][f] = v
                    keep["_fail"].pop(f, None)
                    ctx.log(keep, f, "filled_from_duplicate_registration", "corrected", "NULL",
                            f"{fmt_val(v)} (from patient {p['_id']})")
            p["_removed"] = True
            ctx.log(p, "patient_id", "entity_duplicate_patient", "merged", p["_id"], f"master patient {root}")
            ctx.crosswalk.append({"source": S, "duplicate_patient_id": p["_id"], "master_patient_id": root,
                                  "duplicate_location": p["_loc"], "master_location": keep["_loc"],
                                  "rule": "same sex + given name, no family/DOB conflict, >=3 of family/DOB/phone/address agree"})
        master[S] = m
    return master


# ---------------------------------------------------------------------------
# 6. Required information
# ---------------------------------------------------------------------------

def required_checks(data, ctx):
    for S, ents in data.items():
        for E in SCHEMA:
            for r in live(ents[E]):
                reasons = []
                if r["_id"] is None:
                    reasons.append(f"invalid_identifier_{KEY[E]}")
                for field, kind, required in SCHEMA[E]:
                    f = "bp_systolic" if kind == "bp" else field
                    if f in r["_fail"] and (required or (E, field) in NULL_HAS_MEANING
                                            or r["_fail"][f] == "unknown_icd9_code"):
                        reasons.append(r["_fail"][f])
                c = r["_clean"]
                if E == "admissions" and c.get("status"):
                    if c["status"] in ("discharged", "deceased") and c.get("discharge_time_utc") is None \
                            and "discharge_time_utc" not in r["_fail"]:
                        reasons.append("missing_discharge_time_on_closed_admission")
                    if c["status"] == "active" and c.get("discharge_time_utc") is not None:
                        reasons.append("discharge_time_on_active_admission")
                if reasons:
                    ctx.reject(r, sorted(set(reasons)))


# ---------------------------------------------------------------------------
# 7. Relationships and chronology (with cascade)
# ---------------------------------------------------------------------------

def _late(a, b, slack):
    """True if a is later than b by more than slack seconds."""
    return (a - b).total_seconds() > slack


def integrity_checks(data, ctx, master, rejects):
    """References + chronology. A record's own rules are always evaluated,
    even when its parent was already quarantined, so that every quarantined
    record lists all of its problems. rejection_type is 'cascade' only when
    the parent being quarantined is the record's sole problem."""
    for S, ents in data.items():
        all_ids = {E: {r["_id"] for r in ents[E] if r["_id"] is not None} for E in SCHEMA}
        for r in rejects:  # structurally malformed rows still tell us the id existed
            if r["_source"] == S and r.get("_id") is not None:
                all_ids[r["_entity"]].add(r["_id"])
        ok = lambda E: {r["_id"]: r for r in live(ents[E])}
        # Every non-duplicate copy, quarantined or not (used for context only).
        known = lambda E: {r["_id"]: r for r in ents[E] if not r.get("_removed") and r["_id"] is not None}
        prof_ok = set(ok("professionals"))
        tz = ZoneInfo(SOURCES[S]["tz"])

        def check_prof(r):
            return [f"unknown_professional_ref({f}={r['_clean'][f]})" for f, kind, _ in SCHEMA[r["_entity"]]
                    if kind == "prof" and r["_clean"].get(f) is not None and r["_clean"][f] not in prof_ok]

        def parent_reason(pid, parent_entity, ok_set):
            if pid in ok_set:
                return None
            if pid in all_ids[parent_entity]:
                return f"parent_{parent_entity[:-1]}_quarantined"
            return f"missing_parent_{parent_entity[:-1]}"

        def finish(r, reasons):
            if reasons:
                own = [x for x in reasons if not x.startswith("parent_")]
                ctx.reject(r, reasons, "direct" if own else "cascade")

        def remap(r):
            pid = r["_clean"]["patient_id"]
            if pid in master[S]:
                r["_clean"]["patient_id"] = master[S][pid]
                ctx.log(r, "patient_id", "patient_ref_remapped_to_master", "corrected", pid, master[S][pid])

        # ---- admissions -> patients --------------------------------------
        pats, pats_known = ok("patients"), known("patients")
        for a in live(ents["admissions"]):
            c = a["_clean"]
            remap(a)
            reasons = check_prof(a)
            why = parent_reason(c["patient_id"], "patients", pats)
            if why:
                reasons.append(why)
            if c.get("discharge_time_utc") and c["discharge_time_utc"] < c["admit_time_utc"]:
                reasons.append("discharge_before_admission")
            p = pats_known.get(c["patient_id"])
            if p and p["_clean"].get("birth_date"):
                local_day = c["admit_time_utc"].astimezone(tz).date()
                if local_day < p["_clean"]["birth_date"]:
                    q = ADMISSION_BEFORE_BIRTH_POLICY == "quarantine"
                    ctx.log(a, "admit_time_utc", "admission_before_birth", "quarantined" if q else "flagged",
                            f"admitted {local_day} (local)", f"patient {c['patient_id']} born {p['_clean']['birth_date']}")
                    if q:
                        reasons.append("admission_before_patient_birth")
            if not reasons and c["status"] == "deceased" and p and p["_clean"].get("life_status") != "deceased":
                ctx.log(a, "status", "death_not_reflected_on_patient", "flagged", c["status"],
                        p["_clean"].get("life_status"))
            finish(a, reasons)

        # ---- children -> admissions (and radiology -> orders) --------------
        adms, adms_known = ok("admissions"), known("admissions")
        ts_field = {"triage": "assessed_at_utc", "unit_stays": "entry_time_utc", "diagnoses": "diagnosed_at_utc",
                    "orders": "ordered_at_utc", "radiology": "performed_at_utc", "procedures": "performed_at_utc",
                    "notes": "written_at_utc", "discharges": "discharge_time_utc"}
        label = {"triage": "triage", "unit_stays": "unit_entry", "diagnoses": "diagnosis", "orders": "order",
                 "radiology": "radiology_exam", "procedures": "procedure", "notes": "note",
                 "discharges": "discharge_record"}

        for E in ["triage", "unit_stays", "diagnoses", "orders", "radiology", "procedures", "notes", "discharges"]:
            if E == "radiology":
                orders_ok, orders_known = ok("orders"), known("orders")
            for r in live(ents[E]):
                c = r["_clean"]
                reasons = check_prof(r)
                aid = c["admission_id"]
                why = parent_reason(aid, "admissions", adms)
                if why:
                    reasons.append(why)
                arec = adms_known.get(aid)
                a = arec["_clean"] if arec else None
                admit = a.get("admit_time_utc") if a else None
                disch = a.get("discharge_time_utc") if a else None
                if admit and disch and disch < admit:
                    disch = None  # parent's own window is broken; do not judge the child against it
                slack = DST_SLACK_SECONDS if (r["_dst"] or (arec and arec["_dst"])) else 0

                if E == "diagnoses":
                    remap(r)
                    # Only meaningful when the admission's own patient exists; an admission
                    # pointing to a non-existent patient is already rejected for that.
                    if a and a.get("patient_id") in pats_known and c["patient_id"] != a["patient_id"]:
                        reasons.append(f"diagnosis_patient_mismatch(diagnosis={c['patient_id']},"
                                       f"admission={a.get('patient_id')})")
                if E == "radiology":
                    why = parent_reason(c["order_id"], "orders", orders_ok)
                    if why:
                        reasons.append(why)
                    o = orders_known.get(c["order_id"])
                    if o:
                        if o["_clean"]["admission_id"] != aid:
                            reasons.append("radiology_order_admission_mismatch")
                        ot = o["_clean"].get("ordered_at_utc")
                        if ot and _late(ot, c["performed_at_utc"], slack):
                            reasons.append("radiology_exam_before_order")
                if E == "discharges" and a and a.get("status") == "active":
                    reasons.append("discharge_record_for_active_admission")

                t = c.get(ts_field[E])
                if t is not None and admit is not None:
                    if _late(admit, t, slack):
                        reasons.append(f"{label[E]}_before_admission")
                    if E != "diagnoses" and disch is not None and _late(t, disch, slack):
                        reasons.append(f"{label[E]}_after_discharge")
                if E == "unit_stays" and c.get("exit_time_utc") is not None:
                    if c["exit_time_utc"] < c["entry_time_utc"]:
                        reasons.append("unit_exit_before_entry")
                    elif disch is not None and _late(c["exit_time_utc"], disch, slack):
                        reasons.append("unit_exit_after_discharge")
                if not reasons and E == "unit_stays" and c.get("exit_time_utc") is None and disch is not None:
                    ctx.log(r, "exit_time_utc", "open_unit_stay_on_closed_admission", "flagged", "NULL",
                            f"admission discharged {fmt_utc(disch)}")
                if not reasons and E == "discharges" and disch is not None and t is not None \
                        and abs((t - disch).total_seconds()) > 60 + slack:
                    ctx.log(r, "discharge_time_utc", "discharge_record_time_differs_from_admission", "flagged",
                            fmt_utc(t), fmt_utc(disch))
                finish(r, reasons)

        # ---- soft checks (flag only) --------------------------------------
        stays = defaultdict(list)
        for s in live(ents["unit_stays"]):
            stays[s["_clean"]["admission_id"]].append(s)
        for aid, ss in stays.items():
            ss.sort(key=lambda s: s["_clean"]["entry_time_utc"])
            for prev, nxt in zip(ss, ss[1:]):
                pe = prev["_clean"].get("exit_time_utc")
                if pe is None or _late(pe, nxt["_clean"]["entry_time_utc"], 60):
                    ctx.log(nxt, "entry_time_utc", "unit_stay_overlap", "flagged",
                            f"previous stay {prev['_id']} exit {fmt_val(pe)}",
                            f"this entry {fmt_utc(nxt['_clean']['entry_time_utc'])}")
        n_dis = Counter(d["_clean"]["admission_id"] for d in live(ents["discharges"]))
        adms = ok("admissions")
        for aid, n in n_dis.items():
            if n > 1 and aid in adms:
                ctx.log(adms[aid], "admission_id", "multiple_discharge_records", "flagged", n)
