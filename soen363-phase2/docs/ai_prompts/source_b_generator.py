#!/usr/bin/env python3
"""
Synthetic raw data generator for Source B: "Uganda National Hospital" (fictional), Africa.

STATEMENT: All data produced by this script is entirely fictional, created exclusively for
educational and learning purposes (SOEN 363 Project Phase 2). It does not describe real
patients and does not include any real personal information. Names are random combinations
of common first names and surnames; phone numbers, plot numbers and IDs are random.

AI DISCLOSURE: this script was written by Claude Code (Anthropic), model Claude Opus 5.5.
It is part of the AI-use disclosure and is NOT part of the team's pipeline. It only generates
raw data; it does no loading, profiling, cleaning or transformation.

Output: one CSV per entity in soen363-phase2/data/raw/B_csv/ and a generation log
(soen363-phase2/docs/ai_prompts/source_b_generation_log.md) with exact counts of every
injected problem. Seeded, so re-running produces byte-identical files.

Run:  python3 soen363-phase2/docs/ai_prompts/source_b_generator.py
"""

import csv
import datetime as dt
import random
from collections import Counter, defaultdict
from pathlib import Path

SEED = 363
rng = random.Random(SEED)

HERE = Path(__file__).resolve().parent          # soen363-phase2/docs/ai_prompts
PHASE2 = HERE.parent.parent                     # soen363-phase2
REPO = PHASE2.parent
ICD_PATH = REPO / "soen363-phase1" / "data" / "icd9_dictionary.csv"
OUT_DIR = PHASE2 / "data" / "raw" / "B_csv"
LOG_PATH = HERE / "source_b_generation_log.md"

START = dt.datetime(2022, 1, 1, 0, 0)
CUTOFF = dt.datetime(2025, 10, 31, 18, 0)       # extract time, local Africa/Kampala
N_PATIENTS = 660

# =============================================================================
# ICD-9 codes (only the shared dictionary) and fake codes
# =============================================================================
with open(ICD_PATH, newline="", encoding="utf-8") as f:
    ICD_CODES = [r["icd9_code"] for r in csv.DictReader(f)]
ICD_SET = set(ICD_CODES)
_NODOT = Counter(c.replace(".", "") for c in ICD_CODES)
assert all(v == 1 for v in _NODOT.values()), "no-decimal forms must be unique"
FAKE_ICD = ["999.99", "123.4", "V99.9", "000.1", "E999.9", "4O1.9", "72.15", "629.99", "301.X"]
for _fc in FAKE_ICD:
    assert _fc not in ICD_SET and _fc.replace(".", "") not in _NODOT
    assert ("0" + _fc) not in ICD_SET and ("00" + _fc) not in ICD_SET

# =============================================================================
# Clinical knowledge per ICD code (keeps the records internally consistent)
#   reason: presenting complaints, sym: triage symptoms, sev: 1 low .. 3 high,
#   short: label used in order indications, tests: diagnostic orders,
#   meds: discharge medications, plan: progress-note sentences
# =============================================================================
CLIN = {
    "038.9": dict(reason=["Fever, rigors and confusion", "High fever with low blood pressure", "Fever and lethargy for 3 days"],
                  sym=["fever, chills, confusion", "high fever, rigors, weakness", "fever, vomiting, drowsiness"], sev=3, short="sepsis",
                  tests=["Blood culture", "Full Blood Count", "Malaria RDT", "Serum lactate", "Chest X-ray"],
                  meds="Ceftriaxone 2g IV OD then Cefixime 200mg BD x5 days",
                  plan=["Started IV antibiotics and fluids, blood cultures sent.", "Remains febrile, BP improved on fluids.", "Afebrile for 24h, switched to oral antibiotics."]),
    "244.9": dict(reason=["Fatigue and weight gain, known hypothyroid", "Review of thyroid replacement"],
                  sym=["tiredness, cold intolerance", "weight gain, constipation"], sev=1, short="hypothyroidism",
                  tests=["TSH", "Free T4"], meds="Levothyroxine 100mcg OD",
                  plan=["TSH elevated, levothyroxine dose increased.", "Symptoms improving on current dose."]),
    "250.00": dict(reason=["Poorly controlled blood sugar", "Diabetes review, high glucose readings"],
                   sym=["polyuria, thirst", "tiredness, frequent urination"], sev=1, short="uncontrolled diabetes",
                   tests=["HbA1c", "Random blood sugar", "Renal function tests"], meds="Metformin 500mg BD; Glibenclamide 5mg OD",
                   plan=["Glucose readings 8-12 mmol/L, metformin continued.", "Diabetic education given."]),
    "272.4": dict(reason=["Lipid review", "High cholesterol on screening"], sym=["no complaints", "routine check"], sev=1,
                  short="hyperlipidaemia", tests=["Lipid profile"], meds="Atorvastatin 20mg nocte",
                  plan=["Lipids elevated, started statin.", "Diet advice given."]),
    "276.51": dict(reason=["Vomiting and diarrhoea, unable to keep fluids", "Dehydration after diarrhoea"],
                   sym=["vomiting, diarrhoea, dizziness", "watery stools, dry mouth"], sev=2, short="dehydration",
                   tests=["Serum electrolytes", "Renal function tests", "Stool analysis"], meds="ORS sachets; Zinc 20mg OD x10 days",
                   plan=["IV fluids running, tolerating sips.", "Rehydrated, passing urine well."]),
    "285.9": dict(reason=["Weakness and pallor", "Low haemoglobin on routine test"],
                  sym=["fatigue, dizziness, pallor", "shortness of breath on exertion"], sev=2, short="anaemia",
                  tests=["Full Blood Count", "Blood smear for MPs", "Iron studies"], meds="Ferrous sulphate 200mg TDS; Folic acid 5mg OD",
                  plan=["Hb 7.2 g/dL, 1 unit of blood transfused.", "Hb improved post transfusion."]),
    "305.1": dict(reason=["Smoking cessation review", "Tobacco use counselling"], sym=["morning cough", "no complaints"], sev=1,
                  short="tobacco use", tests=["Chest X-ray"], meds="Nicotine replacement patch 21mg daily",
                  plan=["Counselled on smoking cessation.", "Motivated to quit, NRT started."]),
    "401.9": dict(reason=["Headache with high blood pressure", "Hypertension review", "Elevated BP at clinic"],
                  sym=["headache, dizziness", "blurred vision, headache", "no complaints"], sev=1, short="hypertension",
                  tests=["Renal function tests", "Urinalysis", "ECG"], meds="Amlodipine 10mg OD; Hydrochlorothiazide 25mg OD",
                  plan=["BP 168/102, amlodipine increased.", "BP better controlled at 138/86."]),
    "410.9": dict(reason=["Severe central chest pain radiating to left arm", "Chest pain and sweating"],
                  sym=["crushing chest pain, sweating", "chest pain, shortness of breath, nausea"], sev=3, short="myocardial infarction",
                  tests=["Troponin I", "ECG", "Chest X-ray", "Lipid profile"],
                  meds="Aspirin 75mg OD; Clopidogrel 75mg OD; Atorvastatin 40mg nocte; Bisoprolol 2.5mg OD",
                  plan=["ECG shows ST elevation, loaded with aspirin and clopidogrel.", "Chest pain settled, troponin trending down."]),
    "414.01": dict(reason=["Exertional chest pain, planned angiography", "Known CAD for elective angiogram"],
                   sym=["chest tightness on exertion", "exertional angina"], sev=2, short="coronary artery disease",
                   tests=["ECG", "Lipid profile", "Renal function tests"],
                   meds="Aspirin 75mg OD; Atorvastatin 40mg nocte; Isosorbide mononitrate 30mg OD",
                   plan=["Pre-procedure checks done.", "Post angiography, groin site clean and dry."]),
    "415.19": dict(reason=["Sudden shortness of breath and chest pain", "Breathlessness after long bus journey"],
                   sym=["sudden breathlessness, pleuritic chest pain", "shortness of breath, leg swelling"], sev=3, short="pulmonary embolism",
                   tests=["D-dimer", "CT pulmonary angiogram", "ECG"], meds="Rivaroxaban 15mg BD x21 days then 20mg OD",
                   plan=["Started anticoagulation.", "Breathing easier, SpO2 96% on room air."]),
    "427.31": dict(reason=["Palpitations and dizziness", "Irregular heartbeat"], sym=["palpitations, dizziness", "racing heart, breathlessness"],
                   sev=2, short="atrial fibrillation", tests=["ECG", "Serum electrolytes", "TSH"], meds="Bisoprolol 5mg OD; Rivaroxaban 20mg OD",
                   plan=["Rate controlled on bisoprolol.", "Remains in AF, rate in the 80s."]),
    "428.0": dict(reason=["Breathlessness and leg swelling", "Worsening shortness of breath, cannot lie flat"],
                  sym=["breathlessness, orthopnoea, leg swelling", "cough, swollen legs"], sev=3, short="heart failure",
                  tests=["Chest X-ray", "Renal function tests", "Serum electrolytes", "BNP"],
                  meds="Furosemide 40mg OD; Enalapril 5mg BD; Spironolactone 25mg OD",
                  plan=["IV furosemide given, good diuresis.", "Weight down 2kg, less breathless."]),
    "434.91": dict(reason=["Sudden weakness of right side and slurred speech", "Facial droop and arm weakness"],
                   sym=["right sided weakness, slurred speech", "facial droop, confusion"], sev=3, short="stroke",
                   tests=["CT head", "Full Blood Count", "Lipid profile", "Random blood sugar"],
                   meds="Aspirin 300mg OD x14 days then Clopidogrel 75mg OD; Atorvastatin 80mg nocte",
                   plan=["CT done, no bleed. Aspirin started.", "Speech improving, physiotherapy started."]),
    "486": dict(reason=["Cough, fever and difficulty breathing", "Productive cough and chest pain"],
                sym=["cough, fever, breathlessness", "productive cough, chest pain, fever"], sev=2, short="pneumonia",
                tests=["Chest X-ray", "Full Blood Count", "Sputum culture", "Malaria RDT"], meds="Amoxicillin-clavulanate 625mg TDS x7 days",
                plan=["Started IV antibiotics, oxygen via nasal prongs.", "Fever settling, cough improving."]),
    "491.21": dict(reason=["Worsening cough and wheeze, known COPD", "Breathlessness, COPD flare"],
                   sym=["wheeze, cough, breathlessness", "increased sputum, breathlessness"], sev=2, short="COPD exacerbation",
                   tests=["Chest X-ray", "Arterial blood gas", "Full Blood Count"],
                   meds="Salbutamol inhaler 2 puffs PRN; Prednisolone 40mg OD x5 days; Doxycycline 100mg OD x5 days",
                   plan=["Nebulised salbutamol given, steroids started.", "Wheeze reduced, mobilising on ward."]),
    "493.92": dict(reason=["Acute asthma attack", "Severe wheeze not relieved by inhaler"], sym=["wheeze, tight chest", "breathlessness, night cough"],
                   sev=2, short="acute asthma", tests=["Peak flow", "Chest X-ray"],
                   meds="Salbutamol inhaler PRN; Beclomethasone inhaler 2 puffs BD; Prednisolone 40mg OD x5 days",
                   plan=["Back-to-back nebs given, improving.", "Peak flow 80% of predicted."]),
    "518.81": dict(reason=["Severe difficulty breathing, drowsy", "Respiratory distress"], sym=["severe breathlessness, drowsiness", "laboured breathing, confusion"],
                   sev=3, short="respiratory failure", tests=["Arterial blood gas", "Chest X-ray", "Full Blood Count"],
                   meds="Salbutamol nebules PRN; Home oxygen assessment",
                   plan=["On high-flow oxygen, ABG repeated.", "Weaned to nasal prongs, more alert."]),
    "530.81": dict(reason=["Heartburn and acid reflux", "Epigastric burning, planned endoscopy"], sym=["heartburn, regurgitation", "epigastric pain after meals"],
                   sev=1, short="reflux disease", tests=["H. pylori stool antigen"], meds="Omeprazole 20mg BD x8 weeks",
                   plan=["Started PPI, lifestyle advice given.", "Symptoms improving on omeprazole."]),
    "540.9": dict(reason=["Right lower abdominal pain and vomiting", "Abdominal pain moving to the right side"],
                  sym=["right iliac fossa pain, vomiting, fever", "abdominal pain, loss of appetite"], sev=3, short="appendicitis",
                  tests=["Full Blood Count", "Abdominal ultrasound", "Urinalysis"], meds="Paracetamol 1g QID PRN; Metronidazole 400mg TDS x5 days",
                  plan=["Surgical review done, booked for theatre.", "Post-op day 1, tolerating fluids."]),
    "574.00": dict(reason=["Right upper abdominal pain and fever", "Severe pain under right ribs after meals"],
                   sym=["right upper quadrant pain, fever", "pain after fatty meals, vomiting"], sev=2, short="acute cholecystitis",
                   tests=["Abdominal ultrasound", "Liver function tests", "Full Blood Count"], meds="Ciprofloxacin 500mg BD x5 days; Paracetamol 1g PRN",
                   plan=["IV antibiotics, nil by mouth.", "Pain improving, diet reintroduced."]),
    "574.20": dict(reason=["Recurrent biliary colic, for cholecystectomy", "Gallstones, planned surgery"],
                   sym=["intermittent right upper quadrant pain", "bloating after meals"], sev=1, short="gallstones",
                   tests=["Abdominal ultrasound", "Liver function tests"], meds="Paracetamol 1g QID PRN",
                   plan=["Consented for laparoscopic cholecystectomy.", "Post-op, wounds clean."]),
    "577.0": dict(reason=["Severe upper abdominal pain radiating to back", "Epigastric pain and vomiting"],
                  sym=["severe epigastric pain, vomiting", "abdominal pain radiating to back"], sev=3, short="pancreatitis",
                  tests=["Serum amylase", "Abdominal ultrasound", "CT abdomen", "Liver function tests"],
                  meds="Paracetamol 1g QID; Tramadol 50mg PRN; Low-fat diet",
                  plan=["Aggressive IV fluids, analgesia.", "Amylase falling, tolerating clear fluids."]),
    "578.9": dict(reason=["Vomiting blood", "Black tarry stools and dizziness"], sym=["haematemesis, dizziness", "melaena, weakness"],
                  sev=3, short="GI bleed", tests=["Full Blood Count", "Blood grouping and crossmatch", "Liver function tests"],
                  meds="Omeprazole 40mg BD x8 weeks",
                  plan=["2 units of blood crossmatched, IV PPI started.", "No further bleeding, Hb stable."]),
    "584.9": dict(reason=["Reduced urine output and swelling", "Raised creatinine and vomiting"], sym=["reduced urine, leg swelling", "nausea, reduced urine output"],
                  sev=3, short="acute kidney injury", tests=["Renal function tests", "Serum electrolytes", "Renal ultrasound", "Urinalysis"],
                  meds="Avoid NSAIDs; Furosemide 40mg OD",
                  plan=["Fluid balance chart started, nephrotoxins stopped.", "Creatinine improving."]),
    "585.9": dict(reason=["CKD review, for fistula creation", "Worsening kidney function"], sym=["fatigue, itching", "leg swelling, tiredness"],
                  sev=2, short="chronic kidney disease", tests=["Renal function tests", "Full Blood Count", "Renal ultrasound"],
                  meds="Calcium carbonate 500mg TDS; Erythropoietin weekly; Amlodipine 5mg OD",
                  plan=["Renal team review, fistula planned.", "Electrolytes stable."]),
    "599.0": dict(reason=["Painful urination and fever", "Lower abdominal pain and frequent urination"],
                  sym=["dysuria, frequency, fever", "burning urine, lower abdominal pain"], sev=1, short="urinary tract infection",
                  tests=["Urinalysis", "Urine culture", "Full Blood Count"], meds="Nitrofurantoin 100mg BD x5 days",
                  plan=["Urine dipstick positive, antibiotics started.", "Afebrile, symptoms resolving."]),
    "715.35": dict(reason=["Chronic knee pain, for knee replacement", "Osteoarthritis of knee, planned surgery"],
                   sym=["knee pain, stiffness", "difficulty walking, knee pain"], sev=1, short="osteoarthritis of knee",
                   tests=["X-ray knee", "Full Blood Count"], meds="Paracetamol 1g QID; Enoxaparin 40mg SC OD x14 days",
                   plan=["Pre-op assessment complete.", "Post-op day 2, mobilising with physio."]),
    "780.2": dict(reason=["Collapsed at home", "Fainting episode"], sym=["brief loss of consciousness", "dizziness then fainted"],
                  sev=2, short="syncope", tests=["ECG", "Random blood sugar", "Full Blood Count"], meds="No new medication",
                  plan=["ECG normal, observe on monitor.", "No further episodes overnight."]),
    "780.39": dict(reason=["Seizure at home", "Convulsions"], sym=["seizure, confusion afterwards", "jerking movements, tongue bite"],
                   sev=3, short="seizure", tests=["CT head", "MRI brain", "Serum electrolytes", "Random blood sugar", "Malaria RDT"],
                   meds="Carbamazepine 200mg BD",
                   plan=["Loaded with anticonvulsant, seizure precautions.", "No further seizures, alert and oriented."]),
    "786.50": dict(reason=["Chest pain, cause unclear", "Central chest discomfort"], sym=["chest pain", "chest discomfort, anxiety"],
                   sev=2, short="chest pain", tests=["ECG", "Troponin I", "Chest X-ray"], meds="Omeprazole 20mg OD; Paracetamol PRN",
                   plan=["Serial troponins negative.", "Pain settled, likely musculoskeletal."]),
    "820.8": dict(reason=["Fall at home with hip pain, unable to walk", "Hip injury after fall"],
                  sym=["hip pain, unable to bear weight", "pain in right hip after fall"], sev=3, short="hip fracture",
                  tests=["X-ray pelvis", "Full Blood Count", "Blood grouping and crossmatch"],
                  meds="Paracetamol 1g QID; Enoxaparin 40mg SC OD x28 days",
                  plan=["Skin traction applied, listed for theatre.", "Post-op, mobilising with frame."]),
    "850.9": dict(reason=["Head injury after road traffic accident", "Hit head, brief loss of consciousness"],
                  sym=["headache, brief loss of consciousness", "head injury, vomiting once"], sev=2, short="concussion",
                  tests=["CT head"], meds="Paracetamol 1g PRN",
                  plan=["GCS 15/15, neuro obs 2-hourly.", "Headache improving, no new deficits."]),
}
assert set(CLIN) == ICD_SET, "every dictionary code needs clinical info"

