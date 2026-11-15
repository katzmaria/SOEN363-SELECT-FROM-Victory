"""
SOEN 363 Project Phase 2 - synthetic source generator.

Creates four independent, ENTIRELY FICTIONAL hospital data sources for
educational and learning purposes only. No real patients, no real personal
information. Generated with a generative AI tool (Claude), which the Phase 2
handout permits for creating the synthetic source datasets only.

    Source A - Europe        - TXT  (pipe-delimited, one file per entity)
    Source B - North America - CSV  (one file per entity)
    Source C - Asia          - XML  (one file, nested admission children)
    Source D - Africa        - JSON (one file, nested encounter children)

Each source contains controlled data-quality problems (duplicates, missing
values, messy text, invalid/ambiguous dates, invalid numbers, broken
references, chronology errors, repeated local IDs). Every injected problem is
counted and written to output/injection_manifest.json.

Usage:
    pip install faker==40.39.0
    python generator/generate_sources.py          # writes output/raw/...

Deterministic: the same seed always produces byte-identical files.
"""

import csv
import json
import random
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.dom import minidom

from faker import Faker

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "raw"
MANIFEST = ROOT / "output" / "injection_manifest.json"

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

# Real ICD-9-CM codes and official titles. Codes are strings (leading zeros
# such as 038.9 and 008.45 must be preserved).
ICD9 = [
    ("401.9", "Unspecified essential hypertension", "Circulatory"),
    ("410.9", "Acute myocardial infarction, unspecified site", "Circulatory"),
    ("414.01", "Coronary atherosclerosis of native coronary artery", "Circulatory"),
    ("427.31", "Atrial fibrillation", "Circulatory"),
    ("428.0", "Congestive heart failure, unspecified", "Circulatory"),
    ("434.91", "Cerebral artery occlusion, unspecified with cerebral infarction", "Circulatory"),
    ("786.50", "Chest pain, unspecified", "Symptoms"),
    ("780.60", "Fever, unspecified", "Symptoms"),
    ("250.00", "Diabetes mellitus without mention of complication, type II or unspecified type, not stated as uncontrolled", "Endocrine"),
    ("244.9", "Unspecified acquired hypothyroidism", "Endocrine"),
    ("272.4", "Other and unspecified hyperlipidemia", "Endocrine"),
    ("276.51", "Dehydration", "Endocrine"),
    ("486", "Pneumonia, organism unspecified", "Respiratory"),
    ("491.21", "Obstructive chronic bronchitis with (acute) exacerbation", "Respiratory"),
    ("493.90", "Asthma, unspecified type, unspecified", "Respiratory"),
    ("496", "Chronic airway obstruction, not elsewhere classified", "Respiratory"),
    ("518.81", "Acute respiratory failure", "Respiratory"),
    ("038.9", "Unspecified septicemia", "Infectious"),
    ("008.45", "Intestinal infection due to Clostridium difficile", "Infectious"),
    ("599.0", "Urinary tract infection, site not specified", "Genitourinary"),
    ("584.9", "Acute kidney failure, unspecified", "Genitourinary"),
    ("540.9", "Acute appendicitis without mention of peritonitis", "Digestive"),
    ("574.20", "Calculus of gallbladder without mention of cholecystitis, without mention of obstruction", "Digestive"),
    ("578.9", "Hemorrhage of gastrointestinal tract, unspecified", "Digestive"),
    ("820.8", "Closed fracture of unspecified part of neck of femur", "Injury"),
    ("285.9", "Anemia, unspecified", "Blood"),
    ("V30.00", "Single liveborn, born in hospital, delivered without mention of cesarean section", "Supplementary"),
]
ICD9_CODES = [c for c, _, _ in ICD9]
SURGICAL_CODES = {"540.9", "574.20", "820.8", "414.01", "410.9"}

ADMISSION_TYPES = ["emergency", "urgent", "elective", "outpatient", "newborn"]
ADMISSION_WEIGHTS = [30, 22, 22, 22, 4]
TRIAGE = ["high", "medium", "low"]
UNITS = ["Emergency Department", "ICU", "CCU", "MICU", "SICU", "General Ward"]
CRITICAL = ["ICU", "CCU", "MICU", "SICU"]
ROLES = ["physician", "nurse", "surgeon", "radiologist", "radiology technician"]
ORDER_EXAMS = ["Chest X-ray", "CT scan", "MRI", "Ultrasound", "ECG", "Blood panel"]
RAD_EXAMS = {"Chest X-ray": "Chest", "CT scan": "Abdomen", "MRI": "Head", "Ultrasound": "Abdomen"}
PROCEDURES = ["Appendectomy", "Cholecystectomy", "Hip fracture repair",
              "Coronary artery bypass graft", "Cardiac catheterization", "Hernia repair"]
DESTINATIONS = ["home", "home with support", "rehabilitation facility", "long-term care", "transfer to another hospital"]
MEDS = ["Aspirin 81 mg", "Metoprolol 25 mg", "Atorvastatin 40 mg", "Metformin 500 mg",
        "Amoxicillin 500 mg", "Furosemide 40 mg", "Lisinopril 10 mg", "None"]
ALLERGIES = ["None known", "Penicillin", "Latex", "Sulfa drugs", "Peanuts", "Shellfish"]
SYMPTOMS = ["chest pain", "shortness of breath", "fever", "abdominal pain", "dizziness",
            "headache", "cough", "nausea", "fall injury", "weakness"]

START = datetime(2023, 1, 1)
END = datetime(2026, 10, 31)


# ---------------------------------------------------------------------------
# Canonical model (one hospital system per source)
# ---------------------------------------------------------------------------

class Injector:
    """Counts every injected problem so the documentation can report it."""

    def __init__(self, source):
        self.source = source
        self.counts = Counter()

    def hit(self, kind, n=1):
        self.counts[kind] += n


def rand_dt(rng, a, b):
    return a + timedelta(seconds=rng.randint(0, int((b - a).total_seconds())))


