-- SOEN 363 Project Phase 2: Hospital Management System
-- Integrated hospital database schema

PRAGMA foreign_keys = ON;

CREATE TABLE SourceSystem (
    source_system      TEXT NOT NULL PRIMARY KEY CHECK (source_system IN ('A', 'B', 'C', 'D')),
    continent          TEXT NOT NULL UNIQUE,
    hospital_name      TEXT NOT NULL,
    file_format        TEXT NOT NULL CHECK (file_format IN ('TXT', 'CSV', 'XML', 'JSON')),
    source_timezone    TEXT NOT NULL
);

-- Global surrogate keys (handout 6.1, 6.2). Every clean record gets one row: its source (continent via
-- SourceSystem), its local key from the clean files, its original raw ID, and the integrated key it was given.
-- integrated_id is not unique on purpose: a merged patient keeps one row per source record.
CREATE TABLE IdMapping (
    entity_type        TEXT    NOT NULL CHECK (entity_type IN ('Patient', 'HealthcareProfessional', 'Admission',
                           'TriageAssessment', 'Diagnosis', 'ClinicalNote', 'DiagnosticOrder',
                           'RadiologyExamination', 'SurgicalProcedure', 'UnitStay', 'DischargeRecord')),
    source_system      TEXT    NOT NULL REFERENCES SourceSystem(source_system),
    source_local_id    INTEGER NOT NULL,
    source_record_id   TEXT    NOT NULL,
    integrated_id      INTEGER NOT NULL,
    PRIMARY KEY (entity_type, source_system, source_local_id),
    UNIQUE (entity_type, source_system, source_record_id)
);

CREATE TABLE HealthcareProfessional (
    source_system      TEXT NOT NULL REFERENCES SourceSystem(source_system),
    source_record_id   TEXT NOT NULL,
    professional_id    INTEGER PRIMARY KEY,
    title              TEXT,
    full_name          TEXT,
    role               TEXT,
    department         TEXT,
    quality_flags      TEXT,
    UNIQUE (source_system, source_record_id)
);

CREATE TABLE ICD9Dictionary (
    icd9_code          TEXT NOT NULL PRIMARY KEY,
    official_title     TEXT NOT NULL,
    description        TEXT,
    disease_category   TEXT
);

-- No source columns here: a merged patient can come from several sources. Its source records are in IdMapping.
CREATE TABLE Patient (
    patient_id                      INTEGER PRIMARY KEY,
    first_name                      TEXT,
    last_name                       TEXT,
    full_name                       TEXT NOT NULL,
    date_of_birth                   DATE NOT NULL,
    sex                             TEXT CHECK (sex IN ('female', 'male', 'unknown')),
    address                         TEXT,
    phone                           TEXT,
    emergency_contact_name          TEXT,
    emergency_contact_relationship  TEXT,
    emergency_contact_phone         TEXT,
    life_status                     TEXT CHECK (life_status IN ('alive', 'deceased')),
    quality_flags                   TEXT
);

-- Possible cross-source duplicates found by the matching rules (task3_integration/README.md).
-- 'merged' pairs share one Patient; 'uncertain' pairs stay separate patients; 'merged_transitive' pairs were
-- uncertain on their own but share one Patient because both records were merged with the same other record.
CREATE TABLE PatientMatchCandidate (
    candidate_id       INTEGER PRIMARY KEY,
    source_system_1    TEXT    NOT NULL REFERENCES SourceSystem(source_system),
    source_local_id_1  INTEGER NOT NULL,
    patient_id_1       INTEGER NOT NULL REFERENCES Patient(patient_id),
    source_system_2    TEXT    NOT NULL REFERENCES SourceSystem(source_system),
    source_local_id_2  INTEGER NOT NULL,
    patient_id_2       INTEGER NOT NULL REFERENCES Patient(patient_id),
    rule_code          TEXT    NOT NULL,
    evidence           TEXT    NOT NULL,
    decision           TEXT    NOT NULL CHECK (decision IN ('merged', 'merged_transitive', 'uncertain')),
    CHECK (source_system_1 < source_system_2),
    UNIQUE (source_system_1, source_local_id_1, source_system_2, source_local_id_2),
    CHECK ((decision IN ('merged', 'merged_transitive')) = (patient_id_1 = patient_id_2))
);

