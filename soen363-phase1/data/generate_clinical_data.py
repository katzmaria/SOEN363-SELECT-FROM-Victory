"""
SOEN 363 Project Phase 1 - clinical data generator

Runs after generate_data.py and builds on the admissions it created.
Generates: ICD9Dictionary (loaded from icd9_dictionary.csv), Diagnosis,
DiagnosticOrder, RadiologyExamination, SurgicalProcedure, ClinicalNote
and DischargeRecord.

Deaths: for each patient generated as deceased, their most recent
(completed) admission becomes the admission during which they died.
That admission gets final_admission_status = 'deceased', and its
discharge time is the time of death.

All data is synthetic: clinical text comes from fixed templates and every
choice is made with a seeded random generator. No real patient data.
"""

import csv
import random
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "db" / "hospital.db"
ICD9_CSV = Path(__file__).resolve().parent / "icd9_dictionary.csv"

rng = random.Random(3633)
FMT = "%Y-%m-%d %H:%M:%S"
CRITICAL_UNITS = ("ICU", "CCU", "MICU", "SICU")
ACTIVE_WINDOW = timedelta(hours=72)  # events for still-open admissions fall in their first 72 h


# Condition group -> drives lab orders, follow-up advice and clinic
GROUP = {
    "410.9": "cardiac", "414.01": "cardiac", "427.31": "cardiac", "428.0": "cardiac", "786.50": "cardiac",
    "486": "respiratory", "491.21": "respiratory", "493.92": "respiratory", "518.81": "respiratory",
    "415.19": "respiratory",
    "434.91": "neuro", "780.2": "neuro", "780.39": "neuro", "850.9": "neuro",
    "540.9": "surgical", "574.00": "surgical", "574.20": "surgical",
    "577.0": "digestive", "578.9": "digestive", "530.81": "digestive",
    "584.9": "renal", "599.0": "renal",
    "038.9": "infection",
    "820.8": "ortho", "715.35": "ortho",
    "276.51": "general", "285.9": "general",
}

# Candidate primary diagnoses, picked by the most specific context available
PRIMARY_POOLS = {
    "death": ["410.9", "428.0", "518.81", "038.9", "434.91", "415.19"],
    "CCU": ["410.9"] * 4 + ["428.0"] * 2 + ["427.31"] * 2 + ["414.01"] * 2 + ["786.50"],
    "SICU": ["540.9", "574.00", "820.8", "578.9", "577.0", "414.01"],
    "MICU": ["038.9", "518.81", "486", "491.21", "584.9", "577.0"],
    "ICU": ["518.81", "038.9", "410.9", "434.91", "415.19", "578.9"],
    "elective": ["715.35", "574.20", "414.01", "530.81"],
    "outpatient": ["599.0", "786.50", "780.2", "493.92", "850.9", "276.51"],
    "default": ["486", "540.9", "574.00", "820.8", "434.91", "780.2", "780.39", "599.0",
                "584.9", "491.21", "427.31", "786.50", "577.0", "285.9"],
}

CHRONIC = ["401.9", "250.00", "272.4", "244.9", "585.9", "305.1"]
COMPLICATIONS = ["584.9", "276.51", "285.9", "427.31", "599.0", "530.81"]

SURGERY = {
    "540.9": "Appendectomy",
    "574.00": "Gallbladder removal",
    "574.20": "Gallbladder removal",
    "410.9": "Cardiac catheterization",
    "414.01": "Coronary artery bypass graft",
    "820.8": "Hip fracture repair",
    "715.35": "Hip replacement",
}

