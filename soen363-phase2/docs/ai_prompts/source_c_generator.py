"""
Source C raw data generator (SOEN 363 Project Phase 2) - AI-generated, part of the AI disclosure.

STATEMENT: all data produced by this script is entirely fictional, created exclusively for
educational and learning purposes. It does not describe real patients and does not include any
real personal information. Names are random combinations of common Chinese, Malay and Indian
names used in Singapore; addresses, phone numbers, insurance numbers and IDs are random.

Source C: "Straits Regional Medical Centre" (fictional), continent Asia, time zone Asia/Singapore
(UTC+8, no daylight saving time). One nested XML file: an admission's children are nested inside
the <admission> element, and radiology exams are nested inside their order.

This script only GENERATES raw data. It is not part of the loading / cleaning / import pipeline.

    python docs/ai_prompts/source_c_generator.py      (run from soen363-phase2/)

Writes data/raw/C_xml/hospital_records.xml and docs/ai_prompts/source_c_generation_log.md.
Seeded: re-running it reproduces the file exactly (it does not depend on today's date).
"""

import csv
import datetime as dt
import random
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

SEED = 2026
rng = random.Random(SEED)

PHASE2 = Path(__file__).resolve().parents[2]
OUT = PHASE2 / "data" / "raw" / "C_xml"
XML_FILE = OUT / "hospital_records.xml"
LOG = PHASE2 / "docs" / "ai_prompts" / "source_c_generation_log.md"
ICD_FILE = PHASE2.parent / "soen363-phase1" / "data" / "icd9_dictionary.csv"

HOSPITAL = "Straits Regional Medical Centre"
OFFSET = dt.timezone(dt.timedelta(hours=8))           # Asia/Singapore, no DST
START = dt.datetime(2022, 1, 1, 0, 0)
CUTOFF = dt.datetime(2025, 10, 31, 18, 0)             # extract time, local Asia/Singapore
N_PATIENTS = 480

# =============================================================================
# Reference data
# =============================================================================
with open(ICD_FILE, encoding="utf-8") as f:
    ICD_CODES = [r["icd9_code"] for r in csv.DictReader(f)]     # the shared Phase 1 dictionary, as text
FAKE_ICD = ["999.99", "123.45", "000.0", "V99.9", "888.8"]
SURGICAL = {"Appendicectomy": ["540.9"], "Laparoscopic cholecystectomy": ["574.00", "574.20"],
            "Hip hemiarthroplasty": ["820.8"], "Coronary artery bypass graft": ["414.01", "410.9"],
            "Coronary angiography": ["410.9", "414.01", "786.50"], "Inguinal hernia repair": ["550.90"]}
SURGICAL = {k: [c for c in v if c in ICD_CODES] or [rng.choice(ICD_CODES)] for k, v in SURGICAL.items()}
NEWBORN_CODES = [c for c in ["276.51", "285.9", "599.0", "486", "780.39"] if c in ICD_CODES]

CHINESE_FAMILY = ["Tan", "Lim", "Lee", "Ng", "Ong", "Wong", "Goh", "Chua", "Chan", "Koh", "Teo", "Ang", "Yeo",
                  "Tay", "Ho", "Low", "Toh", "Sim", "Chong", "Chia"]
CHINESE_GIVEN = ["Wei Ming", "Xiu Ling", "Jia Hui", "Kai Wen", "Mei Ling", "Jun Jie", "Hui Min", "Zhi Hao",
                 "Li Ting", "Yong Sheng", "Shu Fen", "Boon Kiat", "Siew Lan", "Kok Wai", "Pei Shan", "Chee Keong"]
MALAY_GIVEN_F = ["Nur Aisyah", "Siti Nurhaliza", "Farah", "Nurul Huda", "Aminah", "Zarina", "Hidayah", "Rosnah"]
MALAY_GIVEN_M = ["Muhammad Faiz", "Ahmad Rizal", "Hafiz", "Iskandar", "Azman", "Khairul", "Rahim", "Firdaus"]
MALAY_FATHER = ["Ahmad", "Ismail", "Hassan", "Osman", "Yusof", "Abdullah", "Salleh", "Rahman", "Ibrahim", "Kassim"]
INDIAN_GIVEN_F = ["Priya", "Kavitha", "Lakshmi", "Deepa", "Meena", "Anitha", "Revathi", "Shalini"]
INDIAN_GIVEN_M = ["Arun", "Rajesh", "Suresh", "Vijay", "Kumar", "Ganesh", "Ravi", "Prakash"]
INDIAN_FATHER = ["Rajan", "Subramaniam", "Krishnan", "Pillai", "Nair", "Menon", "Raman", "Govindasamy"]
ROADS = ["Ang Mo Kio Ave 3", "Bedok North St 2", "Jurong West St 41", "Tampines St 81", "Toa Payoh Lor 4",
         "Clementi Ave 2", "Hougang Ave 8", "Woodlands Dr 14", "Yishun Ring Rd", "Bukit Batok St 21",
         "Pasir Ris Dr 6", "Sengkang East Way", "Punggol Field", "Choa Chu Kang Ave 4", "Serangoon North Ave 1"]
INSURERS = ["Lionshield Assurance", "Merlion Health", "Harbour Life", "Eastern Shield", "Straits Mutual"]

ROLE_PLAN = [("physician", 24), ("nurse", 20), ("surgeon", 8), ("radiologist", 6), ("radiology technician", 12)]
DEPTS = {"physician": ["Emergency Medicine", "General Medicine", "Cardiology", "Respiratory Medicine", "Intensive Care",
                       "Paediatrics"], "nurse": ["Emergency", "Medical Ward", "ICU", "Cardiology"],
         "surgeon": ["General Surgery", "Orthopaedics", "Cardiothoracic Surgery"], "radiologist": ["Radiology"],
         "radiology technician": ["Radiology"]}

SYMPTOMS = ["chest pain", "breathlessness", "fever", "abdominal pain", "giddiness", "headache", "cough", "vomiting",
            "fall", "weakness", "confusion", "palpitations"]
REASONS = ["Chest pain", "Breathlessness", "Fever", "Abdominal pain", "Fall at home", "Syncope", "Confusion",
           "Cough and fever", "Palpitations", "Elective surgery", "Further investigation", "Generalised weakness"]
ALLERGIES = ["Penicillin", "Latex", "Sulfonamides", "Shellfish", "Iodinated contrast", "NSAIDs"]
MEDS = ["Aspirin 100 mg", "Atenolol 50 mg", "Simvastatin 20 mg", "Metformin 500 mg", "Amlodipine 5 mg",
        "Frusemide 40 mg", "Thyroxine 50 mcg", "Augmentin 625 mg", "Paracetamol 1 g"]
NONE_ALLERGY = ["none", "None", "NKA", "NKDA", "no known allergies", "No Known Drug Allergy"]
NONE_MEDS = ["none", "None", "NKA", "Nil"]
EXAMS = {"Chest X-ray": "Chest X-Ray", "CT scan": "CT", "MRI": "MRI", "Ultrasound": "Ultrasound", "ECG": "ECG",
         "Blood panel": "Full Blood Count"}
IMAGING = {"Chest X-ray": "Chest", "CT scan": "Abdomen", "MRI": "Brain", "Ultrasound": "Abdomen"}
INDICATIONS = ["Rule out infection", "Rule out fracture", "Rule out ischaemia", "Rule out obstruction",
               "Rule out bleeding", "Follow-up of known lesion", "Pre-operative assessment"]
FINDINGS = ["No acute abnormality.", "Right lower zone consolidation.", "Small left pleural effusion.",
            "Findings in keeping with the clinical suspicion.", "Mild degenerative changes.", "No fracture seen."]
OUTCOMES = ["Uneventful", "Uneventful", "Uneventful", "Uneventful", "Uneventful", "Complicated", "Unsuccessful"]
DESTINATIONS = ["Home", "Home with caregiver", "Community hospital", "Nursing home", "Transferred to another hospital"]
CONDITIONS = ["Stable", "Improved", "Fair"]
FOLLOWUP = ["Review at specialist outpatient clinic in 2 weeks.", "Return to A&E if symptoms worsen.",
            "Rest and adequate fluid intake.", "Polyclinic follow-up in 1 month.", "Physiotherapy twice a week."]
TRANSFER_REASONS = ["condition deteriorated", "condition improved", "closer monitoring needed", "post-operative care"]
SOURCES_ADM = ["Walk-in", "Ambulance (995)", "GP referral", "Polyclinic referral", "Transfer"]

