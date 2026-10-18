-- Query 16
-- List all patients who stayed in more than one type of critical care unit during
-- the same admission. For example, a patient may have been transferred from an ICU to a CCU.

SELECT
    p.full_name,
    a.admission_id
FROM Patient p
INNER JOIN Admission a
    ON p.patient_id = a.patient_id
INNER JOIN UnitStay us
    ON a.admission_id = us.admission_id
WHERE us.unit_type IN ('MICU', 'SICU', 'ICU', 'CCU')
GROUP BY
    p.patient_id,
    p.full_name,
    a.admission_id
HAVING COUNT(DISTINCT us.unit_type) > 1
ORDER BY p.full_name ASC;
