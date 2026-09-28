-- Query 14
-- Retrieve the patient(s) with the longest completed hospital
-- stay, calculated from admission time to discharge time. If
-- multiple patients have the same maximum length of stay, display
-- all of them. Only admissions with a recorded discharge time are
-- considered.
SELECT
    p.full_name,
    a.admission_id,
    a.admission_date_time,
    a.discharge_date_time,
    ROUND(
        (JULIANDAY(a.discharge_date_time) - JULIANDAY(a.admission_date_time)) * 24, 1
    ) AS stay_length_hours
FROM Patient p
JOIN Admission a ON a.patient_id = p.patient_id
WHERE a.discharge_date_time IS NOT NULL
  AND (JULIANDAY(a.discharge_date_time) - JULIANDAY(a.admission_date_time)) = (
        SELECT MAX(JULIANDAY(a2.discharge_date_time) - JULIANDAY(a2.admission_date_time))
        FROM Admission a2
        WHERE a2.discharge_date_time IS NOT NULL
  )
ORDER BY p.full_name;
