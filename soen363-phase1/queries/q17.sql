-- Query 17
-- Find all admissions during which the patient received more than one distinct ICD-9
-- diagnosis. Display the patient name, admission identifier, and number of distinct ICD-9 codes.
SELECT
    p.full_name,
    a.admission_id,
    COUNT(DISTINCT d.icd9_code) AS distinct_icd9_codes
FROM Patient p
JOIN Admission a ON a.patient_id = p.patient_id
JOIN Diagnosis d ON d.admission_id = a.admission_id
GROUP BY a.admission_id, p.full_name
HAVING COUNT(DISTINCT d.icd9_code) > 1
ORDER BY distinct_icd9_codes DESC, a.admission_id;