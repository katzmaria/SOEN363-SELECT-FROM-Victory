"""
Source A raw data generator (SOEN 363 Project Phase 2) - AI-generated, part of the AI disclosure.

STATEMENT: all data produced by this script is entirely fictional, created exclusively for
educational and learning purposes. It does not describe real patients and does not include any
real personal information. Names are random combinations of common French first names and
surnames; addresses, phone numbers, insurance numbers and IDs are random.

Source A: "CHU de Montclair-sur-Loire" (fictional), continent Europe, time zone Europe/Paris
(CET/CEST, with daylight saving time). Pipe-delimited TXT files, one file per entity.

This script only GENERATES raw data. It is not part of the loading / cleaning / import pipeline.

    python docs/ai_prompts/source_a_generator.py      (run from soen363-phase2/)

Writes data/raw/A_txt/*.txt and docs/ai_prompts/source_a_generation_log.md.
Seeded: re-running it reproduces the files exactly (it does not depend on today's date).
"""

import csv
import datetime as dt
import random
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

SEED = 2025
rng = random.Random(SEED)

PHASE2 = Path(__file__).resolve().parents[2]
OUT = PHASE2 / "data" / "raw" / "A_txt"
LOG = PHASE2 / "docs" / "ai_prompts" / "source_a_generation_log.md"
ICD_FILE = PHASE2.parent / "soen363-phase1" / "data" / "icd9_dictionary.csv"

HOSPITAL = "CHU de Montclair-sur-Loire"
TZ = ZoneInfo("Europe/Paris")
START = dt.datetime(2022, 1, 1, 0, 0)
CUTOFF = dt.datetime(2025, 10, 31, 18, 0)        # extract time, local Europe/Paris
N_PATIENTS = 480
N_PROFESSIONALS = 70

# =============================================================================
# Reference data
# =============================================================================
with open(ICD_FILE, encoding="utf-8") as f:
    ICD_CODES = [r["icd9_code"] for r in csv.DictReader(f)]     # the shared Phase 1 dictionary, as text
FAKE_ICD = ["999.99", "123.45", "000.0", "V99.9", "888.8"]
SURGICAL = {"Appendicectomie": ["540.9"], "Cholecystectomie": ["574.00", "574.20"],
            "Osteosynthese col du femur": ["820.8"], "Pontage aorto-coronarien": ["414.01", "410.9"],
            "Coronarographie": ["410.9", "414.01", "786.50"], "Cure de hernie inguinale": ["550.90"]}
SURGICAL = {k: [c for c in v if c in ICD_CODES] or [rng.choice(ICD_CODES)] for k, v in SURGICAL.items()}
NEWBORN_CODES = [c for c in ["276.51", "285.9", "599.0", "486", "780.39"] if c in ICD_CODES]

FIRST_F = ["Camille", "Lea", "Manon", "Chloe", "Ines", "Jade", "Louise", "Emma", "Sarah", "Juliette", "Anne", "Claire",
           "Sophie", "Isabelle", "Nathalie", "Sandrine", "Celine", "Aurelie", "Helene", "Margaux", "Lucie", "Elise",
           "Agathe", "Mathilde", "Pauline", "Marie", "Jeanne", "Odile", "Brigitte", "Monique", "Josette", "Yvette"]
FIRST_M = ["Lucas", "Hugo", "Louis", "Gabriel", "Arthur", "Jules", "Adam", "Nathan", "Thomas", "Nicolas", "Julien",
           "Pierre", "Antoine", "Laurent", "Olivier", "Philippe", "Christophe", "Stephane", "Eric", "Mathieu",
           "Bernard", "Michel", "Alain", "Jacques", "Rene", "Marcel", "Andre", "Yves", "Gerard", "Francois", "Remi"]
SURNAMES = ["Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand", "Leroy", "Moreau",
            "Simon", "Laurent", "Lefebvre", "Michel", "Garcia", "David", "Bertrand", "Roux", "Vincent", "Fournier",
            "Morel", "Girard", "Andre", "Lefevre", "Mercier", "Dupont", "Lambert", "Bonnet", "Francois", "Martinez",
            "Legrand", "Garnier", "Faure", "Rousseau", "Blanc", "Guerin", "Muller", "Henry", "Roussel", "Nicolas",
            "Perrin", "Morin", "Mathieu", "Clement", "Gauthier", "Dumont", "Lopez", "Fontaine", "Chevalier", "Robin",
            "Masson", "Sanchez", "Boyer", "Denis", "Lemaire", "Duval", "Joly", "Gautier", "Roger", "Roche",
            "Le Gall", "Le Roux", "de La Tour", "Saint-Clair", "O'Neill", "Da Silva"]
STREETS = ["rue des Tilleuls", "avenue de la Loire", "rue Victor Hugo", "boulevard Pasteur", "place du Marche",
           "rue des Ecoles", "chemin des Vignes", "rue de la Gare", "allee des Peupliers", "rue du Moulin",
           "impasse des Lilas", "quai Saint-Martin", "rue Jean Jaures", "avenue des Acacias", "rue Pierre Curie"]
TOWNS = ["Montclair-sur-Loire", "Saint-Avold-le-Haut", "Bellerive-en-Val", "Vernay", "Chasseneuil-Bas", "Les Ormeaux"]
INSURERS = ["Mutuelle Generale", "Harmonie Sante", "MGEN", "Mutuelle des Vallees", "Prevoyance Loire", "Sante Plus"]

ROLE_PLAN = [("physician", 24), ("nurse", 20), ("surgeon", 8), ("radiologist", 6), ("radiology technician", 12)]
SERVICES = {"physician": ["Urgences", "Medecine interne", "Cardiologie", "Pneumologie", "Reanimation", "Pediatrie"],
            "nurse": ["Urgences", "Medecine interne", "Reanimation", "Cardiologie"], "surgeon": ["Chirurgie viscerale",
            "Chirurgie orthopedique", "Chirurgie cardiaque"], "radiologist": ["Imagerie"], "radiology technician": ["Imagerie"]}
TITLES = {"physician": "Dr", "surgeon": "Pr", "radiologist": "Dr", "nurse": "", "radiology technician": ""}

SYMPTOMS = ["chest pain", "shortness of breath", "fever", "abdominal pain", "dizziness", "headache", "cough",
            "nausea", "fall", "weakness", "confusion", "palpitations"]
REASONS = ["Chest pain", "Shortness of breath", "Fever", "Abdominal pain", "Fall at home", "Syncope", "Confusion",
           "Cough and fever", "Palpitations", "Planned surgery", "Follow-up investigation", "General weakness"]
ALLERGIES = ["Penicillin", "Latex", "Sulfa drugs", "Peanuts", "Iodine contrast", "Aspirin"]
MEDS = ["Aspirin 75 mg", "Bisoprolol 2.5 mg", "Atorvastatin 20 mg", "Metformin 850 mg", "Ramipril 5 mg",
        "Furosemide 40 mg", "Levothyroxine 50 mcg", "Amoxicillin 1 g", "Paracetamol 1 g"]
NONE_ALLERGY = ["none", "None", "NKA", "no known allergies", "No Known Allergies", "aucune"]
NONE_MEDS = ["none", "None", "NKA", "aucun"]
EXAMS = {"Chest X-ray": "RADIO THORAX", "CT scan": "SCANNER", "MRI": "IRM", "Ultrasound": "ECHOGRAPHIE",
         "ECG": "ECG", "Blood panel": "BILAN SANGUIN"}
IMAGING = {"Chest X-ray": "Thorax", "CT scan": "Abdomen", "MRI": "Crane", "Ultrasound": "Abdomen"}
INDICATIONS = ["Rule out infection", "Rule out fracture", "Rule out ischaemia", "Rule out obstruction",
               "Rule out bleeding", "Follow-up of known lesion", "Pre-operative assessment"]
FINDINGS = ["No acute findings.", "Consolidation in the right lower lobe.", "Small pleural effusion.",
            "Findings consistent with clinical suspicion.", "Mild degenerative changes.", "No fracture seen."]
OUTCOMES = ["Succes", "Succes", "Succes", "Succes", "Succes", "Complications", "Echec"]
DESTINATIONS = ["Domicile", "Domicile avec aide", "SSR (reeducation)", "EHPAD", "Transfert autre hopital"]
CONDITIONS = ["Stable", "Ameliore", "Moyen"]
FOLLOWUP = ["Follow up with the GP in 2 weeks.", "Return to the emergency department if symptoms worsen.",
            "Rest and hydration.", "Outpatient clinic appointment booked.", "Physiotherapy twice a week."]
TRANSFER_REASONS = ["condition worsened", "condition improved", "monitoring required", "post-operative care"]
SOURCES_ADM = ["Domicile", "SAMU", "Medecin traitant", "Transfert"]

