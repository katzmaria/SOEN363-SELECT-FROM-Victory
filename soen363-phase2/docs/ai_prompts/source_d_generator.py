#!/usr/bin/env python3
"""
Synthetic raw data generator for Source D: "Coral Coast Health Service" (fictional), Oceania (Australia).

STATEMENT: All data produced by this script is entirely fictional, created exclusively for
educational and learning purposes (SOEN 363 Project Phase 2). It does not describe real
patients and does not include any real personal information. Names are random combinations
of common first names and surnames; suburbs and streets are invented; telephone numbers come
from the Australian ranges reserved for fiction ((02) 5550 xxxx and (02) 7010 xxxx); URLs use
the reserved .example domain.

AI DISCLOSURE: this script was written by Claude Code (Anthropic), model Claude Opus 5.5.
It is part of the AI-use disclosure and is NOT part of the team's pipeline. It only generates
raw data; it does no loading, profiling, cleaning or transformation.

Output: JSON files in soen363-phase2/data/raw/D_json/ (an API-style export: practitioners in
their own file, patients paginated over three files with admissions and all clinical records
nested inside) and a generation log (soen363-phase2/docs/ai_prompts/source_d_generation_log.md)
with exact counts of every record and every injected problem. Seeded, so re-running produces
byte-identical files.

Run:  python3 soen363-phase2/docs/ai_prompts/source_d_generator.py
"""

import copy
import csv
import datetime as dt
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

SEED = 2061
rng = random.Random(SEED)

HERE = Path(__file__).resolve().parent          # soen363-phase2/docs/ai_prompts
PHASE2 = HERE.parent.parent                     # soen363-phase2
REPO = PHASE2.parent
ICD_PATH = REPO / "soen363-phase1" / "data" / "icd9_dictionary.csv"
OUT_DIR = PHASE2 / "data" / "raw" / "D_json"
LOG_PATH = HERE / "source_d_generation_log.md"

SYSTEM = "Coral Coast Health Service"
SYD = ZoneInfo("Australia/Sydney")
UTC = dt.timezone.utc
START = dt.datetime(2022, 1, 1, 0, 0)
CUTOFF = dt.datetime(2025, 10, 31, 18, 0)       # extract time, local Australia/Sydney (+11:00, daylight saving)
N_PATIENTS = 655
N_PAGES = 3

# =============================================================================
# ICD-9 codes (only the shared dictionary) and fake codes
# =============================================================================
with open(ICD_PATH, newline="", encoding="utf-8") as f:
    ICD_CODES = [r["icd9_code"] for r in csv.DictReader(f)]
ICD_SET = set(ICD_CODES)
_NODOT = Counter(c.replace(".", "") for c in ICD_CODES)
assert all(v == 1 for v in _NODOT.values()), "no-decimal forms must be unique"
FAKE_ICD = ["999.9", "V99.99", "123.45", "E000.0", "4l0.9", "880.88", "555.55", "XXX.X", "042.99"]
for _fc in FAKE_ICD:
    assert _fc not in ICD_SET and _fc.replace(".", "") not in _NODOT
    assert ("0" + _fc) not in ICD_SET and ("00" + _fc) not in ICD_SET


# =============================================================================
# Time-zone helpers (all canonical times are naive Australia/Sydney local times)
# =============================================================================
def aware(t):
    return t.replace(tzinfo=SYD)


def in_gap(t):
    """True if the local time does not exist (skipped hour when daylight saving starts)."""
    back = aware(t).astimezone(UTC).astimezone(SYD).replace(tzinfo=None, fold=0)
    return back != t.replace(fold=0)


def in_overlap(t):
    """True if the local time happens twice (repeated hour when daylight saving ends)."""
    return not in_gap(t) and aware(t.replace(fold=0)).utcoffset() != aware(t.replace(fold=1)).utcoffset()


def fx(t):
    """Move a time that falls in the skipped hour forward by one hour (same instant, valid local time)."""
    return t + dt.timedelta(hours=1) if in_gap(t) else t


def utc_of(t):
    return aware(t).astimezone(UTC)


def first_sunday(y, m):
    d = dt.date(y, m, 1)
    return d + dt.timedelta(days=(6 - d.weekday()) % 7)


DST_NIGHTS = []                                  # (kind, date of the change)
for _y in range(2022, 2026):
    DST_NIGHTS.append(("overlap", first_sunday(_y, 4)))
    DST_NIGHTS.append(("gap", first_sunday(_y, 10)))
DST_NIGHTS = [(k, d) for k, d in DST_NIGHTS if dt.datetime.combine(d, dt.time(4)) < CUTOFF - dt.timedelta(days=14)]
for _k, _d in DST_NIGHTS:
    _t = dt.datetime.combine(_d, dt.time(2, 30))
    assert (in_gap(_t) if _k == "gap" else in_overlap(_t)), (_k, _d)

# =============================================================================
# Clinical knowledge per ICD code (keeps the records internally consistent)
#   reason: presenting problems, sym: triage symptoms, sev: 1 low .. 3 high,
#   short: label used in order indications, tests: diagnostic orders,
#   meds: discharge medications, plan: progress-note sentences
# =============================================================================
CLIN = {
    "038.9": dict(reason=["Fever, rigors and confusion", "Febrile and hypotensive", "Fever and lethargy for 3 days"],
                  sym=["fever, rigors, confusion", "high fever, weakness", "fever, vomiting, drowsy"], sev=3, short="sepsis",
                  tests=["Blood cultures", "FBC", "Serum lactate", "CRP", "Chest X-ray"],
                  meds="Ceftriaxone 1g IV daily then Amoxicillin-clavulanate 875/125mg BD x5 days",
                  plan=["Sepsis pathway commenced, IV antibiotics and fluids, cultures sent.", "Remains febrile, BP improved with fluid bolus.", "Afebrile 24h, stepped down to oral antibiotics."]),
    "244.9": dict(reason=["Fatigue and weight gain, known hypothyroid", "Review of thyroxine dose"],
                  sym=["tiredness, cold intolerance", "weight gain, constipation"], sev=1, short="hypothyroidism",
                  tests=["TSH", "Free T4"], meds="Levothyroxine 100mcg mane",
                  plan=["TSH raised, thyroxine dose increased.", "Symptoms improving on current dose."]),
    "250.00": dict(reason=["Hyperglycaemia, poorly controlled T2DM", "Diabetes review, high BSLs"],
                   sym=["polyuria, thirst", "tiredness, frequent urination"], sev=1, short="T2DM",
                   tests=["HbA1c", "BSL", "UEC"], meds="Metformin XR 1g nocte; Gliclazide MR 60mg mane",
                   plan=["BSLs 9-13 mmol/L, metformin continued, diabetes educator referral.", "Diabetes education provided."]),
    "272.4": dict(reason=["Lipid review", "High cholesterol on screening"], sym=["no complaints", "routine review"], sev=1,
                  short="hyperlipidaemia", tests=["Fasting lipids"], meds="Atorvastatin 20mg nocte",
                  plan=["Lipids elevated, statin commenced.", "Dietary advice given."]),
    "276.51": dict(reason=["Vomiting and diarrhoea, unable to tolerate fluids", "Dehydration after gastro"],
                   sym=["vomiting, diarrhoea, dizziness", "watery stools, dry mouth"], sev=2, short="dehydration",
                   tests=["UEC", "VBG", "Faecal MCS"], meds="Oral rehydration solution PRN",
                   plan=["IV fluids running, tolerating sips.", "Rehydrated, passing urine well."]),
    "285.9": dict(reason=["Weakness and pallor", "Low haemoglobin on routine bloods"],
                  sym=["fatigue, dizziness, pallor", "short of breath on exertion"], sev=2, short="anaemia",
                  tests=["FBC", "Blood film", "Iron studies"], meds="Ferrous sulfate 325mg daily",
                  plan=["Hb 72 g/L, 1 unit PRBC transfused.", "Hb improved post transfusion."]),
    "305.1": dict(reason=["Smoking cessation review", "Tobacco use counselling"], sym=["morning cough", "no complaints"], sev=1,
                  short="tobacco use", tests=["Chest X-ray"], meds="Nicotine patch 21mg/24h daily",
                  plan=["Quitline referral made.", "Motivated to quit, NRT started."]),
    "401.9": dict(reason=["Headache with high blood pressure", "Hypertension review", "Elevated BP at GP"],
                  sym=["headache, dizziness", "blurred vision, headache", "no complaints"], sev=1, short="hypertension",
                  tests=["UEC", "Urinalysis", "ECG"], meds="Amlodipine 10mg daily; Perindopril 5mg daily",
                  plan=["BP 172/104, amlodipine uptitrated.", "BP better controlled at 136/84."]),
    "410.9": dict(reason=["Central chest pain radiating to left arm", "Chest pain and diaphoresis"],
                  sym=["crushing chest pain, sweating", "chest pain, SOB, nausea"], sev=3, short="AMI",
                  tests=["Troponin", "ECG", "Chest X-ray", "Fasting lipids"],
                  meds="Aspirin 100mg daily; Ticagrelor 90mg BD; Atorvastatin 80mg nocte; Metoprolol 25mg BD",
                  plan=["ECG STEMI, loaded with aspirin and ticagrelor, cath lab activated.", "Chest pain settled, troponin trending down."]),
    "414.01": dict(reason=["Exertional chest pain, booked for angiography", "Known CAD for elective angiogram"],
                   sym=["chest tightness on exertion", "exertional angina"], sev=2, short="CAD",
                   tests=["ECG", "Fasting lipids", "UEC"],
                   meds="Aspirin 100mg daily; Atorvastatin 40mg nocte; Isosorbide mononitrate 60mg mane",
                   plan=["Pre-procedure checks complete.", "Post angiography, radial site clean and dry."]),
    "415.19": dict(reason=["Sudden SOB and pleuritic chest pain", "Breathlessness after long-haul flight"],
                   sym=["sudden breathlessness, pleuritic chest pain", "SOB, calf swelling"], sev=3, short="PE",
                   tests=["D-dimer", "CTPA", "ECG"], meds="Apixaban 10mg BD x7 days then 5mg BD",
                   plan=["Anticoagulation commenced.", "Breathing easier, SpO2 96% on room air."]),
    "427.31": dict(reason=["Palpitations and dizziness", "Irregular heartbeat"], sym=["palpitations, dizziness", "racing heart, SOB"],
                   sev=2, short="AF", tests=["ECG", "UEC", "TSH"], meds="Metoprolol 50mg BD; Apixaban 5mg BD",
                   plan=["Rate controlled on metoprolol.", "Remains in AF, rate 80s."]),
    "428.0": dict(reason=["SOB and leg swelling", "Worsening breathlessness, orthopnoea"],
                  sym=["breathlessness, orthopnoea, leg oedema", "cough, swollen legs"], sev=3, short="CCF",
                  tests=["Chest X-ray", "UEC", "BNP", "Echocardiogram"],
                  meds="Furosemide 40mg mane; Perindopril 2.5mg daily; Spironolactone 25mg daily",
                  plan=["IV furosemide, good diuresis.", "Weight down 2 kg, less breathless."]),
    "434.91": dict(reason=["Sudden right-sided weakness and slurred speech", "Facial droop and arm weakness"],
                   sym=["right sided weakness, slurred speech", "facial droop, confusion"], sev=3, short="stroke",
                   tests=["CT brain", "FBC", "Fasting lipids", "BSL"],
                   meds="Aspirin 100mg daily then Clopidogrel 75mg daily; Atorvastatin 80mg nocte",
                   plan=["Code stroke called, CT no haemorrhage, aspirin started.", "Speech improving, physio commenced."]),
    "486": dict(reason=["Cough, fever and SOB", "Productive cough and pleuritic pain"],
                sym=["cough, fever, breathlessness", "productive cough, chest pain, fever"], sev=2, short="pneumonia",
                tests=["Chest X-ray", "FBC", "Sputum MCS", "CRP"], meds="Amoxicillin 1g TDS x5 days; Doxycycline 100mg BD x5 days",
                plan=["IV antibiotics, O2 via nasal prongs.", "Fever settling, cough improving."]),
    "491.21": dict(reason=["Worsening cough and wheeze, known COPD", "Breathless, COPD flare"],
                   sym=["wheeze, cough, breathlessness", "increased sputum, breathlessness"], sev=2, short="COPD exacerbation",
                   tests=["Chest X-ray", "VBG", "FBC"],
                   meds="Salbutamol MDI 4 puffs PRN; Prednisolone 50mg daily x5 days; Doxycycline 100mg daily x5 days",
                   plan=["Salbutamol nebs, steroids commenced.", "Wheeze reduced, mobilising on ward."]),
    "493.92": dict(reason=["Acute asthma", "Severe wheeze not relieved by puffer"], sym=["wheeze, tight chest", "breathlessness, night cough"],
                   sev=2, short="acute asthma", tests=["Peak flow", "Chest X-ray"],
                   meds="Salbutamol MDI PRN; Budesonide/formoterol 200/6 2 puffs BD; Prednisolone 50mg daily x5 days",
                   plan=["Back-to-back salbutamol, improving.", "Peak flow 80% predicted."]),
    "518.81": dict(reason=["Severe respiratory distress, drowsy", "Hypoxic respiratory failure"], sym=["severe breathlessness, drowsiness", "laboured breathing, confusion"],
                   sev=3, short="respiratory failure", tests=["ABG", "Chest X-ray", "FBC"],
                   meds="Salbutamol nebules PRN; Home oxygen assessment",
                   plan=["On high-flow nasal O2, ABG repeated.", "Weaned to nasal prongs, more alert."]),
    "530.81": dict(reason=["Heartburn and reflux", "Epigastric burning, booked for gastroscopy"], sym=["heartburn, regurgitation", "epigastric pain after meals"],
                   sev=1, short="GORD", tests=["H. pylori breath test"], meds="Pantoprazole 40mg daily x8 weeks",
                   plan=["PPI commenced, lifestyle advice.", "Symptoms improving on pantoprazole."]),
    "540.9": dict(reason=["RIF pain and vomiting", "Periumbilical pain migrating to right side"],
                  sym=["right iliac fossa pain, vomiting, fever", "abdominal pain, anorexia"], sev=3, short="appendicitis",
                  tests=["FBC", "Ultrasound abdomen", "Urinalysis"], meds="Paracetamol 1g QID PRN; Oxycodone 5mg PRN x3 days",
                  plan=["Surgical review, booked for theatre.", "Day 1 post-op, tolerating fluids."]),
    "574.00": dict(reason=["RUQ pain and fever", "Severe pain under right ribs after meals"],
                   sym=["right upper quadrant pain, fever", "pain after fatty meals, vomiting"], sev=2, short="cholecystitis",
                   tests=["Ultrasound abdomen", "LFT", "FBC"], meds="Amoxicillin-clavulanate 875/125mg BD x5 days; Paracetamol 1g PRN",
                   plan=["IV antibiotics, nil by mouth.", "Pain improving, diet reintroduced."]),
    "574.20": dict(reason=["Recurrent biliary colic, for cholecystectomy", "Gallstones, booked surgery"],
                   sym=["intermittent RUQ pain", "bloating after meals"], sev=1, short="cholelithiasis",
                   tests=["Ultrasound abdomen", "LFT"], meds="Paracetamol 1g QID PRN",
                   plan=["Consented for laparoscopic cholecystectomy.", "Post-op, port sites clean."]),
    "577.0": dict(reason=["Severe epigastric pain radiating to back", "Epigastric pain and vomiting"],
                  sym=["severe epigastric pain, vomiting", "abdominal pain radiating to back"], sev=3, short="pancreatitis",
                  tests=["Lipase", "Ultrasound abdomen", "CT abdomen", "LFT"],
                  meds="Paracetamol 1g QID; Oxycodone 5mg PRN; Low-fat diet",
                  plan=["Aggressive IV fluids and analgesia.", "Lipase falling, tolerating clear fluids."]),
    "578.9": dict(reason=["Haematemesis", "Melaena and dizziness"], sym=["vomiting blood, dizziness", "black stools, weakness"],
                  sev=3, short="upper GI bleed", tests=["FBC", "Group and hold", "LFT"],
                  meds="Pantoprazole 40mg BD x8 weeks",
                  plan=["2 units crossmatched, IV pantoprazole infusion.", "No further bleeding, Hb stable."]),
    "584.9": dict(reason=["Reduced urine output and swelling", "Rising creatinine and vomiting"], sym=["reduced urine, leg swelling", "nausea, oliguria"],
                  sev=3, short="AKI", tests=["UEC", "VBG", "Ultrasound renal", "Urinalysis"],
                  meds="Withhold NSAIDs and ACE inhibitor; Furosemide 40mg daily",
                  plan=["Fluid balance chart commenced, nephrotoxins withheld.", "Creatinine improving."]),
    "585.9": dict(reason=["CKD review, for AV fistula", "Declining kidney function"], sym=["fatigue, itch", "leg swelling, tiredness"],
                  sev=2, short="CKD", tests=["UEC", "FBC", "Ultrasound renal"],
                  meds="Calcium carbonate 600mg TDS; Darbepoetin weekly; Amlodipine 5mg daily",
                  plan=["Renal team review, fistula planned.", "Electrolytes stable."]),
    "599.0": dict(reason=["Dysuria and fever", "Suprapubic pain and frequency"],
                  sym=["dysuria, frequency, fever", "burning urine, suprapubic pain"], sev=1, short="UTI",
                  tests=["Urinalysis", "Urine MCS", "FBC"], meds="Cefalexin 500mg BD x5 days",
                  plan=["Urine dipstick positive, antibiotics started.", "Afebrile, symptoms resolving."]),
    "715.35": dict(reason=["Chronic knee pain, for knee replacement", "Knee osteoarthritis, booked surgery"],
                   sym=["knee pain, stiffness", "difficulty walking, knee pain"], sev=1, short="knee OA",
                   tests=["X-ray knee", "FBC"], meds="Paracetamol 1g QID; Enoxaparin 40mg SC daily x14 days",
                   plan=["Pre-admission clinic complete.", "Day 2 post-op, mobilising with physio."]),
    "780.2": dict(reason=["Collapse at home", "Syncopal episode"], sym=["brief loss of consciousness", "dizzy then fainted"],
                  sev=2, short="syncope", tests=["ECG", "BSL", "FBC"], meds="No new medication",
                  plan=["ECG normal, telemetry overnight.", "No further episodes overnight."]),
    "780.39": dict(reason=["Seizure at home", "Witnessed tonic-clonic seizure"], sym=["seizure, post-ictal confusion", "jerking movements, tongue bite"],
                   sev=3, short="seizure", tests=["CT brain", "MRI brain", "UEC", "BSL"],
                   meds="Levetiracetam 500mg BD",
                   plan=["Loaded with levetiracetam, seizure precautions.", "No further seizures, alert and oriented."]),
    "786.50": dict(reason=["Chest pain, cause unclear", "Central chest discomfort"], sym=["chest pain", "chest discomfort, anxiety"],
                   sev=2, short="chest pain", tests=["ECG", "Troponin", "Chest X-ray"], meds="Pantoprazole 40mg daily; Paracetamol PRN",
                   plan=["Serial troponins negative.", "Pain settled, likely musculoskeletal."]),
    "820.8": dict(reason=["Fall at home, hip pain, unable to weight bear", "Hip injury after fall"],
                  sym=["hip pain, unable to weight bear", "right hip pain after fall"], sev=3, short="NOF fracture",
                  tests=["X-ray pelvis", "FBC", "Group and hold"],
                  meds="Paracetamol 1g QID; Enoxaparin 40mg SC daily x28 days",
                  plan=["Fascia iliaca block given, listed for theatre.", "Post-op, mobilising with frame."]),
    "850.9": dict(reason=["Head strike after motor vehicle crash", "Hit head, brief LOC"],
                  sym=["headache, brief loss of consciousness", "head injury, vomited once"], sev=2, short="concussion",
                  tests=["CT brain"], meds="Paracetamol 1g PRN",
                  plan=["GCS 15, neuro obs 2-hourly.", "Headache improving, no new deficits."]),
}
assert set(CLIN) == ICD_SET, "every dictionary code needs clinical info"