# Standard value -> (primary Source C label, alternative Source C labels)
LABELS = {
    "admission_type": {"emergency": ("A&E", ["Emergency", "ER"]), "urgent": ("Urgent", ["Priority", "URG"]),
                       "elective": ("Elective", ["Planned", "Scheduled"]),
                       "outpatient": ("Day Case", ["Specialist Outpatient", "SOC"]),
                       "newborn": ("Newborn", ["Birth", "Neonate"])},
    "admission_status": {"discharged": ("Discharged", ["Home", "DISCH"]), "deceased": ("Deceased", ["Expired", "Died"]),
                         "active": ("Inpatient", ["Admitted", "Current"])},
    "life_status": {"alive": ("Alive", ["Living", "A"]), "deceased": ("Deceased", ["Dead", "D"])},
    "sex": {"female": ("F", ["Female", "f"]), "male": ("M", ["Male", "m"]), "unknown": ("U", ["Unknown"])},
    "triage": {"high": ("P1", ["PAC 1", "Resus"]), "medium": ("P2", ["PAC 2", "Major"]),
               "low": ("P3", ["PAC 3", "Minor"])},
    "unit": {"Emergency Department": ("A&E Department", ["Emergency Department", "ED"]),
             "ICU": ("ICU", ["Intensive Care Unit", "General ICU"]), "CCU": ("CCU", ["Coronary Care Unit", "Cardiac ICU"]),
             "MICU": ("MICU", ["Medical ICU"]), "SICU": ("SICU", ["Surgical ICU"]),
             "General Ward": ("General Ward", ["Ward", "GW"])},
    "order_status": {"pending": ("Ordered", ["Pending", "New"]), "in_progress": ("In Progress", ["Processing", "IP"]),
                     "completed": ("Resulted", ["Completed", "Done"]), "cancelled": ("Cancelled", ["Void", "Cancel"])},
    "priority": {"routine": ("Routine", ["R", "Normal"]), "urgent": ("Urgent", ["U", "ASAP"]),
                 "stat": ("STAT", ["Stat", "Immediate"])},
    "exam_status": {"scheduled": ("Booked", ["Scheduled"]), "completed": ("Reported", ["Completed", "Done"]),
                    "cancelled": ("Cancelled", ["Void"])},
    "dx_type": {"primary": ("Principal", ["Primary", "P"]), "secondary": ("Secondary", ["Additional", "S"])},
    "note_type": {"discharge_summary": ("Discharge Summary", ["DS", "Discharge Note"]),
                  "operative_note": ("Operation Note", ["Op Note"]),
                  "progress_note": ("Progress Note", ["Ward Round Note"])},
    "role": {"physician": ("Medical Officer", ["Consultant", "Doctor"]), "nurse": ("Staff Nurse", ["RN", "Nurse"]),
             "surgeon": ("Surgeon", ["Consultant Surgeon"]), "radiologist": ("Radiologist", ["Consultant Radiologist"]),
             "radiology technician": ("Radiographer", ["Radiology Technologist"])},
}
UNMAPPABLE = {"admission_type": ["Observation", "Transfer-In"], "triage": ["P4", "PAC 4"], "unit": ["HDU", "Isolation Ward"],
              "order_status": ["On Hold"], "priority": ["Later"], "exam_status": ["Awaiting Report"]}
LABEL_VARIANT_P = 0.06

# =============================================================================
# 1) Canonical (correct) hospital data
# =============================================================================
def rand_dt(a, b):
    return (a + dt.timedelta(seconds=rng.randint(0, max(0, int((b - a).total_seconds()))))).replace(second=0)


def person_name(sex):
    eth = rng.choices(["chinese", "malay", "indian"], [74, 14, 12])[0]
    female = sex == "female" or (sex == "unknown" and rng.random() < .5)
    if eth == "chinese":
        return rng.choice(CHINESE_FAMILY), rng.choice(CHINESE_GIVEN)
    if eth == "malay":
        given = rng.choice(MALAY_GIVEN_F if female else MALAY_GIVEN_M)
        return rng.choice(MALAY_FATHER), f"{given} {'binte' if female else 'bin'}"
    given = rng.choice(INDIAN_GIVEN_F if female else INDIAN_GIVEN_M)
    return rng.choice(INDIAN_FATHER), f"{given} {'d/o' if female else 's/o'}"


def phone_digits():
    return rng.choice(["8", "9", "6"]) + "".join(str(rng.randint(0, 9)) for _ in range(7))


def full(family, given):
    """How a person is written in this hospital: Chinese names family first, others given first."""
    return f"{family} {given}" if not given.endswith(("bin", "binte", "d/o", "s/o")) else f"{given} {family}"


pros, by_role = [], defaultdict(list)
for role, n in ROLE_PLAN:
    for _ in range(n):
        family, given = person_name(rng.choice(["female", "male"]))
        p_id = len(pros) + 1
        pros.append({"id": p_id, "name": full(family, given), "role": role, "dept": rng.choice(DEPTS[role])})
        by_role[role].append(p_id)

patients, adms, triage, stays, dxs, orders, rads, procs, notes, dischs = ([] for _ in range(10))
ids = Counter()


def nid(kind):
    ids[kind] += 1
    return ids[kind]


def staff(role):
    return rng.choice(by_role[role])