# Standard value -> (primary Source A label, alternative Source A labels). Labels are French codes.
LABELS = {
    "admission_type": {"emergency": ("URGENCE", ["URG", "SAU", "Urgences"]),
                       "urgent": ("SEMI-URGENT", ["SEMI URG", "Semi-urgence"]),
                       "elective": ("PROGRAMME", ["PROG", "Programmee", "HOSPIT PROGRAMMEE"]),
                       "outpatient": ("AMBULATOIRE", ["AMBU", "HDJ", "Hopital de jour"]),
                       "newborn": ("NAISSANCE", ["NOUVEAU-NE", "NN"])},
    "admission_status": {"discharged": ("SORTI", ["SORTIE", "Sorti(e)"]), "deceased": ("DECEDE", ["DCD", "Decede(e)"]),
                         "active": ("HOSPITALISE", ["EN COURS", "Present"])},
    "life_status": {"alive": ("VIVANT", ["V", "Vivant(e)"]), "deceased": ("DECEDE", ["DCD", "Decede(e)"])},
    "sex": {"female": ("F", ["Femme", "FEM"]), "male": ("M", ["Homme", "H", "MASC"]), "unknown": ("I", ["Indetermine"])},
    "triage": {"high": ("1", ["ROUGE", "Tri 1"]), "medium": ("2", ["ORANGE", "Tri 2"]), "low": ("3", ["VERT", "Tri 3"])},
    "unit": {"Emergency Department": ("URGENCES", ["SAU", "Urgences adultes"]),
             "ICU": ("REA", ["Reanimation", "REA POLY"]), "CCU": ("USIC", ["Soins intensifs cardio", "USIC CARDIO"]),
             "MICU": ("REA MED", ["Rea medicale", "REA-MED"]), "SICU": ("REA CHIR", ["Rea chirurgicale", "REA-CHIR"]),
             "General Ward": ("MEDECINE", ["MED", "Hospitalisation conventionnelle"])},
    "order_status": {"pending": ("EN ATTENTE", ["Demande", "ATT"]), "in_progress": ("EN COURS", ["En cours de realisation"]),
                     "completed": ("TERMINE", ["Fait", "REALISE"]), "cancelled": ("ANNULE", ["Annule", "ANN"])},
    "priority": {"routine": ("NORMALE", ["Routine", "N"]), "urgent": ("URGENTE", ["URG", "U"]),
                 "stat": ("IMMEDIATE", ["STAT", "Immediat"])},
    "exam_status": {"scheduled": ("PROGRAMME", ["RDV pris", "Planifie"]), "completed": ("REALISE", ["Fait", "Interprete"]),
                    "cancelled": ("ANNULE", ["Annule"])},
    "dx_type": {"primary": ("DP", ["Principal", "P"]), "secondary": ("DAS", ["Associe", "S"])},
    "note_type": {"discharge_summary": ("CRH", ["Compte rendu de sortie", "CR SORTIE"]),
                  "operative_note": ("CRO", ["Compte rendu operatoire"]),
                  "progress_note": ("OBSERVATION", ["Obs medicale"])},
    "role": {"physician": ("MEDECIN", ["Medecin", "PH"]), "nurse": ("IDE", ["Infirmier(e)", "INF"]),
             "surgeon": ("CHIRURGIEN", ["Chirurgien"]), "radiologist": ("RADIOLOGUE", ["Radiologue"]),
             "radiology technician": ("MANIP RADIO", ["Manipulateur radio", "MERM"])},
}
UNMAPPABLE = {"admission_type": ["AUTRE", "DIVERS"], "triage": ["5", "GRIS"], "unit": ["USC", "SSR"],
              "order_status": ["SUSPENDU"], "priority": ["A VOIR"], "exam_status": ["EN ATTENTE CR"]}
LABEL_VARIANT_P = 0.06

# =============================================================================
# 1) Canonical (correct) hospital data
# =============================================================================
def rand_dt(a, b):
    return a + dt.timedelta(seconds=rng.randint(0, max(0, int((b - a).total_seconds()))))


def real_local(d):
    """Move a wall-clock time out of the spring-forward gap (those times never happen in Paris)."""
    a, b = d.replace(tzinfo=TZ, fold=0), d.replace(tzinfo=TZ, fold=1)
    if a.utcoffset() != b.utcoffset() and a.astimezone(dt.timezone.utc).astimezone(TZ).replace(tzinfo=None) != d:
        return d + dt.timedelta(hours=1)
    return d.replace(second=0, microsecond=0)


def person_name(sex):
    first = rng.choice(FIRST_F if sex == "female" else FIRST_M if sex == "male" else FIRST_F + FIRST_M)
    return first, rng.choice(SURNAMES)


def phone_digits():
    return rng.choice(["6", "7", "1", "2", "3", "4", "5"]) + "".join(str(rng.randint(0, 9)) for _ in range(8))


