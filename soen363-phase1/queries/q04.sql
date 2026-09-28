-- Query 4
-- List all patients who had both a radiology examination and a surgical procedure
-- during the same admission.
SELECT
    p.patient_id,
    p.full_name,
    a.admission_id
FROM Patient p
JOIN Admission a ON a.patient_id = p.patient_id
WHERE EXISTS (
        SELECT 1 FROM RadiologyExamination r
        WHERE r.admission_id = a.admission_id
  )
  AND EXISTS (
        SELECT 1 FROM SurgicalProcedure s
        WHERE s.admission_id = a.admission_id
  )
ORDER BY p.full_name, a.admission_id;