for _ in range(N_PATIENTS):
    p_id = nid("patient")
    sex = rng.choices(["female", "male", "unknown"], [48, 48, 4])[0]
    family, given = person_name(sex)
    pat = {"id": p_id, "family": family, "given": given, "sex": sex, "dob": None,
           "address": f"Blk {rng.randint(1, 990)} {rng.choice(ROADS)}, #{rng.randint(2, 25):02d}-{rng.randint(1, 450)}, "
                      f"Singapore {rng.randint(100000, 829999)}",
           "phone": phone_digits(), "kin": full(*person_name(rng.choice(["female", "male"]))), "kin_phone": phone_digits(),
           "life": "alive"}
    patients.append(pat)
    n_adm = rng.choices([0, 1, 2, 3, 4, 5], [12, 48, 24, 10, 4, 2])[0]
    cursor = rand_dt(START, CUTOFF - dt.timedelta(days=300))
    first_adm = None
    for k in range(n_adm):
        if cursor > CUTOFF - dt.timedelta(days=1) or pat["life"] == "deceased":
            break
        a_id = nid("admission")
        atype = rng.choices(["emergency", "urgent", "elective", "outpatient", "newborn"], [30, 22, 22, 22, 4])[0]
        if atype == "newborn" and k > 0:
            atype = "elective"
        admit = cursor
        first_adm = first_adm or admit
        los = dt.timedelta(hours=rng.randint(1, 10)) if atype == "outpatient" else dt.timedelta(hours=rng.randint(20, 24 * 18))
        status = rng.choices(["discharged", "deceased"], [96, 4])[0] if atype != "newborn" else "discharged"
        disch = admit + los
        if disch > CUTOFF or (admit > CUTOFF - dt.timedelta(days=12) and rng.random() < .5):
            status, disch = "active", None
        if status == "deceased":
            pat["life"] = "deceased"
        if atype == "newborn":
            pat["dob"] = admit.date()
        adm = {"id": a_id, "patient": p_id, "doctor": staff("physician"), "admit": admit, "type": atype,
               "reason": "Birth" if atype == "newborn" else ("Elective surgery" if atype == "elective" and rng.random() < .3
                                                              else rng.choice(REASONS)),
               "source": rng.choice(SOURCES_ADM),
               "insurance": f"MediShield Life + {rng.choice(INSURERS)} IP #{rng.randint(10000000, 99999999)}",
               "discharge": disch, "status": status}
        adms.append(adm)
        end = disch or CUTOFF

        prio_w = {"emergency": [55, 35, 10], "urgent": [20, 55, 25]}.get(atype, [5, 30, 65])
        for j in range(2 if rng.random() < .06 else 1):
            triage.append({"id": nid("triage"), "admission": a_id, "nurse": staff("nurse"),
                           "time": admit + dt.timedelta(minutes=rng.randint(5, 25) + 45 * j),
                           "bp": (rng.randint(100, 170), rng.randint(60, 100)), "hr": rng.randint(55, 125),
                           "rr": rng.randint(12, 28), "temp": round(rng.uniform(36.0, 39.8), 1), "spo2": rng.randint(88, 100),
                           "pain": rng.randint(0, 10), "symptoms": ", ".join(rng.sample(SYMPTOMS, rng.randint(1, 3))),
                           "allergies": rng.choice(ALLERGIES) if rng.random() < .45 else rng.choice(NONE_ALLERGY),
                           "meds": rng.choice(MEDS) if rng.random() < .65 else rng.choice(NONE_MEDS),
                           "priority": rng.choices(["high", "medium", "low"], prio_w)[0]})

        if atype == "emergency":
            path = ["Emergency Department"]
            if rng.random() < .55:
                path.append(rng.choice(["ICU", "CCU", "MICU", "SICU"]))
                if rng.random() < .25:
                    path.append(rng.choice(["ICU", "CCU", "MICU", "SICU"]))
            path.append("General Ward")
        elif atype in ("urgent", "elective"):
            path = ["General Ward"] + (["SICU" if atype == "elective" else rng.choice(["ICU", "CCU", "MICU"]),
                                        "General Ward"] if rng.random() < .3 else [])
        elif atype == "newborn":
            path = ["General Ward"]
        else:
            path = ["Emergency Department"] if rng.random() < .2 else []
        t = admit + dt.timedelta(minutes=30)
        span = (end - t).total_seconds()
        adm_stays = []
        for j, unit in enumerate(path):
            last_one = j == len(path) - 1
            dur = dt.timedelta(seconds=span / (len(path) - j) * rng.uniform(.6, 1.0))
            exit_t = None if (last_one and disch is None) else (disch if last_one else (t + dur).replace(second=0, microsecond=0))
            s = {"id": nid("stay"), "admission": a_id, "doctor": staff("physician"), "unit": unit,
                 "ward": f"Ward {rng.choice(['4', '5', '6', '7', '8', '9', '10'])}{rng.choice('ABC')}",
                 "bed": f"{rng.randint(1, 40):02d}", "entry": t, "exit": exit_t,
                 "reason": None if j == 0 else rng.choice(TRANSFER_REASONS)}
            stays.append(s)
            adm_stays.append(s)
            span -= dur.total_seconds()
            t = exit_t or t

        if atype in ("emergency", "urgent", "elective") and disch is not None and rng.random() < .16:
            proc_name = rng.choice(list(SURGICAL))
            crit = [s for s in adm_stays if s["unit"] in ("ICU", "CCU", "MICU", "SICU")]
            hi = crit[0]["entry"] - dt.timedelta(minutes=30) if crit else admit + (disch - admit) / 2
            lo = admit + dt.timedelta(hours=1)
            ptime = rand_dt(lo, hi if hi > lo else lo + dt.timedelta(minutes=30))
            procs.append({"id": nid("procedure"), "admission": a_id, "surgeon": staff("surgeon"), "type": proc_name,
                          "time": ptime, "outcome": rng.choice(OUTCOMES)})
            notes.append({"id": nid("note"), "admission": a_id, "author": procs[-1]["surgeon"], "type": "operative_note",
                          "time": ptime + dt.timedelta(hours=2),
                          "text": f"Operation note. {proc_name} performed. Patient tolerated the procedure well."})

        if status != "active" or rng.random() < .5:
            if atype == "newborn":
                primary = rng.choice(NEWBORN_CODES)
            elif procs and procs[-1]["admission"] == a_id:
                primary = rng.choice(SURGICAL[procs[-1]["type"]])
            else:
                primary = rng.choice(ICD_CODES)
            codes = [primary] + rng.sample([c for c in ICD_CODES if c != primary], rng.choice([0, 1, 1, 2, 3]))
            for n_, code in enumerate(codes):
                tdx = min(admit + dt.timedelta(hours=rng.randint(1, 20)), end - dt.timedelta(minutes=5))
                dxs.append({"id": nid("diagnosis"), "patient": p_id, "admission": a_id, "code": code,
                            "doctor": staff("physician"), "time": max(tdx, admit),
                            "type": "primary" if n_ == 0 else "secondary"})

        for _o in range(rng.choices([0, 1, 2], [45, 40, 15])[0]):
            exam = rng.choice(list(EXAMS))
            ot = rand_dt(admit, min(end, admit + dt.timedelta(days=3)))
            o_status = rng.choices(["completed", "pending", "in_progress", "cancelled"], [75, 10, 8, 7])[0]
            if disch is None and o_status == "completed" and rng.random() < .3:
                o_status = "in_progress"
            o = {"id": nid("order"), "admission": a_id, "doctor": staff("physician"), "time": ot, "exam": exam,
                 "reason": rng.choice(INDICATIONS), "status": o_status,
                 "priority": rng.choices(["routine", "urgent", "stat"], [55, 30, 15])[0]}
            orders.append(o)
            if exam in IMAGING and o_status in ("completed", "in_progress", "cancelled"):
                et = max(ot, min(ot + dt.timedelta(hours=rng.randint(1, 10)), end - dt.timedelta(minutes=10)))
                st = {"completed": "completed", "in_progress": "scheduled", "cancelled": "cancelled"}[o_status]
                rads.append({"id": nid("radiology"), "admission": a_id, "order": o["id"], "referrer": o["doctor"],
                             "tech": staff("radiology technician"), "type": exam, "time": et, "area": IMAGING[exam],
                             "status": st, "link": f"https://pacs.srmc.example/study/{a_id}-{nid('img')}",
                             "findings": rng.choice(FINDINGS) if st == "completed" else None})
        if rng.random() < .05:
            exam = rng.choice(list(IMAGING))
            rads.append({"id": nid("radiology"), "admission": a_id, "order": None, "referrer": adm["doctor"],
                         "tech": staff("radiology technician"), "type": exam,
                         "time": rand_dt(admit, end - dt.timedelta(minutes=10)) if end > admit + dt.timedelta(minutes=20) else admit,
                         "area": IMAGING[exam], "status": "completed",
                         "link": f"https://pacs.srmc.example/study/{a_id}-{nid('img')}", "findings": rng.choice(FINDINGS)})

        for _n in range(rng.choices([0, 1, 2], [40, 40, 20])[0]):
            notes.append({"id": nid("note"), "admission": a_id, "author": staff("physician"), "type": "progress_note",
                          "time": rand_dt(admit, end),
                          "text": rng.choice(["Seen on ward round. Plan unchanged.", "Vitals stable overnight. Continue current management.",
                                              "Family updated at bedside.", "Pain better controlled; ambulating with assistance."])})
        if disch is not None:
            died = status == "deceased"
            recov = rng.choice(["Recovery", "recovery", "RECOVERY"]) if rng.random() < .45 else None
            text = (f"Discharge summary. Admitted for {adm['reason'].lower()}. "
                    + ("Patient passed away during this admission." if died else
                       (f"{recov} is satisfactory." if recov else "Condition stable on discharge.")))
            notes.append({"id": nid("note"), "admission": a_id, "author": adm["doctor"], "type": "discharge_summary",
                          "time": disch, "text": text})
            dischs.append({"id": nid("discharge"), "admission": a_id, "doctor": staff("physician"), "time": disch,
                           "destination": "Mortuary" if died else rng.choice(DESTINATIONS),
                           "condition": "Deceased" if died else rng.choice(CONDITIONS),
                           "meds": None if died else rng.choice(MEDS + ["none"]),
                           "advice": None if died else rng.choice(FOLLOWUP),
                           "appointment": None if died else (disch + dt.timedelta(days=rng.randint(10, 45),
                                                                                  hours=rng.randint(0, 6))).replace(minute=0)})
        cursor = ((disch or admit) + dt.timedelta(days=rng.randint(30, 300))).replace(second=0, microsecond=0)

    if pat["dob"] is None:
        ref = (first_adm or CUTOFF).date()
        pat["dob"] = ref - dt.timedelta(days=rng.randint(365, 95 * 365))

# =============================================================================
# 2) Rendering to Source C's raw formats
# =============================================================================
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PLACEHOLDERS = ["", "N/A", "null", "-", "?", None]          # None = element left out
PID = lambda i: f"P{i:06d}"
AID = lambda i: f"E{i:06d}"
SID = lambda i: f"S{i:04d}"