pros, by_role = [], defaultdict(list)
pid = 0
for role, n in ROLE_PLAN:
    for _ in range(n):
        pid += 1
        first, last = person_name(rng.choice(["female", "male"]))
        pros.append({"id": pid, "first": first, "last": last, "role": role, "service": rng.choice(SERVICES[role]),
                     "title": TITLES[role]})
        by_role[role].append(pid)

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
    first, last = person_name(sex)
    pat = {"id": p_id, "first": first, "last": last, "sex": sex, "dob": None,
           "address": f"{rng.randint(1, 140)} {rng.choice(STREETS)}, {rng.randint(10, 99)}{rng.randint(100, 999)} {rng.choice(TOWNS)}",
           "phone": phone_digits(), "contact": f"{rng.choice(FIRST_F + FIRST_M)} {rng.choice(SURNAMES)}",
           "contact_phone": phone_digits(), "life": "alive"}
    patients.append(pat)
    n_adm = rng.choices([0, 1, 2, 3, 4, 5], [12, 48, 24, 10, 4, 2])[0]
    cursor = real_local(rand_dt(START, CUTOFF - dt.timedelta(days=300)))
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
        disch = real_local(admit + los)
        if disch > CUTOFF or (admit > CUTOFF - dt.timedelta(days=12) and rng.random() < .5):
            status, disch = "active", None
        if status == "deceased":
            pat["life"] = "deceased"
        if atype == "newborn":
            pat["dob"] = admit.date()
        adm = {"id": a_id, "patient": p_id, "doctor": staff("physician"), "admit": admit, "type": atype,
               "reason": "Birth" if atype == "newborn" else ("Planned surgery" if atype == "elective" and rng.random() < .3
                                                              else rng.choice(REASONS)),
               "source": rng.choice(SOURCES_ADM), "insurance": f"CPAM {rng.randint(1, 95):02d} / {rng.choice(INSURERS)} "
                                                              f"n{rng.randint(100000, 999999)}",
               "discharge": disch, "status": status}
        adms.append(adm)
        end = disch or CUTOFF

        # triage: one per admission, sometimes a re-assessment
        prio_w = {"emergency": [55, 35, 10], "urgent": [20, 55, 25]}.get(atype, [5, 30, 65])
        for j in range(2 if rng.random() < .06 else 1):
            hr = rng.randint(55, 125)
            triage.append({"id": nid("triage"), "admission": a_id, "nurse": staff("nurse"),
                           "time": real_local(admit + dt.timedelta(minutes=rng.randint(5, 25) + 45 * j)),
                           "bp": (rng.randint(100, 170), rng.randint(60, 100)), "hr": hr, "rr": rng.randint(12, 28),
                           "temp": round(rng.uniform(36.0, 39.8), 1), "spo2": rng.randint(88, 100),
                           "pain": rng.randint(0, 10), "symptoms": ", ".join(rng.sample(SYMPTOMS, rng.randint(1, 3))),
                           "allergies": rng.choice(ALLERGIES) if rng.random() < .45 else rng.choice(NONE_ALLERGY),
                           "meds": rng.choice(MEDS) if rng.random() < .65 else rng.choice(NONE_MEDS),
                           "priority": rng.choices(["high", "medium", "low"], prio_w)[0]})

        # unit stays, in order, inside the admission
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
        t = real_local(admit + dt.timedelta(minutes=30))
        span = (end - t).total_seconds()
        adm_stays = []
        for j, unit in enumerate(path):
            last_one = j == len(path) - 1
            dur = dt.timedelta(seconds=span / (len(path) - j) * rng.uniform(.6, 1.0))
            exit_t = None if (last_one and disch is None) else (disch if last_one else real_local(t + dur))
            s = {"id": nid("stay"), "admission": a_id, "doctor": staff("physician"), "unit": unit,
                 "room": f"{unit[:3].upper()}-{rng.randint(1, 40):02d}", "bed": str(rng.randint(1, 4)),
                 "entry": t, "exit": exit_t, "reason": None if j == 0 else rng.choice(TRANSFER_REASONS)}
            stays.append(s)
            adm_stays.append(s)
            span -= dur.total_seconds()
            t = exit_t or t

        # surgery (placed before the first critical-care entry when there is one)
        proc_time = None
        if atype in ("emergency", "urgent", "elective") and disch is not None and rng.random() < .16:
            proc_name = rng.choice(list(SURGICAL))
            crit = [s for s in adm_stays if s["unit"] in ("ICU", "CCU", "MICU", "SICU")]
            hi = crit[0]["entry"] - dt.timedelta(minutes=30) if crit else admit + (disch - admit) / 2
            lo = admit + dt.timedelta(hours=1)
            proc_time = real_local(rand_dt(lo, hi if hi > lo else lo + dt.timedelta(minutes=30)))
            procs.append({"id": nid("procedure"), "admission": a_id, "surgeon": staff("surgeon"), "type": proc_name,
                          "time": proc_time, "outcome": rng.choice(OUTCOMES)})
            notes.append({"id": nid("note"), "admission": a_id, "author": procs[-1]["surgeon"], "type": "operative_note",
                          "time": real_local(proc_time + dt.timedelta(hours=2)),
                          "text": f"Operative note. {proc_name} performed. Patient tolerated the procedure."})

        # diagnoses: completed admissions get exactly one primary
        if status != "active" or rng.random() < .5:
            if atype == "newborn":
                primary = rng.choice(NEWBORN_CODES)
            elif procs and procs[-1]["admission"] == a_id:
                primary = rng.choice(SURGICAL[procs[-1]["type"]])
            else:
                primary = rng.choice(ICD_CODES)
            codes = [primary] + rng.sample([c for c in ICD_CODES if c != primary], rng.choice([0, 1, 1, 2, 3]))
            for n_, code in enumerate(codes):
                tdx = real_local(min(admit + dt.timedelta(hours=rng.randint(1, 20)), end - dt.timedelta(minutes=5)))
                dxs.append({"id": nid("diagnosis"), "patient": p_id, "admission": a_id, "code": code,
                            "doctor": staff("physician"), "time": max(tdx, admit),
                            "type": "primary" if n_ == 0 else "secondary"})

        # orders and radiology
        for _o in range(rng.choices([0, 1, 2], [45, 40, 15])[0]):
            exam = rng.choice(list(EXAMS))
            ot = real_local(rand_dt(admit, min(end, admit + dt.timedelta(days=3))))
            o_status = rng.choices(["completed", "pending", "in_progress", "cancelled"], [75, 10, 8, 7])[0]
            if disch is None and o_status == "completed" and rng.random() < .3:
                o_status = "in_progress"
            o = {"id": nid("order"), "admission": a_id, "doctor": staff("physician"), "time": ot, "exam": exam,
                 "reason": rng.choice(INDICATIONS), "status": o_status,
                 "priority": rng.choices(["routine", "urgent", "stat"], [55, 30, 15])[0]}
            orders.append(o)
            if exam in IMAGING and o_status in ("completed", "in_progress", "cancelled"):
                et = real_local(max(ot, min(ot + dt.timedelta(hours=rng.randint(1, 10)), end - dt.timedelta(minutes=10))))
                st = {"completed": "completed", "in_progress": "scheduled", "cancelled": "cancelled"}[o_status]
                rads.append({"id": nid("radiology"), "admission": a_id, "order": o["id"], "referrer": o["doctor"],
                             "tech": staff("radiology technician"), "type": exam, "time": et, "area": IMAGING[exam],
                             "status": st, "link": f"pacs://chu-montclair/{a_id}/{nid('img')}",
                             "findings": rng.choice(FINDINGS) if st == "completed" else None})
        if rng.random() < .05:   # walk-in exam without an order (order_id is nullable)
            exam = rng.choice(list(IMAGING))
            rads.append({"id": nid("radiology"), "admission": a_id, "order": None, "referrer": adm["doctor"],
                         "tech": staff("radiology technician"), "type": exam,
                         "time": real_local(rand_dt(admit, end - dt.timedelta(minutes=10)) if end > admit + dt.timedelta(minutes=20) else admit),
                         "area": IMAGING[exam], "status": "completed",
                         "link": f"pacs://chu-montclair/{a_id}/{nid('img')}", "findings": rng.choice(FINDINGS)})

        # progress notes, discharge summary and discharge record
        for _n in range(rng.choices([0, 1, 2], [40, 40, 20])[0]):
            notes.append({"id": nid("note"), "admission": a_id, "author": staff("physician"), "type": "progress_note",
                          "time": real_local(rand_dt(admit, end)),
                          "text": rng.choice(["Patient reviewed on the ward round. Plan unchanged.",
                                              "Observations stable overnight. Continue current treatment.",
                                              "Family updated, questions answered.",
                                              "Pain better controlled; mobilising with help."])})
        if disch is not None:
            died = status == "deceased"
            recov = rng.choice(["Recovery", "recovery", "RECOVERY"]) if rng.random() < .45 else None
            text = (f"Discharge summary. Admitted for {adm['reason'].lower()}. "
                    + ("Patient died during the stay." if died else
                       (f"{recov} progressing well." if recov else "Condition stable at discharge.")))
            notes.append({"id": nid("note"), "admission": a_id, "author": adm["doctor"], "type": "discharge_summary",
                          "time": disch, "text": text})
            dischs.append({"id": nid("discharge"), "admission": a_id, "doctor": staff("physician"), "time": disch,
                           "destination": "Chambre mortuaire" if died else rng.choice(DESTINATIONS),
                           "condition": "Decede" if died else rng.choice(CONDITIONS),
                           "meds": None if died else rng.choice(MEDS + ["none"]),
                           "advice": None if died else rng.choice(FOLLOWUP),
                           "appointment": None if died else real_local(disch + dt.timedelta(days=rng.randint(10, 45),
                                                                                             hours=rng.randint(0, 6)))})
        cursor = real_local((disch or admit) + dt.timedelta(days=rng.randint(30, 300)))

    # date of birth before the first admission (newborns already have theirs)
    if pat["dob"] is None:
        ref = (first_adm or CUTOFF).date()
        pat["dob"] = ref - dt.timedelta(days=rng.randint(365, 95 * 365))

# =============================================================================
# 2) Rendering to Source A's raw formats
# =============================================================================
MOIS = ["janv.", "fevr.", "mars", "avr.", "mai", "juin", "juil.", "aout", "sept.", "oct.", "nov.", "dec."]
PLACEHOLDERS = ["", "N/A", "null", "-", "?"]


def fmt_dt(d, tags):
    """Usual format DD/MM/YYYY HH:MM (24h, local Paris time)."""
    r = rng.random()
    if r < 0.95:
        return d.strftime("%d/%m/%Y %H:%M")
    if r < 0.965:
        tags.add("fmt_date_iso")
        return d.strftime(rng.choice(["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M"]))
    if r < 0.98:
        tags.add("fmt_date_french_h")                 # 08/05/2024 14h59
        return d.strftime("%d/%m/%Y ") + f"{d.hour:02d}h{d.minute:02d}"
    if r < 0.995 or d.day <= 12:
        tags.add("fmt_date_dots")                     # 08.05.2024 14:59 (always day-first)
        return d.strftime("%d.%m.%Y %H:%M")
    tags.add("fmt_date_dash")                         # dash date, order mixed, but day > 12 so readable
    return d.strftime("%d-%m-%Y %H:%M") if rng.random() < .5 else d.strftime("%m-%d-%Y %H:%M")


def fmt_date(d, tags):
    r = rng.random()
    if r < 0.88:
        return d.strftime("%d/%m/%Y")
    if r < 0.94:
        tags.add("fmt_date_iso")
        return d.strftime("%Y-%m-%d")
    if r < 0.98 or d.day <= 12:
        tags.add("fmt_date_text")                     # 5 mars 1980
        return f"{d.day} {MOIS[d.month - 1]} {d.year}"
    tags.add("fmt_date_dash")
    return d.strftime("%d-%m-%Y") if rng.random() < .5 else d.strftime("%m-%d-%Y")


def fmt_label(key, v, tags):
    primary, variants = LABELS[key][v]
    if rng.random() < LABEL_VARIANT_P:
        tags.add("fmt_label")
        return rng.choice(variants)
    return primary


def fmt_phone(d, tags):
    norm = "0" + d
    pretty = " ".join(norm[i:i + 2] for i in range(0, 10, 2))
    if rng.random() < .92:
        return pretty
    tags.add("fmt_phone")
    return rng.choice([f"+33 {d[0]} {pretty[3:]}", norm, pretty.replace(" ", "."), f"+33{d}"])


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


def comma(x):
    return str(x).replace(".", ",")


def fmt_vital(col, v, tags):
    if col == "tension":
        s, d_ = v
        if rng.random() < .95:
            return f"{s}/{d_}"
        tags.add("fmt_vital_units")
        return rng.choice([f"{s} / {d_}", f"{s}-{d_}", f"{s}/{d_} mmHg"])
    if col == "temperature":
        if rng.random() < .30:                         # Fahrenheit
            tags.add("fmt_temp_fahrenheit")
            f_ = comma(round(v * 9 / 5 + 32, 1))
            return rng.choice([f"{f_}F", f"{f_} F", f"{f_}", f"{f_} °F"])
        if rng.random() < .08:
            tags.add("fmt_vital_units")
            return rng.choice([f"{comma(v)}C", f"{comma(v)} °C", f"{comma(v)}°C"])
        return comma(v)
    suffix = {"pouls": [" bpm", "/min"], "freq_resp": ["/min", " c/min"], "spo2": ["%", " %"], "eva": ["/10"]}[col]
    if rng.random() < .05:
        tags.add("fmt_vital_units")
        return f"{v}{rng.choice(suffix)}"
    return str(v)


def txt(v):
    return "" if v is None else str(v)


