"""
SOEN 363 Project Phase 1 - synthetic data generator
Generates: HealthcareProfessional, Patient, Admission,
TriageAssessment, UnitStay. Clinical tables (including
SurgicalProcedure) come from generate_clinical_data.py.

Data is synthetic, generated with the Faker library, seeded for
reproducibility. No real patient or personnel information is used.
"""

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from faker import Faker

fake = Faker()
Faker.seed(363)
random.seed(363)

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "db" / "hospital.db"
SCHEMA_PATH = REPO_ROOT / "db" / "schema.sql"

N_PROFESSIONALS = 25
N_PATIENTS = 60
TRIAGE_PRIORITIES = ["low", "medium", "high"]
ADMISSION_TYPES = ["emergency", "urgent", "elective", "outpatient", "newborn"]
ADMISSION_SOURCES = ["self-referral", "physician referral", "transfer from another facility", "walk-in"]
UNIT_TYPES = ["Emergency Department", "ICU", "CCU", "MICU", "SICU", "General Ward"]
CRITICAL_CARE_UNITS = ["ICU", "CCU", "MICU", "SICU"]
INPATIENT_UNITS = [u for u in UNIT_TYPES if u != "Emergency Department"]
LONG_CRITICAL_CARE_RATE = 0.15        # share of discharged admissions with a 7+ day critical care stay
LONG_CRITICAL_CARE_MIN_HOURS = 170    # just over seven days (168 h)
PROFESSIONAL_ROLES = ["Nurse", "Physician", "Surgeon", "Radiologist", "Radiology Technician", "Triage Nurse"]

# Separate generator for the stay-length plan, so adding it does not shift the
# main random stream (Patient, Admission and TriageAssessment rows stay identical).
plan_rng = random.Random(3630)


def random_datetime_between(start: datetime, end: datetime) -> datetime:
    delta = end - start
    seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=seconds)


def build_professionals(cur):
    ids = []
    roles = {}
    for _ in range(N_PROFESSIONALS):
        name = fake.name()
        role = random.choice(PROFESSIONAL_ROLES)
        cur.execute(
            "INSERT INTO HealthcareProfessional (name, role) VALUES (?, ?)",
            (name, role),
        )
        ids.append(cur.lastrowid)
        roles[cur.lastrowid] = role
    return ids, roles


def build_patients(cur):
    """Returns [(patient_id, date_of_birth), ...] so admissions can be kept
    after each patient was actually born."""
    patients = []
    for _ in range(N_PATIENTS):
        dob = fake.date_of_birth(minimum_age=0, maximum_age=95)
        life_status = "deceased" if random.random() < 0.05 else "alive"
        cur.execute(
            """INSERT INTO Patient
               (full_name, date_of_birth, gender, address, telephone_number,
                emergency_contact_info, life_status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                fake.name(),
                dob.isoformat(),
                random.choice(["male", "female", "other"]),
                fake.address().replace("\n", ", "),
                fake.phone_number(),
                f"{fake.name()} ({fake.phone_number()})",
                life_status,
            ),
        )
        patients.append((cur.lastrowid, datetime.combine(dob, datetime.min.time())))
    return patients


def build_admissions(cur, patients, professional_ids):
    """Build each patient's admissions as a single, non-overlapping timeline:
    each admission starts no earlier than the patient's birth and no earlier
    than the previous admission's discharge, and only the last admission in
    the sequence may be left open (active)."""
    patient_ids = [pid for pid, _ in patients]
    dob_by_patient = dict(patients)
    admission_ids_by_patient = {pid: [] for pid in patient_ids}
    window_start = datetime(2024, 1, 1)
    window_end = datetime(2026, 9, 1)

    zero_admission_patients = set(random.sample(patient_ids, k=max(1, N_PATIENTS // 7)))
    remaining = [p for p in patient_ids if p not in zero_admission_patients]
    heavy_patients = set(random.sample(remaining, k=max(1, len(remaining) // 6)))

    for pid in patient_ids:
        if pid in zero_admission_patients:
            continue
        n_admissions = random.randint(4, 7) if pid in heavy_patients else random.randint(1, 3)

        cursor_time = max(window_start, dob_by_patient[pid])

        for i in range(n_admissions):
            if cursor_time >= window_end:
                break  # no time left in the window for another admission

            admit_dt = random_datetime_between(cursor_time, window_end)

            is_last_planned = i == n_admissions - 1
            is_discharged = True if not is_last_planned else random.random() < 0.85
            discharge_dt = admit_dt + timedelta(hours=random.randint(3, 240)) if is_discharged else None
            status = "discharged" if is_discharged else "active"

            # Decide up front whether this admission contains a critical care
            # stay of more than seven days. If it does, the admission window
            # itself must be long enough to hold it (8 to 20 days).
            has_long_critical_stay = plan_rng.random() < LONG_CRITICAL_CARE_RATE
            if has_long_critical_stay and discharge_dt:
                discharge_dt = admit_dt + timedelta(hours=plan_rng.randint(192, 480))

            # 'newborn' only makes sense within 28 days of the patient's birth.
            days_since_birth = (admit_dt - dob_by_patient[pid]).total_seconds() / 86400
            type_choices = ADMISSION_TYPES if days_since_birth <= 28 else [t for t in ADMISSION_TYPES if t != "newborn"]
            admission_type = random.choice(type_choices)

            cur.execute(
                """INSERT INTO Admission
                   (patient_id, admitting_professional_id, admission_date_time,
                    admission_type, reason_for_admission, admission_source,
                    insurance_information, discharge_date_time, final_admission_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    pid,
                    random.choice(professional_ids),
                    admit_dt.isoformat(sep=" "),
                    admission_type,
                    fake.sentence(nb_words=6),
                    random.choice(ADMISSION_SOURCES),
                    fake.company() + " Insurance",
                    discharge_dt.isoformat(sep=" ") if discharge_dt else None,
                    status,
                ),
            )
            admission_ids_by_patient[pid].append(
                (cur.lastrowid, admit_dt, discharge_dt, admission_type, has_long_critical_stay)
            )

            if discharge_dt is None:
                break  # an open admission blocks any further admissions for this patient
            cursor_time = discharge_dt
    return admission_ids_by_patient


