-- SOEN 363 Project Phase 2: Hospital Management System
-- Integrated hospital database schema

PRAGMA foreign_keys = ON;

CREATE TABLE SourceSystem (
    source_id          TEXT PRIMARY KEY CHECK (source_id IN ('A', 'B', 'C', 'D')),
    continent          TEXT NOT NULL UNIQUE,
    hospital_name      TEXT NOT NULL,
    file_format        TEXT NOT NULL CHECK (file_format IN ('TXT', 'CSV', 'XML', 'JSON')),
    source_timezone    TEXT NOT NULL
);

CREATE TABLE IdMapping (
    entity_type        TEXT NOT NULL,
    source_id          TEXT NOT NULL REFERENCES SourceSystem(source_id),
    source_record_id   TEXT NOT NULL,
    integrated_id      INTEGER NOT NULL,
    PRIMARY KEY (entity_type, source_id, source_record_id)
);

CREATE TABLE HealthcareProfessional (
    professional_id    INTEGER PRIMARY KEY,
    name               TEXT,
    role               TEXT,
    title              TEXT,
    department         TEXT,
    source_id          TEXT NOT NULL REFERENCES SourceSystem(source_id),
    source_record_id   TEXT NOT NULL,
    UNIQUE (source_id, source_record_id)
);

CREATE TABLE ICD9Dictionary (
    icd9_code          TEXT PRIMARY KEY,
    official_title     TEXT NOT NULL,
    description        TEXT,
    disease_category   TEXT
);

CREATE TABLE Patient (
    patient_id                      INTEGER PRIMARY KEY,
    full_name                       TEXT NOT NULL,
    date_of_birth                   DATE NOT NULL,
    gender                          TEXT
        CHECK (gender IN ('female', 'male', 'unknown')),
    address                         TEXT,
    telephone_number                TEXT,
    emergency_contact_name          TEXT,
    emergency_contact_relationship  TEXT,
    emergency_contact_phone         TEXT,
    life_status                     TEXT
        CHECK (life_status IN ('alive', 'deceased')),
    source_id          TEXT NOT NULL REFERENCES SourceSystem(source_id),
    source_record_id   TEXT NOT NULL,
    UNIQUE (source_id, source_record_id)
);

CREATE TABLE Admission (
    admission_id                 INTEGER PRIMARY KEY,
    patient_id                   INTEGER NOT NULL REFERENCES Patient(patient_id),
    admitting_professional_id    INTEGER
        REFERENCES HealthcareProfessional(professional_id),
    admission_date_time          DATETIME NOT NULL,
    admission_type               TEXT NOT NULL
        CHECK (admission_type IN ('emergency', 'urgent', 'elective', 'outpatient', 'newborn')),
    reason_for_admission         TEXT NOT NULL,
    admission_source             TEXT,
    insurance_information        TEXT,
    discharge_date_time          DATETIME,
    final_admission_status       TEXT
        CHECK (final_admission_status IN ('active', 'discharged', 'deceased')),
    source_timezone              TEXT,
    source_id          TEXT NOT NULL REFERENCES SourceSystem(source_id),
    source_record_id   TEXT NOT NULL,
    UNIQUE (source_id, source_record_id),
    UNIQUE (admission_id, patient_id),
    CHECK (discharge_date_time IS NULL OR discharge_date_time >= admission_date_time),
    CHECK (final_admission_status IS NULL
        OR (final_admission_status = 'active' AND discharge_date_time IS NULL)
        OR (final_admission_status IN ('discharged', 'deceased') AND discharge_date_time IS NOT NULL))
);

CREATE TABLE TriageAssessment (
    assessment_id                 INTEGER PRIMARY KEY,
    admission_id                  INTEGER NOT NULL REFERENCES Admission(admission_id),
    performing_professional_id    INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    assessment_date_time          DATETIME,
    systolic_bp                   INTEGER CHECK (systolic_bp BETWEEN 50 AND 260),
    diastolic_bp                  INTEGER CHECK (diastolic_bp BETWEEN 20 AND 160),
    heart_rate                    INTEGER CHECK (heart_rate BETWEEN 20 AND 250),
    respiratory_rate              INTEGER CHECK (respiratory_rate BETWEEN 4 AND 60),
    body_temperature              REAL    CHECK (body_temperature BETWEEN 30 AND 45),
    oxygen_saturation             INTEGER CHECK (oxygen_saturation BETWEEN 50 AND 100),
    pain_level                    INTEGER CHECK (pain_level BETWEEN 0 AND 10),
    reported_symptoms             TEXT,
    known_allergies               TEXT,
    current_medications           TEXT,
    triage_priority_level         TEXT NOT NULL
        CHECK (triage_priority_level IN ('low', 'medium', 'high')),
    source_id          TEXT NOT NULL REFERENCES SourceSystem(source_id),
    source_record_id   TEXT NOT NULL,
    UNIQUE (source_id, source_record_id),
    CHECK (systolic_bp IS NULL OR diastolic_bp IS NULL OR systolic_bp > diastolic_bp)
);