# Diagnostic tests: kind (lab/img/other); imaging ones also give modality and body area
TESTS_IMG = {
    "Chest X-ray": ("XR", "Chest"), "CT head": ("CT", "Head"), "Abdominal ultrasound": ("US", "Abdomen"),
    "CT abdomen": ("CT", "Abdomen"), "CT pulmonary angiogram": ("CT", "Chest"), "X-ray knee": ("XR", "Knee"),
    "X-ray pelvis": ("XR", "Pelvis/Hip"), "Renal ultrasound": ("US", "Kidneys"), "MRI brain": ("MRI", "Brain"),
}
FINDINGS = {
    "Chest X-ray": {"486": "Right lower lobe consolidation consistent with pneumonia.",
                    "428.0": "Cardiomegaly with bilateral pleural effusions.",
                    "518.81": "Bilateral diffuse opacities.",
                    "491.21": "Hyperinflated lungs, no focal consolidation.",
                    None: "No acute cardiopulmonary abnormality."},
    "CT head": {"434.91": "Hypodensity in the left MCA territory consistent with acute infarct.",
                "850.9": "No intracranial haemorrhage. No skull fracture.",
                None: "No acute intracranial abnormality."},
    "Abdominal ultrasound": {"574.00": "Gallstones with gallbladder wall thickening.",
                             "574.20": "Multiple gallstones, no wall thickening.",
                             "540.9": "Non-compressible appendix 9 mm with free fluid.",
                             "577.0": "Bulky oedematous pancreas.",
                             None: "Normal abdominal ultrasound."},
    "CT abdomen": {"577.0": "Peripancreatic fat stranding, no necrosis.", None: "No acute abdominal pathology."},
    "CT pulmonary angiogram": {"415.19": "Filling defects in segmental pulmonary arteries consistent with PE.",
                               None: "No pulmonary embolism."},
    "X-ray knee": {"715.35": "Joint space narrowing and osteophytes, medial compartment.", None: "No bony injury."},
    "X-ray pelvis": {"820.8": "Displaced fracture of the right femoral neck.", None: "No fracture seen."},
    "Renal ultrasound": {"585.9": "Small echogenic kidneys bilaterally.", "584.9": "Normal sized kidneys, no hydronephrosis.",
                         None: "Normal renal ultrasound."},
    "MRI brain": {None: "No structural lesion identified."},
}
SURGERY = {
    "540.9": [("Open appendicectomy", 0.45), ("Laparoscopic appendicectomy", 0.40)],
    "574.20": [("Laparoscopic cholecystectomy", 0.75)],
    "574.00": [("Laparoscopic cholecystectomy", 0.35)],
    "820.8": [("Hemiarthroplasty of hip", 0.40), ("Dynamic hip screw fixation", 0.40)],
    "715.35": [("Total knee replacement", 0.80)],
    "414.01": [("Coronary angiography and PCI", 0.60)],
    "410.9": [("Primary PCI", 0.30)],
    "585.9": [("AV fistula creation", 0.55)],
    "578.9": [("Upper GI endoscopy with haemostasis", 0.40)],
    "530.81": [("Diagnostic upper GI endoscopy", 0.50)],
    "038.9": [("Incision and drainage of abscess", 0.12)],
    "518.81": [("Tracheostomy", 0.10)],
    "850.9": [("Suturing of scalp laceration", 0.25)],
}
OUTCOMES = ["Successful, no complications"] * 6 + ["Uneventful recovery"] * 3 + [
    "Minor bleeding, controlled", "Post-op fever, treated", "Wound infection, on antibiotics"]

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
DEATH_RISK = {"038.9": .14, "518.81": .16, "410.9": .10, "428.0": .08, "434.91": .10, "415.19": .07, "578.9": .06}
COMORB = [("401.9", .35), ("250.00", .18), ("272.4", .15), ("305.1", .10), ("285.9", .07),
          ("585.9", .05), ("244.9", .05), ("427.31", .05)]
CHRONIC_MEDS = {"401.9": "Amlodipine 5mg OD", "250.00": "Metformin 500mg BD", "272.4": "Atorvastatin 20mg nocte",
                "244.9": "Levothyroxine 100mcg OD", "427.31": "Bisoprolol 5mg OD", "585.9": "Calcium carbonate 500mg TDS",
                "285.9": "Ferrous sulphate 200mg OD"}
ALLERGENS = ["Penicillin", "Sulfa drugs", "Aspirin", "Chloroquine", "Peanuts", "Codeine", "Latex", "Ibuprofen", "Fansidar"]
NEWBORN_REASON = {"038.9": "Newborn with fever and poor feeding", "486": "Newborn with fast breathing",
                  "276.51": "Newborn feeding poorly, dehydrated", "285.9": "Newborn pallor",
                  None: "Healthy newborn, delivered at UNH"}

# =============================================================================
# People and places (fictional combinations)
# =============================================================================
SURNAMES = ["Okello", "Mukasa", "Nakato", "Namubiru", "Ssempala", "Kato", "Babirye", "Achieng", "Opio", "Akello",
            "Tumusiime", "Byaruhanga", "Atwine", "Kyomuhendo", "Wasswa", "Nsubuga", "Nabukeera", "Odongo", "Ochieng",
            "Amongi", "Kiggundu", "Lubega", "Mugisha", "Asiimwe", "Ainembabazi", "Mwesigwa", "Nalubega", "Ssekandi",
            "Ojok", "Adong", "Tugume", "Kisakye", "Namatovu", "Kabugo", "Nankya", "Ouma", "Auma", "Ekwaru", "Ariong",
            "Nyakato", "Kemigisha", "Bwambale", "Masika", "Kule", "Muhindo", "Okot", "Lamwaka", "Oryem", "Acen",
            "Kizza", "Ssali", "Nantongo", "Bukenya", "Kasozi", "Turyasingura", "Arinaitwe", "Kansiime", "Natukunda",
            "Byamukama", "Otim"]