# primary code -> imaging studies: (examination_type, body_area, order label, typical finding)
IMAGING = {
    "410.9": [("X-ray", "Chest", "Chest X-ray",
               "Heart size at upper limit of normal. Mild pulmonary vascular congestion. Impression: early pulmonary edema.")],
    "414.01": [("X-ray", "Chest", "Chest X-ray",
                "Heart size normal. Lungs clear. Impression: no acute cardiopulmonary disease.")],
    "427.31": [("X-ray", "Chest", "Chest X-ray",
                "Mild cardiomegaly. No consolidation or effusion. Impression: mild cardiomegaly.")],
    "428.0": [("X-ray", "Chest", "Chest X-ray",
               "Cardiomegaly with bilateral pleural effusions and interstitial edema. Impression: congestive heart failure.")],
    "786.50": [("X-ray", "Chest", "Chest X-ray",
                "No acute findings. Impression: normal chest radiograph.")],
    "486": [("X-ray", "Chest", "Chest X-ray",
             "Right lower lobe consolidation with air bronchograms. Impression: right lower lobe pneumonia.")],
    "491.21": [("X-ray", "Chest", "Chest X-ray",
                "Hyperinflated lungs with flattened diaphragms. No focal consolidation. Impression: COPD without acute infiltrate.")],
    "493.92": [("X-ray", "Chest", "Chest X-ray",
                "Mild hyperinflation. No consolidation or pneumothorax. Impression: no acute process.")],
    "518.81": [("X-ray", "Chest", "Chest X-ray",
                "Diffuse bilateral airspace opacities. Impression: bilateral infiltrates consistent with respiratory failure.")],
    "415.19": [("CT angiography", "Chest", "CT pulmonary angiogram",
                "Filling defects in right lower lobe segmental pulmonary arteries. Impression: acute pulmonary embolism.")],
    "434.91": [("CT", "Head", "Head CT",
                "Hypodensity in the left middle cerebral artery territory. No hemorrhage. Impression: acute ischemic infarct."),
               ("MRI", "Brain", "Brain MRI",
                "Restricted diffusion in the left MCA territory. Impression: acute infarction confirmed.")],
    "780.2": [("CT", "Head", "Head CT",
               "No hemorrhage, mass or acute infarct. Impression: normal non-contrast head CT.")],
    "780.39": [("CT", "Head", "Head CT",
                "No hemorrhage or mass lesion. Impression: no acute intracranial abnormality.")],
    "850.9": [("CT", "Head", "Head CT",
               "No skull fracture or intracranial hemorrhage. Impression: no acute traumatic injury.")],
    "540.9": [("CT", "Abdomen and pelvis", "CT abdomen and pelvis",
               "Dilated appendix measuring 11 mm with periappendiceal fat stranding. No abscess. Impression: acute appendicitis.")],
    "574.00": [("Ultrasound", "Abdomen", "Abdominal ultrasound",
                "Multiple gallstones with gallbladder wall thickening and pericholecystic fluid. Impression: acute calculous cholecystitis.")],
    "574.20": [("Ultrasound", "Abdomen", "Abdominal ultrasound",
                "Multiple mobile gallstones. Gallbladder wall normal. Impression: cholelithiasis without cholecystitis.")],
    "577.0": [("CT", "Abdomen and pelvis", "CT abdomen and pelvis",
               "Edematous pancreas with peripancreatic fluid. No necrosis. Impression: acute interstitial pancreatitis.")],
    "578.9": [("CT angiography", "Abdomen and pelvis", "CT angiogram abdomen",
               "No active contrast extravasation. Impression: no active bleeding source identified.")],
    "584.9": [("Ultrasound", "Kidneys", "Renal ultrasound",
               "Normal-sized kidneys with increased echogenicity. No hydronephrosis. Impression: medical renal disease, no obstruction.")],
    "599.0": [("Ultrasound", "Kidneys", "Renal ultrasound",
               "No hydronephrosis or calculi. Impression: normal renal ultrasound.")],
    "038.9": [("X-ray", "Chest", "Chest X-ray",
               "No focal consolidation. Impression: no pulmonary source of infection identified.")],
    "820.8": [("X-ray", "Pelvis and hip", "Hip X-ray",
               "Displaced fracture of the right femoral neck. Impression: femoral neck fracture.")],
    "715.35": [("X-ray", "Pelvis and hip", "Hip X-ray",
                "Severe joint space narrowing of the left hip with osteophytes. Impression: advanced osteoarthritis.")],
}

