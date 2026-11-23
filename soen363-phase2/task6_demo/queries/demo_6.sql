-- Demo 6: integrity checks for orphaned records and invalid chronology (0 violations = PASS).
-- Foreign keys are enforced by the database, so the orphan checks show the result of that enforcement.
SELECT check_name, violations, CASE WHEN violations = 0 THEN 'PASS' ELSE 'FAIL' END AS result
FROM (
    SELECT 'Admission without an existing patient' AS check_name, COUNT(*) AS violations
      FROM Admission a WHERE NOT EXISTS (SELECT 1 FROM Patient p WHERE p.patient_id = a.patient_id)
    UNION ALL SELECT 'Diagnosis without an existing admission', COUNT(*)
      FROM Diagnosis x WHERE NOT EXISTS (SELECT 1 FROM Admission a WHERE a.admission_id = x.admission_id)
    UNION ALL SELECT 'Diagnosis with an ICD-9 code missing from the dictionary', COUNT(*)
      FROM Diagnosis x WHERE NOT EXISTS (SELECT 1 FROM ICD9Dictionary i WHERE i.icd9_code = x.icd9_code)
    UNION ALL SELECT 'Diagnosis whose patient differs from its admission''s patient', COUNT(*)
      FROM Diagnosis x JOIN Admission a ON a.admission_id = x.admission_id WHERE a.patient_id <> x.patient_id
    UNION ALL SELECT 'TriageAssessment without an existing admission', COUNT(*)
      FROM TriageAssessment x WHERE NOT EXISTS (SELECT 1 FROM Admission a WHERE a.admission_id = x.admission_id)
    UNION ALL SELECT 'ClinicalNote without an existing admission', COUNT(*)
      FROM ClinicalNote x WHERE NOT EXISTS (SELECT 1 FROM Admission a WHERE a.admission_id = x.admission_id)
    UNION ALL SELECT 'DiagnosticOrder without an existing admission', COUNT(*)
      FROM DiagnosticOrder x WHERE NOT EXISTS (SELECT 1 FROM Admission a WHERE a.admission_id = x.admission_id)
    UNION ALL SELECT 'RadiologyExamination without an existing admission', COUNT(*)
      FROM RadiologyExamination x WHERE NOT EXISTS (SELECT 1 FROM Admission a WHERE a.admission_id = x.admission_id)
    UNION ALL SELECT 'RadiologyExamination pointing at a missing order', COUNT(*)
      FROM RadiologyExamination x WHERE x.order_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM DiagnosticOrder o WHERE o.order_id = x.order_id)
    UNION ALL SELECT 'SurgicalProcedure without an existing admission', COUNT(*)
      FROM SurgicalProcedure x WHERE NOT EXISTS (SELECT 1 FROM Admission a WHERE a.admission_id = x.admission_id)
    UNION ALL SELECT 'UnitStay without an existing admission', COUNT(*)
      FROM UnitStay x WHERE NOT EXISTS (SELECT 1 FROM Admission a WHERE a.admission_id = x.admission_id)
    UNION ALL SELECT 'DischargeRecord without an existing admission', COUNT(*)
      FROM DischargeRecord x WHERE NOT EXISTS (SELECT 1 FROM Admission a WHERE a.admission_id = x.admission_id)
    UNION ALL SELECT 'Discharge before admission', COUNT(*)
      FROM Admission WHERE discharge_time IS NOT NULL AND discharge_time < admit_time
    UNION ALL SELECT 'Unit exit before unit entry', COUNT(*)
      FROM UnitStay WHERE exit_time IS NOT NULL AND exit_time < entry_time
    UNION ALL SELECT 'Radiology exam outside its admission period', COUNT(*)
      FROM RadiologyExamination x JOIN Admission a ON a.admission_id = x.admission_id
      WHERE x.exam_time < a.admit_time OR (a.discharge_time IS NOT NULL AND x.exam_time > a.discharge_time)
    UNION ALL SELECT 'Surgical procedure outside its admission period', COUNT(*)
      FROM SurgicalProcedure x JOIN Admission a ON a.admission_id = x.admission_id
      WHERE x.procedure_time < a.admit_time OR (a.discharge_time IS NOT NULL AND x.procedure_time > a.discharge_time)
);