def build_triage(cur, admission_ids_by_patient, nurse_ids):
    for pid, admissions in admission_ids_by_patient.items():
        for admission_id, admit_dt, *_ in admissions:
            cur.execute(
                """INSERT INTO TriageAssessment
                   (admission_id, performing_professional_id, blood_pressure,
                    heart_rate, respiratory_rate, body_temperature, oxygen_saturation,
                    pain_level, reported_symptoms, known_allergies, current_medications,
                    triage_priority_level)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    admission_id,
                    random.choice(nurse_ids),
                    f"{random.randint(90,160)}/{random.randint(60,100)}",
                    random.randint(55, 130),
                    random.randint(12, 30),
                    round(random.uniform(36.0, 40.0), 1),
                    random.randint(88, 100),
                    random.randint(0, 10),
                    fake.sentence(nb_words=8),
                    random.choice(["none", "penicillin", "latex", "peanuts", "none"]),
                    random.choice(["none", "aspirin", "metformin", "lisinopril", "none"]),
                    random.choice(TRIAGE_PRIORITIES),
                ),
            )


def plan_unit_sequence(n_stays, admission_type, has_long_critical_stay):
    """Pick the ordered list of units for one admission.

    The Emergency Department can only ever be the first unit (patients enter
    through it, they are never transferred back into it). Two consecutive
    stays never use the same unit. Returns (units, index_of_long_stay).
    """
    if admission_type == "emergency":
        starts_in_ed = True
    elif admission_type == "urgent":
        starts_in_ed = random.random() < 0.5
    else:
        starts_in_ed = False

    # A long critical care stay needs a non-ED slot to live in.
    if has_long_critical_stay and starts_in_ed and n_stays < 2:
        n_stays = 2

    first_inpatient = 1 if starts_in_ed else 0
    long_idx = random.randint(first_inpatient, n_stays - 1) if has_long_critical_stay else None

    units = []
    for i in range(n_stays):
        prev = units[-1] if units else None
        if i == 0 and starts_in_ed:
            unit = "Emergency Department"
        elif i == long_idx:
            unit = random.choice([u for u in CRITICAL_CARE_UNITS if u != prev])
        else:
            unit = random.choice([u for u in INPATIENT_UNITS if u != prev])
        units.append(unit)
    return units, long_idx


def split_window(total_seconds, n_stays, long_idx):
    """Split an admission window into n consecutive, strictly positive slices
    that add up exactly to the window. If long_idx is set, that slice is kept
    longer than seven days and the others share what is left."""
    if long_idx is not None:
        long_min = LONG_CRITICAL_CARE_MIN_HOURS * 3600
        n_others = n_stays - 1
        durations = [0] * n_stays
        if n_others:
            budget_h = (total_seconds - long_min) // 3600
            cap_h = max(2, min(36, budget_h // n_others))
            for i in range(n_stays):
                if i != long_idx:
                    durations[i] = random.randint(2, cap_h) * 3600
        durations[long_idx] = total_seconds - sum(durations)
        return durations

    weights = [random.uniform(1, 3) for _ in range(n_stays)]
    scale = total_seconds / sum(weights)
    durations = [int(w * scale) for w in weights[:-1]]
    durations.append(total_seconds - sum(durations))  # last slice absorbs rounding
    return durations


def transfer_reason(prev_unit, unit):
    if prev_unit is None:
        return None
    if prev_unit == "Emergency Department":
        return "admitted from Emergency Department"
    if unit in CRITICAL_CARE_UNITS and prev_unit in CRITICAL_CARE_UNITS:
        return "transferred to specialised critical care"
    if unit in CRITICAL_CARE_UNITS:
        return "condition deteriorated, escalated to critical care"
    return "condition improved, stepped down"


def build_unit_stays(cur, admission_ids_by_patient, professional_ids):
    """Build each admission's unit timeline inside the admission window.

    Discharged admissions: the window from admission to discharge is split
    into consecutive, non-overlapping slices with positive length, and the
    last stay ends exactly at discharge.
    Active admissions: stays are consecutive from admission and the last one
    is still open (exit_date_time is NULL).
    """
    for pid, admissions in admission_ids_by_patient.items():
        for admission_id, admit_dt, discharge_dt, admission_type, has_long in admissions:
            n_stays = random.randint(1, 3)
            units, long_idx = plan_unit_sequence(n_stays, admission_type, has_long)
            n_stays = len(units)

            if discharge_dt:
                total_seconds = int((discharge_dt - admit_dt).total_seconds())
                durations = split_window(total_seconds, n_stays, long_idx)
            else:
                durations = []
                for i in range(n_stays):
                    if i == long_idx:
                        hours = random.randint(LONG_CRITICAL_CARE_MIN_HOURS, 400)
                    else:
                        hours = random.randint(4, 96)
                    durations.append(hours * 3600)

            entry_dt = admit_dt
            for i, unit in enumerate(units):
                exit_dt = entry_dt + timedelta(seconds=durations[i])
                is_open = discharge_dt is None and i == n_stays - 1
                cur.execute(
                    """INSERT INTO UnitStay
                       (admission_id, responsible_professional_id, unit_type,
                        ward_and_room, bed_number, entry_date_time, exit_date_time,
                        reason_for_transfer)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        admission_id,
                        random.choice(professional_ids),
                        unit,
                        f"Ward {random.randint(1,9)}, Room {random.randint(100,399)}",
                        str(random.randint(1, 40)),
                        entry_dt.isoformat(sep=" "),
                        None if is_open else exit_dt.isoformat(sep=" "),
                        transfer_reason(units[i - 1] if i else None, unit),
                    ),
                )
                entry_dt = exit_dt

            if discharge_dt:
                assert entry_dt == discharge_dt, f"admission {admission_id}: last stay must end at discharge"


def main():
    # Start from a fresh file so re-running doesn't fail on CREATE TABLE
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    with open(SCHEMA_PATH) as f:
        cur.executescript(f.read())

    professional_ids, professional_roles = build_professionals(cur)
    nurse_ids = [pid for pid in professional_ids if professional_roles[pid] in ("Nurse", "Triage Nurse")]
    patients = build_patients(cur)
    admission_ids_by_patient = build_admissions(cur, patients, professional_ids)
    build_triage(cur, admission_ids_by_patient, nurse_ids or professional_ids)
    build_unit_stays(cur, admission_ids_by_patient, professional_ids)
    # SurgicalProcedure is generated by generate_clinical_data.py

    conn.commit()

    for table in ["HealthcareProfessional", "Patient", "Admission", "TriageAssessment", "UnitStay"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {n} rows")

    conn.close()


if __name__ == "__main__":
    main()