NORMAL_FINDING = {
    "Chest": "Lungs clear. Heart size normal. Impression: no acute cardiopulmonary process.",
    "Head": "No hemorrhage, mass or acute infarct. Impression: no acute intracranial abnormality.",
    "Brain": "No restricted diffusion or mass. Impression: normal brain MRI.",
    "Abdomen and pelvis": "Normal appendix, pancreas and bowel. Impression: no acute abdominal or pelvic abnormality.",
    "Abdomen": "Normal gallbladder and biliary tree. Impression: normal abdominal ultrasound.",
    "Kidneys": "Normal renal size and echogenicity. Impression: normal renal ultrasound.",
    "Pelvis and hip": "No fracture or dislocation. Impression: no acute osseous abnormality.",
}

LABS = {
    "cardiac": ["12-lead ECG", "Troponin", "Lipid panel"],
    "respiratory": ["Arterial blood gas", "CBC", "Sputum culture"],
    "neuro": ["CBC", "Coagulation panel", "Blood glucose"],
    "surgical": ["CBC", "Basic metabolic panel", "Coagulation panel"],
    "digestive": ["CBC", "Lipase", "Liver function tests"],
    "renal": ["Basic metabolic panel", "Urinalysis", "Urine culture"],
    "infection": ["Blood cultures", "Lactate", "CBC"],
    "ortho": ["CBC", "Coagulation panel", "Group and screen"],
    "general": ["CBC", "Basic metabolic panel"],
}

MEDS = {
    "410.9": ["aspirin 81 mg daily", "ticagrelor 90 mg twice daily", "atorvastatin 80 mg daily", "metoprolol 25 mg twice daily"],
    "414.01": ["aspirin 81 mg daily", "atorvastatin 40 mg daily", "metoprolol 25 mg twice daily"],
    "427.31": ["apixaban 5 mg twice daily", "metoprolol 50 mg twice daily"],
    "428.0": ["furosemide 40 mg daily", "ramipril 5 mg daily", "bisoprolol 2.5 mg daily"],
    "486": ["amoxicillin-clavulanate 875 mg twice daily for 7 days"],
    "491.21": ["prednisone 40 mg daily for 5 days", "tiotropium inhaler daily"],
    "493.92": ["salbutamol inhaler as needed", "fluticasone inhaler twice daily"],
    "518.81": ["salbutamol inhaler as needed"],
    "415.19": ["apixaban 5 mg twice daily"],
    "434.91": ["aspirin 81 mg daily", "atorvastatin 80 mg daily"],
    "780.39": ["levetiracetam 500 mg twice daily"],
    "850.9": ["acetaminophen 500 mg as needed"],
    "540.9": ["acetaminophen 1 g every 6 hours as needed"],
    "574.00": ["acetaminophen 1 g every 6 hours as needed"],
    "574.20": ["acetaminophen 1 g every 6 hours as needed"],
    "578.9": ["pantoprazole 40 mg twice daily"],
    "599.0": ["nitrofurantoin 100 mg twice daily for 5 days"],
    "038.9": ["ciprofloxacin 500 mg twice daily for 7 days"],
    "820.8": ["acetaminophen 1 g every 6 hours", "enoxaparin 40 mg daily for 28 days"],
    "715.35": ["acetaminophen 1 g every 6 hours", "enoxaparin 40 mg daily for 28 days"],
    "285.9": ["ferrous sulfate 300 mg daily"],
    "530.81": ["pantoprazole 40 mg daily"],
    "401.9": ["amlodipine 5 mg daily"],
    "250.00": ["metformin 500 mg twice daily"],
    "272.4": ["atorvastatin 20 mg daily"],
    "244.9": ["levothyroxine 75 mcg daily"],
    "305.1": ["nicotine patch 21 mg daily"],
}

FOLLOW_UP = {
    "cardiac": "Avoid strenuous activity for 2 weeks. Return to the emergency department if chest pain recurs.",
    "respiratory": "Complete the full medication course. Return if breathing worsens or fever returns.",
    "neuro": "Do not drive until cleared by neurology. Return immediately for new weakness or speech changes.",
    "surgical": "Keep the incision clean and dry. No heavy lifting for 4 weeks. Return for fever or wound redness.",
    "digestive": "Low-fat diet and adequate hydration. Return for severe abdominal pain or black stools.",
    "renal": "Maintain fluid intake and avoid anti-inflammatory drugs. Repeat blood work in 1 week.",
    "infection": "Complete the antibiotic course. Return for fever, confusion or dizziness.",
    "ortho": "Weight-bearing as tolerated with a walker. Physiotherapy twice weekly.",
    "general": "Follow up with the family physician. Return if symptoms worsen.",
}