# File specs: name, entity, columns, required (NOT NULL in the schema), optional (droppable), date columns
SPECS = {
    "professionnels.txt": dict(entity="HealthcareProfessional",
                               cols=["id_pro", "titre", "nom_prenom", "fonction", "service"],
                               req=["nom_prenom", "fonction"], opt=[], dates=[], fk={}),
    "patients.txt": dict(entity="Patient",
                         cols=["num_patient", "nom", "prenom", "date_naissance", "sexe", "adresse", "telephone",
                               "personne_a_prevenir", "statut_vital"],
                         req=["nom", "date_naissance"], opt=["sexe", "adresse", "telephone", "personne_a_prevenir"],
                         dates=["date_naissance"], fk={}),
    "sejours.txt": dict(entity="Admission",
                        cols=["num_sejour", "num_patient", "medecin_entree", "date_heure_entree", "type_sejour",
                              "motif", "provenance", "couverture", "date_heure_sortie", "statut_sejour"],
                        req=["date_heure_entree", "type_sejour", "motif"], opt=["provenance", "couverture"],
                        dates=["date_heure_entree"], fk={"num_patient": "patient", "medecin_entree": "pro"}),
    "triage.txt": dict(entity="TriageAssessment",
                       cols=["num_triage", "num_sejour", "ide", "date_heure_triage", "tension", "pouls", "freq_resp",
                             "temperature", "spo2", "eva", "symptomes", "allergies", "traitement_habituel", "niveau_tri"],
                       req=["num_sejour", "ide", "niveau_tri"],
                       opt=["tension", "pouls", "freq_resp", "temperature", "spo2", "eva", "symptomes", "allergies",
                            "traitement_habituel"],
                       dates=["date_heure_triage"], fk={"num_sejour": "admission", "ide": "pro"}),
    "diagnostics.txt": dict(entity="Diagnosis",
                            cols=["num_diag", "num_patient", "num_sejour", "code_cim9", "medecin", "date_heure_diag",
                                  "type_diag"],
                            req=["num_sejour", "code_cim9", "medecin", "date_heure_diag", "type_diag"], opt=[],
                            dates=["date_heure_diag"], fk={"num_sejour": "admission", "medecin": "pro"}),
    "notes_cliniques.txt": dict(entity="ClinicalNote",
                                cols=["num_note", "num_sejour", "auteur", "type_note", "date_heure_note", "texte"],
                                req=["num_sejour", "auteur", "type_note", "date_heure_note", "texte"], opt=[],
                                dates=["date_heure_note"], fk={"num_sejour": "admission", "auteur": "pro"}),
    "demandes_examens.txt": dict(entity="DiagnosticOrder",
                                 cols=["num_demande", "num_sejour", "prescripteur", "date_heure_demande", "examen",
                                       "indication", "statut_demande", "priorite"],
                                 req=["num_sejour", "prescripteur", "date_heure_demande", "indication",
                                      "statut_demande", "priorite"], opt=[],
                                 dates=["date_heure_demande"], fk={"num_sejour": "admission", "prescripteur": "pro"}),
    "imagerie.txt": dict(entity="RadiologyExamination",
                         cols=["num_examen", "num_sejour", "num_demande", "medecin_demandeur", "manipulateur",
                               "type_examen", "date_heure_examen", "zone", "statut_examen", "lien_pacs", "conclusion"],
                         req=["num_sejour", "medecin_demandeur", "manipulateur", "type_examen", "date_heure_examen",
                              "statut_examen"],
                         opt=["zone", "lien_pacs", "conclusion"], dates=["date_heure_examen"],
                         fk={"num_sejour": "admission", "medecin_demandeur": "pro", "num_demande": "order"}),
    "bloc_operatoire.txt": dict(entity="SurgicalProcedure",
                                cols=["num_intervention", "num_sejour", "chirurgien", "intervention",
                                      "date_heure_intervention", "resultat"],
                                req=["num_sejour", "chirurgien", "intervention", "date_heure_intervention"],
                                opt=["resultat"], dates=["date_heure_intervention"],
                                fk={"num_sejour": "admission", "chirurgien": "pro"}),
    "mouvements.txt": dict(entity="UnitStay",
                           cols=["num_mouvement", "num_sejour", "medecin_responsable", "unite", "chambre", "lit",
                                 "date_heure_entree", "date_heure_sortie", "motif_transfert"],
                           req=["num_sejour", "medecin_responsable", "unite", "date_heure_entree"],
                           opt=["chambre", "lit", "motif_transfert"], dates=["date_heure_entree"],
                           fk={"num_sejour": "admission", "medecin_responsable": "pro"}),
    "sorties.txt": dict(entity="DischargeRecord",
                        cols=["num_sortie", "num_sejour", "medecin_signataire", "date_heure_sortie", "destination",
                              "etat_sortie", "ordonnance", "consignes", "prochain_rdv"],
                        req=["num_sejour", "medecin_signataire", "date_heure_sortie"],
                        opt=["destination", "etat_sortie", "ordonnance", "consignes", "prochain_rdv"],
                        dates=["date_heure_sortie"], fk={"num_sejour": "admission", "medecin_signataire": "pro"}),
}

# Rates per file (fraction of the file's original rows). Parents (patients, admissions) on the low end.
RATES = {
    "professionnels.txt": dict(missing_req=.02, bad_date=0, broken=0, chrono=0, case_ws=.10, unmap=0),
    "patients.txt": dict(missing_req=.006, bad_date=.005, broken=0, chrono=0, case_ws=.16, unmap=0),
    "sejours.txt": dict(missing_req=.006, bad_date=.004, broken=.004, chrono=.005, case_ws=.17, unmap=.003),
    "triage.txt": dict(missing_req=.018, bad_date=0, broken=.018, chrono=0, case_ws=.17, unmap=.003),
    "diagnostics.txt": dict(missing_req=.018, bad_date=.018, broken=.018, chrono=.018, case_ws=.16, unmap=0),
    "notes_cliniques.txt": dict(missing_req=.018, bad_date=.018, broken=.018, chrono=.018, case_ws=.16, unmap=0),
    "demandes_examens.txt": dict(missing_req=.018, bad_date=.018, broken=.018, chrono=.018, case_ws=.16, unmap=.004),
    "imagerie.txt": dict(missing_req=.02, bad_date=.02, broken=.02, chrono=.02, case_ws=.16, unmap=.005),
    "bloc_operatoire.txt": dict(missing_req=.02, bad_date=.02, broken=.02, chrono=.02, case_ws=.15, unmap=0),
    "mouvements.txt": dict(missing_req=.018, bad_date=.018, broken=.018, chrono=.018, case_ws=.16, unmap=.003),
    "sorties.txt": dict(missing_req=.018, bad_date=.018, broken=.018, chrono=.02, case_ws=.16, unmap=0),
}
MISSING_OPT_RATE = .21
INVALID_VITAL_RATE = .47      # share of triage rows with one invalid vital sign
EXACT_DUP = .019
NEAR_DUP = .029
DETAIL = defaultdict(Counter)
adm_by_id = {a["id"]: a for a in adms}
pat_by_id = {p["id"]: p for p in patients}
order_by_id = {o["id"]: o for o in orders}


def row(fname, rid, canon, raw, tags=None):
    return {"file": fname, "id": rid, "canon": canon, "raw": raw, "tags": set(tags or ()), "touched": set(),
            "parent_adm": canon.get("_adm"), "parent_pat": canon.get("_pat"), "parent_order": canon.get("_order")}