FIRST_M = ["John", "Joseph", "Moses", "Peter", "David", "Isaac", "Patrick", "Ronald", "Emmanuel", "Denis", "Godfrey",
           "Ivan", "Hassan", "Ibrahim", "Brian", "Collins", "Samuel", "Andrew", "Paul", "Simon", "Richard", "Robert",
           "Fred", "Charles", "Henry", "Julius", "Martin", "Edward", "Geoffrey", "Musa"]
FIRST_F = ["Grace", "Sarah", "Esther", "Ruth", "Brenda", "Florence", "Joan", "Harriet", "Agnes", "Prossy", "Winnie",
           "Shamim", "Aisha", "Fatuma", "Doreen", "Juliet", "Lydia", "Mercy", "Rebecca", "Martha", "Annet", "Betty",
           "Christine", "Sylvia", "Rose", "Immaculate", "Josephine", "Irene", "Patience", "Gloria"]
DISTRICTS = ["Kampala", "Wakiso", "Mukono", "Entebbe", "Jinja", "Mbarara", "Gulu", "Lira", "Mbale", "Masaka",
             "Fort Portal", "Arua", "Hoima", "Soroti", "Kabale", "Mityana", "Luweero", "Iganga"]
RELATIONS = ["Mother", "Father", "Spouse", "Brother", "Sister", "Son", "Daughter", "Aunt", "Uncle", "Guardian"]
PAYERS = ["Self-pay"] * 5 + ["Private Insurance (Plan A)", "Private Insurance (Plan B)", "Employer Scheme",
                             "Government (free care)", "Government (free care)", "UNH Staff Scheme", "Community Health Fund"]
SOURCES = {
    "emergency": ["Self-referral", "Self-referral", "Ambulance", "Health Centre IV referral", "Police", "Private clinic referral"],
    "urgent": ["Self-referral", "Health Centre III referral", "Health Centre IV referral", "Private clinic referral"],
    "elective": ["OPD clinic", "Specialist clinic referral"],
    "outpatient": ["OPD clinic", "Self-referral"],
    "newborn": ["Born at UNH"],
}

# =============================================================================
# Source B's own category labels:  canonical -> (usual label, [other labels seen])
# =============================================================================
LABELS = {
    "sex": {"M": ("M", ["Male"]), "F": ("F", ["Female"])},
    "life": {"alive": ("Alive", ["Living", "A"]), "deceased": ("Deceased", ["Dead", "Died", "RIP"])},
    "adm_type": {"emergency": ("Emergency", ["A&E", "Casualty", "Emergency Dept", "EMERG"]),
                 "urgent": ("Urgent", ["URG", "Urgent Care"]),
                 "elective": ("Elective", ["Planned", "Booked"]),
                 "outpatient": ("OPD", ["Outpatient", "Day Case"]),
                 "newborn": ("Newborn", ["Neonate", "Born in Hospital"])},
    "adm_status": {"discharged": ("Discharged", ["DISCH", "D/C"]),
                   "active": ("Admitted", ["In-patient", "Active", "Still Admitted"]),
                   "deceased": ("Died", ["Deceased", "Expired", "RIP"])},
    "triage": {"high": ("HIGH", ["Hi", "Red", "P1"]), "medium": ("MEDIUM", ["Med", "Yellow", "P2"]),
               "low": ("LOW", ["Lo", "Green", "Routine", "P3"])},
    "diag_type": {"primary": ("Primary", ["Principal", "Main", "P"]),
                  "secondary": ("Secondary", ["Comorbidity", "Additional", "S"])},
    "order_status": {"pending": ("Pending", ["Awaiting", "Requested"]),
                     "in_progress": ("In Progress", ["Processing", "Sample Received"]),
                     "completed": ("Completed", ["Done", "Resulted"]),
                     "cancelled": ("Cancelled", ["Canceled", "CXL"])},
    "priority": {"routine": ("Routine", ["R", "Normal"]), "urgent": ("Urgent", ["URG", "U"]),
                 "stat": ("STAT", ["Stat", "Immediate", "ASAP"])},
    "exam_status": {"completed": ("Done", ["Completed", "Reported"]), "scheduled": ("Booked", ["Scheduled", "Pending"]),
                    "cancelled": ("Cancelled", ["Canceled"])},
    "modality": {"XR": ("X-Ray", ["XR", "XRAY", "Plain Film"]), "CT": ("CT Scan", ["CT", "C.T."]),
                 "US": ("Ultrasound", ["USS", "U/S", "Sonography"]), "MRI": ("MRI", ["MRI Scan", "M.R.I"])},
    "unit": {"ED": ("Emergency Dept", ["A&E", "Casualty"]), "ICU": ("ICU", ["Intensive Care Unit", "I.C.U"]),
             "CCU": ("CCU", ["Cardiac Care Unit", "Coronary Care"]), "MICU": ("MICU", ["Medical ICU"]),
             "SICU": ("SICU", ["Surgical ICU"]), "WARD": ("General Ward", ["Gen Ward", "Medical Ward", "Surgical Ward", "Ward"])},
}
LABEL_VARIANT_P = 0.07
UNMAPPABLE = {"AdmissionCategory": ["OTHER", "Transfer In", "Type 4"], "TriageCategory": ["Blue", "Category X"],
              "DiagType": ["Provisional", "Differential"], "RequestStatus": ["On Hold", "Sent"],
              "Urgency": ["As per protocol", "Level 2"], "ExamStatus": ["DNA", "Postponed"],
              "Unit": ["HDU", "Theatre Recovery", "Isolation"]}
NONE_ALLERGY = ["none", "None", "NKA", "no known allergies", "No Known Allergies"]
NONE_MEDS = ["none", "None", "none", "NKA"]
PH_TEXT = ["", "N/A", "null", "-", "?"]
PH_NUM = ["", "N/A", "null", "-", "?", "-1"]
PH_DATE = ["", "N/A", "null", "-", "0000-00-00"]


class Raw:
    """A literal raw string that the renderer must output untouched (used for invalid numbers)."""
    def __init__(self, s):
        self.s = s


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
    return a + dt.timedelta(minutes=rng.randint(0, max(span, 0)))


def end_of(adm):
    return adm["discharge"] if adm["discharge"] else CUTOFF


def within(adm, lo, hi):
    s, e = adm["admit"], end_of(adm)
    t = s + dt.timedelta(seconds=(e - s).total_seconds() * rng.uniform(lo, hi))
    t = t.replace(second=0, microsecond=0)
    if t <= s:
        t = s + dt.timedelta(minutes=2)
    if t >= e:
        t = e - dt.timedelta(minutes=1)
    return t


def age_on(dob, when):
    d = when.date() if isinstance(when, dt.datetime) else when
    return d.year - dob.year - ((d.month, d.day) < (dob.month, dob.day))


def phone_digits():
    return rng.choice(["70", "71", "72", "74", "75", "76", "77", "78"]) + "".join(str(rng.randint(0, 9)) for _ in range(7))


# =============================================================================
# 1) Canonical (clean, internally consistent) data
# =============================================================================
STAFF_PLAN = [  # (cadre, kind, departments, count)
    ("Medical Officer", "doctor", ["Internal Medicine", "Paediatrics", "Emergency Medicine"], 14),
    ("Consultant Physician", "doctor", ["Internal Medicine", "Cardiology", "Paediatrics"], 6),
    ("Intern Doctor", "doctor", ["Internal Medicine", "Emergency Medicine"], 4),
    ("Clinical Officer", "doctor", ["Emergency Medicine", "Outpatients"], 5),
    ("Consultant Surgeon", "surgeon", ["Surgery", "Orthopaedics"], 3),
    ("Surgeon", "surgeon", ["Surgery", "Orthopaedics"], 4),
    ("Nursing Officer", "nurse", ["Nursing"], 14),
    ("Enrolled Nurse", "nurse", ["Nursing"], 10),
    ("Midwife", "nurse", ["Maternity"], 4),
    ("Radiographer", "radiographer", ["Radiology"], 6),
    ("Radiologist", "radiologist", ["Radiology"], 3),
    ("Laboratory Technologist", "lab", ["Laboratory"], 4),
    ("Records Officer", "admin", ["Medical Records"], 3),
]
staff = []
_used_names = set()
for cadre, kind, depts, cnt in STAFF_PLAN:
    for _ in range(cnt):
        while True:
            sex = rng.choice("MF")
            nm = f"{rng.choice(FIRST_M if sex == 'M' else FIRST_F)} {rng.choice(SURNAMES)}"
            if nm not in _used_names:
                _used_names.add(nm)
                break
        title = "Dr" if kind in ("doctor", "surgeon", "radiologist") else ("Sr" if kind == "nurse" and sex == "F" and rng.random() < .5 else ("Mr" if sex == "M" else "Ms"))
        staff.append(dict(StaffName=nm, Cadre=cadre, Department=rng.choice(depts), Title=title, _kind=kind))
rng.shuffle(staff)
for i, s in enumerate(staff, 1):
    s["StaffID"] = i
BY_KIND = defaultdict(list)
for s in staff:
    BY_KIND[s["_kind"]].append(s["StaffID"])
# a few staff do most of the work (realistic skew)
_weights = {sid: rng.uniform(0.3, 3.0) for sid in range(1, len(staff) + 1)}


def prof(kind):
    ids = BY_KIND[kind]
    return wchoice([(i, _weights[i]) for i in ids])