TESTS_IMG = {   # imaging tests: (modality, body site)
    "Chest X-ray": ("XR", "Chest"), "CT brain": ("CT", "Head"), "Ultrasound abdomen": ("US", "Abdomen"),
    "CT abdomen": ("CT", "Abdomen/Pelvis"), "CTPA": ("CT", "Chest"), "X-ray knee": ("XR", "Knee"),
    "X-ray pelvis": ("XR", "Pelvis/Hip"), "Ultrasound renal": ("US", "Kidneys"), "MRI brain": ("MRI", "Brain"),
    "Echocardiogram": ("US", "Heart"),
}
FINDINGS = {
    "Chest X-ray": {"486": "Right lower lobe consolidation consistent with pneumonia.", "428.0": "Cardiomegaly with bilateral pleural effusions.",
                    "518.81": "Bilateral diffuse airspace opacities.", "491.21": "Hyperinflated lungs, no focal consolidation.",
                    None: "No acute cardiopulmonary abnormality."},
    "CT brain": {"434.91": "Early hypodensity left MCA territory, no haemorrhage.", "850.9": "No intracranial haemorrhage. No skull fracture.",
                 None: "No acute intracranial abnormality."},
    "Ultrasound abdomen": {"574.00": "Gallstones with gallbladder wall thickening and positive sonographic Murphy's sign.",
                           "574.20": "Multiple gallstones, no wall thickening.", "540.9": "Non-compressible appendix 9 mm with free fluid.",
                           "577.0": "Bulky oedematous pancreas.", None: "Normal abdominal ultrasound."},
    "CT abdomen": {"577.0": "Peripancreatic fat stranding, no necrosis.", None: "No acute abdominal pathology."},
    "CTPA": {"415.19": "Filling defects in segmental pulmonary arteries consistent with PE.", None: "No pulmonary embolism."},
    "X-ray knee": {"715.35": "Medial compartment joint space narrowing with osteophytes.", None: "No bony injury."},
    "X-ray pelvis": {"820.8": "Displaced subcapital fracture of the right neck of femur.", None: "No fracture seen."},
    "Ultrasound renal": {"585.9": "Small echogenic kidneys bilaterally.", "584.9": "Normal sized kidneys, no hydronephrosis.",
                         None: "Normal renal ultrasound."},
    "MRI brain": {None: "No structural lesion identified."},
    "Echocardiogram": {"428.0": "LVEF 30%, global hypokinesis.", None: "Normal LV size and function."},
}
SURGERY = {     # icd -> [(procedure, probability, performer kind, day case?)]
    "540.9": [("Laparoscopic appendicectomy", 0.70, "surgeon", False), ("Open appendicectomy", 0.15, "surgeon", False)],
    "574.20": [("Laparoscopic cholecystectomy", 0.80, "surgeon", True)],
    "574.00": [("Laparoscopic cholecystectomy", 0.35, "surgeon", False)],
    "820.8": [("Hemiarthroplasty of hip", 0.45, "surgeon", False), ("Dynamic hip screw fixation", 0.40, "surgeon", False)],
    "715.35": [("Total knee replacement", 0.80, "surgeon", False)],
    "414.01": [("Coronary angiography and PCI", 0.65, "cardio", True)],
    "410.9": [("Primary PCI", 0.45, "cardio", False)],
    "585.9": [("AV fistula creation", 0.55, "surgeon", True)],
    "578.9": [("Gastroscopy with haemostasis", 0.50, "gastro", False)],
    "530.81": [("Diagnostic gastroscopy", 0.55, "gastro", True)],
    "038.9": [("Incision and drainage of abscess", 0.10, "surgeon", False)],
    "518.81": [("Tracheostomy", 0.08, "surgeon", False)],
    "850.9": [("Repair of scalp laceration", 0.20, "surgeon", False)],
}
OUTCOMES = ["No complications"] * 6 + ["Uneventful recovery"] * 3 + [
    "Minor bleeding, controlled intra-op", "Post-op fever, treated", "Superficial wound infection, oral antibiotics", "Converted to open procedure"]

TYPE_ICDS = {
    "emergency": ["486", "038.9", "410.9", "428.0", "434.91", "518.81", "540.9", "578.9", "584.9", "780.39", "786.50",
                  "820.8", "850.9", "427.31", "493.92", "491.21", "415.19", "276.51", "780.2", "577.0", "574.00"],
    "urgent": ["599.0", "276.51", "574.00", "427.31", "285.9", "584.9", "493.92", "486", "786.50", "780.2", "401.9"],
    "elective": ["715.35", "574.20", "414.01", "585.9", "530.81", "250.00"],
    "outpatient": ["401.9", "250.00", "272.4", "244.9", "530.81", "305.1", "285.9", "599.0"],
}
MIN_AGE = {"715.35": 40, "414.01": 35, "410.9": 30, "428.0": 30, "434.91": 30, "491.21": 40, "585.9": 25,
           "272.4": 25, "305.1": 16, "820.8": 45, "427.31": 30, "415.19": 18, "250.00": 12, "401.9": 18}
ICU_FOR = {"038.9": "MICU", "518.81": "MICU", "410.9": "CCU", "427.31": "CCU", "428.0": "CCU",
           "434.91": "ICU", "415.19": "ICU", "577.0": "ICU", "578.9": "MICU"}
DEATH_RISK = {"038.9": .12, "518.81": .14, "410.9": .08, "428.0": .07, "434.91": .09, "415.19": .05, "578.9": .05}
COMORB = [("401.9", .35), ("250.00", .17), ("272.4", .20), ("305.1", .10), ("285.9", .06),
          ("585.9", .05), ("244.9", .06), ("427.31", .06)]
CHRONIC_MEDS = {"401.9": "Perindopril 5mg daily", "250.00": "Metformin XR 1g nocte", "272.4": "Atorvastatin 20mg nocte",
                "244.9": "Levothyroxine 100mcg mane", "427.31": "Apixaban 5mg BD", "585.9": "Calcium carbonate 600mg TDS",
                "285.9": "Ferrous sulfate 325mg daily"}
ALLERGENS = ["Penicillin", "Sulfonamides", "Aspirin", "Morphine", "Codeine", "Peanuts", "Latex", "Ibuprofen", "Cephalosporins", "Shellfish"]
NEWBORN_REASON = {"038.9": "Neonate with fever and poor feeding", "486": "Neonate with tachypnoea",
                  "276.51": "Neonate feeding poorly, dehydrated", "285.9": "Neonate pallor",
                  None: "Well baby, born at Coral Coast"}

# =============================================================================
# People and places (fictional combinations)
# =============================================================================
SURNAMES = ["Smith", "Jones", "Williams", "Brown", "Wilson", "Taylor", "Nguyen", "Johnson", "Martin", "White", "Anderson",
            "Walker", "Thompson", "Thomas", "Lee", "Ryan", "Kelly", "Harris", "King", "Campbell", "Chen", "Wang", "Singh",
            "Patel", "Kaur", "Tran", "Le", "O'Brien", "O'Connor", "McDonald", "MacKenzie", "Murphy", "Robinson", "Clarke",
            "Hughes", "Edwards", "Mitchell", "Young", "Scott", "Wright", "Green", "Hall", "Baker", "Cooper", "Morris",
            "Rossi", "Russo", "Papadopoulos", "Nikolaidis", "Kowalski", "Haddad", "Khoury", "Nakamura", "Kim", "Park",
            "Fernando", "Silva", "Ahmed", "Ali", "Stewart", "Watson", "Bennett", "Fitzgerald", "Van der Berg", "D'Souza"]
FIRST_M = ["Jack", "Oliver", "William", "Noah", "Thomas", "James", "Lucas", "Henry", "Liam", "Ethan", "Samuel", "Daniel",
           "Matthew", "Joshua", "Benjamin", "Ryan", "Andrew", "David", "Michael", "Peter", "Mark", "Paul", "Stephen", "Raj",
           "Minh", "Wei", "Omar", "Luca", "Hamish", "Lachlan", "Cooper", "Harrison", "Angus", "Callum", "Dimitri"]
FIRST_F = ["Charlotte", "Olivia", "Amelia", "Isla", "Mia", "Ava", "Grace", "Chloe", "Sophie", "Emily", "Ruby", "Zoe",
           "Hannah", "Jessica", "Sarah", "Emma", "Rebecca", "Michelle", "Karen", "Linda", "Margaret", "Priya", "Mai",
           "Ling", "Fatima", "Giulia", "Eleni", "Mei", "Siobhan", "Matilda", "Harper", "Georgia", "Leilani", "Anh", "Bronwyn"]
SUBURBS = [("Coral Heights", "2481"), ("Banksia Point", "2483"), ("Pelican Shores", "2478"), ("Driftwood Park", "2486"),
           ("Saltwater Flats", "2489"), ("Reefton", "2480"), ("Tidewater", "2484"), ("Sandpiper Beach", "2487"),
           ("Bluegum Ridge", "2482"), ("Ironbark Downs", "2479"), ("Kookaburra Hill", "2485"), ("Lighthouse Point", "2488"),
           ("Mangrove Bend", "2477"), ("Turtle Cove", "2490")]
STREETS = ["Banksia St", "Ocean Pde", "Marine Dr", "Wattle Ave", "Jacaranda Cres", "Reef Rd", "Shell Cl", "Frangipani Way",
           "Dune St", "Coastal Hwy", "Lagoon Rd", "Pandanus Ct", "Seagull Lane", "Tern Pl", "Mariner Blvd"]
RELATIONS = ["Mother", "Father", "Spouse", "Partner", "Brother", "Sister", "Son", "Daughter", "Friend", "Guardian"]
FUNDING = ["Medicare (public)"] * 7 + ["Private health insurance"] * 3 + [
    "DVA", "Workers compensation", "Overseas visitor (OVHC)", "Self-funded", "Motor accident (CTP)"]
SOURCES = {
    "emergency": ["Self-presented", "Self-presented", "Ambulance", "Ambulance", "GP referral", "Police", "Inter-hospital transfer"],
    "urgent": ["GP referral", "Self-presented", "Specialist referral", "Urgent care clinic"],
    "elective": ["Elective surgery waitlist", "Specialist rooms"],
    "outpatient": ["Outpatient clinic", "GP referral"],
    "newborn": ["Born at Coral Coast"],
}
WARDS = ["Ward 3 North", "Ward 3 South", "Ward 4A", "Ward 4B", "Ward 5 (Surgical)", "Ward 6 (Medical)", "Ward 7 (Ortho)"]

# =============================================================================
# Source D's own category labels: canonical -> (usual label, [other labels seen])
# =============================================================================
LABELS = {
    "sex": {"M": ("M", ["Male", "male"]), "F": ("F", ["Female", "female"])},
    "adm_type": {"emergency": ("ED", ["Emergency", "EMERG", "Emerg Dept"]),
                 "urgent": ("Urgent", ["UCC", "Urgent Care"]),
                 "elective": ("Elective", ["Planned", "Booked Elective"]),
                 "outpatient": ("Outpatient Clinic", ["OPD", "Clinic", "Non-admitted"]),
                 "newborn": ("Birth", ["Newborn", "Neonatal"])},
    "adm_status": {"discharged": ("Separated", ["Discharged", "D/C", "Completed"]),
                   "active": ("Current", ["Admitted", "In Progress", "Inpatient"]),
                   "deceased": ("Died", ["Deceased", "Died in hospital"])},
    "diag_type": {"primary": ("Principal", ["Principal Dx", "P", "PRIMARY"]),
                  "secondary": ("Additional", ["Comorbidity", "Secondary", "A"])},
    "order_status": {"pending": ("requested", ["ordered", "Pending"]),
                     "in_progress": ("in-progress", ["collected", "In Lab"]),
                     "completed": ("final", ["resulted", "Complete"]),
                     "cancelled": ("cancelled", ["canceled", "CXL"])},
    "priority": {"routine": ("routine", ["R", "Routine"]), "urgent": ("urgent", ["URG", "U"]),
                 "stat": ("stat", ["STAT", "Immediate"])},
    "exam_status": {"completed": ("reported", ["final", "Completed"]), "scheduled": ("booked", ["scheduled", "Booked"]),
                    "cancelled": ("cancelled", ["canceled"])},
    "modality": {"XR": ("XR", ["X-Ray", "Plain film", "DX"]), "CT": ("CT", ["CT Scan"]),
                 "US": ("US", ["Ultrasound", "USS"]), "MRI": ("MR", ["MRI"])},
    "unit": {"ED": ("ED", ["Emergency", "Emergency Dept"]), "RESUS": ("Resus", ["Resus Bay"]),
             "ICU": ("ICU", ["Intensive Care", "GICU"]), "CCU": ("CCU", ["Coronary Care"]),
             "MICU": ("MICU", ["Medical ICU"]), "SICU": ("SICU", ["Surgical ICU", "Post-op ICU"]),
             "WARD": ("Inpatient Ward", ["Ward", "Gen Med", "Medical Ward", "Surgical Ward"])},
}
UNIT_STD = {"ED": "Emergency Department", "RESUS": "Emergency Department", "ICU": "ICU", "CCU": "CCU", "MICU": "MICU",
            "SICU": "SICU", "WARD": "General Ward"}