CREATE TABLE Admission (
    source_system                TEXT NOT NULL REFERENCES SourceSystem(source_system),
    source_record_id             TEXT NOT NULL,
    admission_id                 INTEGER PRIMARY KEY,
    patient_id                   INTEGER NOT NULL REFERENCES Patient(patient_id),
    admitting_professional_id    INTEGER REFERENCES HealthcareProfessional(professional_id),
    admit_time                   DATETIME NOT NULL,
    admission_type               TEXT NOT NULL
        CHECK (admission_type IN ('emergency', 'urgent', 'elective', 'outpatient', 'newborn')),
    reason                       TEXT NOT NULL,
    admission_source             TEXT,
    insurance                    TEXT,
    discharge_time               DATETIME,
    admission_status             TEXT
        CHECK (admission_status IN ('active', 'discharged', 'deceased')),
    source_timezone              TEXT,
    quality_flags                TEXT,
    UNIQUE (source_system, source_record_id),
    UNIQUE (admission_id, patient_id),
    CHECK (discharge_time IS NULL OR discharge_time >= admit_time),
    CHECK (admission_status IS NULL
        OR (admission_status = 'active' AND discharge_time IS NULL)
        OR (admission_status IN ('discharged', 'deceased') AND discharge_time IS NOT NULL))
);

CREATE TABLE TriageAssessment (
    source_system         TEXT NOT NULL REFERENCES SourceSystem(source_system),
    source_record_id      TEXT NOT NULL,
    triage_id             INTEGER PRIMARY KEY,
    admission_id          INTEGER NOT NULL REFERENCES Admission(admission_id),
    nurse_id              INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    triage_time           DATETIME,
    systolic_bp           INTEGER CHECK (systolic_bp BETWEEN 50 AND 260),
    diastolic_bp          INTEGER CHECK (diastolic_bp BETWEEN 20 AND 160),
    heart_rate            INTEGER CHECK (heart_rate BETWEEN 20 AND 250),
    respiratory_rate      INTEGER CHECK (respiratory_rate BETWEEN 4 AND 60),
    temperature_c         REAL    CHECK (temperature_c BETWEEN 30 AND 45),
    spo2_pct              INTEGER CHECK (spo2_pct BETWEEN 50 AND 100),
    pain_score            INTEGER CHECK (pain_score BETWEEN 0 AND 10),
    symptoms              TEXT,
    allergies             TEXT,
    home_medications      TEXT,
    triage_priority       TEXT NOT NULL CHECK (triage_priority IN ('low', 'medium', 'high')),
    quality_flags         TEXT,
    UNIQUE (source_system, source_record_id),
    CHECK (systolic_bp IS NULL OR diastolic_bp IS NULL OR systolic_bp > diastolic_bp)
);

CREATE TABLE Diagnosis (
    source_system         TEXT NOT NULL REFERENCES SourceSystem(source_system),
    source_record_id      TEXT NOT NULL,
    diagnosis_id          INTEGER PRIMARY KEY,
    admission_id          INTEGER NOT NULL,
    patient_id            INTEGER NOT NULL REFERENCES Patient(patient_id),
    icd9_code             TEXT NOT NULL REFERENCES ICD9Dictionary(icd9_code),
    professional_id       INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    diagnosis_time        DATETIME NOT NULL,
    diagnosis_type        TEXT NOT NULL CHECK (diagnosis_type IN ('primary', 'secondary')),
    quality_flags         TEXT,
    UNIQUE (source_system, source_record_id),
    FOREIGN KEY (admission_id, patient_id) REFERENCES Admission(admission_id, patient_id)
);

CREATE TABLE ClinicalNote (
    source_system         TEXT NOT NULL REFERENCES SourceSystem(source_system),
    source_record_id      TEXT NOT NULL,
    note_id               INTEGER PRIMARY KEY,
    admission_id          INTEGER NOT NULL REFERENCES Admission(admission_id),
    author_id             INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    note_type             TEXT NOT NULL,
    note_time             DATETIME NOT NULL,
    note_text             TEXT NOT NULL,
    quality_flags         TEXT,
    UNIQUE (source_system, source_record_id)
);

