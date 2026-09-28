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
PROFESSIONAL_ROLES = ["Nurse", "Physician", "Surgeon", "Radiologist", "Radiology Technician", "Triage Nurse"]


def random_datetime_between(start: datetime, end: datetime) -> datetime:
    delta = end - start
    seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=seconds)


def build_professionals(cur):
    ids = []
    for _ in range(N_PROFESSIONALS):
        name = fake.name()
        role = random.choice(PROFESSIONAL_ROLES)
        cur.execute(
            "INSERT INTO HealthcareProfessional (name, role) VALUES (?, ?)",
            (name, role),
        )
        ids.append(cur.lastrowid)
    return ids


def build_patients(cur):
    ids = []
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
        ids.append(cur.lastrowid)
    return ids


def build_admissions(cur, patient_ids, professional_ids):
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
        for _ in range(n_admissions):
            admit_dt = random_datetime_between(window_start, window_end)
            is_discharged = random.random() < 0.85
            discharge_dt = admit_dt + timedelta(hours=random.randint(3, 240)) if is_discharged else None
            status = "discharged" if is_discharged else "active"
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
                    random.choice(ADMISSION_TYPES),
                    fake.sentence(nb_words=6),
                    random.choice(ADMISSION_SOURCES),
                    fake.company() + " Insurance",
                    discharge_dt.isoformat(sep=" ") if discharge_dt else None,
                    status,
                ),
            )
            admission_ids_by_patient[pid].append((cur.lastrowid, admit_dt, discharge_dt))
    return admission_ids_by_patient


def build_triage(cur, admission_ids_by_patient, professional_ids):
    for pid, admissions in admission_ids_by_patient.items():
        for admission_id, admit_dt, _ in admissions:
            cur.execute(
                """INSERT INTO TriageAssessment
                   (admission_id, performing_professional_id, blood_pressure,
                    heart_rate, respiratory_rate, body_temperature, oxygen_saturation,
                    pain_level, reported_symptoms, known_allergies, current_medications,
                    triage_priority_level)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    admission_id,
                    random.choice(professional_ids),
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


def build_unit_stays(cur, admission_ids_by_patient, professional_ids):
    for pid, admissions in admission_ids_by_patient.items():
        for admission_id, admit_dt, discharge_dt in admissions:
            n_stays = random.randint(1, 3)
            cursor_time = admit_dt
            for i in range(n_stays):
                unit = random.choice(UNIT_TYPES)
                if unit in ("ICU", "CCU", "MICU", "SICU") and random.random() < 0.2:
                    hours = random.randint(170, 400)
                else:
                    hours = random.randint(4, 96)
                entry_dt = cursor_time
                exit_dt = entry_dt + timedelta(hours=hours)
                if discharge_dt and i == n_stays - 1:
                    if entry_dt > discharge_dt:
                        entry_dt = discharge_dt
                    exit_dt = discharge_dt
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
                        exit_dt.isoformat(sep=" ") if (discharge_dt or i < n_stays - 1) else None,
                        None if i == 0 else "condition improved, stepped down",
                    ),
                )
                cursor_time = exit_dt


def main():
    # Start from a fresh file so re-running doesn't fail on CREATE TABLE
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    with open(SCHEMA_PATH) as f:
        cur.executescript(f.read())

    professional_ids = build_professionals(cur)
    patient_ids = build_patients(cur)
    admission_ids_by_patient = build_admissions(cur, patient_ids, professional_ids)
    build_triage(cur, admission_ids_by_patient, professional_ids)
    build_unit_stays(cur, admission_ids_by_patient, professional_ids)
    # SurgicalProcedure is generated by generate_clinical_data.py

    conn.commit()

    for table in ["HealthcareProfessional", "Patient", "Admission", "TriageAssessment", "UnitStay"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {n} rows")

    conn.close()


if __name__ == "__main__":
    main()
