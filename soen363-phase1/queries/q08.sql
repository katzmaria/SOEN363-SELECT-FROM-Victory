-- Query 8
-- Retrieve the most frequently assigned primary ICD-9 diagnosis among admissions that
-- included at least one ICU or CCU stay. Display the ICD-9 code, its official
-- description, and the number of times it was assigned.

SELECT d.icd9_code,
       i.official_title,
       COUNT(*) AS times_assigned
FROM Diagnosis d

JOIN ICD9Dictionary i ON i.icd9_code = d.icd9_code

WHERE d.diagnosis_type = 'primary'
AND EXISTS (
    SELECT 1
    FROM UnitStay u
              
    WHERE u.admission_id = d.admission_id
    AND u.unit_type IN ('ICU', 'CCU')
)

GROUP BY d.icd9_code, i.official_title
ORDER BY times_assigned DESC

LIMIT 1;