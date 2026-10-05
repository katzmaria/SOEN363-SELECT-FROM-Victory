-- Query 7
-- List all patients who entered the hospital through the Emergency Department and
-- were later transferred to an ICU or CCU during the same admission.

SELECT
    p.full_name
FROM Patient p
INNER JOIN Admission a
    ON p.patient_id = a.patient_id
INNER JOIN UnitStay us
    ON a.admission_id = us.admission_id
WHERE [Emergency Department condition]
    AND us.unit_type IN ('ICU', 'CCU');