def build_hospital(rng, fake, n_patients):
    """Clean canonical data. Problems are injected afterwards."""
    pros = []
    for i in range(1, 41):
        role = ROLES[i % len(ROLES)] if i > 5 else "physician"
        pros.append({"id": i, "name": f"{fake.first_name()} {fake.last_name()}", "role": role})
    by_role = defaultdict(list)
    for p in pros:
        by_role[p["role"]].append(p["id"])

    patients, admissions, triage, stays, diagnoses = [], [], [], [], []
    orders, radiology, surgeries, notes, discharges = [], [], [], [], []
    ids = Counter()

    def nid(kind):
        ids[kind] += 1
        return ids[kind]

    for _ in range(n_patients):
        pid = nid("patient")
        dob = fake.date_of_birth(minimum_age=0, maximum_age=95)
        patients.append({
            "id": pid,
            "first": fake.first_name(), "last": fake.last_name(),
            "dob": dob, "gender": rng.choice(["F", "M", "F", "M", "X"]),
            "address": fake.address().replace("\n", ", "),
            "phone": fake.phone_number(),
            "emergency": f"{fake.first_name()} {fake.last_name()} {fake.phone_number()}",
            "life_status": "alive",
        })
        n_adm = rng.choices([0, 1, 2, 3, 4, 5], [8, 38, 26, 15, 8, 5])[0]
        cursor = rand_dt(rng, START, END - timedelta(days=400))
        for _ in range(n_adm):
            if cursor > END - timedelta(days=2):
                break
            aid = nid("admission")
            atype = rng.choices(ADMISSION_TYPES, ADMISSION_WEIGHTS)[0]
            adt = cursor
            if atype == "newborn":
                if any(a["patient"] == pid for a in admissions):
                    atype = "elective"  # only a first visit can be a birth
                else:
                    patients[-1]["dob"] = adt.date()
            if atype == "outpatient":
                los = timedelta(hours=rng.randint(1, 10))
            else:
                los = timedelta(hours=rng.randint(20, 24 * 18))
            status = rng.choices(["discharged", "deceased"], [96, 4])[0]
            ddt = adt + los
            if ddt > END:
                status, ddt = "active", None
            elif adt > END - timedelta(days=12) and rng.random() < 0.5:
                status, ddt = "active", None
            adm = {
                "id": aid, "patient": pid, "admitting": rng.choice(by_role["physician"]),
                "admit": adt, "type": atype,
                "reason": "Birth" if atype == "newborn" else rng.choice(SYMPTOMS).capitalize(),
                "source": rng.choice(["walk-in", "ambulance", "physician referral", "transfer"]),
                "insurance": f"{fake.company()} #{rng.randint(100000, 999999)}",
                "discharge": ddt, "status": status,
            }
            admissions.append(adm)
            end = ddt or END

            # triage: one per admission, sometimes a reassessment
            for k in range(1 if rng.random() > 0.06 else 2):
                prio = {"emergency": [55, 35, 10], "urgent": [20, 55, 25]}.get(atype, [5, 30, 65])
                triage.append({
                    "id": nid("triage"), "admission": aid,
                    "performer": rng.choice(by_role["nurse"]),
                    "time": adt + timedelta(minutes=5 + 40 * k),
                    "bp": f"{rng.randint(95, 175)}/{rng.randint(55, 105)}",
                    "hr": rng.randint(52, 135), "rr": rng.randint(11, 30),
                    "temp_c": round(rng.uniform(35.8, 40.2), 1),
                    "spo2": rng.randint(85, 100), "pain": rng.randint(0, 10),
                    "symptoms": ", ".join(rng.sample(SYMPTOMS, 2)),
                    "allergies": rng.choice(ALLERGIES),
                    "medications": rng.choice(MEDS),
                    "priority": rng.choices(TRIAGE, prio)[0],
                })

            # unit stays, in order
            path = []
            if atype == "emergency":
                path = ["Emergency Department"]
                if rng.random() < 0.55:
                    path.append(rng.choice(CRITICAL))
                    if rng.random() < 0.25:
                        path.append(rng.choice(CRITICAL))
                path.append("General Ward")
            elif atype in ("urgent", "elective"):
                path = ["General Ward"]
                if rng.random() < 0.3:
                    path.append(rng.choice(CRITICAL))
                    path.append("General Ward")
            elif atype == "newborn":
                path = ["General Ward"]
            elif rng.random() < 0.15:
                path = ["Emergency Department"]
            t = adt + timedelta(minutes=30)
            span = (end - t).total_seconds()
            for j, unit in enumerate(path):
                remaining = len(path) - j
                dur = timedelta(seconds=span / remaining * rng.uniform(0.6, 1.0))
                exit_t = t + dur
                last = j == len(path) - 1
                stays.append({
                    "id": nid("stay"), "admission": aid,
                    "responsible": rng.choice(by_role["physician"]),
                    "unit": unit, "ward_room": f"{unit[:3].upper()}-{rng.randint(1, 40):02d}",
                    "bed": str(rng.randint(1, 4)),
                    "entry": t, "exit": None if (last and ddt is None) else (ddt if last else exit_t),
                    "reason": None if j == 0 else rng.choice(["condition worsened", "condition improved", "monitoring required", "post-operative care"]),
                })
                span -= dur.total_seconds()
                t = exit_t

            # diagnoses: completed admissions get exactly one primary
            if status != "active" or rng.random() < 0.5:
                primary = "V30.00" if atype == "newborn" else rng.choice(ICD9_CODES[:-1])
                codes = [primary] + rng.sample([c for c in ICD9_CODES[:-1] if c != primary], rng.choice([0, 1, 1, 2, 3]))
                for n, code in enumerate(codes):
                    diagnoses.append({
                        "id": nid("diagnosis"), "patient": pid, "admission": aid,
                        "code": code, "diagnoser": rng.choice(by_role["physician"]),
                        "time": adt + timedelta(hours=rng.randint(1, 20)),
                        "type": "primary" if n == 0 else "secondary",
                    })

            # orders and radiology
            for _ in range(rng.choices([0, 1, 2], [45, 40, 15])[0]):
                oid = nid("order")
                exam = rng.choice(ORDER_EXAMS)
                ot = rand_dt(rng, adt, min(end, adt + timedelta(days=3)))
                o_status = rng.choices(["completed", "pending", "in_progress", "cancelled"], [75, 10, 8, 7])[0]
                orders.append({
                    "id": oid, "admission": aid, "requester": rng.choice(by_role["physician"]),
                    "time": ot, "exam": exam, "reason": f"Rule out {rng.choice(['infection', 'fracture', 'ischemia', 'obstruction', 'bleeding'])}",
                    "status": o_status, "priority": rng.choices(["routine", "urgent", "stat"], [55, 30, 15])[0],
                })
                if exam in RAD_EXAMS and o_status in ("completed", "in_progress"):
                    et = min(ot + timedelta(hours=rng.randint(1, 10)), end - timedelta(minutes=10))
                    radiology.append({
                        "id": nid("radiology"), "admission": aid, "order": oid,
                        "referrer": rng.choice(by_role["physician"]),
                        "technician": rng.choice(by_role["radiology technician"]),
                        "type": exam, "time": max(et, ot), "area": RAD_EXAMS[exam],
                        "status": "completed" if o_status == "completed" else "scheduled",
                        "images": f"pacs://img/{aid}/{nid('img')}",
                        "findings": rng.choice(["No acute findings.", "Consolidation in the right lower lobe.",
                                                "Small effusion noted.", "Findings consistent with clinical suspicion.",
                                                "Mild degenerative changes."]),
                    })

            # surgery
            if atype != "outpatient" and atype != "newborn" and rng.random() < 0.14 and ddt is not None:
                st = rand_dt(rng, adt + timedelta(hours=2), adt + (ddt - adt) / 2)
                sid = nid("surgery")
                proc = rng.choice(PROCEDURES)
                surgeries.append({
                    "id": sid, "admission": aid, "surgeon": rng.choice(by_role["surgeon"]),
                    "type": proc, "time": st,
                    "outcome": rng.choices(["successful", "complications", "unsuccessful"], [85, 12, 3])[0],
                })
                notes.append({
                    "id": nid("note"), "admission": aid, "author": rng.choice(by_role["surgeon"]),
                    "type": "operative_note", "time": st + timedelta(hours=2),
                    "text": f"Operative note. {proc} performed. Patient tolerated the procedure.",
                })

            # discharge record + discharge summary
            if ddt is not None:
                died = status == "deceased"
                if died:
                    patients[-1]["life_status"] = "deceased"
                recov = rng.choice(["Recovery", "recovery", "RECOVERY", "Recovery"]) if rng.random() < 0.45 else None
                summary = (f"Discharge summary. Admitted for {adm['reason'].lower()}. "
                           + ("Patient died during the stay." if died else
                              (f"{recov} progressing well." if recov else "Condition stable at discharge.")))
                notes.append({"id": nid("note"), "admission": aid, "author": adm["admitting"],
                              "type": "discharge_summary", "time": ddt, "text": summary})
                discharges.append({
                    "id": nid("discharge"), "admission": aid, "authorizer": rng.choice(by_role["physician"]),
                    "time": ddt,
                    "destination": "morgue" if died else rng.choice(DESTINATIONS),
                    "condition": "deceased" if died else rng.choice(["stable", "improved", "fair"]),
                    "medications": None if died else rng.choice(MEDS),
                    "follow_up": None if died else rng.choice(["Follow up with family doctor in 2 weeks.", "Return if symptoms worsen.", "Rest and hydration."]),
                    "appointments": None if died else (adt + timedelta(days=30)).date().isoformat(),
                })
            cursor = (ddt or adt) + timedelta(days=rng.randint(30, 300))

    return {
        "professionals": pros, "patients": patients, "admissions": admissions,
        "triage": triage, "stays": stays, "diagnoses": diagnoses, "orders": orders,
        "radiology": radiology, "surgeries": surgeries, "notes": notes, "discharges": discharges,
    }