def fmt_dt(d, tags):
    """Usual format ISO 8601 with the +08:00 offset."""
    r = rng.random()
    if r < 0.92:
        return d.strftime("%Y-%m-%dT%H:%M:00+08:00")
    if r < 0.945:
        tags.add("fmt_date_no_offset")                # local time, no offset written
        return d.strftime("%Y-%m-%d %H:%M")
    if r < 0.965:
        tags.add("fmt_date_utc")                      # converted to UTC by an interface engine
        return (d.replace(tzinfo=OFFSET).astimezone(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:00Z")
    if r < 0.98:
        tags.add("fmt_date_text")                     # 08 May 2024 02:59 PM
        h = d.hour % 12 or 12
        return f"{d.day:02d} {MON[d.month - 1]} {d.year} {h:02d}:{d.minute:02d} {'AM' if d.hour < 12 else 'PM'}"
    if r < 0.995 or d.day <= 12:
        tags.add("fmt_date_dayfirst")                 # 08/05/2024 14:59 (slash dates are always day-first)
        return d.strftime("%d/%m/%Y %H:%M")
    tags.add("fmt_date_dash")                         # dash date, order mixed, but day > 12 so readable
    return d.strftime("%d-%m-%Y %H:%M") if rng.random() < .5 else d.strftime("%m-%d-%Y %H:%M")


def fmt_date(d, tags):
    r = rng.random()
    if r < 0.88:
        return d.strftime("%Y-%m-%d")
    if r < 0.94:
        tags.add("fmt_date_dayfirst")
        return d.strftime("%d/%m/%Y")
    if r < 0.98 or d.day <= 12:
        tags.add("fmt_date_text")
        return f"{d.day} {MON[d.month - 1]} {d.year}"
    tags.add("fmt_date_dash")
    return d.strftime("%d-%m-%Y") if rng.random() < .5 else d.strftime("%m-%d-%Y")


def fmt_label(key, v, tags):
    primary, variants = LABELS[key][v]
    if rng.random() < LABEL_VARIANT_P:
        tags.add("fmt_label")
        return rng.choice(variants)
    return primary


def fmt_phone(d, tags):
    pretty = f"+65 {d[:4]} {d[4:]}"
    if rng.random() < .92:
        return pretty
    tags.add("fmt_phone")
    return rng.choice([d, f"{d[:4]}-{d[4:]}", f"(65) {d}", f"65{d}"])


def fmt_icd(code, tags):
    if code == "038.9" and rng.random() < .3:
        tags.add("fmt_icd_leading_zero_lost")
        return "38.9"
    r = rng.random()
    if r < .85:
        return code
    if r < .93 and "." in code:
        tags.add("fmt_icd_no_decimal")
        return code.replace(".", "")
    tags.add("case_ws")
    return rng.choice([" " + code, code + " ", "  " + code + " "])


def fmt_vital(col, v, tags, raw):
    """Returns the text; for temperature also sets raw['temperature@unit']."""
    if col == "bloodPressure":
        s, d_ = v
        if rng.random() < .95:
            return f"{s}/{d_}"
        tags.add("fmt_vital_units")
        return rng.choice([f"{s} / {d_}", f"{s}-{d_}", f"{s}/{d_} mmHg"])
    if col == "temperature":
        if rng.random() < .30:
            tags.add("fmt_temp_fahrenheit")
            f_ = round(v * 9 / 5 + 32, 1)
            if rng.random() < .85:
                raw["temperature@unit"] = "F"
                return f"{f_}"
            raw["temperature@unit"] = None                # unit written in the text instead of the attribute
            return rng.choice([f"{f_}F", f"{f_} °F"])
        if rng.random() < .08:
            tags.add("fmt_vital_units")
            raw["temperature@unit"] = None
            return rng.choice([f"{v}C", f"{v} °C"])
        raw["temperature@unit"] = "C"
        return f"{v}"
    if col == "oxygenSaturation":                      # this hospital stores SpO2 as a fraction (0.97)
        if rng.random() < .08:
            tags.add("fmt_vital_units")
            return rng.choice([f"{v}%", f"{v} %"])
        return f"{v / 100:.2f}"
    suffix = {"heartRate": [" bpm", "/min"], "respRate": ["/min", " bpm"], "painScore": ["/10"]}[col]
    if rng.random() < .05:
        tags.add("fmt_vital_units")
        return f"{v}{rng.choice(suffix)}"
    return str(v)


def txt(v):
    return "" if v is None else str(v)


# Entity specs: XML element, id attribute, child fields in order, required / optional fields, date field, foreign keys
SPECS = {
    "HealthcareProfessional": dict(el="member", idattr="staffId", fields=["name", "designation", "department"],
                                   req=["name", "designation"], opt=[], date=None, fk={}),
    "Patient": dict(el="patient", idattr="patientId",
                    fields=["name/family", "name/given", "birthDate", "sex", "address", "phone", "nextOfKin", "vitalStatus"],
                    req=["name/family", "birthDate"], opt=["sex", "address", "phone", "nextOfKin"], date="birthDate", fk={}),
    "Admission": dict(el="admission", idattr="admissionId",
                      fields=["admittedBy", "admittedAt", "admissionClass", "chiefComplaint", "referralSource", "payer",
                              "dischargedAt", "status"],
                      req=["admittedAt", "admissionClass", "chiefComplaint"], opt=["referralSource", "payer"],
                      date="admittedAt", fk={"@patientRef": "patient", "admittedBy": "pro"}),
    "TriageAssessment": dict(el="triage", idattr="id",
                             fields=["nurse", "assessedAt", "bloodPressure", "heartRate", "respRate", "temperature",
                                     "oxygenSaturation", "painScore", "symptoms", "allergies", "homeMedication", "pacLevel"],
                             req=["nurse", "pacLevel"],
                             opt=["bloodPressure", "heartRate", "respRate", "temperature", "oxygenSaturation", "painScore",
                                  "symptoms", "allergies", "homeMedication"],
                             date="assessedAt", fk={"@admission": "admission", "nurse": "pro"}),
    "Diagnosis": dict(el="diagnosis", idattr="id", fields=["icd9", "type", "diagnosedAt", "doctor"],
                      req=["icd9", "type", "diagnosedAt", "doctor"], opt=[], date="diagnosedAt",
                      fk={"@admission": "admission", "doctor": "pro"}),
    "ClinicalNote": dict(el="note", idattr="id", fields=["@type", "writtenAt", "author", "text"],
                         req=["@type", "writtenAt", "author", "text"], opt=[], date="writtenAt",
                         fk={"@admission": "admission", "author": "pro"}),
    "DiagnosticOrder": dict(el="labOrder", idattr="id",
                            fields=["test", "orderedAt", "indication", "status", "priority", "orderedBy"],
                            req=["orderedAt", "indication", "status", "priority", "orderedBy"], opt=[], date="orderedAt",
                            fk={"@admission": "admission", "orderedBy": "pro"}),
    "RadiologyExamination": dict(el="imaging", idattr="id",
                                 fields=["modality", "performedAt", "bodyPart", "status", "pacsUrl", "report", "referrer",
                                         "radiographer"],
                                 req=["modality", "performedAt", "status", "referrer", "radiographer"],
                                 opt=["bodyPart", "pacsUrl", "report"], date="performedAt",
                                 fk={"@admission": "admission", "referrer": "pro"}),
    "SurgicalProcedure": dict(el="operation", idattr="id", fields=["procedure", "performedAt", "outcome", "surgeon"],
                              req=["procedure", "performedAt", "surgeon"], opt=["outcome"], date="performedAt",
                              fk={"@admission": "admission", "surgeon": "pro"}),
    "UnitStay": dict(el="wardMovement", idattr="id",
                     fields=["unit", "ward", "bed", "transferIn", "transferOut", "transferReason", "doctor"],
                     req=["unit", "transferIn", "doctor"], opt=["ward", "bed", "transferReason"], date="transferIn",
                     fk={"@admission": "admission", "doctor": "pro"}),
    "DischargeRecord": dict(el="discharge", idattr="id",
                            fields=["dischargedAt", "destination", "condition", "medications", "instructions", "followUp",
                                    "authorisedBy"],
                            req=["dischargedAt", "authorisedBy"],
                            opt=["destination", "condition", "medications", "instructions", "followUp"],
                            date="dischargedAt", fk={"@admission": "admission", "authorisedBy": "pro"}),
}
CHILDREN = ["TriageAssessment", "UnitStay", "Diagnosis", "DiagnosticOrder", "RadiologyExamination", "SurgicalProcedure",
            "ClinicalNote", "DischargeRecord"]


def row(entity, rid, canon, raw, tags, adm=None, order=None, patient=None):
    return {"entity": entity, "id": rid, "canon": canon, "raw": raw, "tags": set(tags), "touched": set(),
            "adm": adm, "order": order, "patient": patient}


R = {e: [] for e in SPECS}
for p in pros:
    tg = set()
    R["HealthcareProfessional"].append(row("HealthcareProfessional", SID(p["id"]), {}, {
        "name": p["name"], "designation": fmt_label("role", p["role"], tg), "department": p["dept"]}, tg))
for p in patients:
    tg = set()
    R["Patient"].append(row("Patient", PID(p["id"]), {"birthDate": p["dob"]}, {
        "name/family": p["family"], "name/given": p["given"], "birthDate": fmt_date(p["dob"], tg),
        "sex": fmt_label("sex", p["sex"], tg), "address": p["address"], "phone": fmt_phone(p["phone"], tg),
        "nextOfKin": f"{p['kin']} ({fmt_phone(p['kin_phone'], tg)})", "vitalStatus": fmt_label("life_status", p["life"], tg)}, tg))
for a in adms:
    tg = set()
    R["Admission"].append(row("Admission", AID(a["id"]), {"admittedAt": a["admit"]}, {
        "@patientRef": PID(a["patient"]), "admittedBy": SID(a["doctor"]), "admittedAt": fmt_dt(a["admit"], tg),
        "admissionClass": fmt_label("admission_type", a["type"], tg), "chiefComplaint": a["reason"],
        "referralSource": a["source"], "payer": a["insurance"],
        "dischargedAt": fmt_dt(a["discharge"], tg) if a["discharge"] else None,
        "status": fmt_label("admission_status", a["status"], tg)}, tg, adm=AID(a["id"]), patient=PID(a["patient"])))
for x in triage:
    tg, raw = set(), {}
    raw.update({"nurse": SID(x["nurse"]), "assessedAt": fmt_dt(x["time"], tg),
                "bloodPressure": fmt_vital("bloodPressure", x["bp"], tg, raw), "heartRate": fmt_vital("heartRate", x["hr"], tg, raw),
                "respRate": fmt_vital("respRate", x["rr"], tg, raw), "temperature": fmt_vital("temperature", x["temp"], tg, raw),
                "oxygenSaturation": fmt_vital("oxygenSaturation", x["spo2"], tg, raw),
                "painScore": fmt_vital("painScore", x["pain"], tg, raw), "symptoms": x["symptoms"],
                "allergies": x["allergies"], "homeMedication": x["meds"], "pacLevel": fmt_label("triage", x["priority"], tg)})
    R["TriageAssessment"].append(row("TriageAssessment", str(x["id"]), {"assessedAt": x["time"]}, raw, tg, adm=AID(x["admission"])))
for x in dxs:
    tg = set()
    R["Diagnosis"].append(row("Diagnosis", str(x["id"]), {"diagnosedAt": x["time"]}, {
        "@patientRef": PID(x["patient"]), "icd9": fmt_icd(x["code"], tg), "type": fmt_label("dx_type", x["type"], tg),
        "diagnosedAt": fmt_dt(x["time"], tg), "doctor": SID(x["doctor"])}, tg, adm=AID(x["admission"]), patient=PID(x["patient"])))
for x in notes:
    tg = set()
    R["ClinicalNote"].append(row("ClinicalNote", str(x["id"]), {"writtenAt": x["time"]}, {
        "@type": fmt_label("note_type", x["type"], tg), "writtenAt": fmt_dt(x["time"], tg), "author": SID(x["author"]),
        "text": x["text"]}, tg, adm=AID(x["admission"])))
for x in orders:
    tg = set()
    R["DiagnosticOrder"].append(row("DiagnosticOrder", str(x["id"]), {"orderedAt": x["time"]}, {
        "test": EXAMS[x["exam"]], "orderedAt": fmt_dt(x["time"], tg), "indication": x["reason"],
        "status": fmt_label("order_status", x["status"], tg), "priority": fmt_label("priority", x["priority"], tg),
        "orderedBy": SID(x["doctor"])}, tg, adm=AID(x["admission"])))
for x in rads:
    tg = set()
    R["RadiologyExamination"].append(row("RadiologyExamination", str(x["id"]), {"performedAt": x["time"]}, {
        "modality": EXAMS[x["type"]], "performedAt": fmt_dt(x["time"], tg), "bodyPart": x["area"],
        "status": fmt_label("exam_status", x["status"], tg), "pacsUrl": x["link"], "report": x["findings"],
        "referrer": SID(x["referrer"]), "radiographer": SID(x["tech"])}, tg, adm=AID(x["admission"]),
        order=str(x["order"]) if x["order"] else None))
for x in procs:
    tg = set()
    R["SurgicalProcedure"].append(row("SurgicalProcedure", str(x["id"]), {"performedAt": x["time"]}, {
        "procedure": x["type"], "performedAt": fmt_dt(x["time"], tg), "outcome": x["outcome"],
        "surgeon": SID(x["surgeon"])}, tg, adm=AID(x["admission"])))
for x in stays:
    tg = set()
    R["UnitStay"].append(row("UnitStay", str(x["id"]), {"transferIn": x["entry"]}, {
        "unit": fmt_label("unit", x["unit"], tg), "ward": x["ward"], "bed": x["bed"], "transferIn": fmt_dt(x["entry"], tg),
        "transferOut": fmt_dt(x["exit"], tg) if x["exit"] else None, "transferReason": x["reason"],
        "doctor": SID(x["doctor"])}, tg, adm=AID(x["admission"])))
for x in dischs:
    tg = set()
    R["DischargeRecord"].append(row("DischargeRecord", str(x["id"]), {"dischargedAt": x["time"]}, {
        "dischargedAt": fmt_dt(x["time"], tg), "destination": x["destination"], "condition": x["condition"],
        "medications": x["meds"], "instructions": x["advice"],
        "followUp": fmt_dt(x["appointment"], tg) if x["appointment"] else None,
        "authorisedBy": SID(x["doctor"])}, tg, adm=AID(x["admission"])))

# =============================================================================
# 3) Injected data-quality problems
# =============================================================================
RATES = {
    "HealthcareProfessional": dict(missing_req=.02, bad_date=0, broken=0, chrono=0, case_ws=.10, unmap=0),
    "Patient": dict(missing_req=.006, bad_date=.005, broken=0, chrono=0, case_ws=.15, unmap=0),
    "Admission": dict(missing_req=.006, bad_date=.004, broken=.004, chrono=.005, case_ws=.17, unmap=.003),
    "TriageAssessment": dict(missing_req=.018, bad_date=0, broken=.018, chrono=0, case_ws=.15, unmap=.003),
    "Diagnosis": dict(missing_req=.018, bad_date=.018, broken=.018, chrono=.018, case_ws=.16, unmap=0),
    "ClinicalNote": dict(missing_req=.018, bad_date=.018, broken=.018, chrono=.018, case_ws=.16, unmap=0),
    "DiagnosticOrder": dict(missing_req=.018, bad_date=.018, broken=.018, chrono=.018, case_ws=.16, unmap=.004),
    "RadiologyExamination": dict(missing_req=.02, bad_date=.02, broken=.02, chrono=.02, case_ws=.16, unmap=.005),
    "SurgicalProcedure": dict(missing_req=.02, bad_date=.02, broken=.02, chrono=.02, case_ws=.15, unmap=0),
    "UnitStay": dict(missing_req=.018, bad_date=.018, broken=.018, chrono=.018, case_ws=.16, unmap=.003),
    "DischargeRecord": dict(missing_req=.018, bad_date=.018, broken=.018, chrono=.02, case_ws=.16, unmap=0),
}
MISSING_OPT_RATE = .21
INVALID_VITAL_RATE = .47
EXACT_DUP = .019
NEAR_DUP = .029
DETAIL = defaultdict(Counter)
adm_by_aid = {AID(a["id"]): a for a in adms}
pat_by_pid = {PID(p["id"]): p for p in patients}
stay_by_id = {str(s["id"]): s for s in stays}
TEXT_COLS = {
    "HealthcareProfessional": ["name", "designation", "department"],
    "Patient": ["name/family", "name/given", "address", "sex", "vitalStatus", "nextOfKin"],
    "Admission": ["admissionClass", "chiefComplaint", "referralSource", "payer", "status"],
    "TriageAssessment": ["symptoms", "allergies", "homeMedication", "pacLevel"],
    "Diagnosis": ["type"], "ClinicalNote": ["@type", "text"],
    "DiagnosticOrder": ["test", "indication", "status", "priority"],
    "RadiologyExamination": ["modality", "bodyPart", "status", "report"],
    "SurgicalProcedure": ["procedure", "outcome"], "UnitStay": ["unit", "ward", "transferReason"],
    "DischargeRecord": ["destination", "condition", "instructions"],
}
LABEL_COL = {"Admission": ("admissionClass", "admission_type"), "TriageAssessment": ("pacLevel", "triage"),
             "UnitStay": ("unit", "unit"), "DiagnosticOrder": ("status", "order_status"),
             "RadiologyExamination": ("status", "exam_status")}


def pick(rows, rate, exclude=()):
    pool = [i for i, r in enumerate(rows) if not (r["touched"] & set(exclude))]
    k = min(len(pool), round(rate * len(rows)))
    return rng.sample(pool, k) if k else []


def invalid_date_string(d, with_time):
    tm = f"T{d.hour:02d}:{d.minute:02d}:00+08:00" if with_time else ""
    return rng.choice([f"{d.year}-02-30{tm}", f"{d.year}-02-31{tm}", f"{d.year}-13-{d.day:02d}{tm}",
                       f"{d.year}-{d.month:02d}-32{tm}", f"{d.year}-{d.month:02d}-{d.day:02d}T25:{d.minute:02d}:00+08:00"
                       if with_time else f"{d.year}-00-{d.day:02d}", "TBC", "unknown date"])


def mess_case(s):
    if not s:
        return s
    return rng.choice([s.upper(), s.lower(), f"  {s}", f"{s}   ", f" {s} ", s.replace(" ", "  ", 1) if " " in s else f"{s} ",
                       s.swapcase()])


def placeholder(numeric=False, date=False):
    return rng.choice(PLACEHOLDERS + (["-1"] if numeric else []) + (["0000-00-00"] if date else []))


for ent, spec in SPECS.items():
    rows, rates = R[ent], RATES[ent]

    # broken references
    for i in pick(rows, rates["broken"]):
        r = rows[i]
        col = rng.choice(list(spec["fk"]))
        kind = spec["fk"][col]
        if kind == "admission":
            r["adm"] = AID(len(adms) + rng.randint(500, 4000))     # placed under <unlinkedRecords>
            r["orphan"] = True
        elif kind == "patient":
            r["raw"]["@patientRef"] = PID(len(patients) + rng.randint(500, 4000))
        else:
            r["raw"][col] = SID(len(pros) + rng.randint(200, 900))
        r["tags"].add("broken_ref")
        r["touched"].add(col)
        DETAIL[ent][f"broken ref: {col.lstrip('@')} -> nonexistent {kind}"] += 1
    if ent == "RadiologyExamination":
        for i in pick(rows, .012, exclude=("@admission",)):
            r = rows[i]
            if r["order"] and not r.get("orphan"):
                r["order"] = str(len(orders) + rng.randint(500, 4000))
                r["bad_order"] = True                                # stand-alone <imaging orderRef="...">
                r["tags"].add("broken_ref")
                r["touched"].add("orderRef")
                DETAIL[ent]["broken ref: orderRef -> nonexistent order"] += 1
    if ent == "Diagnosis":
        for i in pick(rows, .006, exclude=("@admission",)):
            r = rows[i]
            a = adm_by_aid[r["adm"]]
            r["raw"]["@patientRef"] = PID(rng.choice([p for p in range(1, len(patients) + 1) if p != a["patient"]]))
            r["tags"].add("patient_mismatch")
            r["touched"].add("@patientRef")
            DETAIL[ent]["broken ref: patientRef differs from the admission's patient"] += 1

    # chronology
    if rates["chrono"]:
        for i in pick(rows, rates["chrono"], exclude=tuple(spec["fk"])):
            r = rows[i]
            if ent == "Admission":
                a = adm_by_aid[r["id"]]
                if a["discharge"] is None or rng.random() < .25:
                    born = dt.datetime.combine(pat_by_pid[PID(a["patient"])]["dob"], dt.time(9, 0))
                    r["raw"]["admittedAt"] = fmt_dt(born - dt.timedelta(days=rng.randint(30, 400)), r["tags"])
                    DETAIL[ent]["chronology: admission before patient date of birth"] += 1
                else:
                    r["raw"]["dischargedAt"] = fmt_dt(a["admit"] - dt.timedelta(hours=rng.randint(2, 72)), r["tags"])
                    DETAIL[ent]["chronology: discharge before admission"] += 1
            elif ent == "UnitStay":
                s = stay_by_id[r["id"]]
                if s["exit"] is not None and rng.random() < .6:
                    r["raw"]["transferOut"] = fmt_dt(s["entry"] - dt.timedelta(hours=rng.randint(1, 30)), r["tags"])
                    DETAIL[ent]["chronology: unit exit before entry"] += 1
                else:
                    a = adm_by_aid[r["adm"]]
                    r["raw"]["transferIn"] = fmt_dt(a["admit"] - dt.timedelta(days=rng.randint(2, 15)), r["tags"])
                    DETAIL[ent]["chronology: unit entry before admission"] += 1
            elif ent == "DischargeRecord":
                a = adm_by_aid[r["adm"]]
                r["raw"]["dischargedAt"] = fmt_dt(a["admit"] - dt.timedelta(hours=rng.randint(3, 72)), r["tags"])
                DETAIL[ent]["chronology: discharge record before admission"] += 1
            else:
                a = adm_by_aid[r["adm"]]
                col = spec["date"]
                end = a["discharge"] or CUTOFF
                if a["discharge"] is not None and rng.random() < .5:
                    bad, what = end + dt.timedelta(days=rng.randint(2, 20)), "after discharge"
                else:
                    bad, what = a["admit"] - dt.timedelta(days=rng.randint(2, 20)), "before admission"
                r["raw"][col] = fmt_dt(bad, r["tags"])
                DETAIL[ent][f"chronology: {col} {what}"] += 1
            r["tags"].add("chrono")
            r["touched"].add("date")
        if ent == "DischargeRecord":
            active = [a for a in adms if a["status"] == "active"]
            for a in rng.sample(active, min(4, len(active))):
                tg = set()
                t_ = a["admit"] + dt.timedelta(days=2)
                did = str(len(dischs) + len([x for x in rows if int(x["id"]) > len(dischs)]) + 1)
                extra = row(ent, did, {"dischargedAt": t_}, {
                    "dischargedAt": fmt_dt(t_, tg), "destination": "Home", "condition": "Stable", "medications": None,
                    "instructions": None, "followUp": None, "authorisedBy": SID(a["doctor"])}, tg | {"chrono"}, adm=AID(a["id"]))
                extra["touched"].add("date")
                rows.append(extra)
                DETAIL[ent]["chronology: discharge record for an admission that is still active"] += 1

    # missing required values
    for i in pick(rows, rates["missing_req"], exclude=("date",)):
        r = rows[i]
        col = rng.choice([c for c in spec["req"] if c not in r["touched"]])
        r["raw"][col] = placeholder(date=col == spec["date"])
        r["tags"].add("missing_req")
        r["touched"].add(col)
        DETAIL[ent][f"missing required: {col}"] += 1

    # invalid or ambiguous dates
    if rates["bad_date"]:
        for i in pick(rows, rates["bad_date"], exclude=("date",)):
            r = rows[i]
            col = spec["date"]
            if col in r["touched"]:
                continue
            d = r["canon"][col]
            with_time = isinstance(d, dt.datetime)
            if d.day <= 12 and d.month <= 12 and d.day != d.month and rng.random() < .8:
                r["raw"][col] = f"{d.day:02d}-{d.month:02d}-{d.year}" + (f" {d.hour:02d}:{d.minute:02d}" if with_time else "")
                r["tags"].add("date_ambiguous")
                DETAIL[ent][f"ambiguous date: {col}"] += 1
            else:
                r["raw"][col] = invalid_date_string(d, with_time)
                r["tags"].add("date_invalid")
                DETAIL[ent][f"invalid date: {col}"] += 1
            r["touched"].add(col)

    # unmappable labels
    if rates["unmap"] and ent in LABEL_COL:
        col, key = LABEL_COL[ent]
        for i in pick(rows, rates["unmap"]):
            r = rows[i]
            if col in r["touched"]:
                continue
            r["raw"][col] = rng.choice(UNMAPPABLE[key])
            r["tags"].add("unmappable")
            r["touched"].add(col)
            DETAIL[ent][f"unmappable label: {col}"] += 1

    # missing optional values
    if spec["opt"]:
        for i in pick(rows, MISSING_OPT_RATE):
            r = rows[i]
            cands = [c for c in spec["opt"] if c not in r["touched"] and r["raw"].get(c)]
            if not cands:
                continue
            col = rng.choice(cands)
            r["raw"][col] = placeholder(numeric=col in ("heartRate", "respRate", "oxygenSaturation", "painScore", "temperature"))
            if col == "temperature":
                r["raw"]["temperature@unit"] = None
            r["tags"].add("missing_opt")
            r["touched"].add(col)
            DETAIL[ent][f"missing optional: {col}"] += 1

    # invalid numbers (optional triage vitals)
    if ent == "TriageAssessment":
        bad_values = {"heartRate": ["-72", "0", "420", "abc", "999"], "respRate": ["0", "95", "xx", "150"],
                      "temperature": ["300", "4.5", "410", "hot", "52"], "oxygenSaturation": ["1.40", "1.05", "-0.03", "abc"],
                      "painScore": ["14", "11", "-2", "severe"], "bloodPressure": ["300/20", "abc/def", "0/0", "12/8000"]}
        for i in pick(rows, INVALID_VITAL_RATE):
            r = rows[i]
            cands = [c for c in bad_values if c not in r["touched"]]
            col = rng.choice(cands)
            r["raw"][col] = rng.choice(bad_values[col])
            if col == "temperature":
                r["raw"]["temperature@unit"] = "C"
            r["tags"].add("invalid_number")
            r["touched"].add(col)
            DETAIL[ent][f"invalid number: {col}"] += 1

    if ent == "Diagnosis":
        for i in pick(rows, .011, exclude=("icd9",)):
            r = rows[i]
            r["raw"]["icd9"] = rng.choice(FAKE_ICD)
            r["tags"].add("fake_icd")
            r["touched"].add("icd9")
            DETAIL[ent]["fake ICD-9 code"] += 1

    for i in pick(rows, rates["case_ws"]):
        r = rows[i]
        cands = [c for c in TEXT_COLS[ent] if c not in r["touched"] and r["raw"].get(c)]
        if not cands:
            continue
        col = rng.choice(cands)
        new = mess_case(r["raw"][col])
        if new != r["raw"][col]:
            r["raw"][col] = new
            r["tags"].add("case_ws")
            DETAIL[ent][f"case/whitespace: {col}"] += 1

# =============================================================================
# 4) Duplicates
# =============================================================================
next_num = {e: (len(pros) if e == "HealthcareProfessional" else len(patients) if e == "Patient" else len(adms)
                if e == "Admission" else max(int(r["id"]) for r in R[e])) for e in SPECS}
fmt_id = {"HealthcareProfessional": SID, "Patient": PID, "Admission": AID}
REJECTING = {"missing_req", "date_invalid", "date_ambiguous", "broken_ref", "chrono", "unmappable", "fake_icd",
             "patient_mismatch"}
for ent, spec in SPECS.items():
    rows = R[ent]
    originals = list(rows)
    n = len(originals)
    for src in (rng.sample(originals, round(EXACT_DUP * n)) if n > 20 else rng.sample(originals, min(1, n))):
        raw = dict(src["raw"])
        if rng.random() < .3:
            cands = [c for c in TEXT_COLS[ent] if raw.get(c)]
            if cands:
                c = rng.choice(cands)
                raw[c] = rng.choice([raw[c].upper(), f" {raw[c]} ", raw[c].lower()])
        dup = row(ent, src["id"], dict(src["canon"]), raw, set(src["tags"]) | {"exact_dup"}, adm=src["adm"],
                  order=src["order"], patient=src["patient"])
        dup["orphan"], dup["bad_order"] = src.get("orphan"), src.get("bad_order")
        rows.insert(min(rows.index(src) + 1, len(rows)), dup)
        DETAIL[ent]["exact duplicate rows"] += 1
    pool = [r for r in originals if not (r["tags"] & REJECTING) and not r.get("orphan")]
    for src in (rng.sample(pool, round(NEAR_DUP * n)) if n > 20 else rng.sample(pool, min(2, len(pool)))):
        next_num[ent] += 1
        new_id = fmt_id.get(ent, str)(next_num[ent])
        tg = {"near_dup"}
        raw = dict(src["raw"])
        if spec["date"] and src["canon"].get(spec["date"]) is not None:
            v = src["canon"][spec["date"]]
            raw[spec["date"]] = fmt_dt(v, tg) if isinstance(v, dt.datetime) else fmt_date(v, tg)
        for c in TEXT_COLS[ent]:
            if raw.get(c) and rng.random() < .35:
                raw[c] = rng.choice([raw[c].upper(), raw[c].lower(), f" {raw[c]}", raw[c].title()])
        if ent == "Patient" and rng.random() < .5:
            raw["phone"] = ""
        dup = row(ent, new_id, dict(src["canon"]), raw, tg, adm=new_id if ent == "Admission" else src["adm"],
                  order=src["order"], patient=src["patient"])
        rows.append(dup)
        DETAIL[ent]["near duplicate rows (new ID)"] += 1
        if ent == "Patient" and rng.random() < .5:
            kids = [r for r in R["Admission"] if r["raw"]["@patientRef"] == src["id"] and "near_dup" not in r["tags"]]
            if kids:
                k_ = rng.choice(kids)
                k_["raw"]["@patientRef"] = new_id
                k_["pat_dup"] = True
                DETAIL["Admission"]["admission points to a near-duplicate patient (re-point it)"] += 1
        if ent == "Admission" and rng.random() < .5:
            kids = [r for r in R["ClinicalNote"] if r["adm"] == src["id"] and not r.get("orphan")]
            if kids:
                k_ = rng.choice(kids)
                k_["adm"] = new_id
                k_["adm_dup"] = True
                DETAIL["ClinicalNote"]["note nested under a near-duplicate admission (re-point it)"] += 1

# a few records whose id attribute is missing (cannot be identified -> malformed)
for ent in ("TriageAssessment", "ClinicalNote", "UnitStay"):
    for r in rng.sample([x for x in R[ent] if not x["tags"] & {"exact_dup", "near_dup"} and not x.get("orphan")], 1 if ent != "ClinicalNote" else 2):
        r["no_id"] = True
        r["tags"].add("malformed")
        DETAIL[ent]["record with no id attribute (malformed)"] += 1

# =============================================================================
# 5) Write the XML file
# =============================================================================
def put(parent, path, value):
    """value None -> element left out; '' -> empty element."""
    if value is None:
        return
    if "/" in path:
        head, tail = path.split("/", 1)
        holder = parent.find(head)
        if holder is None:
            holder = ET.SubElement(parent, head)
        put(holder, tail, value)
        return
    ET.SubElement(parent, path).text = value


def element(r, parent):
    spec = SPECS[r["entity"]]
    attrs = {} if r.get("no_id") else {spec["idattr"]: r["id"]}
    if "@patientRef" in r["raw"] and r["raw"]["@patientRef"] is not None:
        attrs["patientRef"] = r["raw"]["@patientRef"]
    if r["entity"] == "ClinicalNote" and r["raw"].get("@type") is not None:
        attrs["type"] = r["raw"]["@type"]
    if r.get("orphan"):
        attrs["admissionRef"] = r["adm"]
    if r.get("bad_order"):
        attrs["orderRef"] = r["order"]
    e = ET.SubElement(parent, spec["el"], attrs)
    for f in spec["fields"]:
        if f.startswith("@"):
            continue
        if f == "temperature":
            v = r["raw"].get("temperature")
            if v is not None:
                unit = r["raw"].get("temperature@unit")
                ET.SubElement(e, "temperature", {"unit": unit} if unit else {}).text = v
            continue
        put(e, f, r["raw"].get(f))
    return e


root = ET.Element("hospitalRecords", {"system": HOSPITAL, "continent": "Asia", "timezone": "Asia/Singapore",
                                      "extractTime": CUTOFF.strftime("%Y-%m-%dT%H:%M:00+08:00")})
staff_el = ET.SubElement(root, "staff")
for r in R["HealthcareProfessional"]:
    element(r, staff_el)
pat_el = ET.SubElement(root, "patients")
for r in R["Patient"]:
    element(r, pat_el)

kids_by_adm = defaultdict(lambda: defaultdict(list))
orphans = []
for ent in CHILDREN:
    for r in R[ent]:
        if r.get("orphan"):
            orphans.append(r)
        else:
            kids_by_adm[r["adm"]][ent].append(r)
adm_el = ET.SubElement(root, "admissions")
seen_adm = set()
for r in R["Admission"]:
    e = element(r, adm_el)
    if r["id"] in seen_adm:
        continue                                           # exact duplicate copy: children stay under the first copy
    seen_adm.add(r["id"])
    ch = kids_by_adm[r["id"]]
    order_els = {}
    for ent in ["TriageAssessment", "UnitStay", "Diagnosis", "DiagnosticOrder"]:
        for k in ch[ent]:
            ke = element(k, e)
            if ent == "DiagnosticOrder" and not k.get("no_id"):
                order_els.setdefault(k["id"], ke)
    for k in ch["RadiologyExamination"]:
        parent = order_els.get(k["order"]) if (k["order"] and not k.get("bad_order")) else None
        element(k, parent if parent is not None else e)
    for ent in ["SurgicalProcedure", "ClinicalNote", "DischargeRecord"]:
        for k in ch[ent]:
            element(k, e)
unl = ET.SubElement(root, "unlinkedRecords")
for r in orphans:
    element(r, unl)

OUT.mkdir(parents=True, exist_ok=True)
ET.indent(root, space="  ")
ET.ElementTree(root).write(XML_FILE, encoding="utf-8", xml_declaration=True)

# =============================================================================
# 6) Generation log
# =============================================================================
CATS = [("Exact duplicates", lambda t: "exact_dup" in t), ("Near duplicates", lambda t: "near_dup" in t),
        ("Missing optional", lambda t: "missing_opt" in t), ("Missing required", lambda t: "missing_req" in t),
        ("Case / whitespace", lambda t: "case_ws" in t),
        ("Non-standard format", lambda t: any(x.startswith("fmt_") for x in t)),
        ("Invalid date", lambda t: "date_invalid" in t), ("Ambiguous date", lambda t: "date_ambiguous" in t),
        ("Invalid number", lambda t: "invalid_number" in t),
        ("Broken reference", lambda t: "broken_ref" in t or "patient_mismatch" in t),
        ("Chronology", lambda t: "chrono" in t), ("Unmappable label", lambda t: "unmappable" in t),
        ("Fake ICD-9", lambda t: "fake_icd" in t), ("No id (malformed)", lambda t: "malformed" in t)]
REJECT = REJECTING | {"exact_dup", "near_dup", "malformed"}

rej_pat = {r["id"] for r in R["Patient"] if (r["tags"] & REJECT) and not r["tags"] & {"exact_dup", "near_dup"}}
rej_adm, est, casc = set(), Counter(), Counter()
for r in R["Admission"]:
    own = bool(r["tags"] & REJECT)
    cascade = (not own) and r["raw"].get("@patientRef") in rej_pat and not r.get("pat_dup")
    if (own and not r["tags"] & {"exact_dup", "near_dup"}) or cascade:
        rej_adm.add(r["id"])
    if own or cascade:
        est["Admission"] += 1
        casc["Admission"] += int(bool(cascade))
rej_order = set()
for ent in CHILDREN:
    for r in R[ent]:
        own = bool(r["tags"] & REJECT)
        cascade = (not own) and r["adm"] in rej_adm and not r.get("adm_dup")
        if ent == "RadiologyExamination" and not own and not cascade and r["order"]:
            cascade = r["order"] in rej_order
        if ent == "DiagnosticOrder" and (own or cascade) and "exact_dup" not in r["tags"]:
            rej_order.add(r["id"])
        if own or cascade:
            est[ent] += 1
            casc[ent] += int(bool(cascade))
for ent in ("HealthcareProfessional", "Patient"):
    est[ent] = sum(1 for r in R[ent] if r["tags"] & REJECT)

total = sum(len(v) for v in R.values())
L = []
w = L.append
w(f"# Source C ({HOSPITAL}): generation log\n")
w("> **Statement:** all of this data is entirely fictional, created exclusively for educational and learning purposes "
  "(SOEN 363 Project Phase 2). It does not describe real patients and does not include any real personal information. "
  "Names are random combinations of common Chinese, Malay and Indian names used in Singapore; addresses, phone numbers, "
  "insurance numbers and IDs are random.\n")
w(f"Generated by `source_c_generator.py` (seed `{SEED}`). Re-running the script reproduces the file exactly (it does not "
  f"use the current date). AI tool: Claude Code (Anthropic), model Claude Opus 5.5. Hospital system: **{HOSPITAL}** "
  f"(fictional), continent **Asia**, time zone **Asia/Singapore** (UTC+8, no daylight saving time). Extract time (local): "
  f"{CUTOFF.strftime('%Y-%m-%d %H:%M')} Asia/Singapore. Admissions span 2022-01-01 to the extract time.\n")
w("All counts below are **records** (one XML element = one entity instance, nested ones included; the `<staff>`, "
  "`<patients>`, `<admissions>` and `<unlinkedRecords>` containers are not records). A record can have several problems, "
  "so the columns overlap (as section 7 of the contract allows). Every count comes from the script's own bookkeeping.\n")
w("## File, elements and record counts\n")
w("One file: `data/raw/C_xml/hospital_records.xml` (UTF-8).\n")
w("| Entity | XML element | Where | Records (incl. duplicates) | Original records | Duplicate records |")
w("|---|---|---|---:|---:|---:|")
where = {"HealthcareProfessional": "`/hospitalRecords/staff`", "Patient": "`/hospitalRecords/patients`",
         "Admission": "`/hospitalRecords/admissions`", "RadiologyExamination": "inside `<labOrder>` (or `<admission>` when there is no order)"}
tr = to = td = 0
for ent, spec in SPECS.items():
    rows = R[ent]
    d = sum(1 for r in rows if r["tags"] & {"exact_dup", "near_dup"})
    w(f"| {ent} | `<{spec['el']}>` | {where.get(ent, 'inside `<admission>`')} | {len(rows)} | {len(rows) - d} | {d} |")
    tr, to, td = tr + len(rows), to + len(rows) - d, td + d
w(f"| **Total** | | | **{tr}** | **{to}** | **{td}** |\n")
w(f"`<unlinkedRecords>` holds {len(orphans)} child records whose `admissionRef` points to an admission that does not exist "
  "(the injected broken references to admissions). No ICD-9 dictionary is generated; diagnoses use codes from "
  "`soen363-phase1/data/icd9_dictionary.csv`. Numbering starts at 1 in every entity (`P000001`, `E000001`, `S0001`, `1`).\n")
w("## Injected problems per entity (records affected)\n")
w("| Entity | " + " | ".join(c for c, _ in CATS) + " |")
w("|---|" + "---:|" * len(CATS))
tot = Counter()
for ent in SPECS:
    cells = []
    for c, f in CATS:
        k = sum(1 for r in R[ent] if f(r["tags"]))
        tot[c] += k
        cells.append(str(k))
    w(f"| {ent} | " + " | ".join(cells) + " |")
w("| **Total** | " + " | ".join(f"**{tot[c]}**" for c, _ in CATS) + " |")
w("| **% of all records** | " + " | ".join(f"{100 * tot[c] / total:.1f}%" for c, _ in CATS) + " |\n")
w(f"Compared with contract section 7: duplicates (exact + near) "
  f"{100 * (tot['Exact duplicates'] + tot['Near duplicates']) / total:.1f}% (target ~5%), missing optional "
  f"{100 * tot['Missing optional'] / total:.1f}% (~10%), missing required {100 * tot['Missing required'] / total:.1f}% "
  f"(~2%, lower on purpose for patients/admissions), case/whitespace {100 * tot['Case / whitespace'] / total:.1f}% (~15%), "
  f"non-standard formats {100 * tot['Non-standard format'] / total:.1f}% (~15%), invalid or ambiguous dates "
  f"{100 * (tot['Invalid date'] + tot['Ambiguous date']) / total:.1f}% (~2%), invalid numbers "
  f"{100 * tot['Invalid number'] / total:.1f}% (~5%), broken references {100 * tot['Broken reference'] / total:.1f}% "
  f"(~2%), chronology {100 * tot['Chronology'] / total:.1f}% (~2%).\n")
w("## Estimated rejections\n")
w("Records that carry a rejecting problem (duplicate, missing required, invalid/ambiguous date, broken reference, "
  "chronology, unmappable label, fake ICD-9, no id), plus records that cascade from a rejected patient, admission or order. "
  "Children of near-duplicate patients and admissions are not counted, because the contract re-points them to the kept "
  "record. Treat this as a sanity check, not the answer: your cleaning rules decide the real number.\n")
w("| Entity | Records | Estimated rejected | of which cascaded | % |")
w("|---|---:|---:|---:|---:|")
te = tc = 0
for ent in SPECS:
    n = len(R[ent])
    w(f"| {ent} | {n} | {est[ent]} | {casc[ent]} | {100 * est[ent] / n:.1f}% |")
    te, tc = te + est[ent], tc + casc[ent]
w(f"| **Total** | **{total}** | **{te}** | **{tc}** | **{100 * te / total:.1f}%** |\n")
w("Radiology records nested under a rejected order are counted as cascaded here; since `order_id` is nullable, your "
  "cleaning might keep them with a blank order instead.\n")
w("Side effect to expect in validation (handout Task 5): when a discharge or diagnosis record gets a rejecting problem, "
  "its real admission loses that discharge record or that primary diagnosis after cleaning. So a few completed admissions "
  "will have no discharge record or no primary diagnosis in the clean data. This comes from the injected problems.\n")
w("## Problem details per entity\n")
names = {"fmt_date_no_offset": "local time without the +08:00 offset", "fmt_date_utc": "time already in UTC (`...Z`)",
         "fmt_date_text": "text date (`08 May 2024 02:59 PM` / `8 May 1980`)",
         "fmt_date_dayfirst": "day-first slash date (`DD/MM/YYYY`)", "fmt_date_dash": "dash date with a value > 12 (readable)",
         "fmt_label": "alternative category label", "fmt_phone": "alternative phone format",
         "fmt_icd_no_decimal": "ICD-9 without decimal point", "fmt_icd_leading_zero_lost": "ICD-9 `38.9` for `038.9`",
         "fmt_temp_fahrenheit": "temperature in Fahrenheit", "fmt_vital_units": "unit text inside a vital sign"}
for ent in SPECS:
    w(f"### {ent}\n")
    for k, v in sorted(DETAIL[ent].items()):
        w(f"- {k}: {v}")
    for k, v in sorted(Counter(x for r in R[ent] for x in r["tags"] if x.startswith("fmt_")).items()):
        w(f"- non-standard format: {names.get(k, k)}: {v}")
    w("")
w("## How duplicates were made\n")
w("- **Exact duplicate:** the same element again with the **same ID**, right after the original. A duplicated "
  "`<admission>` has no children of its own (the children stay under the first copy). In about 30% of them one text "
  "field differs only in case or spacing, so they are still exact duplicates under the contract.")
w("- **Near duplicate:** the same facts under a **new ID** (numbering continues after the last original ID), written again "
  "so the date, labels and text can use another format or case. They match the contract's duplicate keys: patient = name + "
  "DOB, staff = name + role, admission = patient + admit time, others = admission + timestamp + type. For some near-duplicate "
  "patients and admissions, one child (an admission, or a note nested under the duplicate admission) points to the new ID, "
  "so the cleaning has to re-point it to the kept record (contract section 7).\n")
w("## Source C conventions (for checking your profiling)\n")
w("- **Structure:** root `<hospitalRecords>` (attributes: system, continent, timezone, extractTime) with `<staff>`, "
  "`<patients>`, `<admissions>` and `<unlinkedRecords>`. Inside each `<admission>`: `<triage>`, `<wardMovement>`, "
  "`<diagnosis>`, `<labOrder>` (with its `<imaging>` exams nested inside), `<imaging>` without an order (walk-in), "
  "`<operation>`, `<note type=\"...\">` and `<discharge>`. The parent admission of a nested record is the enclosing "
  "`<admission>`; records in `<unlinkedRecords>` carry `admissionRef` instead, and an `<imaging orderRef=\"...\">` directly "
  "under an admission points to an order that does not exist. A few records have no id attribute at all (malformed).")
w("- **IDs:** patients `P000001`, admissions `E000001`, staff `S0001`, every other entity a plain number. The contract "
  "puts the numeric part in the key column and the full text ID in `source_record_id`.")
w("- **Timestamps** are Asia/Singapore time (UTC+8, no DST). Usual format ISO 8601 with offset "
  "(`2024-05-08T14:59:00+08:00`). Also present: local time without offset (`2024-05-08 14:59`, still Singapore time), "
  "UTC with `Z` (`2024-05-08T06:59:00Z`), text dates (`08 May 2024 02:59 PM`), day-first slash dates (`08/05/2024 14:59`, "
  "always day-first), and a few dash dates (`NN-NN-YYYY HH:MM`) written in **either** order. Dash dates with a value over "
  "12 can be read; dash dates where both numbers are 12 or less are the injected **ambiguous dates**.")
w("- **Date of birth**: usually `YYYY-MM-DD`; also `DD/MM/YYYY`, `8 May 1980` style, and dash dates (same rule as above).")
w("- **Names:** `<name><family/><given/></name>`. Chinese names are written family name first; Malay and Indian names "
  "use `bin`/`binte` and `s/o`/`d/o` with the father's name in `<family>`. Staff names are one `<name>` element.")
w("- **Temperature**: `<temperature unit=\"C\">37.2</temperature>`; about 30% in Fahrenheit (`unit=\"F\"`, or no unit "
  "attribute and the unit in the text, `99.1F` / `99.1 °F`); some Celsius values carry the unit in the text (`37.2C`). "
  "**Oxygen saturation** is stored as a **fraction** (`0.97`), sometimes as a percent (`97%`). Other vitals sometimes carry "
  "units (`88 bpm`, `4/10`, `120/80 mmHg`, `120-80`).")
w("- **Missing values** (injected): element left out, empty element, `N/A`, `null`, `-`, `?`; `-1` for numbers; "
  "`0000-00-00` for dates. Values that are legitimately empty (no `<dischargedAt>` for an active admission, no "
  "`<transferOut>` for a current unit stay, no `<report>` for an exam not done, no prescription or follow-up after a death) "
  "are left out and are **not** counted as problems.")
w("- **Allergies / medications** with none: `none`, `None`, `NKA`, `NKDA`, `no known allergies`, `No Known Drug Allergy` "
  "(medications: `none`, `None`, `NKA`, `Nil`). These mean \"none\", not missing.")
w("- **ICD-9 codes**: dictionary codes only, sometimes without the decimal point (`4019`), with extra spaces (` 428.0`), "
  f"or `38.9` for `038.9`; plus fake codes from this list: {', '.join('`' + c + '`' for c in FAKE_ICD)}.")
w("- **Invalid numbers** are only in optional triage vitals (e.g. temperature `300`, pulse `-72`, SpO2 `1.40`, pain `14`, "
  "`abc`). `-1` on its own is the missing-value placeholder, not an invalid number.\n")
w("## Intended label mapping (answer key)\n")
w("| Raw element | Standard value | Source C labels |")
w("|---|---|---|")
COLMAP = {"admission_type": "admission/admissionClass", "admission_status": "admission/status",
          "life_status": "patient/vitalStatus", "sex": "patient/sex", "triage": "triage/pacLevel",
          "unit": "wardMovement/unit", "order_status": "labOrder/status", "priority": "labOrder/priority",
          "exam_status": "imaging/status", "dx_type": "diagnosis/type", "note_type": "note/@type",
          "role": "member/designation"}
for key, m in LABELS.items():
    for std, (prim, alts) in m.items():
        w(f"| `{COLMAP[key]}` | {std} | " + ", ".join(f"`{x}`" for x in [prim] + alts) + " |")
for key, vals in UNMAPPABLE.items():
    w(f"| `{COLMAP[key]}` | *(unmappable on purpose)* | " + ", ".join(f"`{x}`" for x in vals) + " |")
w("\nExam types (`labOrder/test`, `imaging/modality`): `Chest X-Ray`, `CT`, `MRI`, `Ultrasound`, `ECG`, `Full Blood Count`. "
  "Body parts: `Chest`, `Abdomen`, `Brain`.")
LOG.write_text("\n".join(L) + "\n", encoding="utf-8")

print(f"Source C: {total} records written to {XML_FILE}")
for c, _ in CATS:
    print(f"  {c:22s} {tot[c]:5d}  ({100 * tot[c] / total:.1f}%)")
print(f"  estimated rejected     {te:5d}  ({100 * te / total:.1f}%)")
