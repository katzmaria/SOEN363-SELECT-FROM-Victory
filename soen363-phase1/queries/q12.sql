-- Query 12
-- Find all patients whose discharge-summary clinical note contains the keyword
-- "recovery". The search should be case-insensitive.
SELECT DISTINCT
    p.patient_id,
    p.full_name
FROM Patient p
JOIN Admission a    ON a.patient_id = p.patient_id
JOIN ClinicalNote c ON c.admission_id = a.admission_id
WHERE c.note_type = 'discharge_summary'
  AND LOWER(c.contents) LIKE '%recovery%'
ORDER BY p.full_name;
 