# ---------------------------------------------------------------------------
# Controlled data-quality problems (applied to the canonical model)
# ---------------------------------------------------------------------------

def inject_common(h, rng, inj, fake):
    P, A = h["patients"], h["admissions"]
    pid_max = max(p["id"] for p in P)
    aid_set = {a["id"] for a in A}

    # Entity duplicates: same person registered again under a new local id,
    # name written differently. Half of them get one admission moved over.
    for p in rng.sample(P, max(1, len(P) // 100)):
        pid_max += 1
        d = dict(p, id=pid_max)
        d["first"] = rng.choice([d["first"].upper(), d["first"].lower(), f" {d['first']}  "])
        P.append(d)
        own = [a for a in A if a["patient"] == p["id"]]
        if own and rng.random() < 0.5:
            moved = rng.choice(own)
            moved["patient"] = d["id"]
            for dx in h["diagnoses"]:
                if dx["admission"] == moved["id"]:
                    dx["patient"] = d["id"]
        inj.hit("entity_duplicate_patient")

    # Missing required values
    for p in rng.sample(P, max(1, len(P) // 150)):
        p["last"] = None; inj.hit("missing_required_patient_name")
    for p in rng.sample(P, max(1, len(P) // 150)):
        p["dob"] = None; inj.hit("missing_required_date_of_birth")
    for a in rng.sample(A, max(1, len(A) // 200)):
        a["admit"] = None; inj.hit("missing_required_admission_time")
    for d in rng.sample(h["diagnoses"], max(1, len(h["diagnoses"]) // 200)):
        d["code"] = None; inj.hit("missing_required_icd9_code")

    # Missing optional values
    for p in P:
        if rng.random() < 0.08: p["phone"] = None; inj.hit("missing_optional_phone")
        if rng.random() < 0.06: p["address"] = None; inj.hit("missing_optional_address")
        if rng.random() < 0.05: p["emergency"] = None; inj.hit("missing_optional_emergency_contact")
    for a in A:
        if rng.random() < 0.10: a["insurance"] = None; inj.hit("missing_optional_insurance")
    for t in h["triage"]:
        if rng.random() < 0.05: t["allergies"] = None; inj.hit("missing_optional_allergies")

    # Inconsistent capitalization / whitespace in names
    for p in P:
        if rng.random() < 0.05 and p["last"]:
            p["last"] = rng.choice([p["last"].upper(), p["last"].lower(), f"  {p['last']} "])
            inj.hit("messy_name_text")

    # Invalid numeric values in triage
    for t in h["triage"]:
        r = rng.random()
        if r < 0.008: t["hr"] = rng.choice([-5, 0, 420]); inj.hit("invalid_heart_rate")
        elif r < 0.014: t["pain"] = rng.choice([-1, 11, 15]); inj.hit("invalid_pain_level")
        elif r < 0.019: t["temp_c"] = rng.choice([4.5, 98.0, 410.0]); inj.hit("invalid_temperature")
        elif r < 0.024: t["spo2"] = rng.choice([105, 140, -3]); inj.hit("invalid_oxygen_saturation")
        elif r < 0.029: t["rr"] = rng.choice(["abc", "--", "?"]); inj.hit("non_numeric_respiratory_rate")

    # Broken references
    ghost = max(aid_set) + 5000
    for a in rng.sample(A, max(1, len(A) // 100)):
        a["patient"] = pid_max + rng.randint(1000, 9000); inj.hit("broken_admission_patient_ref")
    for d in rng.sample(h["diagnoses"], max(1, len(h["diagnoses"]) // 200)):
        d["code"] = rng.choice(["999.99", "123.45", "E000"]); inj.hit("broken_diagnosis_icd9_ref")
    for s in rng.sample(h["stays"], max(1, len(h["stays"]) // 200)):
        s["admission"] = ghost + rng.randint(1, 999); inj.hit("broken_unitstay_admission_ref")
    if h["radiology"]:
        for r in rng.sample(h["radiology"], max(1, len(h["radiology"]) // 100)):
            r["order"] = 90000 + rng.randint(1, 999); inj.hit("broken_radiology_order_ref")
    adm_by_id = {a["id"]: a for a in A}
    for d in rng.sample(h["diagnoses"], max(1, len(h["diagnoses"]) // 300)):
        others = [p["id"] for p in P if p["id"] != adm_by_id[d["admission"]]["patient"]]
        d["patient"] = rng.choice(others); inj.hit("diagnosis_patient_mismatch")

    # Chronology problems
    done = [a for a in A if a["discharge"] and a["admit"]]
    for a in rng.sample(done, max(1, len(done) // 100)):
        a["discharge"] = a["admit"] - timedelta(hours=rng.randint(2, 72)); inj.hit("discharge_before_admission")
    closed = [s for s in h["stays"] if s["exit"]]
    for s in rng.sample(closed, max(1, len(closed) // 100)):
        s["exit"] = s["entry"] - timedelta(hours=rng.randint(1, 30)); inj.hit("unit_exit_before_entry")
    for s in rng.sample(h["surgeries"], max(1, len(h["surgeries"]) // 25)):
        a = adm_by_id[s["admission"]]
        if a["admit"]:
            s["time"] = a["admit"] - timedelta(days=rng.randint(2, 20)); inj.hit("procedure_outside_admission")
    for r in rng.sample(h["radiology"], max(1, len(h["radiology"]) // 100)):
        a = adm_by_id[r["admission"]]
        end = a["discharge"] or END
        r["time"] = end + timedelta(days=rng.randint(3, 15)); inj.hit("exam_outside_admission")

    # Discharge information disagreeing with admission status
    active = [a for a in A if a["status"] == "active"]
    for a in rng.sample(active, min(len(active), max(1, len(A) // 300))):
        h["discharges"].append({
            "id": max(d["id"] for d in h["discharges"]) + 1, "admission": a["id"],
            "authorizer": a["admitting"], "time": (a["admit"] or START) + timedelta(days=2),
            "destination": "home", "condition": "stable", "medications": None,
            "follow_up": None, "appointments": None,
        })
        inj.hit("discharge_record_for_active_admission")


def exact_duplicates(rows, rng, inj, kind, rate):
    """Append verbatim copies of some rows (same local id, same values)."""
    picks = rng.sample(rows, max(1, int(len(rows) * rate)))
    rows.extend(dict(r) for r in picks)
    inj.hit(f"exact_duplicate_{kind}", len(picks))


def messy_label(label, rng, inj, rate=0.05):
    if label is None or rng.random() >= rate:
        return label
    inj.hit("messy_category_label")
    return rng.choice([label.upper(), label.lower(), f" {label} ", f"{label}  "])


def fmt_or_none(v, f):
    return None if v is None else f(v)


# ---------------------------------------------------------------------------
# Source A - Europe - TXT (pipe-delimited). Local time Europe/Paris, no offset.
# Dates DD/MM/YYYY HH:MM. Decimal comma. Missing = empty or "N/A".
# ---------------------------------------------------------------------------

A_ADM = {"emergency": "EMER", "urgent": "URG", "elective": "ELEC", "outpatient": "AMB", "newborn": "NN"}
A_TRI = {"high": "1", "medium": "2", "low": "3"}
A_UNIT = {"Emergency Department": "URGENCES", "ICU": "REA", "CCU": "USIC", "MICU": "REA-MED",
          "SICU": "REA-CHIR", "General Ward": "MED"}
A_STATUS = {"discharged": "SORTI", "deceased": "DECEDE", "active": "EN COURS"}


def write_source_a(h, rng, inj):
    d = OUT / "source_A_europe"
    d.mkdir(parents=True, exist_ok=True)

    def dt(v):
        if v is None:
            return rng.choice(["", "N/A"])
        if rng.random() < 0.02 and v.day <= 12:  # written US-style: ambiguous
            inj.hit("ambiguous_date_mm_dd")
            return v.strftime("%m/%d/%Y %H:%M")
        return v.strftime("%d/%m/%Y %H:%M")

    def date(v):
        return rng.choice(["", "N/A"]) if v is None else v.strftime("%d/%m/%Y")

    def num(v):
        if v is None:
            return ""
        return str(v).replace(".", ",") if isinstance(v, float) else str(v)

    def opt(v):
        return v if v is not None else rng.choice(["", "N/A"])

    def bad_date(s):
        if rng.random() < 0.006:
            inj.hit("invalid_date")
            return rng.choice(["31/02/2025 10:00", "00/13/2024 08:30", "45/07/2025 25:61", "??/??/????"])
        return s

    tables = {
        "professionals.txt": (["prof_no", "nom_complet", "fonction"],
                              [[p["id"], p["name"], p["role"].upper()] for p in h["professionals"]]),
        "icd9_dictionary.txt": (["code_cim9", "libelle_officiel", "description", "categorie"],
                                [[c, t, t.lower(), cat] for c, t, cat in ICD9]),
        "patients.txt": (["pat_no", "nom", "prenom", "date_naissance", "sexe", "adresse", "telephone", "contact_urgence", "statut_vital"],
                         [[p["id"], opt(p["last"]), p["first"], date(p["dob"]),
                           {"F": "F", "M": "H", "X": "I"}[p["gender"]], opt(p["address"]),
                           opt(p["phone"]), opt(p["emergency"]),
                           "VIVANT" if p["life_status"] == "alive" else "DECEDE"] for p in h["patients"]]),
        "admissions.txt": (["sejour_no", "pat_no", "medecin_admission", "date_entree", "type_sejour", "motif", "provenance", "assurance", "date_sortie", "statut"],
                           [[a["id"], a["patient"], a["admitting"], bad_date(dt(a["admit"])),
                             messy_label(A_ADM[a["type"]], rng, inj), a["reason"], a["source"], opt(a["insurance"]),
                             dt(a["discharge"]), A_STATUS[a["status"]]] for a in h["admissions"]]),
        "triage.txt": (["triage_no", "sejour_no", "infirmier", "date_heure", "tension", "fc", "fr", "temp_c", "spo2_pct", "douleur", "symptomes", "allergies", "traitement", "priorite"],
                       [[t["id"], t["admission"], t["performer"], dt(t["time"]), t["bp"], num(t["hr"]), num(t["rr"]),
                         num(t["temp_c"]), num(t["spo2"]), num(t["pain"]), t["symptoms"], opt(t["allergies"]),
                         t["medications"], messy_label(A_TRI[t["priority"]], rng, inj)] for t in h["triage"]]),
        "mouvements.txt": (["mvt_no", "sejour_no", "medecin_resp", "unite", "chambre", "lit", "entree", "sortie", "motif_transfert"],
                           [[s["id"], s["admission"], s["responsible"], messy_label(A_UNIT[s["unit"]], rng, inj),
                             s["ward_room"], s["bed"], dt(s["entry"]), dt(s["exit"]) if s["exit"] else "",
                             opt(s["reason"])] for s in h["stays"]]),
        "diagnostics.txt": (["diag_no", "pat_no", "sejour_no", "code_cim9", "medecin", "date_heure", "rang"],
                            [[x["id"], x["patient"], x["admission"], x["code"] or "", x["diagnoser"], dt(x["time"]),
                              "P" if x["type"] == "primary" else "S"] for x in h["diagnoses"]]),
        "demandes_examen.txt": (["demande_no", "sejour_no", "prescripteur", "date_heure", "examen", "motif", "statut", "priorite"],
                                [[o["id"], o["admission"], o["requester"], dt(o["time"]), o["exam"], o["reason"],
                                  o["status"].upper(), o["priority"].upper()] for o in h["orders"]]),
        "radiologie.txt": (["examen_no", "sejour_no", "demande_no", "medecin_ref", "manipulateur", "type_examen", "date_heure", "zone", "statut", "lien_images", "compte_rendu"],
                           [[r["id"], r["admission"], r["order"], r["referrer"], r["technician"], r["type"], dt(r["time"]),
                             r["area"], r["status"].upper(), r["images"], r["findings"]] for r in h["radiology"]]),
        "chirurgie.txt": (["acte_no", "sejour_no", "chirurgien", "intervention", "date_heure", "resultat"],
                          [[s["id"], s["admission"], s["surgeon"], s["type"], dt(s["time"]), s["outcome"]] for s in h["surgeries"]]),
        "notes_cliniques.txt": (["note_no", "sejour_no", "auteur", "type_note", "date_heure", "contenu"],
                                [[n["id"], n["admission"], n["author"], n["type"].upper(), dt(n["time"]), n["text"]] for n in h["notes"]]),
        "sorties.txt": (["sortie_no", "sejour_no", "medecin_autorisant", "date_sortie", "destination", "etat_sortie", "ordonnance", "consignes", "rdv"],
                        [[x["id"], x["admission"], x["authorizer"], dt(x["time"]), x["destination"], x["condition"],
                          opt(x["medications"]), opt(x["follow_up"]), opt(x["appointments"])] for x in h["discharges"]]),
    }
    for name, (header, rows) in tables.items():
        with open(d / name, "w", encoding="utf-8", newline="\n") as f:
            f.write("|".join(header) + "\n")
            for i, r in enumerate(rows):
                line = "|".join("" if v is None else str(v).replace("|", "/") for v in r)
                if name in ("patients.txt", "admissions.txt") and rng.random() < 0.003:
                    line = line.rsplit("|", 2)[0]  # truncated line: wrong field count
                    inj.hit("malformed_line_wrong_field_count")
                f.write(line + "\n")


# ---------------------------------------------------------------------------
# Source B - North America - CSV. Local time America/Toronto, no offset.
# Dates MM/DD/YYYY hh:mm AM/PM. Fahrenheit. Missing = "", "NULL", "unknown".
# Names written "Last, First". ICD-9 leading zeros sometimes lost.
# ---------------------------------------------------------------------------

B_ADM = {"emergency": "Emergency", "urgent": "Urgent", "elective": "Elective", "outpatient": "Outpatient", "newborn": "Newborn"}
B_TRI = {"high": "High", "medium": "Medium", "low": "Low"}
B_UNIT = {"Emergency Department": "Emergency Department", "ICU": "Intensive Care Unit", "CCU": "Coronary Care Unit",
          "MICU": "Medical ICU", "SICU": "Surgical ICU", "General Ward": "General Ward"}


def write_source_b(h, rng, inj):
    d = OUT / "source_B_north_america"
    d.mkdir(parents=True, exist_ok=True)
    miss = lambda: rng.choice(["", "NULL", "unknown"])

    def dt(v):
        if v is None:
            return miss()
        if rng.random() < 0.006:
            inj.hit("invalid_date")
            return rng.choice(["02/30/2025 10:00 AM", "13/45/2024 09:15 PM", "TBD"])
        return v.strftime("%m/%d/%Y %I:%M %p")

    def code(c):
        if c and c.startswith("0") and rng.random() < 0.3:
            inj.hit("icd9_leading_zero_lost")
            return c.lstrip("0")
        return c or miss()

    def f_temp(c):
        if isinstance(c, (int, float)):
            return round(c * 9 / 5 + 32, 1)
        return c

    tables = {
        "professionals.csv": (["ProviderID", "ProviderName", "Title"],
                              [[p["id"], p["name"], p["role"].title()] for p in h["professionals"]]),
        "icd9_codes.csv": (["ICD9Code", "Title", "LongDescription", "Chapter"],
                           [[c, t, t, cat] for c, t, cat in ICD9]),
        "patients.csv": (["PatientID", "FullName", "DOB", "Sex", "HomeAddress", "Phone", "EmergencyContact", "Deceased"],
                         [[p["id"], f"{p['last'] if p['last'] else ''}, {p['first']}", p["dob"].strftime("%m/%d/%Y") if p["dob"] else miss(),
                           {"F": "Female", "M": "Male", "X": "Unknown"}[p["gender"]], p["address"] or miss(), p["phone"] or miss(),
                           p["emergency"] or miss(), "Y" if p["life_status"] == "deceased" else "N"] for p in h["patients"]]),
        "encounters.csv": (["EncounterID", "PatientID", "AdmittingProviderID", "AdmitDateTime", "AdmitType", "ChiefComplaint", "AdmitSource", "Insurance", "DischargeDateTime", "EncounterStatus"],
                           [[a["id"], a["patient"], a["admitting"], dt(a["admit"]), messy_label(B_ADM[a["type"]], rng, inj), a["reason"],
                             a["source"].title(), a["insurance"] or miss(), dt(a["discharge"]) if a["discharge"] else "",
                             {"discharged": "Discharged", "deceased": "Expired", "active": "In House"}[a["status"]]] for a in h["admissions"]]),
        "triage.csv": (["TriageID", "EncounterID", "NurseID", "AssessedAt", "BloodPressure", "HeartRate", "RespRate", "TempF", "SpO2", "PainScore", "Symptoms", "Allergies", "HomeMeds", "Acuity"],
                       [[t["id"], t["admission"], t["performer"], dt(t["time"]), t["bp"], t["hr"], t["rr"], f_temp(t["temp_c"]),
                         t["spo2"], t["pain"], t["symptoms"], t["allergies"] or miss(), t["medications"],
                         messy_label(B_TRI[t["priority"]], rng, inj)] for t in h["triage"]]),
        "unit_stays.csv": (["StayID", "EncounterID", "AttendingID", "Unit", "Room", "Bed", "InTime", "OutTime", "TransferReason"],
                           [[s["id"], s["admission"], s["responsible"], messy_label(B_UNIT[s["unit"]], rng, inj), s["ward_room"], s["bed"],
                             dt(s["entry"]), dt(s["exit"]) if s["exit"] else "", s["reason"] or ""] for s in h["stays"]]),
        "diagnoses.csv": (["DxID", "PatientID", "EncounterID", "ICD9", "ProviderID", "DxDateTime", "DxRank"],
                          [[x["id"], x["patient"], x["admission"], code(x["code"]), x["diagnoser"], dt(x["time"]),
                            "Principal" if x["type"] == "primary" else "Secondary"] for x in h["diagnoses"]]),
        "orders.csv": (["OrderID", "EncounterID", "OrderingProviderID", "OrderedAt", "Test", "Indication", "OrderStatus", "Priority"],
                       [[o["id"], o["admission"], o["requester"], dt(o["time"]), o["exam"], o["reason"], o["status"].title(), o["priority"].upper()] for o in h["orders"]]),
        "imaging.csv": (["ImagingID", "EncounterID", "OrderID", "ReferringProviderID", "TechID", "Modality", "PerformedAt", "BodyPart", "Status", "ImageURL", "Impression"],
                        [[r["id"], r["admission"], r["order"], r["referrer"], r["technician"], r["type"], dt(r["time"]), r["area"],
                          r["status"].title(), r["images"], r["findings"]] for r in h["radiology"]]),
        "procedures.csv": (["ProcedureID", "EncounterID", "SurgeonID", "Procedure", "PerformedAt", "Outcome"],
                           [[s["id"], s["admission"], s["surgeon"], s["type"], dt(s["time"]), s["outcome"].title()] for s in h["surgeries"]]),
        "notes.csv": (["NoteID", "EncounterID", "AuthorID", "NoteType", "WrittenAt", "NoteText"],
                      [[n["id"], n["admission"], n["author"], n["type"].replace("_", " ").title(), dt(n["time"]), n["text"]] for n in h["notes"]]),
        "discharges.csv": (["DischargeID", "EncounterID", "AuthorizingProviderID", "DischargedAt", "Disposition", "ConditionAtDischarge", "Prescriptions", "Instructions", "FollowUp"],
                           [[x["id"], x["admission"], x["authorizer"], dt(x["time"]), x["destination"].title(), x["condition"].title(),
                             x["medications"] or miss(), x["follow_up"] or miss(), x["appointments"] or ""] for x in h["discharges"]]),
    }
    for name, (header, rows) in tables.items():
        with open(d / name, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            for r in rows:
                if name in ("patients.csv", "encounters.csv") and rng.random() < 0.003:
                    w.writerow(["" if v is None else v for v in r] + ["EXTRA", "FIELD"])  # malformed: too many fields
                    inj.hit("malformed_line_extra_fields")
                    continue
                w.writerow(["" if v is None else v for v in r])


# ---------------------------------------------------------------------------
# Source C - Asia - XML. Local time Asia/Singapore, ISO 8601 with +08:00.
# Oxygen saturation as a fraction (0.97). Missing = empty or absent element.
# ---------------------------------------------------------------------------

SGT = timezone(timedelta(hours=8))
C_ADM = {"emergency": "ER", "urgent": "Urgent Care", "elective": "Scheduled", "outpatient": "Ambulatory", "newborn": "Birth"}
C_TRI = {"high": "Red", "medium": "Yellow", "low": "Green"}
C_UNIT = {"Emergency Department": "Emergency Room", "ICU": "ICU", "CCU": "CCU", "MICU": "Medical ICU",
          "SICU": "Surgical ICU", "General Ward": "Ward"}


def write_source_c(h, rng, inj):
    d = OUT / "source_C_asia"
    d.mkdir(parents=True, exist_ok=True)

    def ts(v):
        if v is None:
            return None
        if rng.random() < 0.006:
            inj.hit("invalid_date")
            return rng.choice(["2025-02-30T10:00:00+08:00", "2024-13-01T08:00:00+08:00", "unknown"])
        return v.replace(tzinfo=SGT).isoformat()

    def sub(parent, tag, value, keep_empty=True):
        if value is None:
            if keep_empty and rng.random() < 0.5:
                ET.SubElement(parent, tag)  # empty element
            return  # otherwise the element is simply absent
        ET.SubElement(parent, tag).text = str(value)

    root = ET.Element("hospitalSystem", {"continent": "Asia", "name": "Fictional Asia Regional Hospital", "timezone": "Asia/Singapore"})
    pros = ET.SubElement(root, "staff")
    for p in h["professionals"]:
        e = ET.SubElement(pros, "member", {"staffId": f"S{p['id']:03d}"})
        sub(e, "name", p["name"]); sub(e, "role", p["role"])
    dic = ET.SubElement(root, "icd9Dictionary")
    for c, t, cat in ICD9:
        e = ET.SubElement(dic, "entry", {"code": c})
        sub(e, "title", t); sub(e, "category", cat)

    pts = ET.SubElement(root, "patients")
    for p in h["patients"]:
        e = ET.SubElement(pts, "patient", {"patientNo": str(p["id"])})
        n = ET.SubElement(e, "name")
        sub(n, "family", p["last"]); sub(n, "given", p["first"])
        sub(e, "birthDate", p["dob"].isoformat() if p["dob"] else None)
        sub(e, "gender", {"F": "female", "M": "male", "X": "unspecified"}[p["gender"]])
        sub(e, "address", p["address"]); sub(e, "phone", p["phone"]); sub(e, "nextOfKin", p["emergency"])
        sub(e, "vitalStatus", "living" if p["life_status"] == "alive" else "dead")

    by_adm = defaultdict(lambda: defaultdict(list))
    for kind in ("triage", "stays", "diagnoses", "orders", "radiology", "surgeries", "notes", "discharges"):
        for r in h[kind]:
            by_adm[r["admission"]][kind].append(r)
    rad_by_order = defaultdict(list)
    for r in h["radiology"]:
        rad_by_order[r["order"]].append(r)
    order_ids = {o["id"] for o in h["orders"]}

    adms = ET.SubElement(root, "admissions")
    all_adm_ids = [a["id"] for a in h["admissions"]] + sorted(set(by_adm) - {a["id"] for a in h["admissions"]})
    adm_by_id = {}
    for a in h["admissions"]:
        adm_by_id.setdefault(a["id"], []).append(a)
    for aid in dict.fromkeys(all_adm_ids):
        rows = adm_by_id.get(aid) or [None]
        for a in rows:
            attrs = {"admissionNo": str(aid)}
            if a:
                attrs["patientRef"] = str(a["patient"])
            e = ET.SubElement(adms, "admission", attrs)
            if a:
                sub(e, "admittedAt", ts(a["admit"])); sub(e, "category", messy_label(C_ADM[a["type"]], rng, inj))
                sub(e, "reason", a["reason"]); sub(e, "arrivalMode", a["source"]); sub(e, "insurer", a["insurance"])
                sub(e, "admittingStaff", f"S{a['admitting']:03d}")
                sub(e, "dischargedAt", ts(a["discharge"]), keep_empty=False)
                sub(e, "status", {"discharged": "Discharged", "deceased": "Died", "active": "Admitted"}[a["status"]])
            ch = by_adm[aid]
            if a is not rows[0]:
                continue  # children once, under the first copy
            for t in ch["triage"]:
                x = ET.SubElement(e, "triage", {"id": str(t["id"])})
                sub(x, "nurse", f"S{t['performer']:03d}"); sub(x, "at", ts(t["time"])); sub(x, "bp", t["bp"])
                sub(x, "pulse", t["hr"]); sub(x, "respiration", t["rr"]); sub(x, "temperatureC", t["temp_c"])
                spo2 = t["spo2"]
                sub(x, "oxygenSaturation", round(spo2 / 100, 2) if isinstance(spo2, int) else spo2)
                sub(x, "pain", t["pain"]); sub(x, "symptoms", t["symptoms"]); sub(x, "allergies", t["allergies"])
                sub(x, "medications", t["medications"]); sub(x, "level", messy_label(C_TRI[t["priority"]], rng, inj))
            for s in ch["stays"]:
                x = ET.SubElement(e, "unitStay", {"id": str(s["id"])})
                sub(x, "unit", messy_label(C_UNIT[s["unit"]], rng, inj)); sub(x, "room", s["ward_room"]); sub(x, "bed", s["bed"])
                sub(x, "in", ts(s["entry"])); sub(x, "out", ts(s["exit"]), keep_empty=False)
                sub(x, "doctor", f"S{s['responsible']:03d}"); sub(x, "transferReason", s["reason"], keep_empty=False)
            for dx in ch["diagnoses"]:
                x = ET.SubElement(e, "diagnosis", {"id": str(dx["id"]), "patientRef": str(dx["patient"])})
                sub(x, "icd9", dx["code"]); sub(x, "kind", dx["type"].upper()); sub(x, "at", ts(dx["time"]))
                sub(x, "doctor", f"S{dx['diagnoser']:03d}")
            for o in ch["orders"]:
                x = ET.SubElement(e, "order", {"id": str(o["id"])})
                sub(x, "test", o["exam"]); sub(x, "at", ts(o["time"])); sub(x, "reason", o["reason"])
                sub(x, "status", o["status"]); sub(x, "priority", o["priority"]); sub(x, "doctor", f"S{o['requester']:03d}")
                for r in rad_by_order.get(o["id"], []):
                    y = ET.SubElement(x, "radiologyExam", {"id": str(r["id"])})
                    sub(y, "type", r["type"]); sub(y, "at", ts(r["time"])); sub(y, "bodyArea", r["area"])
                    sub(y, "status", r["status"]); sub(y, "images", r["images"]); sub(y, "report", r["findings"])
                    sub(y, "referrer", f"S{r['referrer']:03d}"); sub(y, "technician", f"S{r['technician']:03d}")
            for r in ch["radiology"]:
                if r["order"] not in order_ids:  # broken order reference: kept as a standalone exam
                    y = ET.SubElement(e, "radiologyExam", {"id": str(r["id"]), "orderRef": str(r["order"])})
                    sub(y, "type", r["type"]); sub(y, "at", ts(r["time"])); sub(y, "bodyArea", r["area"])
                    sub(y, "status", r["status"]); sub(y, "images", r["images"]); sub(y, "report", r["findings"])
                    sub(y, "referrer", f"S{r['referrer']:03d}"); sub(y, "technician", f"S{r['technician']:03d}")
            for s in ch["surgeries"]:
                x = ET.SubElement(e, "surgery", {"id": str(s["id"])})
                sub(x, "procedure", s["type"]); sub(x, "at", ts(s["time"])); sub(x, "outcome", s["outcome"])
                sub(x, "surgeon", f"S{s['surgeon']:03d}")
            for n in ch["notes"]:
                x = ET.SubElement(e, "note", {"id": str(n["id"]), "type": n["type"]})
                sub(x, "at", ts(n["time"])); sub(x, "author", f"S{n['author']:03d}"); sub(x, "text", n["text"])
            for dc in ch["discharges"]:
                x = ET.SubElement(e, "discharge", {"id": str(dc["id"])})
                sub(x, "at", ts(dc["time"])); sub(x, "destination", dc["destination"]); sub(x, "condition", dc["condition"])
                sub(x, "medications", dc["medications"]); sub(x, "followUp", dc["follow_up"])
                sub(x, "appointment", dc["appointments"]); sub(x, "authorizedBy", f"S{dc['authorizer']:03d}")

    xml = minidom.parseString(ET.tostring(root, encoding="utf-8")).toprettyxml(indent="  ", encoding="utf-8")
    (d / "hospital_asia.xml").write_bytes(xml)


# ---------------------------------------------------------------------------
# Source D - Africa - JSON. Mostly UTC ISO 8601 ("Z"); some local times with
# no offset (unknown zone) and some epoch seconds. Missing = null, "", absent.
# Admission type and triage priority as numeric codes (see codebook).
# ---------------------------------------------------------------------------

SAST = timezone(timedelta(hours=2))
D_ADM = {"emergency": 1, "urgent": 2, "elective": 3, "outpatient": 4, "newborn": 5}
D_TRI = {"high": "P1", "medium": "P2", "low": "P3"}
D_UNIT = {"Emergency Department": "emergency", "ICU": "icu", "CCU": "ccu", "MICU": "micu", "SICU": "sicu", "General Ward": "ward"}


def write_source_d(h, rng, inj):
    d = OUT / "source_D_africa"
    d.mkdir(parents=True, exist_ok=True)

    def ts(v):
        if v is None:
            return rng.choice([None, ""])
        local = v.replace(tzinfo=SAST)
        r = rng.random()
        if r < 0.03:
            inj.hit("timestamp_without_timezone")
            return v.strftime("%Y-%m-%dT%H:%M:%S")
        if r < 0.04:
            inj.hit("timestamp_as_epoch_seconds")
            return int(local.timestamp())
        if r < 0.046:
            inj.hit("invalid_date")
            return rng.choice(["2025-02-30T10:00:00Z", "31-31-2024", "not recorded"])
        return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def opt(v):
        return v if v is not None else rng.choice([None, "", "unknown"])

    def maybe_str(v):
        return str(v) if (isinstance(v, (int, float)) and rng.random() < 0.15) else v

    out = {
        "facility": {"name": "Fictional Africa Teaching Hospital", "continent": "Africa",
                     "local_timezone": "Africa/Johannesburg",
                     "codebook": {"encounter_type": {str(v): k for k, v in D_ADM.items()},
                                  "triage_category": {v: k for k, v in D_TRI.items()}}},
        "practitioners": [{"practitioner_id": f"PR-{p['id']}", "display_name": p["name"], "speciality": p["role"]} for p in h["professionals"]],
        "icd9_reference": [{"icd9": c, "label": t, "group": cat} for c, t, cat in ICD9],
        "patients": [],
        "encounters": [],
    }
    for p in h["patients"]:
        rec = {"mrn": p["id"], "surname": p["last"], "first_names": p["first"],
               "birth_date": p["dob"].isoformat() if p["dob"] else None,
               "sex": {"F": "f", "M": "m", "X": "o"}[p["gender"]],
               "contact": {"address": opt(p["address"]), "phone": opt(p["phone"]), "next_of_kin": opt(p["emergency"])},
               "deceased": p["life_status"] == "deceased"}
        if rec["surname"] is None and rng.random() < 0.5:
            del rec["surname"]  # absent key rather than null
        out["patients"].append(rec)

    by_adm = defaultdict(lambda: defaultdict(list))
    for kind in ("triage", "stays", "diagnoses", "orders", "radiology", "surgeries", "notes", "discharges"):
        for r in h[kind]:
            by_adm[r["admission"]][kind].append(r)
    seen = set()
    enc_rows = list(h["admissions"]) + [{"id": aid, "orphan": True} for aid in sorted(set(by_adm) - {a["id"] for a in h["admissions"]})]
    for a in enc_rows:
        if a.get("orphan"):
            enc = {"encounter_id": a["id"], "patient_mrn": None}
        else:
            enc = {"encounter_id": a["id"], "patient_mrn": a["patient"], "admitted_by": f"PR-{a['admitting']}",
                   "start": ts(a["admit"]), "encounter_type": D_ADM[a["type"]], "reason": a["reason"],
                   "referral_source": a["source"], "medical_aid": opt(a["insurance"]),
                   "end": ts(a["discharge"]) if a["discharge"] else None,
                   "outcome": messy_label({"discharged": "discharged", "deceased": "died", "active": "inpatient"}[a["status"]], rng, inj)}
        ch = by_adm[a["id"]]
        first = a["id"] not in seen
        seen.add(a["id"])
        if first:
            enc["triage"] = [{"triage_id": t["id"], "nurse": f"PR-{t['performer']}", "at": ts(t["time"]), "bp": t["bp"],
                              "pulse": maybe_str(t["hr"]), "resp_rate": maybe_str(t["rr"]), "temp_c": maybe_str(t["temp_c"]),
                              "spo2": maybe_str(t["spo2"]), "pain_score": maybe_str(t["pain"]), "complaints": t["symptoms"].split(", "),
                              "allergies": opt(t["allergies"]), "current_meds": t["medications"],
                              "category": messy_label(D_TRI[t["priority"]], rng, inj)} for t in ch["triage"]]
            enc["ward_movements"] = [{"movement_id": s["id"], "ward": messy_label(D_UNIT[s["unit"]], rng, inj), "room": s["ward_room"],
                                      "bed": s["bed"], "from": ts(s["entry"]), "to": ts(s["exit"]) if s["exit"] else None,
                                      "clinician": f"PR-{s['responsible']}", "why": s["reason"]} for s in ch["stays"]]
            enc["diagnoses"] = [{"dx_id": x["id"], "patient_mrn": x["patient"], "icd9": x["code"],
                                 "primary": x["type"] == "primary", "at": ts(x["time"]), "by": f"PR-{x['diagnoser']}"} for x in ch["diagnoses"]]
            enc["investigations"] = [{"order_id": o["id"], "test": o["exam"], "requested_at": ts(o["time"]), "requested_by": f"PR-{o['requester']}",
                                      "indication": o["reason"], "state": o["status"], "urgency": o["priority"]} for o in ch["orders"]]
            enc["imaging"] = [{"imaging_id": r["id"], "order_id": r["order"], "modality": r["type"], "at": ts(r["time"]),
                               "region": r["area"], "state": r["status"], "pacs_link": r["images"], "report": r["findings"],
                               "referred_by": f"PR-{r['referrer']}", "radiographer": f"PR-{r['technician']}"} for r in ch["radiology"]]
            enc["theatre"] = [{"procedure_id": s["id"], "procedure": s["type"], "at": ts(s["time"]), "surgeon": f"PR-{s['surgeon']}",
                               "result": s["outcome"]} for s in ch["surgeries"]]
            enc["notes"] = [{"note_id": n["id"], "kind": n["type"], "at": ts(n["time"]), "author": f"PR-{n['author']}", "body": n["text"]} for n in ch["notes"]]
            dcs = [{"discharge_id": x["id"], "at": ts(x["time"]), "to": x["destination"], "condition": x["condition"],
                    "scripts": x["medications"], "advice": x["follow_up"], "next_visit": x["appointments"],
                    "authorised_by": f"PR-{x['authorizer']}"} for x in ch["discharges"]]
            enc["discharge"] = dcs[0] if len(dcs) == 1 else (dcs or None)
        out["encounters"].append(enc)

    (d / "hospital_africa.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------

def make_source(key, locale, seed, n_patients, writer):
    rng = random.Random(seed)
    fake = Faker(locale)
    fake.seed_instance(seed)
    inj = Injector(key)
    h = build_hospital(rng, fake, n_patients)
    inject_common(h, rng, inj, fake)
    exact_duplicates(h["patients"], rng, inj, "patient", 0.015)
    exact_duplicates(h["admissions"], rng, inj, "admission", 0.01)
    exact_duplicates(h["diagnoses"], rng, inj, "diagnosis", 0.01)
    rng.shuffle(h["patients"])
    writer(h, rng, inj)
    counts = {k: len(v) for k, v in h.items()}
    counts["icd9_dictionary"] = len(ICD9)
    return {"records_by_entity": counts, "total_records": sum(counts.values()),
            "injected_problems": dict(sorted(inj.counts.items()))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "A_europe_txt": make_source("A", "fr_FR", 3631, 480, write_source_a),
        "B_north_america_csv": make_source("B", "en_CA", 3632, 500, write_source_b),
        "C_asia_xml": make_source("C", "en_IN", 3633, 500, write_source_c),
        "D_africa_json": make_source("D", "zu_ZA", 3634, 460, write_source_d),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for k, v in manifest.items():
        print(f"{k:22s} {v['total_records']:>6,d} records")


if __name__ == "__main__":
    main()
