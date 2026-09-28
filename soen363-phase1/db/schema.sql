-- SOEN 363 Project Phase 1 - Hospital Management System
-- Database schema

PRAGMA foreign_keys = ON;

CREATE TABLE HealthcareProfessional (
    professional_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 TEXT NOT NULL,
    role                 TEXT NOT NULL
);

CREATE TABLE ICD9Dictionary (
    icd9_code            TEXT PRIMARY KEY,
    official_title       TEXT NOT NULL,
    description          TEXT,
    disease_category     TEXT
);

CREATE TABLE Patient (
    patient_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name                   TEXT NOT NULL,
    date_of_birth                DATE NOT NULL,
    gender                       TEXT,
    address                      TEXT,
    telephone_number             TEXT,
    emergency_contact_info       TEXT,
    life_status                  TEXT NOT NULL DEFAULT 'alive'
        CHECK (life_status IN ('alive', 'deceased'))
);

CREATE TABLE Admission (
    admission_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id                   INTEGER NOT NULL,
    admitting_professional_id    INTEGER NOT NULL,
    admission_date_time          DATETIME NOT NULL,
    admission_type               TEXT NOT NULL
        CHECK (admission_type IN ('emergency', 'urgent', 'elective', 'outpatient', 'newborn')),
    reason_for_admission         TEXT NOT NULL,
    admission_source             TEXT,
    insurance_information        TEXT,
    discharge_date_time          DATETIME,
    final_admission_status       TEXT NOT NULL DEFAULT 'active'
        CHECK (final_admission_status IN ('active', 'discharged', 'deceased')),
    FOREIGN KEY (patient_id) REFERENCES Patient(patient_id),
    FOREIGN KEY (admitting_professional_id) REFERENCES HealthcareProfessional(professional_id),
    CHECK (discharge_date_time IS NULL OR discharge_date_time >= admission_date_time)
);

CREATE TABLE TriageAssessment (
    assessment_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_id                  INTEGER NOT NULL,
    performing_professional_id    INTEGER NOT NULL,
    blood_pressure                 TEXT,
    heart_rate                     INTEGER,
    respiratory_rate                INTEGER,
    body_temperature                 REAL,
    oxygen_saturation                INTEGER,
    pain_level                       INTEGER CHECK (pain_level BETWEEN 0 AND 10),
    reported_symptoms                TEXT,
    known_allergies                  TEXT,
    current_medications              TEXT,
    triage_priority_level            TEXT NOT NULL
        CHECK (triage_priority_level IN ('low', 'medium', 'high')),
    FOREIGN KEY (admission_id) REFERENCES Admission(admission_id),
    FOREIGN KEY (performing_professional_id) REFERENCES HealthcareProfessional(professional_id)
);

CREATE TABLE Diagnosis (
    diagnosis_id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id                    INTEGER NOT NULL,
    admission_id                  INTEGER NOT NULL,
    icd9_code                     TEXT NOT NULL,
    diagnosing_professional_id    INTEGER NOT NULL,
    diagnosis_date_time           DATETIME NOT NULL,
    diagnosis_type                TEXT NOT NULL
        CHECK (diagnosis_type IN ('primary', 'secondary')),
    FOREIGN KEY (patient_id) REFERENCES Patient(patient_id),
    FOREIGN KEY (admission_id) REFERENCES Admission(admission_id),
    FOREIGN KEY (icd9_code) REFERENCES ICD9Dictionary(icd9_code),
    FOREIGN KEY (diagnosing_professional_id) REFERENCES HealthcareProfessional(professional_id)
);

CREATE TABLE ClinicalNote (
    note_id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_id                  INTEGER NOT NULL,
    authoring_professional_id     INTEGER NOT NULL,
    note_type                     TEXT NOT NULL,
    creation_date_time            DATETIME NOT NULL,
    contents                      TEXT NOT NULL,
    FOREIGN KEY (admission_id) REFERENCES Admission(admission_id),
    FOREIGN KEY (authoring_professional_id) REFERENCES HealthcareProfessional(professional_id)
);

CREATE TABLE DiagnosticOrder (
    order_id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_id                  INTEGER NOT NULL,
    requesting_professional_id    INTEGER NOT NULL,
    request_date_time             DATETIME NOT NULL,
    clinical_reason                TEXT NOT NULL,
    order_status                  TEXT NOT NULL
        CHECK (order_status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    priority                      TEXT NOT NULL
        CHECK (priority IN ('routine', 'urgent', 'stat')),
    FOREIGN KEY (admission_id) REFERENCES Admission(admission_id),
    FOREIGN KEY (requesting_professional_id) REFERENCES HealthcareProfessional(professional_id)
);

CREATE TABLE RadiologyExamination (
    examination_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_id                   INTEGER NOT NULL,
    order_id                       INTEGER,
    referring_professional_id      INTEGER NOT NULL,
    technician_professional_id     INTEGER NOT NULL,
    examination_type               TEXT NOT NULL,
    examination_date_time          DATETIME NOT NULL,
    body_area_examined             TEXT,
    examination_status             TEXT NOT NULL
        CHECK (examination_status IN ('scheduled', 'completed', 'cancelled')),
    link_to_medical_images         TEXT,
    radiologist_findings           TEXT,
    FOREIGN KEY (admission_id) REFERENCES Admission(admission_id),
    FOREIGN KEY (order_id) REFERENCES DiagnosticOrder(order_id),
    FOREIGN KEY (referring_professional_id) REFERENCES HealthcareProfessional(professional_id),
    FOREIGN KEY (technician_professional_id) REFERENCES HealthcareProfessional(professional_id)
);

CREATE TABLE SurgicalProcedure (
    procedure_id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_id                   INTEGER NOT NULL,
    performing_professional_id     INTEGER NOT NULL,
    procedure_type                 TEXT NOT NULL,
    procedure_date_time            DATETIME NOT NULL,
    outcome                        TEXT,
    FOREIGN KEY (admission_id) REFERENCES Admission(admission_id),
    FOREIGN KEY (performing_professional_id) REFERENCES HealthcareProfessional(professional_id)
);

CREATE TABLE UnitStay (
    unit_stay_id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_id                   INTEGER NOT NULL,
    responsible_professional_id    INTEGER NOT NULL,
    unit_type                      TEXT NOT NULL
        CHECK (unit_type IN ('Emergency Department', 'ICU', 'CCU', 'MICU', 'SICU', 'General Ward')),
    ward_and_room                  TEXT,
    bed_number                     TEXT,
    entry_date_time                DATETIME NOT NULL,
    exit_date_time                 DATETIME,
    reason_for_transfer            TEXT,
    FOREIGN KEY (admission_id) REFERENCES Admission(admission_id),
    FOREIGN KEY (responsible_professional_id) REFERENCES HealthcareProfessional(professional_id),
    CHECK (exit_date_time IS NULL OR exit_date_time >= entry_date_time)
);

CREATE TABLE DischargeRecord (
    discharge_id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_id                    INTEGER NOT NULL UNIQUE,
    authorizing_professional_id     INTEGER NOT NULL,
    discharge_date_time             DATETIME NOT NULL,
    discharge_destination           TEXT,
    condition_at_discharge          TEXT,
    prescribed_medications          TEXT,
    follow_up_instructions          TEXT,
    scheduled_appointments          TEXT,
    FOREIGN KEY (admission_id) REFERENCES Admission(admission_id),
    FOREIGN KEY (authorizing_professional_id) REFERENCES HealthcareProfessional(professional_id)
);