def render_all():
    R = {}
    t = set()

    def fresh():
        nonlocal t
        t = set()
        return t
    R["professionnels.txt"] = []
    for p in pros:
        tg = fresh()
        R["professionnels.txt"].append(row("professionnels.txt", p["id"], {"_key": (p["first"], p["last"], p["role"])}, {
            "id_pro": str(p["id"]), "titre": p["title"], "nom_prenom": f"{p['first']} {p['last'].upper()}",
            "fonction": fmt_label("role", p["role"], tg), "service": p["service"]}, tg))
    R["patients.txt"] = []
    for p in patients:
        tg = fresh()
        R["patients.txt"].append(row("patients.txt", p["id"], {"date_naissance": p["dob"], "_key": (p["first"], p["last"], p["dob"])}, {
            "num_patient": str(p["id"]), "nom": p["last"].upper(), "prenom": p["first"],
            "date_naissance": fmt_date(p["dob"], tg), "sexe": fmt_label("sex", p["sex"], tg),
            "adresse": p["address"], "telephone": fmt_phone(p["phone"], tg),
            "personne_a_prevenir": f"{p['contact']} ({fmt_phone(p['contact_phone'], tg)})",
            "statut_vital": fmt_label("life_status", p["life"], tg)}, tg))
    R["sejours.txt"] = []
    for a in adms:
        tg = fresh()
        R["sejours.txt"].append(row("sejours.txt", a["id"], {"date_heure_entree": a["admit"], "_pat": a["patient"],
                                                              "_key": (a["patient"], a["admit"])}, {
            "num_sejour": str(a["id"]), "num_patient": str(a["patient"]), "medecin_entree": str(a["doctor"]),
            "date_heure_entree": fmt_dt(a["admit"], tg), "type_sejour": fmt_label("admission_type", a["type"], tg),
            "motif": a["reason"], "provenance": a["source"], "couverture": a["insurance"],
            "date_heure_sortie": fmt_dt(a["discharge"], tg) if a["discharge"] else "",
            "statut_sejour": fmt_label("admission_status", a["status"], tg)}, tg))
    R["triage.txt"] = []
    for x in triage:
        tg = fresh()
        R["triage.txt"].append(row("triage.txt", x["id"], {"date_heure_triage": x["time"], "_adm": x["admission"],
                                                            "_key": (x["admission"], x["time"], x["priority"])}, {
            "num_triage": str(x["id"]), "num_sejour": str(x["admission"]), "ide": str(x["nurse"]),
            "date_heure_triage": fmt_dt(x["time"], tg), "tension": fmt_vital("tension", x["bp"], tg),
            "pouls": fmt_vital("pouls", x["hr"], tg), "freq_resp": fmt_vital("freq_resp", x["rr"], tg),
            "temperature": fmt_vital("temperature", x["temp"], tg), "spo2": fmt_vital("spo2", x["spo2"], tg),
            "eva": fmt_vital("eva", x["pain"], tg), "symptomes": x["symptoms"], "allergies": x["allergies"],
            "traitement_habituel": x["meds"], "niveau_tri": fmt_label("triage", x["priority"], tg)}, tg))
    R["diagnostics.txt"] = []
    for x in dxs:
        tg = fresh()
        R["diagnostics.txt"].append(row("diagnostics.txt", x["id"], {"date_heure_diag": x["time"], "_adm": x["admission"],
                                                                      "_key": (x["admission"], x["time"], x["code"])}, {
            "num_diag": str(x["id"]), "num_patient": str(x["patient"]), "num_sejour": str(x["admission"]),
            "code_cim9": fmt_icd(x["code"], tg), "medecin": str(x["doctor"]), "date_heure_diag": fmt_dt(x["time"], tg),
            "type_diag": fmt_label("dx_type", x["type"], tg)}, tg))
    R["notes_cliniques.txt"] = []
    for x in notes:
        tg = fresh()
        R["notes_cliniques.txt"].append(row("notes_cliniques.txt", x["id"], {"date_heure_note": x["time"], "_adm": x["admission"],
                                                                              "_key": (x["admission"], x["time"], x["type"])}, {
            "num_note": str(x["id"]), "num_sejour": str(x["admission"]), "auteur": str(x["author"]),
            "type_note": fmt_label("note_type", x["type"], tg), "date_heure_note": fmt_dt(x["time"], tg),
            "texte": x["text"]}, tg))
    R["demandes_examens.txt"] = []
    for x in orders:
        tg = fresh()
        R["demandes_examens.txt"].append(row("demandes_examens.txt", x["id"], {"date_heure_demande": x["time"], "_adm": x["admission"],
                                                                                "_key": (x["admission"], x["time"], x["exam"])}, {
            "num_demande": str(x["id"]), "num_sejour": str(x["admission"]), "prescripteur": str(x["doctor"]),
            "date_heure_demande": fmt_dt(x["time"], tg), "examen": EXAMS[x["exam"]], "indication": x["reason"],
            "statut_demande": fmt_label("order_status", x["status"], tg),
            "priorite": fmt_label("priority", x["priority"], tg)}, tg))
    R["imagerie.txt"] = []
    for x in rads:
        tg = fresh()
        R["imagerie.txt"].append(row("imagerie.txt", x["id"], {"date_heure_examen": x["time"], "_adm": x["admission"],
                                                                "_order": x["order"], "_key": (x["admission"], x["time"], x["type"])}, {
            "num_examen": str(x["id"]), "num_sejour": str(x["admission"]), "num_demande": txt(x["order"]),
            "medecin_demandeur": str(x["referrer"]), "manipulateur": str(x["tech"]), "type_examen": EXAMS[x["type"]],
            "date_heure_examen": fmt_dt(x["time"], tg), "zone": x["area"],
            "statut_examen": fmt_label("exam_status", x["status"], tg), "lien_pacs": x["link"],
            "conclusion": txt(x["findings"])}, tg))
    R["bloc_operatoire.txt"] = []
    for x in procs:
        tg = fresh()
        R["bloc_operatoire.txt"].append(row("bloc_operatoire.txt", x["id"], {"date_heure_intervention": x["time"], "_adm": x["admission"],
                                                                              "_key": (x["admission"], x["time"], x["type"])}, {
            "num_intervention": str(x["id"]), "num_sejour": str(x["admission"]), "chirurgien": str(x["surgeon"]),
            "intervention": x["type"], "date_heure_intervention": fmt_dt(x["time"], tg), "resultat": x["outcome"]}, tg))
    R["mouvements.txt"] = []
    for x in stays:
        tg = fresh()
        R["mouvements.txt"].append(row("mouvements.txt", x["id"], {"date_heure_entree": x["entry"], "_adm": x["admission"],
                                                                    "_key": (x["admission"], x["entry"], x["unit"])}, {
            "num_mouvement": str(x["id"]), "num_sejour": str(x["admission"]), "medecin_responsable": str(x["doctor"]),
            "unite": fmt_label("unit", x["unit"], tg), "chambre": x["room"], "lit": x["bed"],
            "date_heure_entree": fmt_dt(x["entry"], tg),
            "date_heure_sortie": fmt_dt(x["exit"], tg) if x["exit"] else "", "motif_transfert": txt(x["reason"])}, tg))
    R["sorties.txt"] = []
    for x in dischs:
        tg = fresh()
        R["sorties.txt"].append(row("sorties.txt", x["id"], {"date_heure_sortie": x["time"], "_adm": x["admission"],
                                                              "_key": (x["admission"], x["time"], "discharge")}, {
            "num_sortie": str(x["id"]), "num_sejour": str(x["admission"]), "medecin_signataire": str(x["doctor"]),
            "date_heure_sortie": fmt_dt(x["time"], tg), "destination": x["destination"], "etat_sortie": x["condition"],
            "ordonnance": txt(x["meds"]), "consignes": txt(x["advice"]),
            "prochain_rdv": fmt_dt(x["appointment"], tg) if x["appointment"] else ""}, tg))
    return R


R = render_all()

# =============================================================================
# 3) Injected data-quality problems
# =============================================================================
def pick(rows, rate, exclude=()):
    pool = [i for i, r in enumerate(rows) if not (r["touched"] & set(exclude)) and "no_more" not in r["tags"]]
    k = min(len(pool), round(rate * len(rows)))
    return rng.sample(pool, k) if k else []


def invalid_date_string(d, with_time):
    tm = f" {d.hour:02d}:{d.minute:02d}" if with_time else ""
    return rng.choice([f"31/02/{d.year}{tm}", f"30/02/{d.year}{tm}", f"32/{d.month:02d}/{d.year}{tm}",
                       f"{d.day:02d}/13/{d.year}{tm}", f"{d.day:02d}/{d.month:02d}/{d.year} 25:{d.minute:02d}"
                       if with_time else f"{d.day:02d}/00/{d.year}", "a preciser", "inconnue"])


def mess_case(s):
    if not s:
        return s
    return rng.choice([s.upper(), s.lower(), f"  {s}", f"{s}   ", f" {s} ", s.replace(" ", "  ", 1) if " " in s else f"{s} ",
                       s.swapcase()])


TEXT_COLS = {
    "professionnels.txt": ["nom_prenom", "fonction", "service"],
    "patients.txt": ["nom", "prenom", "adresse", "sexe", "statut_vital", "personne_a_prevenir"],
    "sejours.txt": ["type_sejour", "motif", "provenance", "couverture", "statut_sejour"],
    "triage.txt": ["symptomes", "allergies", "traitement_habituel", "niveau_tri"],
    "diagnostics.txt": ["type_diag"],
    "notes_cliniques.txt": ["type_note", "texte"],
    "demandes_examens.txt": ["examen", "indication", "statut_demande", "priorite"],
    "imagerie.txt": ["type_examen", "zone", "statut_examen", "conclusion"],
    "bloc_operatoire.txt": ["intervention", "resultat"],
    "mouvements.txt": ["unite", "chambre", "motif_transfert"],
    "sorties.txt": ["destination", "etat_sortie", "consignes"],
}
LABEL_COL = {"sejours.txt": ("type_sejour", "admission_type"), "triage.txt": ("niveau_tri", "triage"),
             "mouvements.txt": ("unite", "unit"), "demandes_examens.txt": ("statut_demande", "order_status"),
             "imagerie.txt": ("statut_examen", "exam_status")}

max_ids = {"patient": len(patients), "admission": len(adms), "pro": len(pros), "order": len(orders)}