CLINIC = {
    "cardiac": "Cardiology clinic", "respiratory": "Respirology clinic", "neuro": "Neurology clinic",
    "surgical": "General surgery clinic", "digestive": "Gastroenterology clinic", "renal": "Nephrology clinic",
    "infection": "Internal medicine clinic", "ortho": "Orthopedics clinic", "general": "Family physician",
}

DESTINATIONS = ["home"] * 12 + ["home with home care"] * 3 + ["rehabilitation facility"] * 2 + \
               ["long-term care facility", "transferred to another hospital"]
CONDITIONS = ["stable", "stable", "improved", "improved", "good", "fair"]

COURSE_SURGICAL = [
    "Post-operative recovery was uneventful.",
    "Recovery was slower than expected but the patient improved steadily.",
    "Wound healing well; patient ambulating independently before discharge.",
]
COURSE_MEDICAL = [
    "Recovery was uneventful.",
    "Patient made a good recovery with treatment.",
    "Symptoms resolved with treatment and the patient remained stable.",
    "Clinically improved and back to baseline function.",
]
PROGRESS_TEMPLATES = [
    "Progress note. Patient seen on rounds. Vital signs stable overnight. Continue current management.",
    "Progress note. Remains under monitoring in the {unit}. No acute events overnight.",
    "Progress note. Pain well controlled and tolerating oral intake. Recovery progressing as expected.",
    "Progress note. Mobilizing with physiotherapy. Reassess discharge readiness tomorrow.",
]

def parse(s):
    return datetime.strptime(s, FMT) if s else None


def ts(dt):
    return dt.strftime(FMT)


def between(start, end):
    """Random datetime in [start, end]; returns start if the window is empty."""
    if end <= start:
        return start
    return start + timedelta(seconds=rng.randint(0, int((end - start).total_seconds())))


def clamp(adm, dt):
    """Keep a timestamp inside the admission window."""
    return min(max(dt, adm["admit"]), adm["end"])


def impression(finding):
    return finding.split("Impression: ", 1)[-1].rstrip(".")

def load(cur):
    roles = defaultdict(list)
    for pid, role in cur.execute("SELECT professional_id, role FROM HealthcareProfessional ORDER BY professional_id"):
        roles[role].append(pid)
    everyone = [p for ids in roles.values() for p in ids]
    staff = {
        "physician": roles["Physician"] or everyone,
        "surgeon": roles["Surgeon"] or roles["Physician"] or everyone,
        "technician": roles["Radiology Technician"] or everyone,
    }

    admissions = {}
    rows = cur.execute(
        """SELECT a.admission_id, a.patient_id, a.admission_date_time, a.discharge_date_time,
                  a.admission_type, t.triage_priority_level, t.blood_pressure, t.heart_rate,
                  t.oxygen_saturation, t.pain_level
           FROM Admission a
           LEFT JOIN TriageAssessment t ON t.admission_id = a.admission_id
           ORDER BY a.admission_id, t.assessment_id"""
    ).fetchall()
    for (aid, pid, admit, discharge, a_type, prio, bp, hr, spo2, pain) in rows:
        if aid in admissions:
            continue  # keep the first triage assessment only
        admit, discharge = parse(admit), parse(discharge)
        admissions[aid] = {
            "id": aid, "patient_id": pid, "admit": admit, "discharge": discharge,
            "end": discharge or admit + ACTIVE_WINDOW, "type": a_type,
            "triage": (prio, bp, hr, spo2, pain), "stays": [], "died": False,
        }

    for aid, unit, entry, exit_ in cur.execute(
            "SELECT admission_id, unit_type, entry_date_time, exit_date_time FROM UnitStay ORDER BY admission_id, entry_date_time"):
        admissions[aid]["stays"].append((unit, parse(entry), parse(exit_)))

    deceased = {pid for (pid,) in cur.execute("SELECT patient_id FROM Patient WHERE life_status = 'deceased'")}
    return staff, list(admissions.values()), deceased


