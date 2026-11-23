-- Phase 1 query 3 on the integrated database.
-- Same question as Phase 1; renamed columns: admission_date_time -> admit_time, discharge_date_time -> discharge_time, final_admission_status -> admission_status.
-- Query 3
-- Retrieve the names, admission dates, and discharge dates of patients who were
-- discharged without undergoing any surgical procedure during the admission.
SELECT
    p.full_name,
    a.admit_time,
    a.discharge_time
FROM Patient p
JOIN Admission a ON a.patient_id = p.patient_id
WHERE a.admission_status = 'discharged'
  AND NOT EXISTS (
        SELECT 1
        FROM SurgicalProcedure s
        WHERE s.admission_id = a.admission_id
  )
ORDER BY a.admit_time;