for fname, spec in SPECS.items():
    rows, rates = R[fname], RATES[fname]
    n = len(rows)

    # broken references: a foreign key that points to a record that does not exist
    fks = [c for c in spec["fk"] if c != "num_demande"]
    for i in pick(rows, rates["broken"]):
        r = rows[i]
        col = rng.choice(fks)
        kind = spec["fk"][col]
        r["raw"][col] = str(max_ids[kind] + rng.randint(500, 4000))
        r["tags"].add("broken_ref")
        r["touched"].add(col)
        DETAIL[fname][f"broken ref: {col} -> nonexistent {kind}"] += 1
        if col == "num_sejour":
            r["parent_adm"] = None
    if fname == "imagerie.txt":     # radiology pointing to an order that does not exist
        for i in pick(rows, .012, exclude=("num_demande",)):
            r = rows[i]
            if r["raw"]["num_demande"]:
                r["raw"]["num_demande"] = str(max_ids["order"] + rng.randint(500, 4000))
                r["tags"].add("broken_ref")
                r["touched"].add("num_demande")
                DETAIL[fname]["broken ref: num_demande -> nonexistent order"] += 1
    if fname == "diagnostics.txt":  # diagnosis patient differs from the admission's patient
        for i in pick(rows, .006, exclude=("num_sejour",)):
            r = rows[i]
            a = adm_by_id[int(r["raw"]["num_sejour"])]
            r["raw"]["num_patient"] = str(rng.choice([p for p in range(1, len(patients) + 1) if p != a["patient"]]))
            r["tags"].add("patient_mismatch")
            r["touched"].add("num_patient")
            DETAIL[fname]["broken ref: num_patient differs from the admission's patient"] += 1

    # chronology: events out of order in time
    if rates["chrono"]:
        for i in pick(rows, rates["chrono"], exclude=tuple(spec["fk"])):
            r = rows[i]
            if fname == "sejours.txt":
                a = adm_by_id[r["id"]]
                if a["discharge"] is None or rng.random() < .25:
                    p = pat_by_id[a["patient"]]
                    born = dt.datetime.combine(p["dob"], dt.time(9, 0))
                    bad = born - dt.timedelta(days=rng.randint(30, 400))
                    r["raw"]["date_heure_entree"] = fmt_dt(bad, r["tags"])
                    DETAIL[fname]["chronology: admission before patient date of birth"] += 1
                else:
                    bad = a["admit"] - dt.timedelta(hours=rng.randint(2, 72))
                    r["raw"]["date_heure_sortie"] = fmt_dt(bad, r["tags"])
                    DETAIL[fname]["chronology: discharge before admission"] += 1
            elif fname == "mouvements.txt":
                s = next(x for x in stays if x["id"] == r["id"])
                if s["exit"] is not None and rng.random() < .6:
                    r["raw"]["date_heure_sortie"] = fmt_dt(s["entry"] - dt.timedelta(hours=rng.randint(1, 30)), r["tags"])
                    DETAIL[fname]["chronology: unit exit before entry"] += 1
                else:
                    a = adm_by_id[s["admission"]]
                    r["raw"]["date_heure_entree"] = fmt_dt(a["admit"] - dt.timedelta(days=rng.randint(2, 15)), r["tags"])
                    DETAIL[fname]["chronology: unit entry before admission"] += 1
            elif fname == "sorties.txt":
                a = adm_by_id[int(r["raw"]["num_sejour"])]
                r["raw"]["date_heure_sortie"] = fmt_dt(a["admit"] - dt.timedelta(hours=rng.randint(3, 72)), r["tags"])
                DETAIL[fname]["chronology: discharge record before admission"] += 1
            else:
                a = adm_by_id[int(r["raw"]["num_sejour"])]
                col = spec["dates"][0]
                end = a["discharge"] or CUTOFF
                if a["discharge"] is not None and rng.random() < .5:
                    bad, what = end + dt.timedelta(days=rng.randint(2, 20)), "after discharge"
                else:
                    bad, what = a["admit"] - dt.timedelta(days=rng.randint(2, 20)), "before admission"
                r["raw"][col] = fmt_dt(real_local(bad), r["tags"])
                DETAIL[fname][f"chronology: {col} {what}"] += 1
            r["tags"].add("chrono")
            r["touched"].add("date")
        if fname == "sorties.txt":   # discharge record for an admission that is still active
            active = [a for a in adms if a["status"] == "active"]
            for a in rng.sample(active, min(4, len(active))):
                tg = set()
                did = len(dischs) + len([x for x in R[fname] if x["id"] > len(dischs)]) + 1
                t_ = real_local(a["admit"] + dt.timedelta(days=2))
                extra = row(fname, did, {"date_heure_sortie": t_, "_adm": a["id"], "_key": (a["id"], t_, "discharge")}, {
                    "num_sortie": str(did), "num_sejour": str(a["id"]), "medecin_signataire": str(a["doctor"]),
                    "date_heure_sortie": fmt_dt(t_, tg), "destination": "Domicile", "etat_sortie": "Stable",
                    "ordonnance": "", "consignes": "", "prochain_rdv": ""}, tg | {"chrono"})
                extra["touched"].add("date")
                R[fname].append(extra)
                DETAIL[fname]["chronology: discharge record for an admission that is still active"] += 1
            rows = R[fname]

    # missing required values
    for i in pick(rows, rates["missing_req"], exclude=("date",)):
        r = rows[i]
        col = rng.choice([c for c in spec["req"] if c not in r["touched"]])
        r["raw"][col] = rng.choice(PLACEHOLDERS + (["0000-00-00"] if col in spec["dates"] else []))
        r["tags"].add("missing_req")
        r["touched"].add(col)
        DETAIL[fname][f"missing required: {col}"] += 1

    # invalid or ambiguous dates
    for i in pick(rows, rates["bad_date"], exclude=("date",)):
        r = rows[i]
        col = spec["dates"][0]
        if col in r["touched"]:
            continue
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

    # labels nobody can map to a standard value
    if rates["unmap"] and fname in LABEL_COL:
        col, key = LABEL_COL[fname]
        for i in pick(rows, rates["unmap"]):
            r = rows[i]
            if col in r["touched"]:
                continue
            r["raw"][col] = rng.choice(UNMAPPABLE[key])
            r["tags"].add("unmappable")
            r["touched"].add(col)
            DETAIL[fname][f"unmappable label: {col}"] += 1

    # missing optional values (placeholders)
    if spec["opt"]:
        for i in pick(rows, MISSING_OPT_RATE):
            r = rows[i]
            cands = [c for c in spec["opt"] if c not in r["touched"] and r["raw"].get(c)]
            if not cands:
                continue
            col = rng.choice(cands)
            r["raw"][col] = rng.choice(PLACEHOLDERS + (["-1"] if fname == "triage.txt" and col in
                                                       ("pouls", "freq_resp", "spo2", "eva", "temperature") else []))
            r["tags"].add("missing_opt")
            r["touched"].add(col)
            DETAIL[fname][f"missing optional: {col}"] += 1

    # invalid numbers (optional triage vitals)
    if fname == "triage.txt":
        bad_values = {"pouls": ["-72", "0", "420", "abc", "999"], "freq_resp": ["0", "95", "xx", "150"],
                      "temperature": ["300", "4,5", "410", "chaud", "52"], "spo2": ["140", "105", "-3", "abc"],
                      "eva": ["14", "11", "-2", "fort"], "tension": ["300/20", "abc/def", "0/0", "12/8000"]}
        for i in pick(rows, INVALID_VITAL_RATE):
            r = rows[i]
            cands = [c for c in bad_values if c not in r["touched"]]
            col = rng.choice(cands)
            r["raw"][col] = rng.choice(bad_values[col])
            r["tags"].add("invalid_number")
            r["touched"].add(col)
            DETAIL[fname][f"invalid number: {col}"] += 1

    # fake ICD-9 codes (about 1% of diagnoses)
    if fname == "diagnostics.txt":
        for i in pick(rows, .011, exclude=("code_cim9",)):
            r = rows[i]
            r["raw"]["code_cim9"] = rng.choice(FAKE_ICD)
            r["tags"].add("fake_icd")
            r["touched"].add("code_cim9")
            DETAIL[fname]["fake ICD-9 code"] += 1

    # inconsistent capitalization and whitespace
    for i in pick(rows, rates["case_ws"]):
        r = rows[i]
        cands = [c for c in TEXT_COLS[fname] if c not in r["touched"] and r["raw"].get(c)]
        if not cands:
            continue
        col = rng.choice(cands)
        new = mess_case(r["raw"][col])
        if new != r["raw"][col]:
            r["raw"][col] = new
            r["tags"].add("case_ws")
            DETAIL[fname][f"case/whitespace: {col}"] += 1

