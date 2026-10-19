-- Query 1
-- List the names and admission dates of all patients who were
-- classified as high-priority emergency patients during triage.
SELECT
    p.full_name,
    a.admission_date_time
FROM Patient p
JOIN Admission a ON a.patient_id = p.patient_id
JOIN TriageAssessment t ON t.admission_id = a.admission_id
WHERE t.triage_priority_level = 'high'
  AND a.admission_type = 'emergency'
ORDER BY a.admission_date_time;