def mark_deaths(cur, admissions, deceased):
    latest = {}
    for adm in admissions:
        pid = adm["patient_id"]
        if pid in deceased and (pid not in latest or adm["admit"] > latest[pid]["admit"]):
            latest[pid] = adm
    for adm in latest.values():
        if adm["discharge"] is None:
            continue  # still admitted; no time of death to record
        adm["died"] = True
        cur.execute("UPDATE Admission SET final_admission_status = 'deceased' WHERE admission_id = ?", (adm["id"],))


# ---------------------------------------------------------------------------
# Per-admission generation
# ---------------------------------------------------------------------------

def choose_primary(adm):
    units = {u for (u, _, _) in adm["stays"]}
    if adm["died"]:
        pool = PRIMARY_POOLS["death"]
    else:
        pool = next((PRIMARY_POOLS[u] for u in ("CCU", "SICU", "MICU", "ICU") if u in units), None)
        if pool is None:
            pool = PRIMARY_POOLS.get(adm["type"], PRIMARY_POOLS["default"])
    return rng.choice(pool)


def choose_secondaries(adm, primary, chronic):
    codes = [c for c in chronic if c != primary and rng.random() < 0.75]
    if adm["type"] != "outpatient" and rng.random() < 0.35:
        extra = rng.choice(COMPLICATIONS)
        if extra != primary and extra not in codes:
            codes.append(extra)
    return codes


def plan_surgery(adm, primary):
    proc = SURGERY.get(primary)
    if not proc or adm["type"] == "outpatient":
        return None
    if rng.random() > (0.6 if primary == "410.9" else 0.85):
        return None
    earliest = adm["admit"] + timedelta(hours=1)
    latest = min(adm["admit"] + timedelta(hours=48), adm["end"] - timedelta(hours=1))
    if latest <= earliest:
        return None
    # Often operate before a later critical-care transfer (post-op monitoring)
    later_cc = [entry for (u, entry, _) in adm["stays"]
                if u in CRITICAL_UNITS and entry > earliest + timedelta(minutes=30)]
    if later_cc and rng.random() < 0.6:
        cutoff = later_cc[0] - timedelta(minutes=30)
        if cutoff > earliest:
            latest = min(latest, cutoff)
    return {"type": proc, "time": between(earliest, latest)}


def order_status(adm):
    if adm["discharge"] is None:
        return rng.choice(["pending", "in_progress", "completed", "completed"])
    return "cancelled" if rng.random() < 0.12 else "completed"


def order_priority(adm):
    units = {u for (u, _, _) in adm["stays"]}
    if adm["type"] == "emergency" or units & set(CRITICAL_UNITS):
        return rng.choice(["stat", "urgent"])
    if adm["type"] in ("elective", "outpatient"):
        return "routine"
    return rng.choice(["urgent", "routine"])


def unit_at(adm, when):
    for unit, entry, exit_ in adm["stays"]:
        if entry <= when and (exit_ is None or when <= exit_):
            return unit
    return None


