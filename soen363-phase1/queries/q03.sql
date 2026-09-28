-- Query 3
-- Retrieve the names, admission dates, and discharge dates of patients who were
-- discharged without undergoing any surgical procedure during the admission.
SELECT
    p.full_name,
    a.admission_date_time,
    a.discharge_date_time
FROM Patient p
JOIN Admission a ON a.patient_id = p.patient_id
WHERE a.final_admission_status = 'discharged'
  AND NOT EXISTS (
        SELECT 1
        FROM SurgicalProcedure s
        WHERE s.admission_id = a.admission_id
  )
ORDER BY a.admission_date_time;
 