CREATE TABLE Diagnosis (
    diagnosis_id                  INTEGER PRIMARY KEY,
    patient_id                    INTEGER NOT NULL REFERENCES Patient(patient_id),
    admission_id                  INTEGER NOT NULL,
    icd9_code                     TEXT NOT NULL REFERENCES ICD9Dictionary(icd9_code),
    diagnosing_professional_id    INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    diagnosis_date_time           DATETIME NOT NULL,
    diagnosis_type                TEXT NOT NULL
        CHECK (diagnosis_type IN ('primary', 'secondary')),
    source_id          TEXT NOT NULL REFERENCES SourceSystem(source_id),
    source_record_id   TEXT NOT NULL,
    UNIQUE (source_id, source_record_id),
    FOREIGN KEY (admission_id, patient_id) REFERENCES Admission(admission_id, patient_id)
);

CREATE TABLE ClinicalNote (
    note_id                       INTEGER PRIMARY KEY,
    admission_id                  INTEGER NOT NULL REFERENCES Admission(admission_id),
    authoring_professional_id     INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    note_type                     TEXT NOT NULL,
    creation_date_time            DATETIME NOT NULL,
    contents                      TEXT NOT NULL,
    source_id          TEXT NOT NULL REFERENCES SourceSystem(source_id),
    source_record_id   TEXT NOT NULL,
    UNIQUE (source_id, source_record_id)
);

CREATE TABLE DiagnosticOrder (
    order_id                      INTEGER PRIMARY KEY,
    admission_id                  INTEGER NOT NULL REFERENCES Admission(admission_id),
    requesting_professional_id    INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    request_date_time             DATETIME NOT NULL,
    requested_examination         TEXT,
    clinical_reason               TEXT NOT NULL,
    order_status                  TEXT NOT NULL
        CHECK (order_status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    priority                      TEXT NOT NULL
        CHECK (priority IN ('routine', 'urgent', 'stat')),
    source_id          TEXT NOT NULL REFERENCES SourceSystem(source_id),
    source_record_id   TEXT NOT NULL,
    UNIQUE (source_id, source_record_id),
    UNIQUE (order_id, admission_id)
);

CREATE TABLE RadiologyExamination (
    examination_id                 INTEGER PRIMARY KEY,
    admission_id                   INTEGER NOT NULL REFERENCES Admission(admission_id),
    order_id                       INTEGER,
    referring_professional_id      INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    technician_professional_id     INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    examination_type               TEXT NOT NULL,
    examination_date_time          DATETIME NOT NULL,
    body_area_examined             TEXT,
    examination_status             TEXT NOT NULL
        CHECK (examination_status IN ('scheduled', 'completed', 'cancelled')),
    link_to_medical_images         TEXT,
    radiologist_findings           TEXT,
    source_id          TEXT NOT NULL REFERENCES SourceSystem(source_id),
    source_record_id   TEXT NOT NULL,
    UNIQUE (source_id, source_record_id),
    FOREIGN KEY (order_id, admission_id) REFERENCES DiagnosticOrder(order_id, admission_id)
);

CREATE TABLE SurgicalProcedure (
    procedure_id                   INTEGER PRIMARY KEY,
    admission_id                   INTEGER NOT NULL REFERENCES Admission(admission_id),
    performing_professional_id     INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    procedure_type                 TEXT NOT NULL,
    procedure_date_time            DATETIME NOT NULL,
    outcome                        TEXT,
    source_id          TEXT NOT NULL REFERENCES SourceSystem(source_id),
    source_record_id   TEXT NOT NULL,
    UNIQUE (source_id, source_record_id)
);

CREATE TABLE UnitStay (
    unit_stay_id                   INTEGER PRIMARY KEY,
    admission_id                   INTEGER NOT NULL REFERENCES Admission(admission_id),
    responsible_professional_id    INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    unit_type                      TEXT NOT NULL
        CHECK (unit_type IN ('Emergency Department', 'ICU', 'CCU', 'MICU', 'SICU', 'General Ward')),
    ward_and_room                  TEXT,
    bed_number                     TEXT,
    entry_date_time                DATETIME NOT NULL,
    exit_date_time                 DATETIME,
    reason_for_transfer            TEXT,
    source_id          TEXT NOT NULL REFERENCES SourceSystem(source_id),
    source_record_id   TEXT NOT NULL,
    UNIQUE (source_id, source_record_id),
    CHECK (exit_date_time IS NULL OR exit_date_time >= entry_date_time)
);

CREATE TABLE DischargeRecord (
    discharge_id                    INTEGER PRIMARY KEY,
    admission_id                    INTEGER NOT NULL UNIQUE REFERENCES Admission(admission_id),
    authorizing_professional_id     INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    discharge_date_time             DATETIME NOT NULL,
    discharge_destination           TEXT,
    condition_at_discharge          TEXT,
    prescribed_medications          TEXT,
    follow_up_instructions          TEXT,
    scheduled_appointments          TEXT,
    source_id          TEXT NOT NULL REFERENCES SourceSystem(source_id),
    source_record_id   TEXT NOT NULL,
    UNIQUE (source_id, source_record_id)
);

CREATE INDEX idx_admission_patient     ON Admission(patient_id);
CREATE INDEX idx_diagnosis_admission   ON Diagnosis(admission_id);
CREATE INDEX idx_unitstay_admission    ON UnitStay(admission_id);
CREATE INDEX idx_radiology_admission   ON RadiologyExamination(admission_id);
CREATE INDEX idx_procedure_admission   ON SurgicalProcedure(admission_id);
CREATE INDEX idx_note_admission        ON ClinicalNote(admission_id);
CREATE INDEX idx_triage_admission      ON TriageAssessment(admission_id);
CREATE INDEX idx_order_admission       ON DiagnosticOrder(admission_id);