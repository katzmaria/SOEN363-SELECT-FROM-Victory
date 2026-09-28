-- Query 6
-- Count the total number of hospital admissions for each patient,
-- including patients who have no recorded admissions.
SELECT
    p.patient_id,
    p.full_name,
    COUNT(a.admission_id) AS total_admissions
FROM Patient p
LEFT JOIN Admission a ON a.patient_id = p.patient_id
GROUP BY p.patient_id, p.full_name
ORDER BY total_admissions DESC, p.full_name;