# =============================================================================
# 4) Duplicates (exact copies, and near duplicates under a new ID)
# =============================================================================
NEW_ID = {f: max(r["id"] for r in R[f]) for f in R}
PK = {f: s["cols"][0] for f, s in SPECS.items()}
for fname, spec in SPECS.items():
    rows = R[fname]
    originals = [r for r in rows if "no_more" not in r["tags"]]
    n = len(originals)
    exact_src = rng.sample(originals, round(EXACT_DUP * n)) if n > 20 else rng.sample(originals, min(2, n))
    for src in exact_src:
        raw = dict(src["raw"])
        if rng.random() < .3:                          # same after trimming / ignoring case
            cands = [c for c in TEXT_COLS[fname] if raw.get(c)]
            if cands:
                c = rng.choice(cands)
                raw[c] = rng.choice([raw[c].upper(), f" {raw[c]} ", raw[c].lower()])
        dup = row(fname, src["id"], dict(src["canon"]), raw, set(src["tags"]) | {"exact_dup"})
        dup["parent_adm"], dup["parent_pat"], dup["parent_order"] = src["parent_adm"], src["parent_pat"], src["parent_order"]
        dup["dup_of"] = src["id"]
        pos = rows.index(src) + rng.randint(1, 15)
        rows.insert(min(pos, len(rows)), dup)
        DETAIL[fname]["exact duplicate rows"] += 1
    clean_pool = [r for r in originals if not (r["tags"] & {"missing_req", "date_invalid", "date_ambiguous",
                                                           "broken_ref", "chrono", "unmappable", "fake_icd",
                                                           "patient_mismatch"})]
    near_src = rng.sample(clean_pool, round(NEAR_DUP * n)) if n > 20 else rng.sample(clean_pool, min(2, len(clean_pool)))
    for src in near_src:
        NEW_ID[fname] += 1
        new_id = NEW_ID[fname]
        tg = {"near_dup"}
        raw = dict(src["raw"])
        raw[PK[fname]] = str(new_id)
        for c in spec["dates"][:1]:                     # same instant, written again (maybe in another format)
            v = src["canon"].get(c)
            if v is not None:
                raw[c] = fmt_dt(v, tg) if isinstance(v, dt.datetime) else fmt_date(v, tg)
        for c in TEXT_COLS[fname]:                      # retyped by someone else: case/spacing differ
            if raw.get(c) and rng.random() < .35:
                raw[c] = rng.choice([raw[c].upper(), raw[c].lower(), f" {raw[c]}", raw[c].title()])
        if fname == "patients.txt" and rng.random() < .5:   # second registration often lacks the phone
            raw["telephone"] = ""
        dup = row(fname, new_id, dict(src["canon"]), raw, tg)
        dup["parent_adm"], dup["parent_pat"] = src["parent_adm"], src["parent_pat"]
        dup["dup_of"] = src["id"]
        rows.append(dup)
        DETAIL[fname]["near duplicate rows (new ID)"] += 1
        # children of a near duplicate: re-point one child to the new ID (the contract re-points them back)
        if fname == "patients.txt" and rng.random() < .5:
            kids = [r for r in R["sejours.txt"] if r["raw"]["num_patient"] == str(src["id"]) and "near_dup" not in r["tags"]]
            if kids:
                k_ = rng.choice(kids)
                k_["raw"]["num_patient"] = str(new_id)
                k_["parent_pat_dup"] = True
                DETAIL["sejours.txt"]["admission points to a near-duplicate patient (re-point it)"] += 1
        if fname == "sejours.txt" and rng.random() < .5:
            kids = [r for r in R["notes_cliniques.txt"] if r["raw"]["num_sejour"] == str(src["id"])]
            if kids:
                k_ = rng.choice(kids)
                k_["raw"]["num_sejour"] = str(new_id)
                k_["parent_adm_dup"] = True
                DETAIL["notes_cliniques.txt"]["note points to a near-duplicate admission (re-point it)"] += 1

# =============================================================================
# 5) Write the files (pipe-delimited, header line, UTF-8, LF line endings)
# =============================================================================
OUT.mkdir(parents=True, exist_ok=True)
MALFORMED = Counter()
for fname, spec in SPECS.items():
    lines = ["|".join(spec["cols"])]
    for r in R[fname]:
        vals = [r["raw"].get(c, "").replace("|", "/").replace("\n", " ") for c in spec["cols"]]
        line = "|".join(vals)
        if fname in ("notes_cliniques.txt", "triage.txt", "mouvements.txt") and rng.random() < .002 and "exact_dup" not in r["tags"]:
            if rng.random() < .5:
                line = "|".join(vals[:-2])                        # truncated line
            else:
                line = "|".join(vals[:3]) + "|" + "|".join(vals[3:]).replace(", ", "|", 1)  # stray delimiter
            if line.count("|") != len(spec["cols"]) - 1:
                r["tags"].add("malformed")
                MALFORMED[fname] += 1
                DETAIL[fname]["malformed line (wrong number of fields)"] += 1
            else:
                line = "|".join(vals)
        lines.append(line)
    (OUT / fname).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

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
        ("Fake ICD-9", lambda t: "fake_icd" in t), ("Malformed line", lambda t: "malformed" in t)]
REJECT = {"exact_dup", "near_dup", "missing_req", "date_invalid", "date_ambiguous", "broken_ref", "patient_mismatch",
          "chrono", "unmappable", "fake_icd", "malformed"}

# Estimated rejections, with cascade (patient -> admission -> children; order -> radiology).
rej_pat = {r["id"] for r in R["patients.txt"] if (r["tags"] & REJECT) - {"near_dup", "exact_dup"} and "exact_dup" not in r["tags"]}
rej_pro = {r["id"] for r in R["professionnels.txt"] if (r["tags"] & REJECT) - {"near_dup", "exact_dup"} and "exact_dup" not in r["tags"]}
rej_adm, casc = set(), Counter()
est = Counter()
for r in R["sejours.txt"]:
    own = bool(r["tags"] & REJECT)
    cascade = (not own) and (r["raw"]["num_patient"] and r["raw"]["num_patient"].strip().isdigit()
                             and int(r["raw"]["num_patient"]) in rej_pat and not r.get("parent_pat_dup"))
    if (own and "exact_dup" not in r["tags"] and "near_dup" not in r["tags"]) or cascade:
        rej_adm.add(r["id"])
    if own or cascade:
        est["sejours.txt"] += 1
        casc["sejours.txt"] += int(bool(cascade))
rej_order = set()
for fname in [f for f in SPECS if f not in ("professionnels.txt", "patients.txt", "sejours.txt")]:
    for r in R[fname]:
        own = bool(r["tags"] & REJECT)
        a = r["raw"].get("num_sejour", "")
        cascade = (not own) and a.strip().isdigit() and int(a) in rej_adm and not r.get("parent_adm_dup")
        if fname == "imagerie.txt" and not own and not cascade and r["raw"]["num_demande"].strip().isdigit():
            cascade = int(r["raw"]["num_demande"]) in rej_order
        if fname == "demandes_examens.txt" and (own or cascade) and "exact_dup" not in r["tags"]:
            rej_order.add(r["id"])
        if own or cascade:
            est[fname] += 1
            casc[fname] += int(bool(cascade))
for fname in ("professionnels.txt", "patients.txt"):
    est[fname] = sum(1 for r in R[fname] if r["tags"] & REJECT)

total_rows = sum(len(v) for v in R.values())
L = []
w = L.append
w(f"# Source A ({HOSPITAL}): generation log\n")
w("> **Statement:** all of this data is entirely fictional, created exclusively for educational and learning purposes "
  "(SOEN 363 Project Phase 2). It does not describe real patients and does not include any real personal information. "
  "Names are random combinations of common French first names and surnames; addresses, phone numbers, insurance numbers "
  "and IDs are random.\n")
w(f"Generated by `source_a_generator.py` (seed `{SEED}`). Re-running the script reproduces the files exactly (it does not "
  f"use the current date). AI tool: Claude Code (Anthropic), model Claude Opus 5.5. Hospital system: **{HOSPITAL}** "
  f"(fictional), continent **Europe**, time zone **Europe/Paris** (CET UTC+1 / CEST UTC+2, with daylight saving time). "
  f"Extract time (local): {CUTOFF.strftime('%Y-%m-%d %H:%M')} Europe/Paris. Admissions span 2022-01-01 to the extract time.\n")
w("All counts below are **rows**. A row can have several problems, so the columns overlap (as section 7 of the contract "
  "allows). Every count comes from the script's own bookkeeping, so it is exact.\n")
w("## Files and record counts\n")
w("| Raw file | Entity | Rows (incl. duplicates) | Original records | Duplicate rows |")
w("|---|---|---:|---:|---:|")
tr = to = td = 0
for fname, spec in SPECS.items():
    rows = R[fname]
    d = sum(1 for r in rows if r["tags"] & {"exact_dup", "near_dup"})
    w(f"| `{fname}` | {spec['entity']} | {len(rows)} | {len(rows) - d} | {d} |")
    tr, to, td = tr + len(rows), to + len(rows) - d, td + d
w(f"| **Total** | | **{tr}** | **{to}** | **{td}** |\n")
w("No ICD-9 dictionary file is generated; `diagnostics.txt` uses codes from `soen363-phase1/data/icd9_dictionary.csv`. "
  "IDs in every file start at 1.\n")
w("## Injected problems per file (rows affected)\n")
w("| File | " + " | ".join(c for c, _ in CATS) + " |")
w("|---|" + "---:|" * len(CATS))
tot = Counter()
for fname in SPECS:
    cells = []
    for c, f in CATS:
        k = sum(1 for r in R[fname] if f(r["tags"]))
        tot[c] += k
        cells.append(str(k))
    w(f"| `{fname}` | " + " | ".join(cells) + " |")