def generate(cur, staff, admissions, titles):
    chronic_by_patient = {}
    counts = defaultdict(int)

    def insert(sql, params, table):
        cur.execute(sql, params)
        counts[table] += 1
        return cur.lastrowid

    for adm in admissions:
        pid = adm["patient_id"]
        if pid not in chronic_by_patient:
            chronic_by_patient[pid] = rng.sample(CHRONIC, k=rng.choice([0, 0, 1, 1, 2, 3]))
        attending = rng.choice(staff["physician"])
        completed = adm["discharge"] is not None
        primary = choose_primary(adm)
        group = GROUP.get(primary, "general")
        secondaries = choose_secondaries(adm, primary, chronic_by_patient[pid])

        # --- Diagnoses -------------------------------------------------------
        # Completed admissions always get a primary diagnosis; open ones only sometimes
        dx_recorded = completed or rng.random() < 0.6
        if dx_recorded:
            t = clamp(adm, adm["admit"] + timedelta(minutes=rng.randint(30, 480)))
            insert("""INSERT INTO Diagnosis (patient_id, admission_id, icd9_code, diagnosing_professional_id,
                                             diagnosis_date_time, diagnosis_type)
                      VALUES (?, ?, ?, ?, ?, 'primary')""",
                   (pid, adm["id"], primary, attending, ts(t)), "Diagnosis")
            for code in secondaries:
                t = between(clamp(adm, adm["admit"] + timedelta(hours=1)), adm["end"])
                insert("""INSERT INTO Diagnosis (patient_id, admission_id, icd9_code, diagnosing_professional_id,
                                                 diagnosis_date_time, diagnosis_type)
                          VALUES (?, ?, ?, ?, ?, 'secondary')""",
                       (pid, adm["id"], code, attending, ts(t)), "Diagnosis")
        else:
            secondaries = []

        # --- Surgery ---------------------------------------------------------
        surgery = plan_surgery(adm, primary)
        if surgery:
            surgery["surgeon"] = rng.choice(staff["surgeon"])
            surgery["outcome"] = "complications noted" if adm["died"] or rng.random() < 0.2 else "successful"
            insert("""INSERT INTO SurgicalProcedure (admission_id, performing_professional_id, procedure_type,
                                                     procedure_date_time, outcome)
                      VALUES (?, ?, ?, ?, ?)""",
                   (adm["id"], surgery["surgeon"], surgery["type"], ts(surgery["time"]), surgery["outcome"]),
                   "SurgicalProcedure")

        # --- Diagnostic orders and radiology ---------------------------------
        order_labels, impressions = [], []
        priority = order_priority(adm)
        working = f"working diagnosis {primary} ({titles[primary]})"

        def add_exam(order_id, referrer, study, when, status, abnormal_p=0.8):
            exam_type, body, label, finding = study
            done = status == "completed"
            findings = (finding if rng.random() < abnormal_p else NORMAL_FINDING[body]) if done else None
            link = f"pacs://images.hospital.example/studies/{rng.getrandbits(48):012x}" if done else None
            insert("""INSERT INTO RadiologyExamination (admission_id, order_id, referring_professional_id,
                          technician_professional_id, examination_type, examination_date_time,
                          body_area_examined, examination_status, link_to_medical_images, radiologist_findings)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (adm["id"], order_id, referrer, rng.choice(staff["technician"]), exam_type, ts(when),
                    body, status, link, findings), "RadiologyExamination")
            if findings:
                impressions.append(f"{label} ({impression(findings)})")

        # Lab / ECG orders (no examination record)
        for lab in rng.sample(LABS[group], k=rng.randint(1, len(LABS[group]))):
            when = clamp(adm, adm["admit"] + timedelta(minutes=rng.randint(10, 120)))
            insert("""INSERT INTO DiagnosticOrder (admission_id, requesting_professional_id, request_date_time,
                                                   clinical_reason, order_status, priority)
                      VALUES (?, ?, ?, ?, ?, ?)""",
                   (adm["id"], attending, ts(when), f"{lab}; {working}", order_status(adm), priority),
                   "DiagnosticOrder")
            order_labels.append(lab)

        studies = IMAGING.get(primary, [])
        if surgery and studies and rng.random() < 0.8:
            # Pre-operative imaging shortly before the operation, same admission
            study = studies[0]
            exam_time = between(max(adm["admit"], surgery["time"] - timedelta(hours=5)),
                                surgery["time"] - timedelta(minutes=20))
            req_time = between(max(adm["admit"], exam_time - timedelta(hours=2)), exam_time)
            oid = insert("""INSERT INTO DiagnosticOrder (admission_id, requesting_professional_id, request_date_time,
                                                         clinical_reason, order_status, priority)
                            VALUES (?, ?, ?, ?, ?, ?)""",
                         (adm["id"], attending, ts(req_time),
                          f"{study[2]}; pre-operative assessment before {surgery['type'].lower()}",
                          "completed", "urgent"), "DiagnosticOrder")
            order_labels.append(study[2])
            add_exam(oid, attending, study, exam_time, "completed", abnormal_p=0.9)
        elif studies and rng.random() < 0.65:
            for i, study in enumerate(studies):
                if i > 0 and rng.random() < 0.5:
                    continue
                req_time = clamp(adm, adm["admit"] + timedelta(minutes=rng.randint(30, 360)))
                status = order_status(adm)
                oid = insert("""INSERT INTO DiagnosticOrder (admission_id, requesting_professional_id,
                                    request_date_time, clinical_reason, order_status, priority)
                                VALUES (?, ?, ?, ?, ?, ?)""",
                             (adm["id"], attending, ts(req_time), f"{study[2]}; {working}", status, priority),
                             "DiagnosticOrder")
                order_labels.append(study[2])
                exam_time = between(req_time, min(req_time + timedelta(hours=6), adm["end"]))
                if status == "completed":
                    add_exam(oid, attending, study, exam_time, "completed")
                elif status == "in_progress":
                    add_exam(oid, attending, study, exam_time, "scheduled")
                elif status == "cancelled" and rng.random() < 0.5:
                    add_exam(oid, attending, study, exam_time, "cancelled")

        # Occasional portable chest X-ray in critical care, done without a formal order
        cc_stays = [(u, e) for (u, e, _) in adm["stays"] if u in CRITICAL_UNITS and e <= adm["end"]]
        if cc_stays and rng.random() < 0.12:
            unit, entry = cc_stays[0]
            when = between(entry, min(entry + timedelta(hours=12), adm["end"]))
            portable = ("X-ray", "Chest", "Portable chest X-ray",
                        f"Portable film in the {unit}. Support lines in satisfactory position. No pneumothorax. "
                        "Impression: no acute change.")
            add_exam(None, rng.choice(staff["physician"]), portable, when, "completed", abnormal_p=1.0)

        # --- Clinical notes --------------------------------------------------
        prio, bp, hr, spo2, pain = adm["triage"]
        note_time = clamp(adm, adm["admit"] + timedelta(minutes=rng.randint(20, 180)))
        plan = ", ".join(order_labels) if order_labels else "observation and reassessment"
        dx_text = titles[primary] if dx_recorded else "pending"
        insert("""INSERT INTO ClinicalNote (admission_id, authoring_professional_id, note_type,
                                            creation_date_time, contents)
                  VALUES (?, ?, 'admission_note', ?, ?)""",
               (adm["id"], attending, ts(note_time),
                f"Admission assessment ({adm['type']} admission). Triage priority: {prio}. "
                f"Vitals on arrival: BP {bp}, HR {hr} bpm, SpO2 {spo2}%, pain {pain}/10. "
                f"Working diagnosis: {dx_text}. Plan: {plan}."), "ClinicalNote")

        stay_hours = (adm["end"] - adm["admit"]).total_seconds() / 3600
        for _ in range(min(3, int(stay_hours // 24))):
            when = between(adm["admit"] + timedelta(hours=12), adm["end"] - timedelta(hours=1))
            template = rng.choice(PROGRESS_TEMPLATES)
            unit = unit_at(adm, when)
            if "{unit}" in template and unit is None:
                template = PROGRESS_TEMPLATES[0]
            insert("""INSERT INTO ClinicalNote (admission_id, authoring_professional_id, note_type,
                                                creation_date_time, contents)
                      VALUES (?, ?, 'progress_note', ?, ?)""",
                   (adm["id"], rng.choice(staff["physician"]), ts(when), template.format(unit=unit)),
                   "ClinicalNote")

        if surgery:
            when = clamp(adm, surgery["time"] + timedelta(minutes=rng.randint(60, 180)))
            detail = ("Performed without intraoperative complications."
                      if surgery["outcome"] == "successful"
                      else "Intraoperative bleeding encountered and controlled.")
            insert("""INSERT INTO ClinicalNote (admission_id, authoring_professional_id, note_type,
                                                creation_date_time, contents)
                      VALUES (?, ?, 'operative_note', ?, ?)""",
                   (adm["id"], surgery["surgeon"], ts(when),
                    f"Operative note. Procedure: {surgery['type']}. Indication: {titles[primary]}. {detail} "
                    "Patient transferred to the recovery room in stable condition."), "ClinicalNote")

        # --- Discharge record and summary ------------------------------------
        if not completed:
            continue

        units_path = " -> ".join(u for (u, _, _) in adm["stays"]) or "no unit stay"
        if adm["died"]:
            record = ("deceased", "deceased", None, None, None)
            summary = (f"Discharge summary (death). Admitted with {titles[primary]}. Units: {units_path}. "
                       "Despite maximal treatment the patient's condition deteriorated. "
                       f"Pronounced dead at {ts(adm['discharge'])}. Cause of death: {titles[primary]}.")
        else:
            destination = "home" if adm["type"] == "outpatient" else rng.choice(DESTINATIONS)
            condition = rng.choice(CONDITIONS)
            meds = []
            for code in [primary] + secondaries:
                meds += [m for m in MEDS.get(code, []) if m not in meds]
            appt_day = adm["discharge"] + timedelta(days=rng.randint(7, 30))
            appt = appt_day.replace(hour=rng.randint(9, 15), minute=rng.choice([0, 30]), second=0)
            appointment = f"{CLINIC[group]} on {appt.strftime('%Y-%m-%d %H:%M')}"
            record = (destination, condition, "; ".join(meds) or "none", FOLLOW_UP[group], appointment)

            parts = [f"Discharge summary. Reason for admission: {titles[primary]}."]
            if surgery:
                parts.append(f"Procedure: {surgery['type']} on {surgery['time']:%Y-%m-%d} ({surgery['outcome']}).")
            if impressions:
                parts.append(f"Imaging: {'; '.join(impressions)}.")
            parts.append(f"Units: {units_path}.")
            if secondaries:
                parts.append(f"Secondary diagnoses: {', '.join(titles[c] for c in secondaries)}.")
            parts.append(rng.choice(COURSE_SURGICAL if surgery else COURSE_MEDICAL))
            parts.append(f"Discharged to {destination} in {condition} condition. Follow-up: {appointment}.")
            summary = " ".join(parts)

        insert("""INSERT INTO DischargeRecord (admission_id, authorizing_professional_id, discharge_date_time,
                      discharge_destination, condition_at_discharge, prescribed_medications,
                      follow_up_instructions, scheduled_appointments)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
               (adm["id"], attending, ts(adm["discharge"])) + record, "DischargeRecord")
        insert("""INSERT INTO ClinicalNote (admission_id, authoring_professional_id, note_type,
                                            creation_date_time, contents)
                  VALUES (?, ?, 'discharge_summary', ?, ?)""",
               (adm["id"], attending, ts(adm["discharge"]), summary), "ClinicalNote")

    return counts


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # Idempotent: clear anything a previous run created
    for table in ["DischargeRecord", "ClinicalNote", "RadiologyExamination", "DiagnosticOrder",
                  "SurgicalProcedure", "Diagnosis", "ICD9Dictionary"]:
        cur.execute(f"DELETE FROM {table}")
    cur.execute("UPDATE Admission SET final_admission_status = 'discharged' "
                "WHERE final_admission_status = 'deceased'")

    with open(ICD9_CSV, newline="") as f:
        icd_rows = list(csv.DictReader(f))
    cur.executemany(
        "INSERT INTO ICD9Dictionary (icd9_code, official_title, description, disease_category) VALUES (?, ?, ?, ?)",
        [(r["icd9_code"], r["official_title"], r["description"], r["disease_category"]) for r in icd_rows],
    )
    titles = {r["icd9_code"]: r["official_title"] for r in icd_rows}

    staff, admissions, deceased = load(cur)
    mark_deaths(cur, admissions, deceased)
    generate(cur, staff, admissions, titles)
    conn.commit()

    for table in ["ICD9Dictionary", "Diagnosis", "DiagnosticOrder", "RadiologyExamination",
                  "SurgicalProcedure", "ClinicalNote", "DischargeRecord"]:
        print(f"{table}: {cur.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]} rows")
    died = cur.execute("SELECT COUNT(*) FROM Admission WHERE final_admission_status = 'deceased'").fetchone()[0]
    print(f"Admissions ending in death: {died}")
    conn.close()


if __name__ == "__main__":
    main()
