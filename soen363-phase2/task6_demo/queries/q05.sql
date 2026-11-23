-- Phase 1 query 5 on the integrated database.
-- Same question as Phase 1; renamed columns: entry_date_time -> entry_time, exit_date_time -> exit_time.
-- Query 5
-- Find all ICU or CCU unit stays that lasted more than seven days. Display the
-- patient name, unit type, unit entry time, unit exit time, and calculated length of stay.

SELECT
    p.full_name,
    us.unit_type,
    us.entry_time,
    us.exit_time,
    ROUND(
        JULIANDAY(us.exit_time) - JULIANDAY(us.entry_time),
        1
    ) AS length_of_stay_days
FROM UnitStay us
INNER JOIN Admission a
    ON us.admission_id = a.admission_id
INNER JOIN Patient p
    ON a.patient_id = p.patient_id
WHERE us.unit_type IN ('ICU', 'CCU', 'MICU', 'SICU')
    AND us.exit_time IS NOT NULL
    AND (JULIANDAY(us.exit_time) - JULIANDAY(us.entry_time)) > 7
ORDER BY length_of_stay_days ASC;
