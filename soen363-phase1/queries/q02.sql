-- Query 2
-- Find all patients who had more than three hospital admissions.
-- Display the patient identifier, patient name, and total number
-- of admissions.
SELECT
    p.patient_id,
    p.full_name,
    COUNT(a.admission_id) AS total_admissions
FROM Patient p
JOIN Admission a ON a.patient_id = p.patient_id
GROUP BY p.patient_id, p.full_name
HAVING COUNT(a.admission_id) > 3
ORDER BY total_admissions DESC;