CREATE TABLE DiagnosticOrder (
    source_system         TEXT NOT NULL REFERENCES SourceSystem(source_system),
    source_record_id      TEXT NOT NULL,
    order_id              INTEGER PRIMARY KEY,
    admission_id          INTEGER NOT NULL REFERENCES Admission(admission_id),
    professional_id       INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    order_time            DATETIME NOT NULL,
    exam_type             TEXT,
    indication            TEXT NOT NULL,
    order_status          TEXT NOT NULL
        CHECK (order_status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    priority              TEXT NOT NULL CHECK (priority IN ('routine', 'urgent', 'stat')),
    quality_flags         TEXT,
    UNIQUE (source_system, source_record_id),
    UNIQUE (order_id, admission_id)
);

CREATE TABLE RadiologyExamination (
    source_system               TEXT NOT NULL REFERENCES SourceSystem(source_system),
    source_record_id            TEXT NOT NULL,
    exam_id                     INTEGER PRIMARY KEY,
    admission_id                INTEGER NOT NULL REFERENCES Admission(admission_id),
    order_id                    INTEGER,
    referring_professional_id   INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    technician_id               INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    exam_type                   TEXT NOT NULL,
    exam_time                   DATETIME NOT NULL,
    body_area                   TEXT,
    exam_status                 TEXT NOT NULL
        CHECK (exam_status IN ('scheduled', 'completed', 'cancelled')),
    image_link                  TEXT,
    findings                    TEXT,
    quality_flags               TEXT,
    UNIQUE (source_system, source_record_id),
    FOREIGN KEY (order_id, admission_id) REFERENCES DiagnosticOrder(order_id, admission_id)
);

CREATE TABLE SurgicalProcedure (
    source_system         TEXT NOT NULL REFERENCES SourceSystem(source_system),
    source_record_id      TEXT NOT NULL,
    procedure_id          INTEGER PRIMARY KEY,
    admission_id          INTEGER NOT NULL REFERENCES Admission(admission_id),
    surgeon_id            INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    procedure_name        TEXT NOT NULL,
    procedure_time        DATETIME NOT NULL,
    outcome               TEXT,
    quality_flags         TEXT,
    UNIQUE (source_system, source_record_id)
);

CREATE TABLE UnitStay (
    source_system         TEXT NOT NULL REFERENCES SourceSystem(source_system),
    source_record_id      TEXT NOT NULL,
    stay_id               INTEGER PRIMARY KEY,
    admission_id          INTEGER NOT NULL REFERENCES Admission(admission_id),
    professional_id       INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    unit_type             TEXT NOT NULL
        CHECK (unit_type IN ('Emergency Department', 'ICU', 'CCU', 'MICU', 'SICU', 'General Ward')),
    room                  TEXT,
    bed                   TEXT,
    entry_time            DATETIME NOT NULL,
    exit_time             DATETIME,
    transfer_reason       TEXT,
    quality_flags         TEXT,
    UNIQUE (source_system, source_record_id),
    CHECK (exit_time IS NULL OR exit_time >= entry_time)
);

CREATE TABLE DischargeRecord (
    source_system         TEXT NOT NULL REFERENCES SourceSystem(source_system),
    source_record_id      TEXT NOT NULL,
    discharge_id          INTEGER PRIMARY KEY,
    admission_id          INTEGER NOT NULL UNIQUE REFERENCES Admission(admission_id),
    professional_id       INTEGER NOT NULL REFERENCES HealthcareProfessional(professional_id),
    discharge_time        DATETIME NOT NULL,
    destination           TEXT,
    discharge_condition   TEXT,
    medications           TEXT,
    instructions          TEXT,
    follow_up_time        TEXT,
    quality_flags         TEXT,
    UNIQUE (source_system, source_record_id)
);

CREATE INDEX idx_admission_patient     ON Admission(patient_id);
CREATE INDEX idx_diagnosis_admission   ON Diagnosis(admission_id);
CREATE INDEX idx_unitstay_admission    ON UnitStay(admission_id);
CREATE INDEX idx_radiology_admission   ON RadiologyExamination(admission_id);
CREATE INDEX idx_procedure_admission   ON SurgicalProcedure(admission_id);
CREATE INDEX idx_note_admission        ON ClinicalNote(admission_id);
CREATE INDEX idx_triage_admission      ON TriageAssessment(admission_id);
CREATE INDEX idx_order_admission       ON DiagnosticOrder(admission_id);
CREATE INDEX idx_idmap_integrated    ON IdMapping(entity_type, integrated_id);

-- Cross-table rules a CHECK cannot express (SQLite CHECKs see one row only). Timestamps are ISO 8601 UTC text
-- ('YYYY-MM-DDTHH:MM:SSZ'), so string comparison is chronological. For radiology and procedures an admission_id
-- that does not exist passes the trigger and is rejected by the foreign key; the DischargeRecord trigger rejects it itself.
CREATE TRIGGER trg_radiology_in_admission_insert BEFORE INSERT ON RadiologyExamination
BEGIN
    SELECT RAISE(ABORT, 'exam_time must be inside its admission period (admit_time to discharge_time)')
    WHERE EXISTS (SELECT 1 FROM Admission a WHERE a.admission_id = NEW.admission_id
                  AND (NEW.exam_time < a.admit_time OR (a.discharge_time IS NOT NULL AND NEW.exam_time > a.discharge_time)));
END;

CREATE TRIGGER trg_radiology_in_admission_update BEFORE UPDATE ON RadiologyExamination
BEGIN
    SELECT RAISE(ABORT, 'exam_time must be inside its admission period (admit_time to discharge_time)')
    WHERE EXISTS (SELECT 1 FROM Admission a WHERE a.admission_id = NEW.admission_id
                  AND (NEW.exam_time < a.admit_time OR (a.discharge_time IS NOT NULL AND NEW.exam_time > a.discharge_time)));
END;

CREATE TRIGGER trg_procedure_in_admission_insert BEFORE INSERT ON SurgicalProcedure
BEGIN
    SELECT RAISE(ABORT, 'procedure_time must be inside its admission period (admit_time to discharge_time)')
    WHERE EXISTS (SELECT 1 FROM Admission a WHERE a.admission_id = NEW.admission_id
                  AND (NEW.procedure_time < a.admit_time OR (a.discharge_time IS NOT NULL AND NEW.procedure_time > a.discharge_time)));
END;

CREATE TRIGGER trg_procedure_in_admission_update BEFORE UPDATE ON SurgicalProcedure
BEGIN
    SELECT RAISE(ABORT, 'procedure_time must be inside its admission period (admit_time to discharge_time)')
    WHERE EXISTS (SELECT 1 FROM Admission a WHERE a.admission_id = NEW.admission_id
                  AND (NEW.procedure_time < a.admit_time OR (a.discharge_time IS NOT NULL AND NEW.procedure_time > a.discharge_time)));
END;

CREATE TRIGGER trg_discharge_record_completed_insert BEFORE INSERT ON DischargeRecord
BEGIN
    SELECT RAISE(ABORT, 'DischargeRecord requires an admission with status discharged or deceased')
    WHERE NOT EXISTS (SELECT 1 FROM Admission a WHERE a.admission_id = NEW.admission_id
                      AND a.admission_status IN ('discharged', 'deceased'));
END;

CREATE TRIGGER trg_discharge_record_completed_update BEFORE UPDATE ON DischargeRecord
BEGIN
    SELECT RAISE(ABORT, 'DischargeRecord requires an admission with status discharged or deceased')
    WHERE NOT EXISTS (SELECT 1 FROM Admission a WHERE a.admission_id = NEW.admission_id
                      AND a.admission_status IN ('discharged', 'deceased'));
END;

-- Admission changes must not strand its children.
CREATE TRIGGER trg_admission_keep_completed BEFORE UPDATE OF admission_status ON Admission
BEGIN
    SELECT RAISE(ABORT, 'admission_status cannot leave discharged/deceased while a DischargeRecord exists')
    WHERE EXISTS (SELECT 1 FROM DischargeRecord d WHERE d.admission_id = NEW.admission_id)
      AND (NEW.admission_status IS NULL OR NEW.admission_status NOT IN ('discharged', 'deceased'));
END;

CREATE TRIGGER trg_admission_keep_window BEFORE UPDATE OF admit_time, discharge_time ON Admission
BEGIN
    SELECT RAISE(ABORT, 'admission period cannot exclude its radiology exams or procedures')
    WHERE EXISTS (SELECT 1 FROM RadiologyExamination e WHERE e.admission_id = NEW.admission_id
                  AND (e.exam_time < NEW.admit_time OR (NEW.discharge_time IS NOT NULL AND e.exam_time > NEW.discharge_time)))
       OR EXISTS (SELECT 1 FROM SurgicalProcedure p WHERE p.admission_id = NEW.admission_id
                  AND (p.procedure_time < NEW.admit_time OR (NEW.discharge_time IS NOT NULL AND p.procedure_time > NEW.discharge_time)));
END;