w("| **Total** | " + " | ".join(f"**{tot[c]}**" for c, _ in CATS) + " |")
w("| **% of all rows** | " + " | ".join(f"{100 * tot[c] / total_rows:.1f}%" for c, _ in CATS) + " |\n")
w(f"Compared with contract section 7: duplicates (exact + near) "
  f"{100 * (tot['Exact duplicates'] + tot['Near duplicates']) / total_rows:.1f}% (target ~5%), missing optional "
  f"{100 * tot['Missing optional'] / total_rows:.1f}% (~10%), missing required {100 * tot['Missing required'] / total_rows:.1f}% "
  f"(~2%, lower on purpose for patients/admissions), case/whitespace {100 * tot['Case / whitespace'] / total_rows:.1f}% (~15%), "
  f"non-standard formats {100 * tot['Non-standard format'] / total_rows:.1f}% (~15%), invalid or ambiguous dates "
  f"{100 * (tot['Invalid date'] + tot['Ambiguous date']) / total_rows:.1f}% (~2%), invalid numbers "
  f"{100 * tot['Invalid number'] / total_rows:.1f}% (~5%), broken references {100 * tot['Broken reference'] / total_rows:.1f}% "
  f"(~2%), chronology {100 * tot['Chronology'] / total_rows:.1f}% (~2%).\n")
w("## Estimated rejections\n")
w("Rows that carry a rejecting problem (duplicate, missing required, invalid/ambiguous date, broken reference, chronology, "
  "unmappable label, fake ICD-9, malformed line), plus rows that cascade from a rejected patient, admission or request. "
  "Children of near-duplicate patients and admissions are not counted, because the contract re-points them to the kept "
  "record. Treat this as a sanity check, not the answer: your cleaning rules decide the real number.\n")
w("| File | Rows | Estimated rejected | of which cascaded | % |")
w("|---|---:|---:|---:|---:|")
te = tc = 0
for fname in SPECS:
    n = len(R[fname])
    w(f"| `{fname}` | {n} | {est[fname]} | {casc[fname]} | {100 * est[fname] / n:.1f}% |")
    te, tc = te + est[fname], tc + casc[fname]
w(f"| **Total** | **{total_rows}** | **{te}** | **{tc}** | **{100 * te / total_rows:.1f}%** |\n")
w("Radiology rows whose `num_demande` points to a rejected request are counted as cascaded here; since `order_id` is "
  "nullable, your cleaning might blank it instead.\n")
w("Side effect to expect in validation (handout Task 5): when a discharge or diagnosis row gets a rejecting problem "
  "(broken reference, missing required value, bad date...), its real admission loses that discharge record or that "
  "primary diagnosis after cleaning. So a few completed admissions will have no discharge record or no primary diagnosis "
  "in the clean data. This comes from the injected problems, not from the hospital data itself.\n")
w("## Problem details per file\n")
for fname in SPECS:
    w(f"### `{fname}`\n")
    for k, v in sorted(DETAIL[fname].items()):
        w(f"- {k}: {v}")
    fmt = Counter(x for r in R[fname] for x in r["tags"] if x.startswith("fmt_"))
    names = {"fmt_date_iso": "ISO date", "fmt_date_french_h": "French time `14h59`", "fmt_date_dots": "dotted date `DD.MM.YYYY`",
             "fmt_date_dash": "dash date with a value > 12 (readable)", "fmt_date_text": "text date (e.g. `5 mars 1980`)",
             "fmt_label": "alternative category label", "fmt_phone": "alternative phone format",
             "fmt_icd_no_decimal": "ICD-9 without decimal point", "fmt_icd_leading_zero_lost": "ICD-9 `38.9` for `038.9`",
             "fmt_temp_fahrenheit": "temperature in Fahrenheit", "fmt_vital_units": "unit text inside a vital sign"}
    for k, v in sorted(fmt.items()):
        w(f"- non-standard format: {names.get(k, k)}: {v}")
    w("")
w("## How duplicates were made\n")
w("- **Exact duplicate:** the same row again with the **same ID**, inserted a few lines after the original. In about 30% "
  "of them one text field differs only in case or spacing, so they are still exact duplicates under the contract "
  "(\"every field is the same after trimming and ignoring case\").")
w("- **Near duplicate:** the same facts under a **new ID** (IDs continue after the last original ID), rendered again so "
  "dates, labels and text can use another format or case. They match the contract's duplicate keys: patient = name + DOB, "
  "staff = name + role, admission = patient + admit time, others = admission + timestamp + type. Placed at the end of the "
  "file. For some near-duplicate patients and admissions, one child row (an admission or a note) points to the new ID, so "
  "the cleaning has to re-point it to the kept record (contract section 7).\n")
w("## Source A conventions (for checking your profiling)\n")
w("- **Files:** one `.txt` file per entity in `data/raw/A_txt/`. UTF-8, `\\n` line endings, **line 1 is a header**, fields "
  "separated by `|` with no quoting (a `|` inside a value was replaced by `/`). A few lines are malformed on purpose "
  "(wrong number of fields).")
w("- **Timestamps** are local **Europe/Paris** wall-clock time (CET/CEST). Usual format `DD/MM/YYYY HH:MM` (24h). Also present: "
  "ISO (`YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DDTHH:MM`), French hour notation (`DD/MM/YYYY 14h59`), dotted dates "
  "(`DD.MM.YYYY HH:MM`, always day-first), and a few dash dates (`NN-NN-YYYY HH:MM`) written in **either** order. Dash dates "
  "with a value over 12 can be read; dash dates where both numbers are 12 or less are the injected **ambiguous dates**. "
  "Times inside the spring daylight-saving gap never occur; times in the autumn repeated hour (02:00-02:59 on the last "
  "Sunday of October) can occur and are ambiguous in UTC.")
w("- **Date of birth**: usually `DD/MM/YYYY`; also ISO, French text dates (`5 mars 1980`), and dash dates (same rule as above).")
w("- **Numbers** use a **decimal comma** (`37,2`). **Temperature**: about 30% in Fahrenheit (`99,1F`, `99,1 F`, `99,1 °F`, "
  "or a bare `99,1`), the rest in Celsius (sometimes `37,2C` / `37,2 °C`). Other vitals sometimes carry units "
  "(`88 bpm`, `96%`, `4/10`, `120/80 mmHg`, `120-80`). Pain is `eva` (0-10 scale).")
w("- **Names:** `nom` is the family name, usually in capitals; `prenom` the first name. `full_name` = `prenom` + `nom`. "
  "Staff names are one field `Prenom NOM`.")
w("- **Missing-value placeholders** (injected): empty, `N/A`, `null`, `-`, `?`; `-1` for numbers; `0000-00-00` for dates. "
  "Values that are legitimately empty (no `date_heure_sortie` for an active admission or a current unit stay, no "
  "`num_demande` for a walk-in exam, no `conclusion` for an exam not done, no prescription or appointment after a death) "
  "are written as an empty field and are **not** counted as problems.")
w("- **Allergies / medications** with none: `none`, `None`, `NKA`, `no known allergies`, `No Known Allergies`, `aucune` "
  "(medications: `none`, `None`, `NKA`, `aucun`). These mean \"none\", not missing.")
w("- **ICD-9 codes**: dictionary codes only, sometimes without the decimal point (`4019`), with extra spaces (` 428.0`), "
  f"or `38.9` for `038.9`; plus fake codes from this list: {', '.join('`' + c + '`' for c in FAKE_ICD)}.")
w("- **Invalid numbers** are only in optional triage vitals (e.g. temperature `300`, pulse `-72`, SpO2 `140`, pain `14`, "
  "`abc`). `-1` on its own is the missing-value placeholder, not an invalid number.")
w("- **Free text** (reasons, symptoms, notes, findings, follow-up advice) is written in English by this hospital; codes, "
  "labels and field names are French.\n")
w("## Intended label mapping (answer key)\n")
w("| Raw column | Standard value | Source A labels |")
w("|---|---|---|")
COLMAP = {"admission_type": "sejours.type_sejour", "admission_status": "sejours.statut_sejour",
          "life_status": "patients.statut_vital", "sex": "patients.sexe", "triage": "triage.niveau_tri",
          "unit": "mouvements.unite", "order_status": "demandes_examens.statut_demande",
          "priority": "demandes_examens.priorite", "exam_status": "imagerie.statut_examen",
          "dx_type": "diagnostics.type_diag", "note_type": "notes_cliniques.type_note", "role": "professionnels.fonction"}
for key, m in LABELS.items():
    for std, (prim, alts) in m.items():
        w(f"| `{COLMAP[key]}` | {std} | " + ", ".join(f"`{x}`" for x in [prim] + alts) + " |")
for key, vals in UNMAPPABLE.items():
    w(f"| `{COLMAP[key]}` | *(unmappable on purpose)* | " + ", ".join(f"`{x}`" for x in vals) + " |")
w("\nExam types (`examen`, `type_examen`): `RADIO THORAX` = Chest X-ray, `SCANNER` = CT scan, `IRM` = MRI, "
  "`ECHOGRAPHIE` = Ultrasound, `ECG` = ECG, `BILAN SANGUIN` = Blood panel. Body areas (`zone`): `Thorax`, `Abdomen`, `Crane`.")
LOG.write_text("\n".join(L) + "\n", encoding="utf-8")

print(f"Source A: {total_rows} rows written to {OUT}")
for c, _ in CATS:
    print(f"  {c:22s} {tot[c]:5d}  ({100 * tot[c] / total_rows:.1f}%)")
print(f"  estimated rejected     {te:5d}  ({100 * te / total_rows:.1f}%)")
