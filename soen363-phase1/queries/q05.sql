-- Query 5
-- Find all ICU or CCU unit stays that lasted more than seven days. Display the
-- patient name, unit type, unit entry time, unit exit time, and calculated length of stay.

SELECT
    p.full_name,
    us.unit_type,
    us.entry_date_time,
    us.exit_date_time,
    ROUND(
        JULIANDAY(us.exit_date_time) - JULIANDAY(us.entry_date_time),
        1
    ) AS length_of_stay
FROM UnitStay us
INNER JOIN Admission a
    ON us.admission_id = a.admission_id
INNER JOIN Patient p
    ON a.patient_id = p.patient_id
WHERE us.unit_type IN ('ICU', 'CCU')
    AND us.exit_date_time IS NOT NULL
    AND (JULIANDAY(us.exit_date_time) - JULIANDAY(us.entry_date_time)) > 7;
