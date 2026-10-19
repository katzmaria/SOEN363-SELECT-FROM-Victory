-- Query 7
-- List all patients who entered the hospital through the Emergency Department and
-- were later transferred to an ICU or CCU during the same admission.

SELECT DISTINCT
    p.full_name
FROM Patient p
INNER JOIN Admission a
    ON p.patient_id = a.patient_id
INNER JOIN UnitStay us1
    ON a.admission_id = us1.admission_id
INNER JOIN UnitStay us2
    ON a.admission_id = us2.admission_id
WHERE us1.unit_type = 'Emergency Department'
    AND us2.unit_type IN ('ICU', 'CCU', 'MICU', 'SICU')
    AND us2.entry_date_time > us1.entry_date_time
ORDER BY p.full_name;