ATS_STD = {1: "high", 2: "high", 3: "medium", 4: "low", 5: "low"}
LABEL_VARIANT_P = 0.06
UNMAPPABLE = {"encounterClass": ["Transfer In", "Other", "Mental Health Act"], "atsCategory": ["Cat 6", "Not triaged", "Cat 0"],
              "rank": ["Provisional", "Rule out"], "status_order": ["on-hold", "entered-in-error"],
              "priority": ["asap", "timed"], "status_exam": ["DNA", "on-hold"],
              "unit": ["HDU", "PACU", "Hospital in the Home"]}
NONE_ALLERGY = ["none", "NKA", "nil known", "Nil known", "NKDA", "None"]
NONE_MEDS = ["none", "nil known", "Nil", "None", "NKA"]


class Raw:
    """A literal raw JSON value the renderer must output untouched (invalid numbers, fake codes)."""
    def __init__(self, v):
        self.v = v


OMIT = object()       # "this key is missing from the JSON object"


# =============================================================================
# Small helpers
# =============================================================================
def wchoice(pairs):
    r, acc = rng.random() * sum(w for _, w in pairs), 0.0
    for v, w in pairs:
        acc += w
        if r <= acc:
            return v
    return pairs[-1][0]


def rdt(a, b):
    span = int((b - a).total_seconds() // 60)
    return fx(a + dt.timedelta(minutes=rng.randint(0, max(span, 0))))


def end_of(adm):
    return adm["discharge"] if adm["discharge"] else CUTOFF


def within(adm, lo, hi):
    s, e = adm["admit"], end_of(adm)
    t = s + dt.timedelta(seconds=(e - s).total_seconds() * rng.uniform(lo, hi))
    t = fx(t.replace(second=0, microsecond=0))
    if t <= s:
        t = s + dt.timedelta(minutes=2)
    if t >= e:
        t = e - dt.timedelta(minutes=1)
    return fx(t)


def age_on(dob, when):
    d = when.date() if isinstance(when, dt.datetime) else when
    return d.year - dob.year - ((d.month, d.day) < (dob.month, dob.day))


def phone_digits():
    return rng.choice(["5550", "7010"]) + f"{rng.randint(0, 9999):04d}"


# =============================================================================
# 1) Canonical (clean, internally consistent) data
# =============================================================================
STAFF_PLAN = [  # (designation, kind, departments, count)
    ("Emergency Physician", "doctor", ["Emergency"], 6),
    ("Emergency Registrar", "doctor", ["Emergency"], 5),
    ("Resident Medical Officer", "doctor", ["General Medicine", "Emergency", "Surgery"], 8),
    ("Consultant Physician", "doctor", ["General Medicine", "Cardiology", "Respiratory", "Renal"], 7),
    ("Medical Registrar", "doctor", ["General Medicine", "Cardiology"], 5),
    ("Paediatrician", "doctor", ["Paediatrics"], 2),
    ("General Surgeon", "surgeon", ["General Surgery"], 3),
    ("Orthopaedic Surgeon", "surgeon", ["Orthopaedics"], 2),
    ("Surgical Registrar", "surgeon", ["General Surgery", "Orthopaedics"], 3),
    ("Interventional Cardiologist", "cardio", ["Cardiology"], 2),
    ("Gastroenterologist", "gastro", ["Gastroenterology"], 2),
    ("Registered Nurse", "nurse", ["Emergency", "Medical Ward", "Surgical Ward", "ICU"], 16),
    ("Clinical Nurse Specialist", "nurse", ["Emergency", "ICU"], 5),
    ("Enrolled Nurse", "nurse", ["Medical Ward", "Surgical Ward"], 6),
    ("Midwife", "nurse", ["Maternity"], 3),
    ("Medical Imaging Technologist", "radiographer", ["Medical Imaging"], 5),
    ("Sonographer", "sonographer", ["Medical Imaging"], 2),
    ("Radiologist", "radiologist", ["Medical Imaging"], 3),
    ("Medical Scientist", "lab", ["Pathology"], 3),
    ("Ward Clerk", "admin", ["Administration"], 3),
]
staff = []
_used_names = set()
for desig, kind, depts, cnt in STAFF_PLAN:
    for _ in range(cnt):
        while True:
            sex = rng.choice("MF")
            nm = f"{rng.choice(FIRST_M if sex == 'M' else FIRST_F)} {rng.choice(SURNAMES)}"
            if nm not in _used_names:
                _used_names.add(nm)
                break
        hon = "Dr" if kind in ("doctor", "surgeon", "cardio", "gastro", "radiologist") else rng.choice(["Mr", "Ms", "Mx"] if sex == "M" else ["Ms", "Mrs", "Miss"])
        if hon == "Mx" and rng.random() < .8:
            hon = "Mr"
        staff.append(dict(honorific=hon, fullName=nm, designation=desig, department=rng.choice(depts),
                          employmentType=wchoice([("Full-time", .6), ("Part-time", .2), ("Casual", .08), ("VMO", .12 if kind in ("surgeon", "cardio", "gastro") else 0)]),
                          active=rng.random() > .05, _kind=kind))
rng.shuffle(staff)
for i, s in enumerate(staff, 1):
    s["practitionerId"] = i
BY_KIND = defaultdict(list)
for s in staff:
    BY_KIND[s["_kind"]].append(s["practitionerId"])
_weights = {s["practitionerId"]: rng.uniform(0.3, 3.0) for s in staff}


def prof(kind):
    return wchoice([(i, _weights[i]) for i in BY_KIND[kind]])


# ---------------- patients and admissions ----------------
# A few emergency admissions are placed on the nights daylight saving starts/ends, so an overnight
# nursing note can fall in the skipped or repeated hour (see the DST notes below).
FORCED_DST = [(k, d) for k, d in DST_NIGHTS for _ in range(2)]
patients, admissions = [], []
_name_dob = set()
for pi in range(N_PATIENTS):
    sex = rng.choice("MF")
    forced = FORCED_DST[pi] if pi < len(FORCED_DST) else None
    newborn = (not forced) and rng.random() < 0.05
    if forced:
        first_admit = dt.datetime.combine(forced[1] - dt.timedelta(days=1), dt.time(rng.randint(18, 22), rng.choice([5, 20, 35, 50])))
    else:
        first_admit = rdt(START, CUTOFF - dt.timedelta(days=2))
    if newborn:
        dob = first_admit.date()
    else:
        u = rng.random()
        age = rng.randint(1, 17) if u < 0.13 else (rng.randint(18, 64) if u < 0.66 else rng.randint(65, 94))
        if forced:
            age = rng.randint(30, 88)
        dob = first_admit.date() - dt.timedelta(days=age * 365 + rng.randint(0, 364))
    while True:
        first = rng.choice(FIRST_M if sex == "M" else FIRST_F)
        last = rng.choice(SURNAMES)
        middle = rng.choice(FIRST_M if sex == "M" else FIRST_F) if rng.random() < 0.15 else None
        if middle == first:
            middle = None
        key = (f"{first} {middle or ''} {last}".lower(), dob)
        if key not in _name_dob:
            _name_dob.add(key)
            break
    age_now = age_on(dob, CUTOFF)
    comorb = [c for c, p in COMORB if age_now >= 40 and rng.random() < p] if not newborn else []
    if 18 <= age_now < 40 and rng.random() < 0.08:
        comorb.append("305.1")
    u = rng.random()
    allergies = [] if u < 0.72 else rng.sample(ALLERGENS, 1 if u < 0.94 else 2)
    nok_rel = rng.choice(["Mother", "Father"]) if age_now < 18 else rng.choice(RELATIONS)
    nok_first = rng.choice(FIRST_F if nok_rel in ("Mother", "Sister", "Daughter") else
                           FIRST_M if nok_rel in ("Father", "Brother", "Son") else FIRST_M + FIRST_F)
    sub, pc = rng.choice(SUBURBS)
    p = dict(patientName=(first, middle, last), dob=dob, sex=sex,
             address=dict(line=f"{rng.choice(['', '', '', f'Unit {rng.randint(1, 24)}/'])}{rng.randint(1, 240)} {rng.choice(STREETS)}",
                          suburb=sub, state="NSW", postcode=pc),
             phone=None if age_now < 14 else phone_digits(),
             nextOfKin=(f"{nok_first} {last if nok_rel in ('Mother', 'Father', 'Spouse', 'Brother', 'Sister', 'Son', 'Daughter') and rng.random() < .8 else rng.choice(SURNAMES)}",
                        nok_rel, phone_digits()),
             deceased=False, _first=first_admit, _comorb=comorb, _allergies=allergies, _adms=[])
    patients.append(p)

    n_adm = 1 if forced else wchoice([(1, .70), (2, .20), (3, .10)])
    t = first_admit
    for k in range(n_adm):
        a_age = age_on(dob, t)
        day_case = False
        if forced:
            typ = "emergency"
        elif newborn and k == 0:
            typ = "newborn"
        else:
            w = {"emergency": .45, "urgent": .17, "elective": .20 if a_age >= 18 else .05, "outpatient": .18}
            typ = wchoice(list(w.items()))
            if typ == "elective":
                t = t.replace(hour=rng.randint(6, 10), minute=rng.choice([0, 15, 30, 45]))
            elif typ == "outpatient":
                t = t.replace(hour=rng.randint(8, 15), minute=rng.randint(0, 59))
        t = fx(t)
        if typ == "newborn":
            icd = None if rng.random() < .5 else rng.choice(["038.9", "486", "276.51", "285.9"])
        else:
            cands = [c for c in TYPE_ICDS[typ] if a_age >= MIN_AGE.get(c, 0)]
            icd = rng.choice(cands)
        sev = CLIN[icd]["sev"] if icd else 1
        hours = {"outpatient": lambda: rng.uniform(1.5, 6), "newborn": lambda: rng.uniform(24, 96),
                 "elective": lambda: rng.uniform(24, 144), "urgent": lambda: rng.uniform(10, 110),
                 "emergency": lambda: rng.uniform(*{1: (6, 40), 2: (20, 110), 3: (40, 280)}[sev])}[typ]()
        icu = None
        if typ == "emergency" and icd in ICU_FOR and rng.random() < .45:
            icu, hours = ICU_FOR[icd], max(hours, 60)
        if typ == "newborn" and icd in ("038.9", "486") and rng.random() < .5:
            icu, hours = "ICU", max(hours, 72)
        surg = None
        if icd in SURGERY and typ != "outpatient":
            r, acc = rng.random(), 0
            for name_s, pr, pkind, day in SURGERY[icd]:
                acc += pr
                if r < acc:
                    surg = (name_s, pkind)
                    if typ == "elective" and day and rng.random() < .7:
                        day_case = True
                    break
            if surg:
                hours = rng.uniform(4, 9) if day_case else max(hours, 30)
        if forced:
            hours = max(hours, 34)
        dis = fx((t + dt.timedelta(hours=hours)).replace(second=0, microsecond=0))
        status = "discharged"
        if not forced and (dis > CUTOFF or ((CUTOFF - t).days < 12 and rng.random() < .6)):
            dis, status = None, "active"
        elif icd in DEATH_RISK and rng.random() < DEATH_RISK[icd] + (.06 if a_age > 70 else 0):
            status = "deceased"
        secondaries = [c for c in p["_comorb"] if c != icd]
        rng.shuffle(secondaries)
        secondaries = secondaries[:rng.randint(0, 2)]
        adm = dict(p=p, admit=t.replace(second=0, microsecond=0), discharge=dis, status=status, type=typ, icd=icd,
                   sev=sev, icu=icu, surg=surg, day_case=day_case, secondaries=secondaries,
                   dst=forced, prof=prof(surg[1]) if (typ == "elective" and surg) else prof("doctor"))
        admissions.append(adm)
        p["_adms"].append(adm)
        if status != "discharged":
            if status == "deceased":
                p["deceased"] = True
            break
        t = dis + dt.timedelta(days=rng.randint(10, 420), hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
        if t > CUTOFF - dt.timedelta(hours=6):
            break

patients.sort(key=lambda p: p["_first"])
for i, p in enumerate(patients, 1):
    p["patientId"] = i
admissions.sort(key=lambda a: a["admit"])
for i, a in enumerate(admissions, 1):
    a["id"] = i
    a["patkey"] = a["p"]["patientId"]          # which patient object it is nested under (may change: near duplicates)

adm_rows = []
for a in admissions:
    reason = NEWBORN_REASON[a["icd"]] if a["type"] == "newborn" else rng.choice(CLIN[a["icd"]]["reason"])
    adm_rows.append(dict(admissionId=a["id"], patientId=OMIT, admittedAt=a["admit"], encounterClass=a["type"],
                         presentingProblem=reason, admittingClinicianId=a["prof"],
                         referralSource=rng.choice(SOURCES[a["type"]]), fundingSource=rng.choice(FUNDING),
                         separatedAt=a["discharge"], episodeStatus=a["status"], _adm=a))

# ---------------- child entities ----------------
triage, diags, notes, orders, exams, procs, stays, seps = ([] for _ in range(8))


def vitals(a):
    icd, nb = a["icd"], a["type"] == "newborn"
    if nb:
        return dict(bp=(rng.randint(60, 80), rng.randint(35, 50)), hr=rng.randint(115, 165), rr=rng.randint(35, 60),
                    temp=round(rng.uniform(38.0, 39.4) if icd in ("038.9", "486") else rng.uniform(36.5, 37.4), 1),
                    spo2=rng.randint(88, 94) if icd == "486" else rng.randint(95, 100)), None
    sbp, dbp = rng.randint(105, 138), rng.randint(64, 88)
    if icd == "401.9" or "401.9" in a["secondaries"]:
        sbp, dbp = rng.randint(148, 188), rng.randint(90, 112)
    if icd in ("038.9", "578.9"):
        sbp, dbp = rng.randint(78, 102), rng.randint(42, 62)
    temp = rng.uniform(38.0, 40.2) if icd in ("038.9", "486", "599.0", "574.00") else rng.uniform(36.2, 37.4)
    hr = rng.randint(102, 142) if icd in ("038.9", "578.9", "427.31", "415.19") else rng.randint(60, 99)
    rr = rng.randint(22, 34) if icd in ("486", "518.81", "428.0", "491.21", "493.92", "415.19") else rng.randint(12, 20)
    spo2 = rng.randint(82, 93) if icd in ("486", "518.81", "491.21", "415.19", "428.0") else rng.randint(95, 100)
    pain = rng.randint(6, 10) if icd in ("410.9", "540.9", "820.8", "577.0", "574.00", "786.50", "415.19") else rng.randint(0, 4)
    return dict(bp=(sbp, dbp), hr=hr, rr=rr, temp=round(temp, 1), spo2=spo2), pain


for a in admissions:
    p, icd, typ = a["p"], a["icd"], a["type"]
    base = dict(_adm=a)
    # triage (ATS category 1-5)
    if rng.random() < {"emergency": 1, "urgent": 1, "newborn": .45, "elective": .25, "outpatient": .3}[typ]:
        sev = a["sev"]
        ats = wchoice({3: [(1, .2), (2, .65), (3, .15)], 2: [(2, .15), (3, .6), (4, .25)],
                       1: [(3, .15), (4, .55), (5, .3)]}[sev]) if icd else 5
        meds = [CHRONIC_MEDS[c] for c in p["_comorb"] if c in CHRONIC_MEDS]
        v, pain = vitals(a)
        triage.append(dict(base, triagedAt=fx(min(a["admit"] + dt.timedelta(minutes=rng.randint(3, 35)), end_of(a) - dt.timedelta(minutes=1))),
                           triageNurseId=prof("nurse"), atsCategory=ats, vitals=v, painScore=pain,
                           symptoms=(rng.choice(CLIN[icd]["sym"]) if icd else "routine newborn check"),
                           allergies=(list(p["_allergies"]) if p["_allergies"] else "NONE"),
                           currentMeds=(meds if meds else "NONE")))
    # diagnoses
    if icd:
        diags.append(dict(base, patientId=None, icd9=icd, rank="primary", diagnosedBy=rng.choice([a["prof"], prof("doctor")]),
                          diagnosedAt=within(a, .01, .25)))
    for c in a["secondaries"]:
        diags.append(dict(base, patientId=None, icd9=c, rank="secondary", diagnosedBy=prof("doctor"), diagnosedAt=within(a, .05, .6)))
    # clinical notes
    days = (end_of(a) - a["admit"]).total_seconds() / 86400
    n_notes = (1 if rng.random() < .4 else 0) if typ == "outpatient" else max(0, 1 + min(3, int(days // 2)) - rng.randint(0, 1))
    if a["day_case"]:
        n_notes = rng.randint(1, 2)
    for j in range(n_notes):
        ntype = ("ED Clinician Note" if typ == "emergency" and rng.random() < .5 else "Admission Note") if j == 0 else \
            rng.choice(["Progress Note", "Ward Round", "Nursing Note"])
        if j == n_notes - 1 and j >= 1 and a["status"] == "discharged" and (j >= 2 or a["day_case"]):
            ntype = "Discharge Summary"
        base_txt = (rng.choice(CLIN[icd]["plan"]) if icd else "Baby feeding well, mother supported with breastfeeding.")
        if ntype in ("Admission Note", "ED Clinician Note"):
            txt = f"Presented with {(rng.choice(CLIN[icd]['sym']) if icd else 'no concerns')}. Impression: {CLIN[icd]['short'] if icd else 'well newborn'}. {base_txt}"
        elif ntype == "Nursing Note":
            txt = rng.choice(["Obs stable, patient comfortable, slept well.", "4-hourly obs attended, no concerns.",
                              "Pt states \"feeling much better today\", eating and drinking well.", "IVC resited L forearm, fluids running.",
                              "Falls risk assessment done, bed alarm on."])
        elif ntype == "Discharge Summary":
            txt = f"Clinically improved. {base_txt} Medications reconciled, GP letter sent."
        else:
            txt = base_txt if rng.random() < .6 else f"Reviewed on ward round, comfortable. {base_txt} Plan: continue current management."
        if rng.random() < .08:
            txt = f"S: {(rng.choice(CLIN[icd]['sym']) if icd else 'feeding well')}\nO: obs within normal limits\nA: {CLIN[icd]['short'] if icd else 'well baby'}\nP: {base_txt}"
        lo, hi = (0.0, .1) if j == 0 else ((j / max(n_notes, 1)) * .9, min(.98, ((j + 1) / max(n_notes, 1))))
        notes.append(dict(base, noteType=ntype, authorId=prof("nurse") if ntype == "Nursing Note" else prof("doctor"),
                          writtenAt=within(a, lo, hi), body=txt))
    if a["dst"]:                       # overnight nursing note in the skipped / repeated hour
        kind, d = a["dst"]
        local = dt.datetime.combine(d, dt.time(2, rng.choice([5, 12, 20, 33, 41, 48, 55])))
        fold = rng.choice([0, 1]) if kind == "overlap" else 0
        local = local.replace(fold=fold)
        notes.append(dict(base, noteType="Nursing Note", authorId=prof("nurse"), writtenAt=fx(local),
                          body=rng.choice(["Overnight obs stable, pt sleeping.", "Pt woke overnight, analgesia given, settled.",
                                           "Night check: obs within normal limits, IV fluids running."]),
                          _dst=(kind, local)))
    # diagnostic orders (+ imaging)
    tests = list(CLIN[icd]["tests"]) if icd else []
    if typ == "newborn" and icd:
        tests = ["FBC", "Blood cultures"] + (["Chest X-ray"] if icd == "486" else [])
    k = min(len(tests), wchoice([(0, .5), (1, .4), (2, .1)]) if typ == "outpatient" else wchoice([(0, .25), (1, .45), (2, .30)]))
    chosen = rng.sample(tests, k)
    if typ in ("emergency", "urgent") and icd and rng.random() < .08:        # walk-in imaging without an order
        img = [t_ for t_ in tests if t_ in TESTS_IMG and t_ not in chosen]
        if img:
            mod, body = TESTS_IMG[img[0]]
            exams.append(dict(base, orderRef=None, modality=mod, bodySite=body, referrerId=a["prof"],
                              radiographerId=prof("sonographer" if mod == "US" else "radiographer"),
                              performedAt=within(a, .02, .2), status="completed",
                              imageUrl=f"https://pacs.coralcoast.example/viewer?study=CC{rng.randint(100000, 999999)}",
                              report=FINDINGS[img[0]].get(icd, FINDINGS[img[0]][None])))
    for tname in chosen:
        sev = a["sev"]
        prio = wchoice({3: [("stat", .5), ("urgent", .4), ("routine", .1)], 2: [("urgent", .5), ("routine", .4), ("stat", .1)],
                        1: [("routine", .85), ("urgent", .15)]}[sev])
        if a["status"] == "active":
            st = wchoice([("pending", .5), ("in_progress", .35), ("completed", .15)])
        else:
            st = wchoice([("completed", .86), ("cancelled", .06), ("pending", .04), ("in_progress", .04)])
        short = CLIN[icd]["short"]
        reason = rng.choice([f"?{short}", f"Rule out {short}", f"Suspected {short}", f"Assess {short}",
                             f"Monitoring - {short}", f"Known {short}, baseline"])
        req_t = within(a, .0, .35)
        o = dict(base, testName=tname, indication=reason, status=st, priority=prio,
                 orderedBy=rng.choice([a["prof"], prof("doctor")]), orderedAt=req_t)
        orders.append(o)
        if tname in TESTS_IMG:
            ex_st = {"completed": "completed", "in_progress": "scheduled", "pending": "scheduled"}.get(st)
            if st == "cancelled":
                ex_st = "cancelled" if rng.random() < .4 else None
            if st == "pending" and a["status"] != "active":
                ex_st = "cancelled" if rng.random() < .5 else None
            if ex_st:
                e_end = end_of(a) if a["status"] != "active" else CUTOFF + dt.timedelta(days=2)
                gap = (e_end - req_t).total_seconds()
                ex_t = fx((req_t + dt.timedelta(seconds=gap * rng.uniform(.05, .5))).replace(second=0, microsecond=0))
                if ex_t <= req_t:
                    ex_t = fx(req_t + dt.timedelta(minutes=10))
                mod, body = TESTS_IMG[tname]
                done = ex_st == "completed"
                exams.append(dict(base, orderRef=o, modality=mod, bodySite=body, referrerId=o["orderedBy"],
                                  radiographerId=prof("sonographer" if mod == "US" else "radiographer"),
                                  performedAt=ex_t, status=ex_st,
                                  imageUrl=f"https://pacs.coralcoast.example/viewer?study=CC{rng.randint(100000, 999999)}" if done else None,
                                  report=FINDINGS[tname].get(icd, FINDINGS[tname][None]) if done else None))
    # procedures
    if a["surg"]:
        if typ == "elective":
            op_t = min(a["admit"] + dt.timedelta(hours=rng.uniform(1, 3) if a["day_case"] else rng.uniform(2, 6)),
                       end_of(a) - dt.timedelta(hours=2)).replace(second=0, microsecond=0)
        else:
            op_t = within(a, .05, .3)
        procs.append(dict(base, procedureName=a["surg"][0], surgeonId=prof(a["surg"][1]), startedAt=fx(op_t),
                          outcome=rng.choice(OUTCOMES)))
    # ward stays
    units = []
    hrs = (end_of(a) - a["admit"]).total_seconds() / 3600
    if typ == "emergency":
        if rng.random() < .75 or hrs < 12:
            units.append("RESUS" if a["sev"] == 3 and rng.random() < .35 else "ED")
        if a["icu"]:
            units.append(a["icu"])
        if hrs >= 12:
            units.append("WARD")
        if a["surg"] and rng.random() < .2 and "WARD" in units:
            units += ["SICU", "WARD"]
    elif typ == "urgent":
        units = (["ED"] if rng.random() < .3 else []) + ["WARD"]
    elif typ == "elective":
        units = ["WARD"] + (["SICU", "WARD"] if a["surg"] and not a["day_case"] and rng.random() < .25 else [])
    elif typ == "outpatient":
        units = ["WARD"] if rng.random() < .3 else []
    else:
        units = ["WARD"] + (["ICU"] if a["icu"] else [])
    if units:
        w = [{"ED": .08, "RESUS": .05}.get(u_, .35 if u_ != "WARD" else 1.0) for u_ in units]
        tot = sum(w)
        bounds, acc = [a["admit"]], 0
        for wi in w[:-1]:
            acc += wi
            bounds.append(fx((a["admit"] + dt.timedelta(seconds=(end_of(a) - a["admit"]).total_seconds() * acc / tot)).replace(second=0, microsecond=0)))
        bounds.append(a["discharge"])
        prev = None
        for j, u_ in enumerate(units):
            entry = fx(bounds[j] + dt.timedelta(minutes=rng.randint(0, 12) if j == 0 else 0))
            ex = bounds[j + 1]
            if ex is not None and ex <= entry:
                ex = fx(entry + dt.timedelta(minutes=30))
            if j == 0:
                reason = None if rng.random() < .7 else ("Admitted from pre-admission clinic" if typ in ("elective", "outpatient") else "Initial bed allocation")
            elif u_ in ("ICU", "MICU", "CCU"):
                reason = rng.choice(["MET call, deteriorating", "Requires ventilatory support", "Haemodynamically unstable, needs inotropes"])
            elif u_ == "SICU":
                reason = "Post-operative monitoring"
            elif prev in ("ED", "RESUS"):
                reason = rng.choice(["Admitted under inpatient team", "Stable for ward"])
            else:
                reason = rng.choice(["Stepped down, clinically stable", "Improving, transferred to ward"])
            if u_ in ("ED", "RESUS"):
                loc = ("ED", f"{'Resus' if u_ == 'RESUS' else 'Cubicle'} {rng.randint(1, 4 if u_ == 'RESUS' else 22)}")
            elif u_ == "WARD":
                loc = ("Maternity Ward" if typ == "newborn" else ("Day Surgery Unit" if a["day_case"] else rng.choice(WARDS)), f"Room {rng.randint(1, 30)}")
            else:
                loc = (u_, f"Pod {rng.choice('ABCD')}")
            bed = rng.choice([f"Bed {rng.randint(1, 30)}", str(rng.randint(1, 30)), f"{rng.randint(1, 30)}{rng.choice('AB')}"])
            stays.append(dict(base, unit=u_, location=loc, bed=bed, clinicianId=prof("doctor"), startAt=entry, endAt=ex, transferReason=reason))
            prev = u_
    # separation (discharge record)
    if a["status"] in ("discharged", "deceased"):
        dead = a["status"] == "deceased"
        appts = []
        if not dead and rng.random() < .6:
            for _ in range(rng.randint(1, 2)):
                nxt = (a["discharge"] + dt.timedelta(days=rng.randint(7, 42))).replace(hour=rng.choice([8, 9, 10, 13, 14, 15]),
                                                                                      minute=rng.choice([0, 15, 30, 45]))
                appts.append((rng.choice(["Cardiology OPD", "Fracture clinic", "General Medicine clinic", "Surgical OPD",
                                          "Renal clinic", "Wound clinic", "GP"]), fx(nxt)))
        seps.append(dict(
            base, separatedAt=a["discharge"], authorisedBy=rng.choice([a["prof"], prof("doctor")]),
            separationMode="Died" if dead else wchoice([("Discharged home", .62), ("Usual residence", .12),
                                                       ("Transferred to another hospital", .07), ("Residential aged care facility", .05),
                                                       ("Hospital in the Home", .04), ("Discharged against medical advice", .06),
                                                       ("Statistical discharge", .04)]),
            conditionAtSeparation="Deceased" if dead else rng.choice(["Improved", "Improved", "Stable", "Recovered", "Fair", "Unchanged"]),
            dischargeMeds=[] if dead else ((CLIN[icd]["meds"].split("; ")) if icd else ["Vitamin K given", "Hep B vaccine given"]),
            followUp=None if dead else rng.choice(["GP review in 1 week", "Return to ED if symptoms worsen",
                                                   "Outpatient review in 4-6 weeks", "Continue medications, specialist follow-up",
                                                   "Wound check with GP in 7-10 days"]),
            appointments=appts))

# Status disagreement: a separation record for an admission still marked "current"
_active = [a for a in admissions if a["status"] == "active"]
for a in rng.sample(_active, min(3, len(_active))):
    seps.append(dict(_adm=a, separatedAt=fx(min(CUTOFF - dt.timedelta(hours=1), a["admit"] + dt.timedelta(hours=rng.randint(20, 60)))),
                     authorisedBy=a["prof"], separationMode="Discharged home", conditionAtSeparation="Improved",
                     dischargeMeds=CLIN[a["icd"]]["meds"].split("; ") if a["icd"] else [], followUp="GP review in 1 week",
                     appointments=[], _pre={"status_conflict"}))


def assign_ids(rows, key, idcol):
    rows.sort(key=lambda r: utc_of(r[key]))
    for i, r in enumerate(rows, 1):
        r[idcol] = i


assign_ids(triage, "triagedAt", "triageId")
assign_ids(diags, "diagnosedAt", "diagnosisId")
assign_ids(notes, "writtenAt", "noteId")
assign_ids(orders, "orderedAt", "orderId")
assign_ids(exams, "performedAt", "examId")
assign_ids(procs, "startedAt", "procedureId")
assign_ids(stays, "startAt", "stayId")
assign_ids(seps, "separatedAt", "separationId")
for e in exams:
    if isinstance(e["orderRef"], dict):
        e["_order"] = e["orderRef"]
        e["orderRef"] = e["orderRef"]["orderId"]

pat_rows = [dict(patientId=p["patientId"], patientName=p["patientName"], dob=p["dob"], sex=p["sex"], address=p["address"],
                 phone=p["phone"], nextOfKin=p["nextOfKin"], deceased=p["deceased"], _p=p) for p in patients]
staff_rows = sorted([dict(practitionerId=s["practitionerId"], honorific=s["honorific"], fullName=s["fullName"],
                          designation=s["designation"], department=s["department"], employmentType=s["employmentType"],
                          active=s["active"], _kind=s["_kind"]) for s in staff], key=lambda r: r["practitionerId"])


# ---------------- consistency check of the canonical data (before any problem is injected) ----------------
def _verify():
    bad = []
    U = utc_of
    for a in admissions:
        if a["admit"].date() < a["p"]["dob"]:
            bad.append(("admission before dob", a["id"]))
        if a["discharge"] and U(a["discharge"]) < U(a["admit"]):
            bad.append(("discharge before admit", a["id"]))
    spans = [(triage, "triagedAt"), (diags, "diagnosedAt"), (notes, "writtenAt"), (orders, "orderedAt"),
             (procs, "startedAt"), (stays, "startAt")]
    for rows, k in spans:
        for r in rows:
            a = r["_adm"]
            if not (U(a["admit"]) <= U(r[k]) <= U(end_of(a))):
                bad.append((k, "outside admission", a["id"]))
    for e in exams:
        a = e["_adm"]
        if U(e["performedAt"]) < U(a["admit"]) or (a["discharge"] and U(e["performedAt"]) > U(a["discharge"])):
            bad.append(("exam outside admission", a["id"]))
        if e.get("_order") and U(e["performedAt"]) < U(e["_order"]["orderedAt"]):
            bad.append(("exam before order", a["id"]))
    for s in stays:
        if s["endAt"] and U(s["endAt"]) < U(s["startAt"]):
            bad.append(("stay exit before entry", s["stayId"]))
    for s in seps:
        if "_pre" not in s and s["separatedAt"] != s["_adm"]["discharge"]:
            bad.append(("separation time differs", s["separationId"]))
    for rows in (triage, diags, notes, orders, exams, procs, stays, seps):
        for r in rows:
            for k, v in r.items():
                if isinstance(v, dt.datetime) and in_gap(v):
                    bad.append(("time in DST gap", k))
    assert not bad, bad[:10]


_verify()

# =============================================================================
# 2) Rendering to Source D's raw JSON shapes
# =============================================================================
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_dt(t, tags):
    a = aware(t)
    r = rng.random()
    if r < 0.92:
        return a.isoformat(timespec="seconds")                    # 2025-03-14T09:30:00+11:00
    if r < 0.94:
        tags.add("fmt_date_iso_variant")
        k = rng.random()
        if k < .4:
            return a.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        if k < .7:
            return a.isoformat(timespec="milliseconds")
        return a.isoformat(timespec="minutes")
    if r < 0.975 and not in_overlap(t):
        tags.add("fmt_date_dayfirst")
        if rng.random() < .75:
            return t.strftime("%d/%m/%Y %H:%M")
        return f"{t.day}/{t.month}/{t.year} {t.hour % 12 or 12}:{t.minute:02d} {'am' if t.hour < 12 else 'pm'}"
    if r < 0.99:
        tags.add("fmt_date_unix")
        s = int(a.timestamp())
        k = rng.random()
        return s if k < .5 else (s * 1000 if k < .8 else str(s))
    if t.day > 12 and not in_overlap(t):
        tags.add("fmt_date_dot")
        return t.strftime("%d.%m.%Y %H:%M") if rng.random() < .5 else t.strftime("%m.%d.%Y %H:%M")
    return a.isoformat(timespec="seconds")


def fmt_date(d, tags):
    r = rng.random()
    if r < 0.90:
        return d.isoformat()
    if r < 0.94:
        tags.add("fmt_date_dayfirst")
        return d.strftime("%d/%m/%Y")
    if r < 0.965:
        tags.add("fmt_date_text")
        return f"{d.day} {MON[d.month - 1]} {d.year}" if rng.random() < .6 else f"{d.day:02d}-{MON[d.month - 1]}-{d.year}"
    if r < 0.985:
        tags.add("fmt_date_unix")
        return int(aware(dt.datetime.combine(d, dt.time(0))).timestamp() * 1000)
    tags.add("fmt_date_iso_variant")
    return aware(dt.datetime.combine(d, dt.time(0))).isoformat(timespec="seconds")


def fmt_label(key, v, tags):
    primary, variants = LABELS[key][v]
    if rng.random() < LABEL_VARIANT_P:
        tags.add("fmt_label")
        return rng.choice(variants)
    return primary


def fmt_triage(ats, tags):
    if rng.random() < LABEL_VARIANT_P + .02:
        tags.add("fmt_label")
        return rng.choice([f"ATS {ats}", f"Category {ats}", ats, f"CAT{ats}"])
    return f"Cat {ats}"


def fmt_phone(d, tags):
    if rng.random() < .94:
        return f"(02) {d[:4]} {d[4:]}"
    tags.add("fmt_phone")
    return rng.choice([f"02 {d[:4]} {d[4:]}", f"+61 2 {d[:4]} {d[4:]}", f"02{d}", f"+612{d}"])


def fmt_name(nm, tags):
    first, middle, last = nm
    if rng.random() < .06:
        tags.add("fmt_name_surname_first")
        return f"{last.upper()}, {first}" + (f" {middle}" if middle else "")
    return f"{first} {middle + ' ' if middle else ''}{last}"


def fmt_address(ad, tags):
    if rng.random() < .05:
        tags.add("fmt_address_flat")
        return f"{ad['line']}, {ad['suburb']} {ad['state']} {ad['postcode']}"
    out = dict(ad)
    if rng.random() < .03:
        tags.add("fmt_type_mix")
        out["postcode"] = int(ad["postcode"])
    return out


def fmt_bool(v, tags):
    if rng.random() < .04:
        tags.add("fmt_bool")
        return rng.choice([("Y" if v else "N"), ("true" if v else "false"), (1 if v else 0), ("yes" if v else "no")])
    return v


def json_number_ok(code):
    return code[0].isdigit() and not code.startswith("0") and ("." not in code or not code.endswith("0"))


def fmt_icd(code, tags):
    if code == "038.9" and rng.random() < .3:
        tags.add("fmt_icd_number")
        return 38.9                                                 # JSON number: leading zero lost
    r = rng.random()
    if r < .80:
        return code
    if r < .88 and "." in code:
        tags.add("fmt_icd_no_decimal")
        return code.replace(".", "")
    if r < .94 and json_number_ok(code):
        tags.add("fmt_icd_number")
        return float(code) if "." in code else int(code)
    tags.add("case_ws")
    return rng.choice([" " + code, code + " ", "  " + code + " "])


def num(v, tags, p=.04):
    if isinstance(v, Raw):
        return v.v
    if rng.random() < p:
        tags.add("fmt_num_string")
        return str(v)
    return v


def fmt_temp(c, tags):
    if isinstance(c, Raw):
        return c.v
    r = rng.random()
    if r < .22:
        tags.add("fmt_temp_fahrenheit")
        f_ = round(c * 9 / 5 + 32, 1)
        k = rng.random()
        if k < .55:
            return {"value": f_, "unit": rng.choice(["F", "degF", "°F"])}
        if k < .8:
            return f_
        return f"{f_}F"
    if r < .27:
        tags.add("fmt_temp_object")
        return {"value": c, "unit": rng.choice(["C", "Cel", "°C"])}
    return num(c, tags)


def fmt_vitals(v, tags):
    out = {}
    bp = v["bp"]
    if isinstance(bp, Raw):
        out["bp"] = bp.v
    else:
        s, d_ = bp
        r = rng.random()
        if r < .95:
            out["bp"] = f"{s}/{d_}"
        else:
            tags.add("fmt_vital_units")
            out["bp"] = rng.choice([{"systolic": s, "diastolic": d_}, f"{s} / {d_}", f"{s}/{d_} mmHg"])
    out["hr"] = num(v["hr"], tags)
    out["rr"] = num(v["rr"], tags)
    out["temp"] = fmt_temp(v["temp"], tags)
    out["spo2"] = num(v["spo2"], tags)
    if not isinstance(v["spo2"], Raw) and rng.random() < .02:
        tags.add("fmt_vital_units")
        out["spo2"] = f"{v['spo2']}%"
    return out


def fmt_pain(v, tags):
    if isinstance(v, Raw):
        return v.v
    r = rng.random()
    if r < .04:
        tags.add("fmt_vital_units")
        return f"{v}/10"
    return num(v, tags)


def fmt_none_list(v, tags, nones):
    if v == "NONE":
        x = rng.choice(nones)
        return [x] if rng.random() < .3 else x
    if rng.random() < .08:
        tags.add("fmt_list_as_string")
        return "; ".join(v)
    return list(v)


def fmt_id(v, tags):
    if isinstance(v, Raw):
        return v.v
    if rng.random() < .005:
        tags.add("fmt_id_string")
        return str(v)
    return v


FIELDS = {
    "Practitioner": [("practitionerId", "id"), ("honorific", "text"), ("fullName", "text"), ("designation", "text"),
                     ("department", "text"), ("employmentType", "text"), ("active", "bool")],
    "Patient": [("patientId", "id"), ("patientName", "name"), ("dob", "date"), ("sex", "label:sex"), ("address", "address"),
                ("phone", "phone"), ("nextOfKin", "nok"), ("deceased", "bool")],
    "Admission": [("admissionId", "id"), ("patientId", "id"), ("admittedAt", "dt"), ("encounterClass", "label:adm_type"),
                  ("presentingProblem", "text"), ("admittingClinicianId", "id"), ("referralSource", "text"),
                  ("fundingSource", "text"), ("separatedAt", "dt"), ("episodeStatus", "label:adm_status")],
    "Triage": [("triageId", "id"), ("triagedAt", "dt"), ("triageNurseId", "id"), ("atsCategory", "ats"), ("vitals", "vitals"),
               ("painScore", "pain"), ("symptoms", "text"), ("allergies", "allergy"), ("currentMeds", "meds")],
    "Diagnosis": [("diagnosisId", "id"), ("patientId", "id"), ("icd9", "icd"), ("rank", "label:diag_type"),
                  ("diagnosedBy", "id"), ("diagnosedAt", "dt")],
    "Note": [("noteId", "id"), ("noteType", "text"), ("authorId", "id"), ("writtenAt", "dtnote"), ("body", "text")],
    "Order": [("orderId", "id"), ("testName", "text"), ("indication", "text"), ("status", "label:order_status"),
              ("priority", "label:priority"), ("orderedBy", "id"), ("orderedAt", "dt")],
    "Imaging": [("examId", "id"), ("orderRef", "id"), ("modality", "label:modality"), ("bodySite", "text"), ("referrerId", "id"),
                ("radiographerId", "id"), ("performedAt", "dt"), ("status", "label:exam_status"), ("imageUrl", "text"), ("report", "text")],
    "Procedure": [("procedureId", "id"), ("procedureName", "text"), ("surgeonId", "id"), ("startedAt", "dt"), ("outcome", "text")],
    "WardStay": [("stayId", "id"), ("unit", "label:unit"), ("location", "location"), ("bed", "text"), ("clinicianId", "id"),
                 ("startAt", "dt"), ("endAt", "dt"), ("transferReason", "text")],
    "Separation": [("separationId", "id"), ("separatedAt", "dt"), ("authorisedBy", "id"), ("separationMode", "text"),
                   ("conditionAtSeparation", "text"), ("dischargeMeds", "list"), ("followUp", "text"), ("appointments", "appts")],
}
DST_RENDER = Counter()


def render_value(typ, key, v, tags, canon):
    if isinstance(v, Raw):
        return v.v
    if typ == "id":
        return fmt_id(v, tags)
    if typ == "dt":
        return fmt_dt(v, tags)
    if typ == "dtnote":
        dst = canon.get("_dst")
        if not dst:
            return fmt_dt(v, tags)
        kind, local = dst
        mode = canon["_dst_mode"]
        if mode == "local":          # wall-clock string with no offset
            if kind == "gap":
                tags.add("date_invalid")
                DST_RENDER["local time in the hour skipped when daylight saving starts (does not exist)"] += 1
            else:
                tags.add("date_ambiguous")
                DST_RENDER["local time in the hour repeated when daylight saving ends (happens twice)"] += 1
            return local.strftime("%d/%m/%Y %H:%M")
        tags.add("fmt_dst_offset")
        if kind == "gap":
            DST_RENDER["skipped-hour wall time written with its +10:00 offset (valid instant)"] += 1
        else:
            DST_RENDER[f"repeated-hour time written with its offset ({'first, +11:00' if local.fold == 0 else 'second, +10:00'})"] += 1
        return aware(local).isoformat(timespec="seconds")
    if typ == "date":
        return fmt_date(v, tags)
    if typ.startswith("label:"):
        return fmt_label(typ[6:], v, tags)
    if typ == "ats":
        return fmt_triage(v, tags)
    if typ == "name":
        return fmt_name(v, tags)
    if typ == "address":
        return fmt_address(v, tags)
    if typ == "phone":
        return fmt_phone(v, tags)
    if typ == "nok":
        nm, rel, ph = v
        return {"name": nm, "relationship": rel, "phone": fmt_phone(ph, tags)}
    if typ == "bool":
        return fmt_bool(v, tags)
    if typ == "icd":
        return fmt_icd(v, tags)
    if typ == "vitals":
        return fmt_vitals(v, tags)
    if typ == "pain":
        return fmt_pain(v, tags)
    if typ == "allergy":
        return fmt_none_list(v, tags, NONE_ALLERGY)
    if typ == "meds":
        return fmt_none_list(v, tags, NONE_MEDS)
    if typ == "location":
        if rng.random() < .04:
            tags.add("fmt_location_flat")
            return f"{v[0]} / {v[1]}"
        return {"ward": v[0], "room": v[1]}
    if typ == "list":
        if rng.random() < .06 and v:
            tags.add("fmt_list_as_string")
            return "; ".join(v)
        return list(v)
    if typ == "appts":
        return [{"clinic": c, "at": fmt_dt(t, tags)} for c, t in v]
    return v


def render(ent, canon, tags):
    out = {}
    for key, typ in FIELDS[ent]:
        v = canon.get(key, OMIT)
        if v is OMIT:
            continue
        if v is None:                      # legitimately empty (e.g. no separatedAt for a current admission)
            if rng.random() < .75:
                out[key] = None
            continue
        out[key] = render_value(typ, key, v, tags, canon)
    return out


# --- dotted paths inside a raw record (e.g. "vitals.hr", "address.suburb") ---
def get_path(raw, path):
    cur = raw
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def set_path(raw, path, value):
    parts = path.split(".")
    cur = raw
    for part in parts[:-1]:
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    if not isinstance(cur, dict):
        return False
    if value is OMIT:
        cur.pop(parts[-1], None)
    else:
        cur[parts[-1]] = value
    return True


def is_present(raw, path):
    ok, v = get_path(raw, path)
    return ok and v is not None and v != "" and v != [] and v != {}


# =============================================================================
# 3) Problem injection
# =============================================================================
REJECT_TAGS = {"missing_req", "date_invalid", "date_ambiguous", "broken_ref", "patient_mismatch", "chrono",
               "status_conflict", "unmapped", "fake_icd", "dup_exact", "dup_near", "malformed"}
CHILD = dict(missing_req=.02, bad_date=.024, broken_ref=.021, chrono=.021, unmapped=.004)
RATES = {
    "Practitioner": dict(missing_req=0, bad_date=0, broken_ref=0, chrono=0, unmapped=0),
    "Patient": dict(missing_req=.006, bad_date=.005, broken_ref=0, chrono=0, unmapped=0),
    "Admission": dict(missing_req=.004, bad_date=.004, broken_ref=.003, chrono=.005, unmapped=.003),
    "Triage": dict(CHILD, bad_date=0, chrono=0),           # triagedAt has no schema column
    "Procedure": dict(CHILD, unmapped=0),
    "Note": dict(CHILD, unmapped=0),
    "Separation": dict(CHILD, unmapped=0),
}
MISSING_OPT_RATE = .17
CASE_WS_RATE = .14
DUP_RATE = .05
DUP_EXACT_SHARE = .4

SPEC = {
    "Practitioner": dict(id="practitionerId", req=["fullName", "designation"], opt=["department", "employmentType"], dates=[],
                         text=["fullName", "designation", "department", "employmentType"], fks={}),
    "Patient": dict(id="patientId", req=["patientName", "dob"], opt=["sex", "address", "phone", "nextOfKin", "deceased"],
                    dates=["dob"], text=["patientName", "sex", "address.suburb", "address.line", "nextOfKin.name", "nextOfKin.relationship"], fks={}),
    "Admission": dict(id="admissionId", req=["admittedAt", "encounterClass", "presentingProblem", "admittingClinicianId"],
                      opt=["referralSource", "fundingSource", "separatedAt"], dates=["admittedAt"],
                      text=["encounterClass", "presentingProblem", "referralSource", "fundingSource", "episodeStatus"],
                      fks={"admittingClinicianId": "prof"}),
    "Triage": dict(id="triageId", req=["triageNurseId", "atsCategory"],
                   opt=["vitals.bp", "vitals.hr", "vitals.rr", "vitals.temp", "vitals.spo2", "painScore", "symptoms", "allergies", "currentMeds"],
                   dates=[], text=["symptoms", "allergies", "currentMeds", "atsCategory"], fks={"triageNurseId": "prof"}),
    "Diagnosis": dict(id="diagnosisId", req=["patientId", "icd9", "rank", "diagnosedBy", "diagnosedAt"], opt=[],
                      dates=["diagnosedAt"], text=["rank"], fks={"diagnosedBy": "prof"}),
    "Note": dict(id="noteId", req=["noteType", "authorId", "writtenAt", "body"], opt=[], dates=["writtenAt"],
                 text=["noteType", "body"], fks={"authorId": "prof"}),
    "Order": dict(id="orderId", req=["indication", "status", "priority", "orderedBy", "orderedAt"], opt=["testName"],
                  dates=["orderedAt"], text=["testName", "indication", "status", "priority"], fks={"orderedBy": "prof"}),
    "Imaging": dict(id="examId", req=["modality", "referrerId", "radiographerId", "performedAt", "status"],
                    opt=["bodySite", "imageUrl", "report"], dates=["performedAt"], text=["modality", "bodySite", "status", "report"],
                    fks={"referrerId": "prof", "radiographerId": "prof", "orderRef": "order"}),
    "Procedure": dict(id="procedureId", req=["procedureName", "surgeonId", "startedAt"], opt=["outcome"], dates=["startedAt"],
                      text=["procedureName", "outcome"], fks={"surgeonId": "prof"}),
    "WardStay": dict(id="stayId", req=["unit", "clinicianId", "startAt"], opt=["location", "bed", "endAt", "transferReason"],
                     dates=["startAt"], text=["unit", "location.ward", "bed", "transferReason"], fks={"clinicianId": "prof"}),
    "Separation": dict(id="separationId", req=["separatedAt", "authorisedBy"],
                       opt=["separationMode", "conditionAtSeparation", "dischargeMeds", "followUp", "appointments"],
                       dates=["separatedAt"], text=["separationMode", "conditionAtSeparation", "followUp"], fks={"authorisedBy": "prof"}),
}
LABEL_COL = {"Admission": ["encounterClass"], "Triage": ["atsCategory"], "Diagnosis": ["rank"],
             "Order": ["status", "priority"], "Imaging": ["status"], "WardStay": ["unit"]}
UNMAP_KEY = {("Order", "status"): "status_order", ("Imaging", "status"): "status_exam"}
NUMERIC_PATHS = {"vitals.hr", "vitals.rr", "vitals.spo2", "vitals.temp", "painScore", "vitals.bp"}
DATE_PATHS = {"dob", "admittedAt", "separatedAt", "endAt", "startAt"}
DETAIL = defaultdict(Counter)
MAX_ID = {}
PH_TEXT = [OMIT, OMIT, None, None, "", "N/A", "-", "?"]
PH_NUM = PH_TEXT + [-1, -1]
PH_DATE = [OMIT, OMIT, None, None, "", "N/A", "0000-00-00", "0000-00-00"]
PH_REQ_ID = [OMIT, OMIT, None, "", "N/A", "?"]


def ph_label(ph):
    return "missing key" if ph is OMIT else ("null" if ph is None else repr(ph))


def mess(s):
    """Inconsistent capitalisation / whitespace, guaranteed to differ from s."""
    for _ in range(10):
        op = rng.choice(["upper", "lower", "words", "lead", "trail", "double", "both"])
        if op == "upper":
            out = s.upper()
        elif op == "lower":
            out = s.lower()
        elif op == "words":
            out = " ".join(w.upper() if rng.random() < .5 else w.lower() for w in s.split(" "))
        elif op == "lead":
            out = rng.choice([" ", "  ", "\t"]) + s
        elif op == "trail":
            out = s + rng.choice([" ", "  ", "   "])
        elif op == "double":
            out = s.replace(" ", rng.choice(["  ", "   "]), 1) if " " in s else "  " + s
        else:
            out = " " + s.upper() + "  "
        if out != s:
            return out
    return " " + s


def invalid_dt_string(d):
    y = d.year
    kind = rng.choice(["feb30", "apr31", "month13", "hour25", "day00", "dayfirst_bad", "unix_bad", "year"])
    if kind == "feb30":
        return f"{y}-02-{rng.choice([30, 31])}T{d.hour:02d}:{d.minute:02d}:00+11:00"
    if kind == "apr31":
        return f"{y}-{rng.choice(['04', '06', '09', '11'])}-31T{d.hour:02d}:{d.minute:02d}:00+10:00"
    if kind == "month13":
        return f"{y}-{rng.choice([13, 14, 19])}-{d.day:02d}T{d.hour:02d}:{d.minute:02d}:00+10:00"
    if kind == "hour25":
        return f"{d.isoformat()[:10]}T{rng.randint(24, 29)}:{d.minute:02d}:00+10:00"
    if kind == "day00":
        return f"00/{d.month:02d}/{y} {d.hour:02d}:{d.minute:02d}"
    if kind == "dayfirst_bad":
        return f"{rng.choice([31, 32])}/{rng.choice(['02', '04', '06', '09', '11'])}/{y} {d.hour:02d}:{d.minute:02d}"
    if kind == "unix_bad":
        return rng.choice([99999999999999999, -62135596800000, 1.7e18])
    return f"{d.day:02d}/{d.month:02d}/{rng.choice(['0202', '20225', str(y)[2:]])} {d.hour:02d}:{d.minute:02d}"


def invalid_date_string(d):
    kind = rng.choice(["feb30", "apr31", "month13", "future", "compact"])
    if kind == "feb30":
        return f"{d.year}-02-30"
    if kind == "apr31":
        return f"31/{rng.choice(['04', '06', '09', '11'])}/{d.year}"
    if kind == "month13":
        return f"{d.year}-{rng.choice([13, 15, 20])}-{d.day:02d}"
    if kind == "future":
        return f"{rng.randint(2031, 2049)}-{d.month:02d}-{d.day:02d}"
    return f"{d.year}{d.month:02d}{d.day:02d}"[:7]                 # truncated compact date


def chrono_inject(ent, c):
    a = c.get("_adm")
    if ent == "Admission":
        if a["discharge"] and rng.random() < .75:
            c["separatedAt"] = fx(a["admit"] - dt.timedelta(hours=rng.randint(3, 120)))
            DETAIL[ent]["chronology: separatedAt before admittedAt"] += 1
        else:
            dob = a["p"]["dob"]
            c["admittedAt"] = fx(dt.datetime.combine(dob, dt.time(rng.randint(0, 23), rng.randint(0, 59))) - dt.timedelta(days=rng.randint(30, 900)))
            DETAIL[ent]["chronology: admittedAt before patient dob"] += 1
        return
    col = SPEC[ent]["dates"][0]
    if ent == "WardStay" and c["endAt"] and rng.random() < .5:
        c["endAt"] = fx(c["startAt"] - dt.timedelta(hours=rng.randint(1, 30)))
        DETAIL[ent]["chronology: endAt before startAt"] += 1
        return
    if ent == "Imaging" and c.get("_order") and rng.random() < .5:
        c[col] = fx(c["_order"]["orderedAt"] - dt.timedelta(hours=rng.randint(2, 30)))
        DETAIL[ent]["chronology: performedAt before its order" + (" (and before admission)" if utc_of(c[col]) < utc_of(a["admit"]) else "")] += 1
        return
    if ent == "Separation":
        c[col] = fx(a["admit"] - dt.timedelta(hours=rng.randint(2, 96)))
        DETAIL[ent]["chronology: separatedAt before the admission"] += 1
        return
    if a["discharge"] and rng.random() < .5:
        c[col] = fx(a["discharge"] + dt.timedelta(days=rng.randint(2, 40), minutes=rng.randint(0, 600)))
        DETAIL[ent][f"chronology: {col} after separation"] += 1
    else:
        c[col] = fx(a["admit"] - dt.timedelta(days=rng.randint(1, 30), minutes=rng.randint(0, 600)))
        DETAIL[ent][f"chronology: {col} before admission"] += 1


def broken_inject(ent, c, tags):
    fks = SPEC[ent]["fks"]
    if ent == "Diagnosis" and rng.random() < .3:
        other = rng.choice([p for p in patients if p["patientId"] != c["patientId"]])
        c["patientId"] = other["patientId"]
        tags.add("patient_mismatch")
        DETAIL[ent]["broken ref: patientId does not match the enclosing patient"] += 1
        return
    if ent == "Imaging" and c["orderRef"] and rng.random() < .35:
        col = "orderRef"
    else:
        cols = [k for k in fks if k != "orderRef"]
        col = rng.choice(cols)
    kind = fks[col]
    c[col] = MAX_ID[kind] + rng.randint(1, {"prof": 60, "pat": 200, "order": 120}[kind])
    tags.add("broken_ref")
    DETAIL[ent][f"broken ref: {col} -> nonexistent {kind}"] += 1


INVALID_NUM = {
    "temp": [300, -4, 3.7, "hot", 373, 0, 120.5, "afebrile"],
    "hr": [-72, -88, 450, "7O", "abc", 0, 1200],
    "rr": [-16, 180, "x", 0, 99],
    "spo2": [140, -5, 101, 1000, "ok on RA"],
    "painScore": [14, -3, 11, "severe", 20],
    "bp": ["1200/80", "120/", "300/400", "abc/def", "80/0", 12080],
}


def process(ent, canon_rows, dup_plan=None, eligible_reject=None):
    spec, rates = SPEC[ent], RATES.get(ent, CHILD)
    rows = [dict(canon=c, tags=set(c.get("_pre", ())), touched=set(), kind="base") for c in canon_rows]
    n = len(rows)
    idx_by_id = {r["canon"][spec["id"]]: i for i, r in enumerate(rows)}
    taken = {i for i, r in enumerate(rows) if r["tags"] & REJECT_TAGS}
    if dup_plan:
        taken |= {idx_by_id[s] for s, _ in dup_plan}

    def pick(rate, filt=None):
        k = round(rate * n)
        pool = [i for i in range(n) if i not in taken and (filt is None or filt(rows[i]["canon"]))
                and (eligible_reject is None or eligible_reject(rows[i]["canon"]))]
        ch = rng.sample(pool, min(k, len(pool)))
        taken.update(ch)
        return ch

    # canonical-level injections
    for i in pick(rates["chrono"]):
        chrono_inject(ent, rows[i]["canon"])
        rows[i]["tags"].add("chrono")
    for i in pick(rates["broken_ref"]):
        broken_inject(ent, rows[i]["canon"], rows[i]["tags"])
    if ent == "Diagnosis":
        for i in pick(.01):
            rows[i]["canon"]["icd9"] = Raw(rng.choice(FAKE_ICD))
            rows[i]["tags"].add("fake_icd")
            DETAIL[ent]["fake ICD-9 code"] += 1
    if ent == "Triage":                        # invalid numbers in optional vitals (blanked by cleaning, not rejecting)
        for i in rng.sample(range(n), round(.50 * n)):
            c = rows[i]["canon"]
            c["vitals"] = dict(c["vitals"])
            cols = [k for k in ("temp", "hr", "rr", "spo2", "bp") if c["vitals"].get(k) is not None]
            if c.get("painScore") is not None:
                cols.append("painScore")
            for col in rng.sample(cols, 2 if rng.random() < .15 else 1):
                bad = Raw(rng.choice(INVALID_NUM[col]))
                if col == "painScore":
                    c["painScore"] = bad
                else:
                    c["vitals"][col] = bad
                rows[i]["touched"].add(col if col == "painScore" else f"vitals.{col}")
                DETAIL[ent][f"invalid number: {col}"] += 1
            rows[i]["tags"].add("invalid_num")

    for r in rows:
        r["raw"] = render(ent, r["canon"], r["tags"])

    # raw-level rejecting injections
    for i in pick(rates["missing_req"], filt=lambda c: "_dst" not in c):
        r = rows[i]
        col = rng.choice(spec["req"])
        ph = rng.choice(PH_DATE if col in spec["dates"] else PH_REQ_ID if col in spec["fks"] or col in ("patientId", "triageNurseId") else PH_TEXT)
        set_path(r["raw"], col, ph)
        r["tags"].add("missing_req")
        r["touched"].add(col)
        DETAIL[ent][f"missing required: {col} ({ph_label(ph)})"] += 1
    if spec["dates"] and rates["bad_date"]:
        for i in pick(rates["bad_date"], filt=lambda c: "_dst" not in c):
            r = rows[i]
            col = spec["dates"][0]
            d = r["canon"][col]
            with_time = isinstance(d, dt.datetime)
            if d.day <= 12 and d.month <= 12 and d.day != d.month and rng.random() < .9:
                r["raw"][col] = (f"{d.day:02d}.{d.month:02d}.{d.year}" if rng.random() < .5 else f"{d.month:02d}.{d.day:02d}.{d.year}") + \
                    (f" {d.hour:02d}:{d.minute:02d}" if with_time else "")
                r["tags"].add("date_ambiguous")
                DETAIL[ent][f"ambiguous date: {col} (dot format, both parts <= 12)"] += 1
            else:
                r["raw"][col] = invalid_dt_string(d) if with_time else invalid_date_string(d)
                r["tags"].add("date_invalid")
                DETAIL[ent][f"invalid date: {col}"] += 1
            r["touched"].add(col)
    if ent in LABEL_COL and rates["unmapped"]:
        for i in pick(rates["unmapped"]):
            col = rng.choice(LABEL_COL[ent])
            rows[i]["raw"][col] = rng.choice(UNMAPPABLE[UNMAP_KEY.get((ent, col), col)])
            rows[i]["tags"].add("unmapped")
            rows[i]["touched"].add(col)
            DETAIL[ent][f"unmappable label: {col}"] += 1

    # non-rejecting injections
    if spec["opt"]:
        for i in rng.sample(range(n), round(MISSING_OPT_RATE * n)):
            r = rows[i]
            cands = [c for c in spec["opt"] if is_present(r["raw"], c) and c not in r["touched"]]
            if ent == "Patient":         # blanking "deceased" of a deceased patient would lose information
                cands = [c for c in cands if not (c == "deceased" and r["canon"]["deceased"])]
            if not cands:
                continue
            col = rng.choice(cands)
            leaf = col.split(".")[-1]
            ph = rng.choice(PH_DATE if col in DATE_PATHS else PH_NUM if (col in NUMERIC_PATHS or leaf in ("hr", "rr", "spo2", "temp")) else PH_TEXT)
            set_path(r["raw"], col, ph)
            r["tags"].add("missing_opt")
            r["touched"].add(col)
            DETAIL[ent][f"missing optional: {col}"] += 1
    for i in rng.sample(range(n), round(CASE_WS_RATE * n)):
        r = rows[i]
        cands = [c for c in spec["text"] if c not in r["touched"] and isinstance(get_path(r["raw"], c)[1], str)
                 and get_path(r["raw"], c)[1].strip()]
        if not cands:
            continue
        col = rng.choice(cands)
        set_path(r["raw"], col, mess(get_path(r["raw"], col)[1]))
        r["tags"].add("case_ws")
        r["touched"].add(col)
        DETAIL[ent][f"case/whitespace: {col}"] += 1

    # duplicates
    if dup_plan is None:
        k = round(DUP_RATE * n)
        clean_idx = [i for i in range(n) if not (rows[i]["tags"] & REJECT_TAGS) and "_dst" not in rows[i]["canon"]]
        srcs = rng.sample(clean_idx, k)
        n_exact = round(k * DUP_EXACT_SHARE)
        next_id = max(r["canon"][spec["id"]] for r in rows) + 1
        dup_plan = []
        for j, i in enumerate(srcs):
            if j < n_exact:
                dup_plan.append((rows[i]["canon"][spec["id"]], None))
            else:
                dup_plan.append((rows[i]["canon"][spec["id"]], next_id))
                next_id += 1
    exact_rows, near_rows = [], []
    for src_id, new_id in dup_plan:
        src = rows[idx_by_id[src_id]]
        if new_id is None:
            raw = copy.deepcopy(src["raw"])
            tags = (src["tags"] - REJECT_TAGS) | {"dup_exact"}
            if rng.random() < .3:            # still an exact duplicate after trimming / ignoring case
                cands = [c for c in spec["text"] if isinstance(get_path(raw, c)[1], str) and get_path(raw, c)[1].strip()]
                if cands:
                    col = rng.choice(cands)
                    v = get_path(raw, col)[1]
                    nv = rng.choice([v.upper(), v.lower(), v + "  ", " " + v])
                    set_path(raw, col, nv)
                    if nv != v:
                        tags.add("case_ws")
            exact_rows.append((idx_by_id[src_id], dict(raw=raw, tags=tags, kind="exact", canon=src["canon"], src=src_id)))
        else:
            c = dict(src["canon"])
            c[spec["id"]] = new_id
            tags = {"dup_near"}
            raw = render(ent, c, tags)            # same facts, freshly rendered (other formats / labels)
            if spec["opt"] and rng.random() < .3:
                cands = [x for x in spec["opt"] if is_present(raw, x)]
                if cands:
                    set_path(raw, rng.choice(cands), rng.choice([OMIT, None, ""]))
                    tags.add("missing_opt")
            if rng.random() < .35:
                cands = [x for x in spec["text"] if isinstance(get_path(raw, x)[1], str) and get_path(raw, x)[1].strip()]
                if cands:
                    col = rng.choice(cands)
                    set_path(raw, col, mess(get_path(raw, col)[1]))
                    tags.add("case_ws")
            near_rows.append(dict(raw=raw, tags=tags, kind="near", canon=c, src=src_id))
    out = [dict(r) for r in rows]
    for orig_idx, er in sorted(exact_rows, key=lambda x: -x[0]):
        pos = rng.randint(orig_idx + 1, len(rows))
        out.insert(pos, er)
    out.extend(sorted(near_rows, key=lambda r: r["canon"][spec["id"]]))
    return out, dup_plan


def plan_parent_dups(canon_rows, idcol, prefer=None, rate=DUP_RATE):
    k = round(rate * len(canon_rows))
    pool = [r[idcol] for r in canon_rows if prefer is None or prefer(r)]
    if len(pool) < k:
        pool = [r[idcol] for r in canon_rows]
    srcs = rng.sample(pool, k)
    n_exact = round(k * DUP_EXACT_SHARE)
    nxt = max(r[idcol] for r in canon_rows) + 1
    return [(s, None) if j < n_exact else (s, nxt + j - n_exact) for j, s in enumerate(srcs)]


REPOINTED = Counter()
ADM_BY_ID = {a["id"]: a for a in admissions}
CHILDREN = {"Triage": triage, "Diagnosis": diags, "Note": notes, "Order": orders, "Imaging": exams,
            "Procedure": procs, "WardStay": stays, "Separation": seps}
for lst in CHILDREN.values():
    for c in lst:
        c["_admkey"] = c["_adm"]["id"]

# --- unlinked encounters: exported outside any patient object, referenced by patientId ---
_unl_pool = [a for a in admissions if a["type"] in ("outpatient", "urgent") and not a["dst"] and len(a["p"]["_adms"]) >= 2]
UNLINKED = rng.sample(_unl_pool, 5)
_rows_by_adm = {r["admissionId"]: r for r in adm_rows}

# --- practitioner duplicates (some admissions point at the near-duplicate practitioner ID) ---
staff_plan = plan_parent_dups(staff_rows, "practitionerId", prefer=lambda r: r["_kind"] in ("doctor", "nurse"))
MAX_ID["prof"] = max([r["practitionerId"] for r in staff_rows] + [n for _, n in staff_plan if n])
for src, new in staff_plan:
    if new:
        refs = [r for r in adm_rows if r["admittingClinicianId"] == src]
        for r in rng.sample(refs, min(2, len(refs))):
            r["admittingClinicianId"] = new
            REPOINTED["Admission.admittingClinicianId -> near-duplicate practitioner"] += 1

# --- patient duplicates (re-registration: later admissions sit under the new patient object) ---
pat_plan = plan_parent_dups(pat_rows, "patientId", prefer=lambda r: len(r["_p"]["_adms"]) >= 2 and not any(a in UNLINKED for a in r["_p"]["_adms"]))
MAX_ID["pat"] = max([r["patientId"] for r in pat_rows] + [n for _, n in pat_plan if n])
_pat_by_id = {r["patientId"]: r for r in pat_rows}
_dup_pat_alias = {}
for src, new in pat_plan:
    if new:
        _dup_pat_alias[new] = src
        adms = _pat_by_id[src]["_p"]["_adms"]
        if len(adms) >= 2 and rng.random() < .7:
            for a in adms[1:]:
                if a not in UNLINKED:
                    a["patkey"] = new
                    REPOINTED["Admission nested under the near-duplicate patient (its diagnoses carry that patientId)"] += 1

for i, a in enumerate(UNLINKED):
    r = _rows_by_adm[a["id"]]
    if i < 3:
        r["patientId"] = MAX_ID["pat"] + rng.randint(5, 300)
        r["_pre"] = {"broken_ref"}
        DETAIL["Admission"]["broken ref: unlinkedEncounters[].patientId -> nonexistent patient"] += 1
        a["unlinked"] = "broken"
    else:
        r["patientId"] = a["p"]["patientId"]
        a["unlinked"] = "valid"
    a["patkey"] = None
for d in diags:
    a = d["_adm"]
    d["patientId"] = a["patkey"] if a["patkey"] is not None else _rows_by_adm[a["id"]]["patientId"]

# --- admission duplicates (some children are nested under the near-duplicate admission) ---
adm_plan = plan_parent_dups(adm_rows, "admissionId", prefer=lambda r: not r["_adm"].get("unlinked") and not r["_adm"]["dst"])
MAX_ID["adm"] = max([r["admissionId"] for r in adm_rows] + [n for _, n in adm_plan if n])
_dup_adm_alias = {}
for src, new in adm_plan:
    if new:
        _dup_adm_alias[new] = src
        if rng.random() < .5:
            for ent, lst in CHILDREN.items():
                for c in lst:
                    if c["_admkey"] == src and rng.random() < .5:
                        c["_admkey"] = new
                        REPOINTED[f"{ent} nested under the near-duplicate admission"] += 1

# DST notes: half written as bare local wall-clock strings (rejected), half with an explicit offset (readable)
_dst_notes = sorted([n for n in notes if "_dst" in n], key=lambda n: n["noteId"])
for kind in ("gap", "overlap"):
    group = [n for n in _dst_notes if n["_dst"][0] == kind]
    for j, n in enumerate(group):
        n["_dst_mode"] = "local" if j % 2 == 0 else "offset"

_unref_staff = lambda c: c["_kind"] in ("lab", "admin", "radiologist")
RESULTS = {}
RESULTS["Practitioner"], _ = process("Practitioner", staff_rows, dup_plan=staff_plan)
for r in rng.sample([r for r in RESULTS["Practitioner"] if r["kind"] == "base" and _unref_staff(r["canon"])], 2):
    col = rng.choice(["fullName", "designation"])
    ph = rng.choice(PH_TEXT)
    set_path(r["raw"], col, ph)
    r["tags"].add("missing_req")
    DETAIL["Practitioner"][f"missing required: {col} ({ph_label(ph)})"] += 1
RESULTS["Patient"], _ = process("Patient", pat_rows, dup_plan=pat_plan, eligible_reject=lambda c: len(c["_p"]["_adms"]) == 1)
for r in RESULTS["Patient"]:
    if r["kind"] == "exact":            # stub copy re-sent by the API, without the admissions array
        pass
RESULTS["Admission"], _ = process("Admission", adm_rows, dup_plan=adm_plan,
                                  eligible_reject=lambda c: not c["_adm"].get("unlinked") and not c["_adm"]["dst"])
for ent in ["Triage", "Diagnosis", "Note", "Order"]:
    RESULTS[ent], _ = process(ent, CHILDREN[ent])
MAX_ID["order"] = max(r["canon"]["orderId"] for r in RESULTS["Order"])
for ent in ["Imaging", "Procedure", "WardStay", "Separation"]:
    RESULTS[ent], _ = process(ent, CHILDREN[ent])
_sc = sum(1 for r in RESULTS["Separation"] if "status_conflict" in r["tags"])
DETAIL["Separation"]["chronology/consistency: separation record for an admission still marked Current"] = _sc

# --- malformed records: wrong JSON types on real records, plus junk entries the API emitted ---
MALFORM = {
    "Triage": [("triageNurseId", lambda r: [12, 40])],
    "Diagnosis": [("diagnosedAt", lambda r: {"$date": 1700000000000 + rng.randint(0, 10 ** 10)}), ("rank", lambda r: ["Principal", "Additional"])],
    "Note": [("body", lambda r: {"format": "rtf", "content": "{\\rtf1\\ansi\\deff0 {\\fonttbl {\\f0 Arial;}} \\f0 Obs stable.}"}), ("writtenAt", lambda r: True)],
    "Order": [("orderedBy", lambda r: [r.get("orderedBy"), 7]), ("orderedAt", lambda r: False)],
    "Imaging": [("modality", lambda r: 7), ("performedAt", lambda r: [])],
    "Procedure": [("procedureName", lambda r: {"code": "30443-00"}), ("startedAt", lambda r: True)],
    "WardStay": [("startAt", lambda r: {"date": "see bed board", "time": None}), ("unit", lambda r: ["ICU", "Ward"])],
    "Separation": [("separatedAt", lambda r: True)],
}
for ent, specs in MALFORM.items():
    dup_srcs = {r["src"] for r in RESULTS[ent] if r["kind"] != "base"}
    pool = [r for r in RESULTS[ent] if r["kind"] == "base" and not (r["tags"] & REJECT_TAGS)
            and r["canon"][SPEC[ent]["id"]] not in dup_srcs and "_dst" not in r["canon"]]
    for (col, fn), r in zip(specs, rng.sample(pool, len(specs))):
        r["raw"][col] = fn(r["raw"])
        r["tags"].add("malformed")
        DETAIL[ent][f"malformed: {col} has the wrong JSON type"] += 1

JUNK = [("Diagnosis", "4019"), ("Note", None), ("WardStay", []), ("Order", "ERROR: HL7 ORM^O01 parse failure at segment OBR"),
        ("Imaging", {}), ("Note", "<<truncated>>")]
_adm_keys = sorted({r["canon"]["admissionId"] for r in RESULTS["Admission"] if r["kind"] in ("base", "near")
                    and not r["canon"]["_adm"].get("unlinked")})
for ent, val in JUNK:
    RESULTS[ent].append(dict(raw=val, tags={"malformed"}, kind="junk", canon={"_admkey": rng.choice(_adm_keys)}))
    DETAIL[ent][f"malformed: junk array element ({type(val).__name__})"] += 1
RESULTS["Patient"].append(dict(raw={"_error": "RECORD_LOCKED", "message": "Record locked by another session, retry later"},
                               tags={"malformed"}, kind="junk", canon={}))
DETAIL["Patient"]["malformed: error object instead of a patient (no patientId)"] += 1
_junk_adm_parent = rng.choice([r["patientId"] for r in pat_rows if len(r["_p"]["_adms"]) >= 1])
RESULTS["Admission"].append(dict(raw=None, tags={"malformed"}, kind="junk", canon={"_patkey": _junk_adm_parent}))
DETAIL["Admission"]["malformed: null element in an admissions array"] += 1

# =============================================================================
# 4) Assemble the nested JSON and write the files
# =============================================================================
NEST = [("Triage", "triage", "single"), ("Diagnosis", "diagnoses", "list"), ("Note", "clinicalNotes", "list"),
        ("Order", "orders", "list"), ("Imaging", "imaging", "list"), ("Procedure", "procedures", "list"),
        ("WardStay", "wardStays", "list"), ("Separation", "separation", "single")]
by_adm = {ent: defaultdict(list) for ent, _, _ in NEST}
for ent, _, _ in NEST:
    for r in RESULTS[ent]:
        by_adm[ent][r["canon"]["_admkey"]].append(r)

SHAPE = Counter()


def build_admission(r):
    if r["kind"] == "junk":
        return None
    obj = r["raw"]
    if r["kind"] == "exact":                         # summary copy: the API did not expand nested collections
        SHAPE["exact-duplicate admission emitted without nested arrays"] += 1
        return obj
    obj = dict(obj)
    aid = r["canon"]["admissionId"]
    for ent, key, mode in NEST:
        kids = [k["raw"] for k in by_adm[ent].get(aid, [])]
        if mode == "single":
            if not kids:
                if rng.random() < .8:
                    obj[key] = None
            elif len(kids) == 1:
                obj[key] = kids[0]
            else:
                obj[key] = kids
                SHAPE[f"admission.{key} is an array (duplicate {ent} records)"] += 1
        else:
            if kids or rng.random() < .85:
                obj[key] = kids
    return obj


adm_by_pat = defaultdict(list)
unlinked_out = []
for r in RESULTS["Admission"]:
    if r["kind"] == "junk":
        adm_by_pat[r["canon"]["_patkey"]].append(r)
        continue
    a = r["canon"]["_adm"]
    if a.get("unlinked"):
        unlinked_out.append(build_admission(r))
        continue
    adm_by_pat[a["patkey"]].append(r)

pat_records = []
for r in RESULTS["Patient"]:
    if r["kind"] == "junk":
        pat_records.append(r["raw"])
        continue
    obj = dict(r["raw"])
    if r["kind"] == "exact":
        SHAPE["exact-duplicate patient emitted as a stub without admissions"] += 1
        pat_records.append(obj)
        continue
    pid = r["canon"]["patientId"]
    obj["admissions"] = [build_admission(x) for x in sorted(adm_by_pat.get(pid, []), key=lambda x: (x["kind"] == "junk", 0))]
    pat_records.append(obj)

# junk patient goes somewhere in the middle, not at the end
_j = pat_records.pop()
pat_records.insert(rng.randint(len(pat_records) // 3, 2 * len(pat_records) // 3), _j)

OUT_DIR.mkdir(parents=True, exist_ok=True)
EXPORTED_AT = aware(CUTOFF).isoformat(timespec="seconds")
NOTICE = ("Fictional data generated for SOEN 363 (educational use only). It does not describe real patients "
          "and contains no real personal information.")
FILES = {}
per = -(-len(pat_records) // N_PAGES)
for pg in range(N_PAGES):
    chunk = pat_records[pg * per:(pg + 1) * per]
    doc = {"meta": {"source": SYSTEM, "region": "Oceania", "country": "AU", "exportType": "patient-episodes",
                    "apiVersion": "2.3", "exportedAt": EXPORTED_AT, "timeZone": "Australia/Sydney", "page": pg + 1,
                    "pages": N_PAGES, "count": len(chunk), "notice": NOTICE},
           "patients": chunk}
    if pg == N_PAGES - 1:
        doc["unlinkedEncounters"] = unlinked_out
    FILES[f"patients_p{pg + 1}.json"] = doc
FILES["practitioners.json"] = {"meta": {"source": SYSTEM, "exportType": "practitioners", "apiVersion": "2.3",
                                        "exportedAt": EXPORTED_AT, "count": len(RESULTS["Practitioner"]), "notice": NOTICE},
                               "practitioners": [r["raw"] for r in RESULTS["Practitioner"]]}
for fname, doc in FILES.items():
    with open(OUT_DIR / fname, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")

# where each record ended up (for the per-file table)
FILE_OF = {}
for fname, doc in FILES.items():
    if fname == "practitioners.json":
        for x in doc["practitioners"]:
            FILE_OF[id(x)] = fname
        continue
    for p in doc["patients"]:
        FILE_OF[id(p)] = fname
        for a in (p.get("admissions") or []) if isinstance(p, dict) else []:
            FILE_OF[id(a)] = fname
    for a in doc.get("unlinkedEncounters", []):
        FILE_OF[id(a)] = fname
per_file = defaultdict(Counter)
for r in RESULTS["Practitioner"]:
    per_file["practitioners.json"]["Practitioner"] += 1
_pat_file = {}
for fname, doc in FILES.items():
    if fname.startswith("patients"):
        for p in doc["patients"]:
            per_file[fname]["Patient"] += 1
            if isinstance(p, dict):
                for a in p.get("admissions") or []:
                    _pat_file[id(a)] = fname
        for a in doc.get("unlinkedEncounters", []):
            _pat_file[id(a)] = fname


def _walk_adm(a, fname):
    per_file[fname]["Admission"] += 1
    if not isinstance(a, dict):
        return
    for ent, key, mode in NEST:
        v = a.get(key)
        if v is None:
            continue
        items = v if (mode == "list" or isinstance(v, list)) else [v]
        per_file[fname][ent] += len(items)


for fname, doc in FILES.items():
    if fname.startswith("patients"):
        for p in doc["patients"]:
            if isinstance(p, dict):
                for a in p.get("admissions") or []:
                    _walk_adm(a, fname)
        for a in doc.get("unlinkedEncounters", []):
            _walk_adm(a, fname)

# =============================================================================
# 5) Generation log (exact counts)
# =============================================================================
ENTITY = {"Practitioner": "HealthcareProfessional", "Patient": "Patient", "Admission": "Admission", "Triage": "TriageAssessment",
          "Diagnosis": "Diagnosis", "Note": "ClinicalNote", "Order": "DiagnosticOrder", "Imaging": "RadiologyExamination",
          "Procedure": "SurgicalProcedure", "WardStay": "UnitStay", "Separation": "DischargeRecord"}
WHERE = {"Practitioner": "`practitioners.json` → `practitioners[]`", "Patient": "`patients_p*.json` → `patients[]`",
         "Admission": "`patients[].admissions[]` and `unlinkedEncounters[]`", "Triage": "`admissions[].triage` (object, or array when duplicated)",
         "Diagnosis": "`admissions[].diagnoses[]`", "Note": "`admissions[].clinicalNotes[]`", "Order": "`admissions[].orders[]`",
         "Imaging": "`admissions[].imaging[]`", "Procedure": "`admissions[].procedures[]`", "WardStay": "`admissions[].wardStays[]`",
         "Separation": "`admissions[].separation` (object, or array when duplicated)"}
CATS = [
    ("Exact duplicates", lambda t: "dup_exact" in t),
    ("Near duplicates", lambda t: "dup_near" in t),
    ("Missing optional", lambda t: "missing_opt" in t),
    ("Missing required", lambda t: "missing_req" in t),
    ("Case / whitespace", lambda t: "case_ws" in t),
    ("Non-standard format", lambda t: any(x.startswith("fmt_") for x in t)),
    ("Invalid date", lambda t: "date_invalid" in t),
    ("Ambiguous date", lambda t: "date_ambiguous" in t),
    ("Invalid number", lambda t: "invalid_num" in t),
    ("Broken reference", lambda t: bool({"broken_ref", "patient_mismatch"} & t)),
    ("Chronology", lambda t: bool({"chrono", "status_conflict"} & t)),
    ("Unmappable label", lambda t: "unmapped" in t),
    ("Fake ICD-9", lambda t: "fake_icd" in t),
    ("Malformed", lambda t: "malformed" in t),
]
FMT_NAMES = {"fmt_date_iso_variant": "ISO variant (UTC `Z`, milliseconds, no seconds, or DOB as midnight with offset)",
             "fmt_date_dayfirst": "day-first local string (`14/03/2025 09:30`, `14/3/2025 9:30 am`, `14/03/1980`)",
             "fmt_date_unix": "Unix timestamp (seconds, milliseconds, or seconds as a string)",
             "fmt_date_dot": "dot date with a part > 12 (readable, either order)", "fmt_date_text": "text date (`5 Mar 1980`, `05-Mar-1980`)",
             "fmt_label": "alternative category label", "fmt_phone": "alternative phone format",
             "fmt_name_surname_first": "name written `SURNAME, Given`", "fmt_address_flat": "address as one string instead of an object",
             "fmt_type_mix": "postcode as a number", "fmt_bool": "boolean as `Y`/`N`, `yes`/`no`, `\"true\"`, `1`/`0`",
             "fmt_temp_fahrenheit": "temperature in Fahrenheit", "fmt_temp_object": "temperature as `{value, unit}` in Celsius",
             "fmt_num_string": "number written as a string (`\"88\"`)", "fmt_vital_units": "unit text or object inside a vital sign",
             "fmt_icd_no_decimal": "ICD-9 without the decimal point", "fmt_icd_number": "ICD-9 as a JSON number (`401.9`, `486`, `38.9`)",
             "fmt_list_as_string": "list written as one `; `-separated string", "fmt_id_string": "ID written as a string (`\"57\"`)",
             "fmt_location_flat": "location as one string instead of an object", "fmt_dst_offset": "DST-hour time written with an explicit offset"}

counts = {e: Counter() for e in RESULTS}
fmt_counts = defaultdict(Counter)
for ent, rows in RESULTS.items():
    for r in rows:
        for name, test in CATS:
            if test(r["tags"]):
                counts[ent][name] += 1
        for tg in r["tags"]:
            if tg.startswith("fmt_"):
                fmt_counts[ent][FMT_NAMES[tg]] += 1

# Estimated rejections after cascading (bookkeeping on the injected problems, not cleaning code)
rej_pat = {r["canon"]["patientId"] for r in RESULTS["Patient"] if r["kind"] == "base" and r["tags"] & REJECT_TAGS}
rej_adm = set()
for r in RESULTS["Admission"]:
    if r["kind"] != "base":
        continue
    a = r["canon"]["_adm"]
    pk = a["patkey"]
    pk = _dup_pat_alias.get(pk, pk)
    if r["tags"] & REJECT_TAGS or (pk is not None and pk in rej_pat):
        rej_adm.add(r["canon"]["admissionId"])
rej_order = {r["canon"]["orderId"] for r in RESULTS["Order"] if r["kind"] == "base" and r["tags"] & REJECT_TAGS}
rejected, cascade = {}, Counter()
for ent, rows in RESULTS.items():
    n_rej = 0
    for r in rows:
        if r["kind"] != "base" or r["tags"] & REJECT_TAGS:
            n_rej += 1
            continue
        c = r["canon"]
        if ent == "Admission" and c["admissionId"] in rej_adm:
            n_rej += 1
            cascade[ent] += 1
            continue
        if ent in CHILDREN:
            k = c["_admkey"]
            if _dup_adm_alias.get(k, k) in rej_adm:
                n_rej += 1
                cascade[ent] += 1
                continue
        if ent == "Imaging" and c.get("orderRef") in rej_order:
            n_rej += 1
            cascade[ent] += 1
    rejected[ent] = n_rej

total_rows = sum(len(v) for v in RESULTS.values())
total_rej = sum(rejected.values())
_walk_total = sum(sum(c.values()) for c in per_file.values())
assert _walk_total == total_rows, (_walk_total, total_rows)

L = []
L.append("# Source D (Coral Coast Health Service): generation log\n")
L.append("> **Statement:** all of this data is entirely fictional, created exclusively for educational and learning purposes "
         "(SOEN 363 Project Phase 2). It does not describe real patients and does not include any real personal information. "
         "Names are random combinations of common first names and surnames; suburbs and streets are invented; phone numbers come "
         "from the Australian ranges reserved for fiction ((02) 5550 xxxx, (02) 7010 xxxx); image links use the reserved `.example` domain.\n")
L.append(f"Generated by `source_d_generator.py` (seed `{SEED}`). Re-running the script reproduces the files exactly. "
         "AI tool: Claude Code (Anthropic), model Claude Opus 5.5. "
         f"Extract time (local): {EXPORTED_AT} Australia/Sydney (UTC+10, UTC+11 during daylight saving). "
         f"Admissions span {START.date()} to the extract time.\n")
L.append("**One record = one entity instance**, wherever it is nested (a patient object, an admission inside it, a diagnosis inside "
         "that admission, and so on). Container objects (`meta`, the page wrapper, `vitals`, `address`, `location`, `appointments`) are "
         "not records. A record can have several problems, so the problem columns overlap (as section 7 of the contract allows). "
         "Every count comes from the script's own bookkeeping, so it is exact.\n")
L.append("## Files\n")
L.append("| File | Top-level arrays | " + " | ".join(ENTITY[e] for e in RESULTS) + " | Total |")
L.append("|---|---|" + "---:|" * (len(RESULTS) + 1))
for fname in sorted(per_file, key=lambda f: (f != "practitioners.json", f)):
    tops = "`practitioners`" if fname == "practitioners.json" else ("`patients`, `unlinkedEncounters`" if "unlinkedEncounters" in FILES[fname] else "`patients`")
    L.append(f"| `{fname}` | {tops} | " + " | ".join(str(per_file[fname][e]) for e in RESULTS) + f" | {sum(per_file[fname].values())} |")
L.append("")
L.append("## Record counts per entity\n")
L.append("| Entity | Where in the JSON | Records (incl. duplicates and junk) | Original records | Duplicates | Malformed junk entries |")
L.append("|---|---|---:|---:|---:|---:|")
for ent, rows in RESULTS.items():
    nb = sum(1 for r in rows if r["kind"] == "base")
    nd = sum(1 for r in rows if r["kind"] in ("exact", "near"))
    nj = sum(1 for r in rows if r["kind"] == "junk")
    L.append(f"| {ENTITY[ent]} | {WHERE[ent]} | {len(rows)} | {nb} | {nd} | {nj} |")
L.append(f"| **Total** | | **{total_rows}** | **{sum(1 for v in RESULTS.values() for r in v if r['kind'] == 'base')}** | "
         f"**{sum(1 for v in RESULTS.values() for r in v if r['kind'] in ('exact', 'near'))}** | "
         f"**{sum(1 for v in RESULTS.values() for r in v if r['kind'] == 'junk')}** |\n")
L.append("No ICD-9 dictionary file is generated; diagnoses use codes from `soen363-phase1/data/icd9_dictionary.csv`. "
         "IDs of every entity start at 1.\n")
L.append("## Injected problems per entity (records affected)\n")
L.append("| Entity | " + " | ".join(n for n, _ in CATS) + " |")
L.append("|---|" + "---:|" * len(CATS))
tot = Counter()
for ent in RESULTS:
    L.append(f"| {ENTITY[ent]} | " + " | ".join(str(counts[ent][n]) for n, _ in CATS) + " |")
    tot.update(counts[ent])
L.append("| **Total** | " + " | ".join(f"**{tot[n]}**" for n, _ in CATS) + " |")
L.append("| **% of all records** | " + " | ".join(f"{100 * tot[n] / total_rows:.1f}%" for n, _ in CATS) + " |\n")
L.append("Compared with contract section 7: duplicates (exact + near) "
         f"{100 * (tot['Exact duplicates'] + tot['Near duplicates']) / total_rows:.1f}% (target ~5%), "
         f"missing optional {100 * tot['Missing optional'] / total_rows:.1f}% (~10%), "
         f"missing required {100 * tot['Missing required'] / total_rows:.1f}% (~2%, lower on purpose for patients and admissions), "
         f"case/whitespace {100 * tot['Case / whitespace'] / total_rows:.1f}% (~15%), "
         f"non-standard formats {100 * tot['Non-standard format'] / total_rows:.1f}% (~15%), "
         f"invalid or ambiguous dates {100 * (tot['Invalid date'] + tot['Ambiguous date']) / total_rows:.1f}% (~2%), "
         f"invalid numbers {100 * tot['Invalid number'] / total_rows:.1f}% (~5%), "
         f"broken references {100 * tot['Broken reference'] / total_rows:.1f}% (~2%), "
         f"chronology {100 * tot['Chronology'] / total_rows:.1f}% (~2%), "
         f"malformed {100 * tot['Malformed'] / total_rows:.1f}%.\n")
L.append("## Estimated rejections\n")
L.append("Records that carry a rejecting problem (duplicate, missing required, invalid/ambiguous date, broken reference, chronology, "
         "unmappable label, fake ICD-9, malformed), plus records that cascade from a rejected patient, admission or order. "
         "Children of near-duplicate patients and admissions are not counted, because the contract re-points them to the kept record. "
         "Treat this as a sanity check, not the answer: your cleaning rules decide the real number.\n")
L.append("| Entity | Records | Estimated rejected | of which cascaded | % |")
L.append("|---|---:|---:|---:|---:|")
for ent, rows in RESULTS.items():
    L.append(f"| {ENTITY[ent]} | {len(rows)} | {rejected[ent]} | {cascade[ent]} | {100 * rejected[ent] / len(rows):.1f}% |")
L.append(f"| **Total** | **{total_rows}** | **{total_rej}** | **{sum(cascade.values())}** | **{100 * total_rej / total_rows:.1f}%** |\n")
L.append("Imaging records whose `orderRef` points to a rejected order are counted as cascaded here; since `order_id` is nullable, "
         "your cleaning might blank it instead.\n")
L.append("## Problem details per entity\n")
for ent in RESULTS:
    L.append(f"### {ENTITY[ent]}\n")
    items = sorted(DETAIL[ent].items())
    for k, v in items:
        L.append(f"- {k}: {v}")
    for k, v in sorted(fmt_counts[ent].items()):
        L.append(f"- non-standard format: {k}: {v}")
    if not items and not fmt_counts[ent]:
        L.append("- (none beyond duplicates)")
    L.append("")
L.append("### Daylight-saving edge cases (all in ClinicalNote `writtenAt`)\n")
L.append("Overnight nursing notes on the nights the clocks change. Bare local strings in the skipped hour are counted as **invalid "
         "dates** (the time does not exist); bare local strings in the repeated hour are counted as **ambiguous dates** (two possible "
         "instants). The ones written with an offset are valid and only count as non-standard format.\n")
for k, v in sorted(DST_RENDER.items()):
    L.append(f"- {k}: {v}")
L.append(f"- nights used: {', '.join(f'{d} ({k})' for k, d in DST_NIGHTS)}\n")
L.append("### Children re-pointed to near-duplicate parents\n")
L.append("These are **not** errors; per contract section 7 they should be re-pointed to the kept record before checking references.\n")
for k, v in sorted(REPOINTED.items()):
    L.append(f"- {k}: {v}")
L.append("")
L.append("### JSON shape quirks (not counted as problems)\n")
for k, v in sorted(SHAPE.items()):
    L.append(f"- {k}: {v}")
L.append(f"- admissions in the top-level `unlinkedEncounters` array (carry an explicit `patientId`): {len(unlinked_out)} "
         f"({sum(1 for a in UNLINKED if a['unlinked'] == 'broken')} point to a patient that does not exist, counted above as broken references; "
         f"{sum(1 for a in UNLINKED if a['unlinked'] == 'valid')} point to a real patient)")
L.append("- a missing nested collection is either an empty array, `null` (for `triage` / `separation`), or the key is absent\n")
L.append("## How duplicates were made\n")
L.append("- **Exact duplicate:** the same record repeated with the **same ID** in the same array, sometimes with one field's case or "
         "surrounding spaces changed (still identical after trimming and ignoring case). Exact-duplicate patients are re-sent as stubs "
         "without `admissions`, and exact-duplicate admissions without their nested arrays, so no child is duplicated by accident.")
L.append("- **Near duplicate:** the same facts under a **new ID** (IDs continue after the last original ID), rendered again so dates, "
         "labels and phone numbers can use another format. They match the contract's duplicate keys: patient = name + DOB, practitioner = "
         "name + role, admission = patient + admit time, others = admission + timestamp + type. For `triage` and `separation`, which are "
         "normally single objects, a duplicate turns the key into an array of two objects.\n")
L.append("## Source D conventions (for checking your profiling)\n")
L.append("- **Timestamps** are local Australia/Sydney time. Usual format: ISO 8601 with the correct offset, `2025-03-14T09:30:00+11:00` "
         "(+11:00 in daylight saving, +10:00 otherwise). Also present: UTC with `Z`, milliseconds, no seconds; day-first local strings "
         "with no offset (`14/03/2025 09:30` or `14/3/2025 9:30 am`; a slash date in this source is **always** day-first); Unix timestamps "
         "(seconds as a number, milliseconds as a number, or seconds as a string; all are true UTC instants); and a few dot dates "
         "(`dd.mm.yyyy HH:MM` or `mm.dd.yyyy HH:MM`, both orders occur). A dot date with a part over 12 can be read; a dot date where both "
         "parts are 12 or less is one of the injected **ambiguous dates**.")
L.append("- **Date of birth** (`dob`): usually `YYYY-MM-DD`; also `DD/MM/YYYY`, `5 Mar 1980` / `05-Mar-1980`, Unix **milliseconds of local "
         "midnight** (converting that to a UTC date gives the previous day), and ISO midnight with offset (`1980-03-14T00:00:00+10:00`).")
L.append("- **Temperature** (`vitals.temp`): a plain number in Celsius (sometimes a string), `{value, unit}` with unit `C`/`Cel`/`°C`, "
         "or Fahrenheit: `{value, unit}` with `F`/`degF`/`°F`, a bare number in the 90s-100s, or a string like `\"99.1F\"`. "
         "Other vitals are numbers, sometimes strings, sometimes with units (`\"96%\"`, `\"4/10\"`, `\"120/80 mmHg\"`, "
         "`{systolic, diastolic}`).")
L.append("- **Missing-value placeholders** (injected): missing key, `null`, `\"\"`, `\"N/A\"`, `\"-\"`, `\"?\"`; `-1` for numbers; "
         "`\"0000-00-00\"` for dates. Values that are legitimately empty (no `separatedAt` for a current admission, no `orderRef` for a "
         "walk-in exam, no report for an exam not done, no `endAt` for a current stay, no phone for young children) are written as `null` "
         "or the key is left out, and are **not** counted as problems.")
L.append("- **Allergies / medications** with none: `none`, `None`, `NKA`, `NKDA`, `nil known`, `Nil known`, `Nil` (sometimes inside a "
         "one-element array). These mean \"none\", not missing. Real values are an array of strings, or sometimes one `; `-separated string.")
L.append("- **Patient life status** is the boolean `deceased` (sometimes `Y`/`N`, `yes`/`no`, `\"true\"`/`\"false\"`, `1`/`0`). "
         "A missing `deceased` means unknown, so the schema default (`alive`) applies.")
L.append("- **ICD-9 codes**: dictionary codes only, sometimes without the decimal point (`4019`), with extra spaces (` 428.0`), or as a JSON "
         "number (`401.9`, `486`, `38.9` for `038.9`); plus fake codes from this list: "
         f"{', '.join('`' + c + '`' for c in FAKE_ICD)}.")
L.append("- **Invalid numbers** are only in optional triage vitals and pain scores (e.g. temperature `300`, heart rate `-72`, SpO2 `140`, "
         "pain `14`, `\"abc\"`). `-1` on its own is the missing-value placeholder, not an invalid number.")
L.append("- **Malformed** records are either real records with a field of the wrong JSON type (e.g. `writtenAt: true`, "
         "`body` as an object, `orderedBy` as an array) or junk entries inside an array (`null`, a bare string, `[]`, `{}`, an error object). "
         "Every file is still valid JSON (UTF-8, 2-space indent).")
L.append("- **IDs** are integers, occasionally written as strings (`\"57\"`). Children are linked to their admission by nesting; "
         "each diagnosis also carries an explicit `patientId`, and each imaging record an optional `orderRef`.\n")
L.append("## Intended label mapping (answer key)\n")
L.append("| Raw key | Standard value | Source D labels |")
L.append("|---|---|---|")
_lab_cols = [("sex", "sex"), ("encounterClass", "adm_type"), ("episodeStatus", "adm_status"), ("rank", "diag_type"),
             ("orders[].status", "order_status"), ("priority", "priority"), ("imaging[].status", "exam_status"),
             ("modality", "modality"), ("unit", "unit")]
for col, key in _lab_cols:
    for canon, (prim, var) in LABELS[key].items():
        std = UNIT_STD.get(canon, canon) if key == "unit" else ({"XR": "X-ray", "US": "Ultrasound"}.get(canon, canon))
        extra = " (elective same-day surgery uses `Day Surgery`)" if key == "adm_type" and canon == "elective" else ""
        labels = [prim] + var + (["Day Surgery"] if key == "adm_type" and canon == "elective" else [])
        L.append(f"| {col} | {std} | {', '.join('`' + x + '`' for x in labels)}{extra} |")
for n in range(1, 6):
    L.append(f"| atsCategory | {ATS_STD[n]} | `Cat {n}`, `ATS {n}`, `Category {n}`, `CAT{n}`, `{n}` (number) |")
L.append("")
L.append("Labels that cannot be mapped (injected on purpose, should end up as `UNMAPPED_CATEGORY`):\n")
_unm_names = {"status_order": "orders[].status", "status_exam": "imaging[].status"}
for col, vals in UNMAPPABLE.items():
    L.append(f"- {_unm_names.get(col, col)}: {', '.join('`' + v + '`' for v in vals)}")
L.append("")
L.append("Keys with no schema column (ignore or drop): practitioner `honorific`, `department`, `employmentType`, `active`; "
         "triage `triagedAt`; order `testName`. `modality` maps to examination_type, which has no fixed list in the contract. "
         "`location` (`{ward, room}`) maps to ward_and_room; `address` and `nextOfKin` are objects that map to one text column each.\n")
LOG_PATH.write_text("\n".join(L), encoding="utf-8")

print(f"wrote {len(FILES)} files, {total_rows} records, estimated rejected {total_rej} ({100 * total_rej / total_rows:.1f}%)")
for ent, rows in RESULTS.items():
    print(f"  {ENTITY[ent]:24s} {len(rows):5d}")