# ---------------- patients and admissions ----------------
patients, admissions = [], []
_name_dob = set()
for _ in range(N_PATIENTS):
    sex = rng.choice("MF")
    newborn = rng.random() < 0.06
    first_admit = rdt(START, CUTOFF - dt.timedelta(days=2))
    if newborn:
        dob = first_admit.date()
    else:
        u = rng.random()
        age = rng.randint(1, 17) if u < 0.14 else (rng.randint(18, 64) if u < 0.68 else rng.randint(65, 93))
        dob = first_admit.date() - dt.timedelta(days=age * 365 + rng.randint(0, 364))
    while True:
        first = rng.choice(FIRST_M if sex == "M" else FIRST_F)
        name = f"{first} {rng.choice(SURNAMES)}"
        if rng.random() < 0.12:
            name = f"{first} {rng.choice(FIRST_M if sex == 'M' else FIRST_F)} {name.split(' ')[-1]}"
        if (name.lower(), dob) not in _name_dob:
            _name_dob.add((name.lower(), dob))
            break
    age_now = age_on(dob, CUTOFF)
    comorb = [c for c, p in COMORB if age_now >= 40 and rng.random() < p] if not newborn else []
    if 18 <= age_now < 40 and rng.random() < 0.08:
        comorb.append("305.1")
    u = rng.random()
    allergies = [] if u < 0.75 else rng.sample(ALLERGENS, 1 if u < 0.95 else 2)
    nok_rel = "Mother" if age_now < 18 else rng.choice(RELATIONS)
    nok_first = rng.choice(FIRST_F if nok_rel in ("Mother", "Sister", "Daughter", "Aunt")
                           else FIRST_M if nok_rel in ("Father", "Brother", "Son", "Uncle") else FIRST_M + FIRST_F)
    p = dict(PatientName=name, DOB=dob, Sex=sex,
             Address=f"Plot {rng.randint(1, 260)}, Zone {rng.choice('ABCDEFGH')}, {rng.choice(DISTRICTS)}",
             PhoneNo=None if age_now < 14 else phone_digits(),
             NextOfKin=(nok_first, rng.choice(SURNAMES), nok_rel, phone_digits()),
             Status="alive", _first=first_admit, _comorb=comorb, _allergies=allergies, _adms=[])
    patients.append(p)

    n_adm = wchoice([(1, .70), (2, .20), (3, .10)])
    t = first_admit
    for k in range(n_adm):
        a_age = age_on(dob, t)
        if newborn and k == 0:
            typ = "newborn"
        else:
            w = {"emergency": .45, "urgent": .17, "elective": .20 if a_age >= 18 else .05, "outpatient": .18}
            typ = wchoice(list(w.items()))
            if typ == "elective":
                t = t.replace(hour=rng.randint(7, 10), minute=rng.choice([0, 15, 30, 45]))
            elif typ == "outpatient":
                t = t.replace(hour=rng.randint(8, 15), minute=rng.randint(0, 59))
        if typ == "newborn":
            icd = None if rng.random() < .5 else rng.choice(["038.9", "486", "276.51", "285.9"])
        else:
            cands = [c for c in TYPE_ICDS[typ] if a_age >= MIN_AGE.get(c, 0)]
            icd = rng.choice(cands)
        sev = CLIN[icd]["sev"] if icd else 1
        hours = {"outpatient": lambda: rng.uniform(2, 8), "newborn": lambda: rng.uniform(24, 96),
                 "elective": lambda: rng.uniform(24, 144), "urgent": lambda: rng.uniform(12, 120),
                 "emergency": lambda: rng.uniform(*{1: (8, 48), 2: (24, 120), 3: (48, 288)}[sev])}[typ]()
        icu = None
        if typ == "emergency" and icd in ICU_FOR and rng.random() < .45:
            icu, hours = ICU_FOR[icd], max(hours, 60)
        if typ == "newborn" and icd in ("038.9", "486") and rng.random() < .5:
            icu, hours = "ICU", max(hours, 72)
        surg = None
        if icd in SURGERY and typ != "outpatient":
            r, acc = rng.random(), 0
            for name_s, pr in SURGERY[icd]:
                acc += pr
                if r < acc:
                    surg = name_s
                    break
            if surg:
                hours = max(hours, 30)
        dis = (t + dt.timedelta(hours=hours)).replace(second=0, microsecond=0)
        status = "discharged"
        if dis > CUTOFF or ((CUTOFF - t).days < 12 and rng.random() < .6):
            dis, status = None, "active"
        elif icd in DEATH_RISK and rng.random() < DEATH_RISK[icd] + (.06 if a_age > 70 else 0):
            status = "deceased"
        secondaries = [c for c in p["_comorb"] if c != icd]
        rng.shuffle(secondaries)
        secondaries = secondaries[:rng.randint(0, 2)]
        adm = dict(p=p, admit=t.replace(second=0, microsecond=0), discharge=dis, status=status, type=typ, icd=icd,
                   sev=sev, icu=icu, surg=surg, secondaries=secondaries,
                   prof=prof("surgeon") if (typ == "elective" and surg) else prof("doctor"))
        admissions.append(adm)
        p["_adms"].append(adm)
        if status != "discharged":
            if status == "deceased":
                p["Status"] = "deceased"
            break
        t = dis + dt.timedelta(days=rng.randint(10, 420), hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
        if t > CUTOFF - dt.timedelta(hours=6):
            break

patients.sort(key=lambda p: p["_first"])
for i, p in enumerate(patients, 1):
    p["PatientNo"] = i
admissions.sort(key=lambda a: a["admit"])
for i, a in enumerate(admissions, 1):
    a["id"] = i
ADM = {a["id"]: a for a in admissions}

adm_rows = []
for a in admissions:
    reason = NEWBORN_REASON[a["icd"]] if a["type"] == "newborn" else rng.choice(CLIN[a["icd"]]["reason"])
    adm_rows.append(dict(AdmissionNo=a["id"], PatientNo=a["p"]["PatientNo"], AdmittingDoctorID=a["prof"],
                         AdmitDateTime=a["admit"], AdmissionCategory=a["type"], PresentingComplaint=reason,
                         ReferredFrom=rng.choice(SOURCES[a["type"]]), PayerScheme=rng.choice(PAYERS),
                         DischargeDateTime=a["discharge"], AdmStatus=a["status"], _adm=a))

# ---------------- child entities ----------------
triage, diags, notes, orders, exams, surgeries, stays, discharges = ([] for _ in range(8))


def vitals(a):
    icd, sev, nb = a["icd"], a["sev"], a["type"] == "newborn"
    if nb:
        return dict(BP=(rng.randint(60, 80), rng.randint(35, 50)), Pulse=rng.randint(115, 165), RespRate=rng.randint(35, 60),
                    Temp=round(rng.uniform(38.0, 39.4) if icd in ("038.9", "486") else rng.uniform(36.5, 37.4), 1),
                    SpO2=rng.randint(88, 94) if icd == "486" else rng.randint(95, 100), PainScore=None)
    sbp, dbp = rng.randint(105, 138), rng.randint(64, 88)
    if icd == "401.9" or "401.9" in a["secondaries"]:
        sbp, dbp = rng.randint(148, 188), rng.randint(90, 112)
    if icd in ("038.9", "578.9"):
        sbp, dbp = rng.randint(78, 102), rng.randint(42, 62)
    temp = rng.uniform(38.0, 40.2) if icd in ("038.9", "486", "599.0", "574.00") else rng.uniform(36.2, 37.4)
    hr = rng.randint(102, 142) if icd in ("038.9", "578.9", "427.31", "415.19") else rng.randint(62, 99)
    rr = rng.randint(22, 34) if icd in ("486", "518.81", "428.0", "491.21", "493.92", "415.19") else rng.randint(13, 20)
    spo2 = rng.randint(82, 93) if icd in ("486", "518.81", "491.21", "415.19", "428.0") else rng.randint(95, 100)
    pain = rng.randint(6, 10) if icd in ("410.9", "540.9", "820.8", "577.0", "574.00", "786.50", "415.19") else rng.randint(0, 4)
    return dict(BP=(sbp, dbp), Pulse=hr, RespRate=rr, Temp=round(temp, 1), SpO2=spo2, PainScore=pain)


for a in admissions:
    p, icd, typ = a["p"], a["icd"], a["type"]
    # triage
    if rng.random() < {"emergency": 1, "urgent": 1, "newborn": .5, "elective": .3, "outpatient": .35}[typ]:
        sev = a["sev"]
        pr = wchoice({3: [("high", .8), ("medium", .2)], 2: [("high", .15), ("medium", .7), ("low", .15)],
                      1: [("low", .7), ("medium", .3)]}[sev]) if icd else "low"
        meds = [CHRONIC_MEDS[c] for c in p["_comorb"] if c in CHRONIC_MEDS]
        row = dict(AdmissionNo=a["id"], NurseID=prof("nurse"),
                   TriageDateTime=min(a["admit"] + dt.timedelta(minutes=rng.randint(5, 40)), end_of(a) - dt.timedelta(minutes=1)),
                   Symptoms=(rng.choice(CLIN[icd]["sym"]) if icd else "routine newborn check"),
                   Allergies=("; ".join(p["_allergies"]) if p["_allergies"] else "NONE"),
                   CurrentMeds=("; ".join(meds) if meds else "NONE"), TriageCategory=pr, _adm=a)
        row.update(vitals(a))
        triage.append(row)
    # diagnoses
    if icd:
        diags.append(dict(PatientNo=p["PatientNo"], AdmissionNo=a["id"], ICD9=icd, DiagnosedBy=rng.choice([a["prof"], prof("doctor")]),
                          DiagDateTime=within(a, .01, .25), DiagType="primary", _adm=a))
    for c in a["secondaries"]:
        diags.append(dict(PatientNo=p["PatientNo"], AdmissionNo=a["id"], ICD9=c, DiagnosedBy=prof("doctor"),
                          DiagDateTime=within(a, .05, .6), DiagType="secondary", _adm=a))
    # clinical notes
    days = (end_of(a) - a["admit"]).total_seconds() / 86400
    n_notes = (1 if rng.random() < .35 else 0) if typ == "outpatient" else max(0, 1 + min(3, int(days // 2)) - rng.randint(0, 1))
    for j in range(n_notes):
        ntype = "Admission Note" if j == 0 else rng.choice(["Progress Note", "Ward Round Note", "Nursing Note"])
        if j == n_notes - 1 and j >= 2 and a["status"] == "discharged":
            ntype = "Discharge Note"
        base = (rng.choice(CLIN[icd]["plan"]) if icd else "Baby feeding well, mother counselled on breastfeeding.")
        if ntype == "Admission Note":
            txt = f"Admitted with {(rng.choice(CLIN[icd]['sym']) if icd else 'no complaints')}. Impression: {CLIN[icd]['short'] if icd else 'healthy newborn'}. {base}"
        elif ntype == "Nursing Note":
            txt = rng.choice(["Vitals stable, patient comfortable, slept well.", "Observations done 4-hourly, no concerns.",
                              "Patient says \"I feel better today\", eating well.", "IV line resited, fluids running."])
        elif ntype == "Discharge Note":
            txt = f"Clinically improved. {base} Fit for discharge, counselled on medication."
        else:
            txt = base if rng.random() < .6 else f"Reviewed on ward round, comfortable. {base} Plan: continue current management."
        if rng.random() < .08:
            txt = f"S: {(rng.choice(CLIN[icd]['sym']) if icd else 'feeding well')}\nO: obs stable\nA: {CLIN[icd]['short'] if icd else 'well baby'}\nP: {base}"
        lo, hi = (0.0, .1) if j == 0 else ((j / max(n_notes, 1)) * .9, min(.98, ((j + 1) / max(n_notes, 1))))
        notes.append(dict(AdmissionNo=a["id"], AuthorID=prof("nurse") if ntype == "Nursing Note" else prof("doctor"),
                          NoteCategory=ntype, NoteDate=within(a, lo, hi), NoteText=txt, _adm=a))
    # diagnostic orders (+ radiology)
    tests = list(CLIN[icd]["tests"]) if icd else []
    if typ == "newborn" and icd:
        tests = ["Full Blood Count", "Blood culture"] + (["Chest X-ray"] if icd == "486" else [])
    k = min(len(tests), wchoice([(0, .5), (1, .4), (2, .1)]) if typ == "outpatient" else wchoice([(0, .25), (1, .45), (2, .30)]))
    chosen = rng.sample(tests, k)
    if typ in ("emergency", "urgent") and icd and rng.random() < .08:      # walk-in exam without a request
        img = [t_ for t_ in tests if t_ in TESTS_IMG and t_ not in chosen]
        if img:
            mod, body = TESTS_IMG[img[0]]
            exams.append(dict(AdmissionNo=a["id"], RequestNo=None, ReferringDr=a["prof"], Radiographer=prof("radiographer"),
                              Modality=mod, ExamDateTime=within(a, .02, .2), BodyPart=body, ExamStatus="completed",
                              PACSLink=f"http://pacs.unh.local/viewer?acc=UNH{rng.randint(100000, 999999)}",
                              Findings=FINDINGS[img[0]].get(icd, FINDINGS[img[0]][None]), _adm=a, _test=img[0]))
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
        o = dict(AdmissionNo=a["id"], RequestedBy=rng.choice([a["prof"], prof("doctor")]), RequestDateTime=req_t,
                 TestRequested=tname, IndicationForTest=reason, RequestStatus=st, Urgency=prio, _adm=a)
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
                ex_t = (req_t + dt.timedelta(seconds=gap * rng.uniform(.05, .5))).replace(second=0, microsecond=0)
                if ex_t <= req_t:
                    ex_t = req_t + dt.timedelta(minutes=10)
                mod, body = TESTS_IMG[tname]
                done = ex_st == "completed"
                exams.append(dict(AdmissionNo=a["id"], RequestNo=o, ReferringDr=o["RequestedBy"], Radiographer=prof("radiographer"),
                                  Modality=mod, ExamDateTime=ex_t, BodyPart=body, ExamStatus=ex_st,
                                  PACSLink=f"http://pacs.unh.local/viewer?acc=UNH{rng.randint(100000, 999999)}" if done else None,
                                  Findings=FINDINGS[tname].get(icd, FINDINGS[tname][None]) if done else None, _adm=a, _test=tname))
    # surgery
    if a["surg"]:
        if typ == "elective":
            op_t = min(a["admit"] + dt.timedelta(hours=rng.uniform(2, 6)), end_of(a) - dt.timedelta(hours=4)).replace(second=0, microsecond=0)
        else:
            op_t = within(a, .05, .3)
        a["op_t"] = op_t
        surgeries.append(dict(AdmissionNo=a["id"], SurgeonID=prof("surgeon"), Operation=a["surg"], OpDateTime=op_t,
                              Outcome=rng.choice(OUTCOMES), _adm=a))
    # unit stays
    units = []
    hrs = (end_of(a) - a["admit"]).total_seconds() / 3600
    if typ == "emergency":
        if rng.random() < .7 or hrs < 12:
            units.append("ED")
        if a["icu"]:
            units.append(a["icu"])
        if hrs >= 12:
            units.append("WARD")
        if a["surg"] and rng.random() < .2 and "WARD" in units:
            units += ["SICU", "WARD"]          # pre-op ward, post-op SICU, back to ward
    elif typ == "urgent":
        units = (["ED"] if rng.random() < .3 else []) + ["WARD"]
    elif typ == "elective":
        units = ["WARD"] + (["SICU", "WARD"] if a["surg"] and rng.random() < .25 else [])
    elif typ == "outpatient":
        units = ["WARD"] if rng.random() < .35 else []
    else:
        units = ["WARD"] + (["ICU"] if a["icu"] else [])
    if units:
        w = [{"ED": .08}.get(u_, .35 if u_ != "WARD" else 1.0) for u_ in units]
        tot = sum(w)
        bounds, acc = [a["admit"]], 0
        for wi in w[:-1]:
            acc += wi
            bounds.append((a["admit"] + dt.timedelta(seconds=(end_of(a) - a["admit"]).total_seconds() * acc / tot)).replace(second=0, microsecond=0))
        bounds.append(a["discharge"])                        # None for active admissions
        prev = None
        for j, u_ in enumerate(units):
            entry = bounds[j] + dt.timedelta(minutes=rng.randint(0, 12) if j == 0 else 0)
            ex = bounds[j + 1]
            if ex is not None and ex <= entry:
                ex = entry + dt.timedelta(minutes=30)
            if j == 0:
                reason = None if rng.random() < .7 else ("Admitted from OPD" if typ in ("elective", "outpatient") else "Initial placement")
            elif u_ in ("ICU", "MICU", "CCU"):
                reason = rng.choice(["Deteriorated, needs close monitoring", "Requires ventilatory support", "Haemodynamically unstable"])
            elif u_ == "SICU":
                reason = "Post-operative monitoring"
            elif prev == "ED":
                reason = rng.choice(["Admitted to ward for ongoing care", "Stable for ward"])
            else:
                reason = rng.choice(["Stepped down, clinically stable", "Improving, transferred to ward"])
            room = {"ED": f"Casualty Bay {rng.randint(1, 8)}", "WARD": f"Ward {'Postnatal' if typ == 'newborn' else rng.choice(['3A', '3B', '4A', '4B', '5A', '5B', '6'])}, Rm {rng.randint(1, 24)}"}.get(
                u_, f"{u_} Bay {rng.randint(1, 6)}")
            bed = rng.choice([f"B{rng.randint(1, 30):02d}", str(rng.randint(1, 30)), f"Bed {rng.randint(1, 30)}"])
            stays.append(dict(AdmissionNo=a["id"], ResponsibleClinician=prof("doctor"), Unit=u_, WardRoom=room, BedNo=bed,
                              TimeIn=entry, TimeOut=ex, TransferReason=reason, _adm=a))
            prev = u_
    # discharge record
    if a["status"] in ("discharged", "deceased"):
        dead = a["status"] == "deceased"
        nxt = a["discharge"] + dt.timedelta(days=rng.randint(7, 35))
        discharges.append(dict(
            AdmissionNo=a["id"], AuthorisedBy=rng.choice([a["prof"], prof("doctor")]), DischargeDateTime=a["discharge"],
            Destination="Mortuary" if dead else wchoice([("Home", .78), ("Referred to regional hospital", .07),
                                                        ("Transferred to rehabilitation centre", .05), ("Hospice care", .03),
                                                        ("Left against medical advice", .07)]),
            ConditionOnDischarge="Deceased" if dead else rng.choice(["Improved", "Improved", "Stable", "Recovered", "Fair", "Unchanged"]),
            DischargeMeds=None if dead else (CLIN[icd]["meds"] if icd else "Vitamin K given; BCG and polio vaccines given"),
            FollowUp=None if dead else rng.choice(["Review in OPD after 2 weeks", "Return immediately if symptoms worsen",
                                                   "Follow up at Health Centre IV in 1 month",
                                                   "Continue medication, review in specialist clinic", "Wound review in 7 days"]),
            NextAppointment=None if dead or rng.random() < .35 else f"{rng.choice(['OPD', 'Medical clinic', 'Surgical clinic', 'Specialist clinic'])} {nxt.strftime('%d/%m/%Y')} {rng.choice(['08:30', '09:00', '10:00', '14:00'])}",
            _adm=a))

# Status disagreement: a discharge record for an admission the admissions file still shows as active
_active = [a for a in admissions if a["status"] == "active"]
for a in rng.sample(_active, min(3, len(_active))):
    discharges.append(dict(AdmissionNo=a["id"], AuthorisedBy=a["prof"],
                           DischargeDateTime=min(CUTOFF - dt.timedelta(hours=1), a["admit"] + dt.timedelta(hours=rng.randint(20, 60))),
                           Destination="Home", ConditionOnDischarge="Improved", DischargeMeds=CLIN[a["icd"]]["meds"] if a["icd"] else None,
                           FollowUp="Review in OPD after 2 weeks", NextAppointment=None, _adm=a, _pre={"status_conflict"}))


def assign_ids(rows, key, idcol):
    rows.sort(key=lambda r: r[key])
    for i, r in enumerate(rows, 1):
        r[idcol] = i


assign_ids(triage, "TriageDateTime", "TriageID")
assign_ids(diags, "DiagDateTime", "DiagID")
assign_ids(notes, "NoteDate", "NoteID")
assign_ids(orders, "RequestDateTime", "RequestNo")
assign_ids(exams, "ExamDateTime", "ExamID")
assign_ids(surgeries, "OpDateTime", "OpID")
assign_ids(stays, "TimeIn", "MovementID")
assign_ids(discharges, "DischargeDateTime", "DischargeID")
for e in exams:                                     # resolve order object -> order id
    if isinstance(e["RequestNo"], dict):
        e["_order"] = e["RequestNo"]
        e["RequestNo"] = e["RequestNo"]["RequestNo"]

pat_rows = []
for p in patients:
    pat_rows.append(dict(PatientNo=p["PatientNo"], PatientName=p["PatientName"], DOB=p["DOB"], Sex=p["Sex"], Address=p["Address"],
                         PhoneNo=p["PhoneNo"], NextOfKin=p["NextOfKin"], Status=p["Status"], _p=p))
staff_rows = [dict(StaffID=s["StaffID"], Title=s["Title"], StaffName=s["StaffName"], Cadre=s["Cadre"],
                   Department=s["Department"], _kind=s["_kind"]) for s in staff]
staff_rows.sort(key=lambda r: r["StaffID"])

# =============================================================================
# 2) Rendering to Source B's raw formats
# =============================================================================
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_dt(d, tags):
    r = rng.random()
    if r < 0.93:
        return d.strftime("%d/%m/%Y %H:%M")
    if r < 0.965:
        tags.add("fmt_date_iso")
        return d.strftime(rng.choice(["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M"]))
    if r < 0.995 or d.day <= 12:
        tags.add("fmt_date_monthfirst_ampm")
        h = d.hour % 12 or 12
        return f"{d.month:02d}/{d.day:02d}/{d.year} {h:02d}:{d.minute:02d} {'AM' if d.hour < 12 else 'PM'}"
    tags.add("fmt_date_dash")                       # dash format, order mixed, but day > 12 so readable
    if rng.random() < .5:
        return d.strftime("%d-%m-%Y %H:%M")
    return d.strftime("%m-%d-%Y %H:%M")


def fmt_date(d, tags):
    r = rng.random()
    if r < 0.88:
        return d.strftime("%d/%m/%Y")
    if r < 0.94:
        tags.add("fmt_date_iso")
        return d.strftime("%Y-%m-%d")
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
    r = rng.random()
    if r < .88:
        return f"0{d[:3]} {d[3:]}"
    tags.add("fmt_phone")
    return rng.choice([f"+256 {d[:3]} {d[3:]}", f"256{d}", f"0{d}", f"0{d[:3]}-{d[3:6]}-{d[6:]}"])


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


def fmt_vital(col, v, tags):
    if col == "BP":
        s, d_ = v
        r = rng.random()
        if r < .95:
            return f"{s}/{d_}"
        tags.add("fmt_vital_units")
        return rng.choice([f"{s} / {d_}", f"{s}-{d_}", f"{s}/{d_} mmHg"])
    if col == "Temp":
        if rng.random() < .30:                      # Fahrenheit
            tags.add("fmt_temp_fahrenheit")
            f_ = round(v * 9 / 5 + 32, 1)
            return rng.choice([f"{f_}F", f"{f_} F", f"{f_}", f"{f_} °F"])
        if rng.random() < .08:
            tags.add("fmt_vital_units")
            return rng.choice([f"{v}C", f"{v} °C", f"{v}°C"])
        return f"{v}"
    suffix = {"Pulse": [" bpm", "bpm"], "RespRate": ["/min", " /min"], "SpO2": ["%", " %"], "PainScore": ["/10"]}[col]
    if rng.random() < .05:
        tags.add("fmt_vital_units")
        return f"{v}{rng.choice(suffix)}"
    return str(v)


COLTYPE = {
    "staff.csv": dict(StaffID="int", Title="text", StaffName="text", Cadre="text", Department="text"),
    "patients.csv": dict(PatientNo="int", PatientName="text", DOB="date", Sex="label:sex", Address="text", PhoneNo="phone",
                         NextOfKin="nok", Status="label:life"),
    "admissions.csv": dict(AdmissionNo="int", PatientNo="int", AdmittingDoctorID="int", AdmitDateTime="dt",
                           AdmissionCategory="label:adm_type", PresentingComplaint="text", ReferredFrom="text",
                           PayerScheme="text", DischargeDateTime="dt", AdmStatus="label:adm_status"),
    "triage.csv": dict(TriageID="int", AdmissionNo="int", NurseID="int", TriageDateTime="dt", BP="vital", Pulse="vital",
                       RespRate="vital", Temp="vital", SpO2="vital", PainScore="vital", Symptoms="text",
                       Allergies="allergy", CurrentMeds="meds", TriageCategory="label:triage"),
    "diagnoses.csv": dict(DiagID="int", PatientNo="int", AdmissionNo="int", ICD9="icd", DiagnosedBy="int",
                          DiagDateTime="dt", DiagType="label:diag_type"),
    "clinical_notes.csv": dict(NoteID="int", AdmissionNo="int", AuthorID="int", NoteCategory="text", NoteDate="dt", NoteText="text"),
    "investigation_requests.csv": dict(RequestNo="int", AdmissionNo="int", RequestedBy="int", RequestDateTime="dt",
                                       TestRequested="text", IndicationForTest="text", RequestStatus="label:order_status",
                                       Urgency="label:priority"),
    "radiology.csv": dict(ExamID="int", AdmissionNo="int", RequestNo="int", ReferringDr="int", Radiographer="int",
                          Modality="label:modality", ExamDateTime="dt", BodyPart="text", ExamStatus="label:exam_status",
                          PACSLink="text", Findings="text"),
    "theatre.csv": dict(OpID="int", AdmissionNo="int", SurgeonID="int", Operation="text", OpDateTime="dt", Outcome="text"),
    "ward_movements.csv": dict(MovementID="int", AdmissionNo="int", ResponsibleClinician="int", Unit="label:unit",
                               WardRoom="text", BedNo="text", TimeIn="dt", TimeOut="dt", TransferReason="text"),
    "discharges.csv": dict(DischargeID="int", AdmissionNo="int", AuthorisedBy="int", DischargeDateTime="dt",
                           Destination="text", ConditionOnDischarge="text", DischargeMeds="text", FollowUp="text",
                           NextAppointment="text"),
}


def render_value(typ, col, v, tags):
    if v is None:
        return ""
    if isinstance(v, Raw):
        return v.s
    if typ == "int":
        return str(v)
    if typ == "dt":
        return fmt_dt(v, tags)
    if typ == "date":
        return fmt_date(v, tags)
    if typ.startswith("label:"):
        return fmt_label(typ[6:], v, tags)
    if typ == "phone":
        return fmt_phone(v, tags)
    if typ == "nok":
        f_, s_, rel, ph = v
        return f"{f_} {s_} ({rel}) {fmt_phone(ph, tags)}"
    if typ == "icd":
        return fmt_icd(v, tags)
    if typ == "vital":
        return fmt_vital(col, v, tags)
    if typ == "allergy":
        return rng.choice(NONE_ALLERGY) if v == "NONE" else v
    if typ == "meds":
        return rng.choice(NONE_MEDS) if v == "NONE" else v
    return str(v)


def render(fname, canon, tags):
    return {col: render_value(t, col, canon.get(col), tags) for col, t in COLTYPE[fname].items()}


# =============================================================================
# 3) Problem injection
# =============================================================================
REJECT_TAGS = {"missing_req", "date_invalid", "date_ambiguous", "broken_ref", "patient_mismatch", "chrono",
               "status_conflict", "unmapped", "fake_icd", "dup_exact", "dup_near"}
CHILD = dict(missing_req=.019, bad_date=.019, broken_ref=.019, chrono=.019, unmapped=.004)
RATES = {
    "staff.csv": dict(missing_req=0, bad_date=0, broken_ref=0, chrono=0, unmapped=0),
    "patients.csv": dict(missing_req=.006, bad_date=.005, broken_ref=0, chrono=0, unmapped=0),
    "admissions.csv": dict(missing_req=.005, bad_date=.004, broken_ref=.004, chrono=.005, unmapped=.003),
    "triage.csv": dict(CHILD, bad_date=0, chrono=0),           # triage has no schema timestamp
}
MISSING_OPT_RATE = .17
CASE_WS_RATE = .13
DUP_RATE = .05
DUP_EXACT_SHARE = .4

SPEC = {
    "staff.csv": dict(id="StaffID", req=["StaffName", "Cadre"], opt=[], dates=[],
                      text=["StaffName", "Cadre", "Department", "Title"], fks={}),
    "patients.csv": dict(id="PatientNo", req=["PatientName", "DOB"], opt=["Sex", "Address", "PhoneNo", "NextOfKin", "Status"],
                         dates=["DOB"], text=["PatientName", "Address", "Sex", "Status", "NextOfKin"], fks={}),
    "admissions.csv": dict(id="AdmissionNo", req=["PatientNo", "AdmittingDoctorID", "AdmitDateTime", "AdmissionCategory", "PresentingComplaint"],
                           opt=["ReferredFrom", "PayerScheme", "DischargeDateTime"], dates=["AdmitDateTime"],
                           text=["AdmissionCategory", "PresentingComplaint", "ReferredFrom", "PayerScheme", "AdmStatus"],
                           fks={"PatientNo": "pat", "AdmittingDoctorID": "prof"}),
    "triage.csv": dict(id="TriageID", req=["AdmissionNo", "NurseID", "TriageCategory"],
                       opt=["BP", "Pulse", "RespRate", "Temp", "SpO2", "PainScore", "Symptoms", "Allergies", "CurrentMeds"],
                       dates=[], text=["Symptoms", "Allergies", "CurrentMeds", "TriageCategory"],
                       fks={"AdmissionNo": "adm", "NurseID": "prof"}),
    "diagnoses.csv": dict(id="DiagID", req=["PatientNo", "AdmissionNo", "ICD9", "DiagnosedBy", "DiagDateTime", "DiagType"], opt=[],
                          dates=["DiagDateTime"], text=["DiagType"], fks={"AdmissionNo": "adm", "DiagnosedBy": "prof"}),
    "clinical_notes.csv": dict(id="NoteID", req=["AdmissionNo", "AuthorID", "NoteCategory", "NoteDate", "NoteText"], opt=[],
                               dates=["NoteDate"], text=["NoteCategory", "NoteText"], fks={"AdmissionNo": "adm", "AuthorID": "prof"}),
    "investigation_requests.csv": dict(id="RequestNo", req=["AdmissionNo", "RequestedBy", "RequestDateTime", "IndicationForTest", "RequestStatus", "Urgency"],
                                       opt=[], dates=["RequestDateTime"], text=["TestRequested", "IndicationForTest", "RequestStatus", "Urgency"],
                                       fks={"AdmissionNo": "adm", "RequestedBy": "prof"}),
    "radiology.csv": dict(id="ExamID", req=["AdmissionNo", "ReferringDr", "Radiographer", "Modality", "ExamDateTime", "ExamStatus"],
                          opt=["BodyPart", "PACSLink", "Findings"], dates=["ExamDateTime"],
                          text=["Modality", "BodyPart", "ExamStatus", "Findings"],
                          fks={"AdmissionNo": "adm", "ReferringDr": "prof", "Radiographer": "prof", "RequestNo": "order"}),
    "theatre.csv": dict(id="OpID", req=["AdmissionNo", "SurgeonID", "Operation", "OpDateTime"], opt=["Outcome"], dates=["OpDateTime"],
                        text=["Operation", "Outcome"], fks={"AdmissionNo": "adm", "SurgeonID": "prof"}),
    "ward_movements.csv": dict(id="MovementID", req=["AdmissionNo", "ResponsibleClinician", "Unit", "TimeIn"],
                               opt=["WardRoom", "BedNo", "TimeOut", "TransferReason"], dates=["TimeIn"],
                               text=["Unit", "WardRoom", "TransferReason"], fks={"AdmissionNo": "adm", "ResponsibleClinician": "prof"}),
    "discharges.csv": dict(id="DischargeID", req=["AdmissionNo", "AuthorisedBy", "DischargeDateTime"],
                           opt=["Destination", "ConditionOnDischarge", "DischargeMeds", "FollowUp", "NextAppointment"],
                           dates=["DischargeDateTime"], text=["Destination", "ConditionOnDischarge", "DischargeMeds", "FollowUp"],
                           fks={"AdmissionNo": "adm", "AuthorisedBy": "prof"}),
}
LABEL_COL = {"admissions.csv": "AdmissionCategory", "triage.csv": "TriageCategory", "diagnoses.csv": "DiagType",
             "investigation_requests.csv": "RequestStatus", "radiology.csv": "ExamStatus", "ward_movements.csv": "Unit"}
DETAIL = defaultdict(Counter)       # file -> Counter of "problem: column/detail"
MAX_ID = {}                         # entity kind -> highest ID present in its raw file (incl. near duplicates)


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
            out = rng.choice([" ", "  ", "   "]) + s
        elif op == "trail":
            out = s + rng.choice([" ", "  ", "    "])
        elif op == "double":
            out = s.replace(" ", rng.choice(["  ", "   "]), 1) if " " in s else "  " + s
        else:
            out = " " + s.upper() + "  "
        if out != s:
            return out
    return " " + s


def invalid_date_string(d, with_time):
    tm = f" {d.hour:02d}:{d.minute:02d}" if with_time else ""
    y = d.year
    kind = rng.choice(["feb30", "day31", "month13", "day00", "hour", "iso_bad", "year"]) if with_time else \
        rng.choice(["feb30", "day31", "month13", "day00", "iso_bad", "year", "future"])
    if kind == "feb30":
        return f"{rng.choice([30, 31])}/02/{y}{tm}"
    if kind == "day31":
        return f"31/{rng.choice(['04', '06', '09', '11'])}/{y}{tm}"
    if kind == "month13":
        return f"{max(d.day, 13):02d}/{rng.choice([13, 14, 15, 19])}/{y}{tm}"
    if kind == "day00":
        return f"00/{d.month:02d}/{y}{tm}"
    if kind == "hour":
        return f"{d.day:02d}/{d.month:02d}/{y} {rng.randint(24, 29)}:{rng.randint(0, 59):02d}"
    if kind == "iso_bad":
        return f"{y}-{rng.choice(['02-30', '13-05', '00-12', '11-31'])}{tm}"
    if kind == "year":
        return f"{d.day:02d}/{d.month:02d}/{rng.choice(['0202', '20025', '2' + str(y)[2:]])}{tm}"
    return f"{d.day:02d}/{d.month:02d}/{rng.randint(2031, 2045)}"   # DOB in the future


def chrono_inject(fname, c):
    a = c.get("_adm")
    if fname == "admissions.csv":
        if a["discharge"] and rng.random() < .75:
            c["DischargeDateTime"] = a["admit"] - dt.timedelta(hours=rng.randint(3, 120))
            DETAIL[fname]["chronology: discharge before admission"] += 1
        else:
            dob = a["p"]["DOB"]
            c["AdmitDateTime"] = dt.datetime.combine(dob, dt.time(rng.randint(0, 23), rng.randint(0, 59))) - dt.timedelta(days=rng.randint(30, 900))
            DETAIL[fname]["chronology: admission before patient date of birth"] += 1
        return
    col = SPEC[fname]["dates"][0]
    if fname == "ward_movements.csv" and c["TimeOut"] and rng.random() < .5:
        c["TimeOut"] = c["TimeIn"] - dt.timedelta(hours=rng.randint(1, 30))
        DETAIL[fname]["chronology: exit before entry"] += 1
        return
    if fname == "radiology.csv" and c.get("_order") and rng.random() < .5:
        c[col] = c["_order"]["RequestDateTime"] - dt.timedelta(hours=rng.randint(2, 30))
        if c[col] < a["admit"]:
            DETAIL[fname]["chronology: exam before admission (and before its request)"] += 1
        else:
            DETAIL[fname]["chronology: exam before its request"] += 1
        return
    if fname == "discharges.csv":
        c[col] = a["admit"] - dt.timedelta(hours=rng.randint(2, 96))
        DETAIL[fname]["chronology: discharge before admission"] += 1
        return
    if a["discharge"] and rng.random() < .5:
        c[col] = a["discharge"] + dt.timedelta(days=rng.randint(2, 40), minutes=rng.randint(0, 600))
        DETAIL[fname][f"chronology: {col} after discharge"] += 1
    else:
        c[col] = a["admit"] - dt.timedelta(days=rng.randint(1, 30), minutes=rng.randint(0, 600))
        DETAIL[fname][f"chronology: {col} before admission"] += 1


def broken_inject(fname, c, tags):
    fks = SPEC[fname]["fks"]
    if fname == "diagnoses.csv" and rng.random() < .25:
        other = rng.choice([p for p in patients if p["PatientNo"] != c["PatientNo"]])
        c["PatientNo"] = other["PatientNo"]
        tags.add("patient_mismatch")
        DETAIL[fname]["broken ref: PatientNo does not match the admission's patient"] += 1
        return
    if fname == "radiology.csv" and c["RequestNo"] and rng.random() < .3:
        col = "RequestNo"
    else:
        cols = [k for k in fks if k != "RequestNo"]
        col = cols[0] if (len(cols) == 1 or rng.random() < .65) else rng.choice(cols[1:])
    kind = fks[col]
    c[col] = MAX_ID[kind] + rng.randint(1, {"adm": 400, "prof": 60, "pat": 200, "order": 120}[kind])
    tags.add("broken_ref")
    DETAIL[fname][f"broken ref: {col} -> nonexistent {kind}"] += 1


INVALID_NUM = {
    "Temp": ["300", "-4", "3.7", "hot", "373", "0", "120.5"],
    "Pulse": ["-72", "-88", "450", "7O", "abc", "0"],
    "RespRate": ["-16", "180", "x", "0", "99"],
    "SpO2": ["140", "-5", "101", "1000", "o2 ok"],
    "PainScore": ["14", "-3", "11", "severe", "20"],
    "BP": ["1200/80", "120/", "300/400", "abc/def", "80/0"],
}


def process(fname, canon_rows, dup_plan=None, eligible_reject=None):
    spec, rates = SPEC[fname], RATES.get(fname, CHILD)
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
        chrono_inject(fname, rows[i]["canon"])
        rows[i]["tags"].add("chrono")
    for i in pick(rates["broken_ref"]):
        broken_inject(fname, rows[i]["canon"], rows[i]["tags"])
    if fname == "diagnoses.csv":
        for i in pick(.01):
            rows[i]["canon"]["ICD9"] = Raw(rng.choice(FAKE_ICD))
            rows[i]["tags"].add("fake_icd")
            DETAIL[fname]["fake ICD-9 code"] += 1
    if fname == "triage.csv":                    # invalid numbers in optional vitals (not rejecting)
        for i in rng.sample(range(n), round(.48 * n)):
            c = rows[i]["canon"]
            cols = [k for k in INVALID_NUM if c.get(k) is not None]
            for col in rng.sample(cols, 2 if rng.random() < .15 else 1):
                c[col] = Raw(rng.choice(INVALID_NUM[col]))
                rows[i]["touched"].add(col)
                DETAIL[fname][f"invalid number: {col}"] += 1
            rows[i]["tags"].add("invalid_num")

    for r in rows:
        r["raw"] = render(fname, r["canon"], r["tags"])

    # raw-level rejecting injections
    for i in pick(rates["missing_req"]):
        r = rows[i]
        col = rng.choice(spec["req"])
        typ = COLTYPE[fname][col]
        r["raw"][col] = rng.choice(PH_DATE if typ in ("dt", "date") else PH_NUM[:-1] if typ == "int" else PH_TEXT)
        r["tags"].add("missing_req")
        r["touched"].add(col)
        DETAIL[fname][f"missing required: {col}"] += 1
    if spec["dates"]:
        for i in pick(rates["bad_date"]):
            r = rows[i]
            col = spec["dates"][0]
            d = r["canon"][col]
            with_time = isinstance(d, dt.datetime)
            if d.day <= 12 and d.month <= 12 and d.day != d.month and rng.random() < .8:
                r["raw"][col] = f"{d.day:02d}-{d.month:02d}-{d.year}" + (f" {d.hour:02d}:{d.minute:02d}" if with_time else "")
                r["tags"].add("date_ambiguous")
                DETAIL[fname][f"ambiguous date: {col}"] += 1
            else:
                r["raw"][col] = invalid_date_string(d, with_time)
                r["tags"].add("date_invalid")
                DETAIL[fname][f"invalid date: {col}"] += 1
            r["touched"].add(col)
    if fname in LABEL_COL and rates["unmapped"]:
        for i in pick(rates["unmapped"]):
            col = LABEL_COL[fname]
            if fname == "investigation_requests.csv" and rng.random() < .5:
                col = "Urgency"
            rows[i]["raw"][col] = rng.choice(UNMAPPABLE[col])
            rows[i]["tags"].add("unmapped")
            rows[i]["touched"].add(col)
            DETAIL[fname][f"unmappable label: {col}"] += 1

    # non-rejecting injections
    if spec["opt"]:
        for i in rng.sample(range(n), round(MISSING_OPT_RATE * n)):
            r = rows[i]
            cands = [c for c in spec["opt"] if r["raw"][c].strip() and c not in r["touched"]]
            if fname == "patients.csv":       # blanking Status of a deceased patient would lose information
                cands = [c for c in cands if not (c == "Status" and r["canon"]["Status"] == "deceased")]
            if not cands:
                continue
            col = rng.choice(cands)
            typ = COLTYPE[fname][col]
            r["raw"][col] = rng.choice(PH_DATE if typ == "dt" else PH_NUM if typ == "vital" else PH_TEXT)
            r["tags"].add("missing_opt")
            r["touched"].add(col)
            DETAIL[fname][f"missing optional: {col}"] += 1
    for i in rng.sample(range(n), round(CASE_WS_RATE * n)):
        r = rows[i]
        cands = [c for c in spec["text"] if r["raw"][c].strip() and c not in r["touched"]]
        if not cands:
            continue
        col = rng.choice(cands)
        r["raw"][col] = mess(r["raw"][col])
        r["tags"].add("case_ws")
        r["touched"].add(col)
        DETAIL[fname][f"case/whitespace: {col}"] += 1

    # duplicates
    if dup_plan is None:
        k = round(DUP_RATE * n)
        clean_idx = [i for i in range(n) if not (rows[i]["tags"] & REJECT_TAGS)]
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
            raw = dict(src["raw"])
            tags = (src["tags"] - REJECT_TAGS) | {"dup_exact"}
            if rng.random() < .3:            # still an exact duplicate after trimming / ignoring case
                col = rng.choice([c for c in spec["text"] if raw[c].strip()])
                raw[col] = rng.choice([raw[col].upper(), raw[col].lower(), raw[col] + "  ", " " + raw[col]])
                if raw[col] != src["raw"][col]:
                    tags.add("case_ws")
            exact_rows.append((idx_by_id[src_id], dict(raw=raw, tags=tags, kind="exact", canon=src["canon"])))
        else:
            c = dict(src["canon"])
            c[spec["id"]] = new_id
            tags = {"dup_near"}
            raw = render(fname, c, tags)            # same facts, freshly rendered (other formats/labels)
            if spec["opt"] and rng.random() < .3:
                cands = [x for x in spec["opt"] if raw[x].strip()]
                if cands:
                    col = rng.choice(cands)
                    raw[col] = ""
                    tags.add("missing_opt")
            if rng.random() < .35:
                col = rng.choice([x for x in spec["text"] if raw[x].strip()])
                raw[col] = mess(raw[col])
                tags.add("case_ws")
            near_rows.append(dict(raw=raw, tags=tags, kind="near", canon=c))
    out = [dict(r) for r in rows]
    # insert each exact copy at a random later position than its original
    for orig_idx, er in sorted(exact_rows, key=lambda x: -x[0]):
        pos = rng.randint(orig_idx + 1, len(rows))
        out.insert(pos, er)
    out.extend(sorted(near_rows, key=lambda r: r["canon"][spec["id"]]))
    return out, dup_plan


def plan_parent_dups(canon_rows, idcol, prefer=None):
    n = len(canon_rows)
    k = round(DUP_RATE * n)
    pool = [r[idcol] for r in canon_rows if prefer is None or prefer(r)]
    if len(pool) < k:
        pool = [r[idcol] for r in canon_rows]
    srcs = rng.sample(pool, k)
    n_exact = round(k * DUP_EXACT_SHARE)
    nxt = max(r[idcol] for r in canon_rows) + 1
    plan = []
    for j, s in enumerate(srcs):
        if j < n_exact:
            plan.append((s, None))
        else:
            plan.append((s, nxt))
            nxt += 1
    return plan


REPOINTED = Counter()

# --- staff duplicates (some admissions point at the duplicate staff ID) ---
staff_plan = plan_parent_dups(staff_rows, "StaffID", prefer=lambda r: r["_kind"] in ("doctor", "nurse"))
MAX_ID["prof"] = max([r["StaffID"] for r in staff_rows] + [n for _, n in staff_plan if n])
for src, new in staff_plan:
    if new:
        refs = [r for r in adm_rows if r["AdmittingDoctorID"] == src]
        for r in rng.sample(refs, min(2, len(refs))):
            r["AdmittingDoctorID"] = new
            REPOINTED["admissions.csv: AdmittingDoctorID -> near-duplicate staff"] += 1

# --- patient duplicates (re-registration: later admissions use the new patient number) ---
pat_plan = plan_parent_dups(pat_rows, "PatientNo", prefer=lambda r: len(r["_p"]["_adms"]) >= 2)
MAX_ID["pat"] = max([r["PatientNo"] for r in pat_rows] + [n for _, n in pat_plan if n])
_pat_by_no = {r["PatientNo"]: r for r in pat_rows}
_dup_pat_alias = {}
for src, new in pat_plan:
    if new:
        _dup_pat_alias[new] = src
        adms = _pat_by_no[src]["_p"]["_adms"]
        if len(adms) >= 2 and rng.random() < .7:
            for a in adms[1:]:
                a["pid_raw"] = new
                REPOINTED["admissions.csv (+ their diagnoses): PatientNo -> near-duplicate patient"] += 1
for r in adm_rows:
    if "pid_raw" in r["_adm"]:
        r["PatientNo"] = r["_adm"]["pid_raw"]
for d in diags:
    d["PatientNo"] = d["_adm"].get("pid_raw", d["PatientNo"])

# --- admission duplicates (some child rows point at the duplicate admission number) ---
adm_plan = plan_parent_dups(adm_rows, "AdmissionNo")
MAX_ID["adm"] = max([r["AdmissionNo"] for r in adm_rows] + [n for _, n in adm_plan if n])
_children = {"triage.csv": triage, "diagnoses.csv": diags, "clinical_notes.csv": notes,
             "investigation_requests.csv": orders, "radiology.csv": exams, "theatre.csv": surgeries,
             "ward_movements.csv": stays, "discharges.csv": discharges}
_dup_adm_alias = {}
for src, new in adm_plan:
    if new:
        _dup_adm_alias[new] = src
        if rng.random() < .5:
            for fname, lst in _children.items():
                for c in lst:
                    if c["AdmissionNo"] == src and rng.random() < .5:
                        c["AdmissionNo"] = new
                        REPOINTED[f"{fname}: AdmissionNo -> near-duplicate admission"] += 1

# parents with rejecting problems: keep them low impact (unreferenced staff; patients with one admission)
_unref_staff = lambda c: c["_kind"] in ("lab", "admin", "radiologist")
RESULTS = {}
RESULTS["staff.csv"], _ = process("staff.csv", staff_rows, dup_plan=staff_plan)
# staff missing-required: only on staff no other record references, so nothing cascades
for r in rng.sample([r for r in RESULTS["staff.csv"] if r["kind"] == "base" and _unref_staff(r["canon"])], 2):
    col = rng.choice(["StaffName", "Cadre"])
    r["raw"][col] = rng.choice(PH_TEXT)
    r["tags"].add("missing_req")
    DETAIL["staff.csv"][f"missing required: {col}"] += 1
RESULTS["patients.csv"], _ = process("patients.csv", pat_rows, dup_plan=pat_plan,
                                     eligible_reject=lambda c: len(c["_p"]["_adms"]) == 1)
RESULTS["admissions.csv"], _ = process("admissions.csv", adm_rows, dup_plan=adm_plan)
for fname in ["triage.csv", "diagnoses.csv", "clinical_notes.csv", "investigation_requests.csv"]:
    RESULTS[fname], _ = process(fname, _children[fname])
MAX_ID["order"] = max(r["canon"]["RequestNo"] for r in RESULTS["investigation_requests.csv"])
for fname in ["radiology.csv", "theatre.csv", "ward_movements.csv", "discharges.csv"]:
    RESULTS[fname], _ = process(fname, _children[fname])
if any("status_conflict" in r["tags"] for r in RESULTS["discharges.csv"]):
    DETAIL["discharges.csv"]["chronology/consistency: discharge record for an admission still marked active"] = \
        sum(1 for r in RESULTS["discharges.csv"] if "status_conflict" in r["tags"])

# =============================================================================
# 4) Write the CSV files
# =============================================================================
OUT_DIR.mkdir(parents=True, exist_ok=True)
for fname, rows in RESULTS.items():
    cols = list(COLTYPE[fname])
    with open(OUT_DIR / fname, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)                    # default dialect: comma, minimal quoting, CRLF line endings
        w.writerow(cols)
        for r in rows:
            w.writerow([r["raw"][c] for c in cols])

# =============================================================================
# 5) Generation log (exact counts)
# =============================================================================
ENTITY = {"staff.csv": "HealthcareProfessional", "patients.csv": "Patient", "admissions.csv": "Admission",
          "triage.csv": "TriageAssessment", "diagnoses.csv": "Diagnosis", "clinical_notes.csv": "ClinicalNote",
          "investigation_requests.csv": "DiagnosticOrder", "radiology.csv": "RadiologyExamination",
          "theatre.csv": "SurgicalProcedure", "ward_movements.csv": "UnitStay", "discharges.csv": "DischargeRecord"}
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
]
FMT_NAMES = {"fmt_date_iso": "ISO date", "fmt_date_monthfirst_ampm": "month-first date with AM/PM",
             "fmt_date_dash": "dash date with day > 12 (readable)", "fmt_date_text": "text date (e.g. 5 Mar 1980)",
             "fmt_label": "alternative category label", "fmt_phone": "alternative phone format",
             "fmt_temp_fahrenheit": "temperature in Fahrenheit", "fmt_vital_units": "unit text inside a vital sign",
             "fmt_icd_no_decimal": "ICD-9 without decimal point", "fmt_icd_leading_zero_lost": "ICD-9 038.9 written as 38.9"}

counts = {f: Counter() for f in RESULTS}
fmt_counts = defaultdict(Counter)
for fname, rows in RESULTS.items():
    for r in rows:
        for name, test in CATS:
            if test(r["tags"]):
                counts[fname][name] += 1
        for tg in r["tags"]:
            if tg.startswith("fmt_"):
                fmt_counts[fname][FMT_NAMES[tg]] += 1

# Estimated rejections after cascading (bookkeeping on the injected problems, not cleaning code)
rej_tags = REJECT_TAGS
rejected = {}
rej_pat = {r["canon"]["PatientNo"] for r in RESULTS["patients.csv"] if r["kind"] == "base" and r["tags"] & rej_tags}
rej_adm = set()
for r in RESULTS["admissions.csv"]:
    if r["kind"] != "base":
        continue
    pid = r["canon"]["PatientNo"]
    pid = _dup_pat_alias.get(pid, pid)
    if r["tags"] & rej_tags or pid in rej_pat:
        rej_adm.add(r["canon"]["AdmissionNo"])
rej_order = {r["canon"]["RequestNo"] for r in RESULTS["investigation_requests.csv"] if r["kind"] == "base" and r["tags"] & rej_tags}
cascade = Counter()
for fname, rows in RESULTS.items():
    n_rej = 0
    for r in rows:
        if r["kind"] != "base" or r["tags"] & rej_tags:
            n_rej += 1
            continue
        c = r["canon"]
        if fname == "admissions.csv" and c["AdmissionNo"] in rej_adm:
            n_rej += 1
            cascade[fname] += 1
            continue
        aid = c.get("AdmissionNo")
        if fname not in ("staff.csv", "patients.csv", "admissions.csv") and _dup_adm_alias.get(aid, aid) in rej_adm:
            n_rej += 1
            cascade[fname] += 1
            continue
        if fname == "radiology.csv" and c.get("RequestNo") in rej_order:
            n_rej += 1
            cascade[fname] += 1
    rejected[fname] = n_rej

total_rows = sum(len(v) for v in RESULTS.values())
total_rej = sum(rejected.values())
L = []
L.append("# Source B (Uganda National Hospital): generation log\n")
L.append("> **Statement:** all of this data is entirely fictional, created exclusively for educational and learning purposes "
         "(SOEN 363 Project Phase 2). It does not describe real patients and does not include any real personal information. "
         "Names are random combinations of common first names and surnames; phone numbers, plot numbers and IDs are random.\n")
L.append(f"Generated by `source_b_generator.py` (seed `{SEED}`). Re-running the script reproduces the files exactly. "
         "AI tool: Claude Code (Anthropic), model Claude Opus 5.5. "
         f"Extract time (local): {CUTOFF.strftime('%Y-%m-%d %H:%M')} Africa/Kampala (UTC+3, no DST). "
         f"Admissions span {START.date()} to the extract time.\n")
L.append("All counts below are **rows**. A row can have several problems, so the columns overlap (as section 7 of the contract allows). "
         "Every count comes from the script's own bookkeeping, so it is exact.\n")
L.append("## Files and record counts\n")
L.append("| Raw file | Entity | Rows (incl. duplicates) | Original records | Duplicate rows |")
L.append("|---|---|---:|---:|---:|")
for fname, rows in RESULTS.items():
    nb = sum(1 for r in rows if r["kind"] == "base")
    L.append(f"| `{fname}` | {ENTITY[fname]} | {len(rows)} | {nb} | {len(rows) - nb} |")
L.append(f"| **Total** | | **{total_rows}** | **{sum(1 for v in RESULTS.values() for r in v if r['kind'] == 'base')}** | "
         f"**{sum(1 for v in RESULTS.values() for r in v if r['kind'] != 'base')}** |\n")
L.append("No ICD-9 dictionary file is generated; `diagnoses.csv` uses codes from `soen363-phase1/data/icd9_dictionary.csv`. "
         "IDs in every file start at 1.\n")
L.append("## Injected problems per file (rows affected)\n")
L.append("| File | " + " | ".join(n for n, _ in CATS) + " |")
L.append("|---|" + "---:|" * len(CATS))
tot = Counter()
for fname in RESULTS:
    L.append(f"| `{fname}` | " + " | ".join(str(counts[fname][n]) for n, _ in CATS) + " |")
    tot.update(counts[fname])
L.append("| **Total** | " + " | ".join(f"**{tot[n]}**" for n, _ in CATS) + " |")
L.append("| **% of all rows** | " + " | ".join(f"{100 * tot[n] / total_rows:.1f}%" for n, _ in CATS) + " |\n")
L.append("Compared with contract section 7: duplicates (exact + near) "
         f"{100 * (tot['Exact duplicates'] + tot['Near duplicates']) / total_rows:.1f}% (target ~5%), "
         f"missing optional {100 * tot['Missing optional'] / total_rows:.1f}% (~10%), "
         f"missing required {100 * tot['Missing required'] / total_rows:.1f}% (~2%, lower on purpose for patients/admissions), "
         f"case/whitespace {100 * tot['Case / whitespace'] / total_rows:.1f}% (~15%), "
         f"non-standard formats {100 * tot['Non-standard format'] / total_rows:.1f}% (~15%), "
         f"invalid or ambiguous dates {100 * (tot['Invalid date'] + tot['Ambiguous date']) / total_rows:.1f}% (~2%), "
         f"invalid numbers {100 * tot['Invalid number'] / total_rows:.1f}% (~5%), "
         f"broken references {100 * tot['Broken reference'] / total_rows:.1f}% (~2%), "
         f"chronology {100 * tot['Chronology'] / total_rows:.1f}% (~2%).\n")
L.append("## Estimated rejections\n")
L.append("Rows that carry a rejecting problem (duplicate, missing required, invalid/ambiguous date, broken reference, chronology, "
         "unmappable label, fake ICD-9), plus rows that cascade from a rejected patient, admission or request. "
         "Children of near-duplicate patients and admissions are not counted, because the contract re-points them to the kept record. "
         "Treat this as a sanity check, not the answer: your cleaning rules decide the real number.\n")
L.append("| File | Rows | Estimated rejected | of which cascaded | % |")
L.append("|---|---:|---:|---:|---:|")
for fname, rows in RESULTS.items():
    L.append(f"| `{fname}` | {len(rows)} | {rejected[fname]} | {cascade[fname]} | {100 * rejected[fname] / len(rows):.1f}% |")
L.append(f"| **Total** | **{total_rows}** | **{total_rej}** | **{sum(cascade.values())}** | **{100 * total_rej / total_rows:.1f}%** |\n")
L.append("Rows rejected with no rejecting problem of their own: radiology rows whose `RequestNo` points to a rejected request are counted as cascaded here; "
         "since `order_id` is nullable, your cleaning might blank it instead.\n")
L.append("## Problem details per file\n")
for fname in RESULTS:
    L.append(f"### `{fname}`\n")
    items = sorted(DETAIL[fname].items())
    for k, v in items:
        L.append(f"- {k}: {v}")
    for k, v in sorted(fmt_counts[fname].items()):
        L.append(f"- non-standard format: {k}: {v}")
    if not items and not fmt_counts[fname]:
        L.append("- (none beyond duplicates)")
    L.append("")
L.append("### Children re-pointed to near-duplicate parents\n")
L.append("These are **not** errors; per contract section 7 they should be re-pointed to the kept record before checking references.\n")
for k, v in sorted(REPOINTED.items()):
    L.append(f"- {k}: {v}")
L.append("")
L.append("## How duplicates were made\n")
L.append("- **Exact duplicate:** the original row repeated with the **same ID**, sometimes with one field's case or surrounding spaces changed "
         "(still identical after trimming and ignoring case). Placed somewhere after the original.")
L.append("- **Near duplicate:** the same facts under a **new ID** (IDs continue after the last original ID), rendered again so dates, "
         "labels and phone numbers can use another format. They match the contract's duplicate keys: patient = name + DOB, staff = name + role, "
         "admission = patient + admit time, others = admission + timestamp + type. Placed at the end of the file.\n")
L.append("## Source B conventions (for checking your profiling)\n")
L.append("- **Timestamps** are local Africa/Kampala time. Usual format `DD/MM/YYYY HH:MM` (24h). Also present: ISO "
         "(`YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DDTHH:MM`), month-first with AM/PM (`MM/DD/YYYY hh:mm AM`), and a few dash dates "
         "(`NN-NN-YYYY HH:MM`) written in **either** order. Dash dates with a value over 12 can be read; dash dates where both numbers are "
         "12 or less are the injected **ambiguous dates**. A slash date with AM/PM is always month-first; a 24h slash date is always day-first.")
L.append("- **Date of birth**: usually `DD/MM/YYYY`; also ISO, `5 Mar 1980` style, and dash dates (same rule as above).")
L.append("- **Temperature**: about 30% in Fahrenheit (`99.1F`, `99.1 F`, `99.1 °F`, or a bare `99.1`), the rest in Celsius (sometimes `37.2C`/`37.2 °C`). "
         "Other vitals sometimes carry units (`88 bpm`, `96%`, `4/10`, `120/80 mmHg`, `120-80`).")
L.append("- **Missing-value placeholders** (injected): empty, `N/A`, `null`, `-`, `?`; `-1` for numbers; `0000-00-00` for dates. "
         "Values that are legitimately empty (e.g. no `TimeOut` for a current stay, no `RequestNo` for a walk-in exam, no findings for an exam not done, "
         "no `DischargeDateTime` for an active admission, no phone for young children) are written as an empty field and are **not** counted as problems.")
L.append("- **Allergies / medications** with none: `none`, `None`, `NKA`, `no known allergies`, `No Known Allergies` (medications use `none`/`None`/`NKA`). "
         "These mean \"none\", not missing.")
L.append("- **ICD-9 codes**: dictionary codes only, sometimes without the decimal point (`4019`), with extra spaces (` 428.0`), or `38.9` for `038.9`; "
         f"plus fake codes from this list: {', '.join('`' + c + '`' for c in FAKE_ICD)}.")
L.append("- **Invalid numbers** are only in optional triage vitals (e.g. temperature `300`, pulse `-72`, SpO2 `140`, pain `14`, `abc`). "
         "`-1` on its own is the missing-value placeholder, not an invalid number.")
L.append("- **CSV**: UTF-8, comma-delimited, minimal quoting, CRLF line endings. Some clinical notes contain commas, double quotes and line breaks (quoted).\n")
L.append("## Intended label mapping (answer key)\n")
L.append("| Raw column | Standard value | Source B labels |")
L.append("|---|---|---|")
_lab_cols = [("Sex", "sex"), ("Status", "life"), ("AdmissionCategory", "adm_type"), ("AdmStatus", "adm_status"),
             ("TriageCategory", "triage"), ("DiagType", "diag_type"), ("RequestStatus", "order_status"), ("Urgency", "priority"),
             ("ExamStatus", "exam_status"), ("Modality", "modality"), ("Unit", "unit")]
_std = {"ED": "Emergency Department", "WARD": "General Ward", "XR": "X-ray", "US": "Ultrasound"}
for col, key in _lab_cols:
    for canon, (prim, var) in LABELS[key].items():
        L.append(f"| {col} | {_std.get(canon, canon)} | {', '.join('`' + x + '`' for x in [prim] + var)} |")
L.append("")
L.append("Labels that cannot be mapped (injected on purpose, should end up as `UNMAPPED_CATEGORY`):\n")
for col, vals in UNMAPPABLE.items():
    L.append(f"- {col}: {', '.join('`' + v + '`' for v in vals)}")
L.append("")
L.append("Columns with no schema equivalent (ignore or drop): `staff.csv` Title, Department; `triage.csv` TriageDateTime; "
         "`investigation_requests.csv` TestRequested. `Modality` maps to examination_type, which has no fixed list in the contract.\n")
LOG_PATH.write_text("\n".join(L), encoding="utf-8")

print(f"wrote {len(RESULTS)} files, {total_rows} rows, estimated rejected {total_rej} ({100 * total_rej / total_rows:.1f}%)")
for fname, rows in RESULTS.items():
    print(f"  {fname:28s} {len(rows):5d}")
