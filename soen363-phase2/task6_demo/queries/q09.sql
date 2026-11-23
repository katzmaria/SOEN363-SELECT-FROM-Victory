-- Phase 1 query 9 on the integrated database.
-- Same question as Phase 1; renamed columns: entry_date_time -> entry_time, exit_date_time -> exit_time.
-- Query 9
-- Calculate the average length of stay for each critical care unit type, such as MICU,
-- SICU, ICU, and CCU. Display the unit type and its average length of stay.

SELECT
    us.unit_type,
    ROUND(
        AVG(
            JULIANDAY(us.exit_time)
            - JULIANDAY(us.entry_time)
        ),
        1
    ) AS average_length_of_stay
FROM UnitStay us
WHERE us.unit_type IN ('MICU', 'SICU', 'ICU', 'CCU')
    AND us.exit_time IS NOT NULL
GROUP BY us.unit_type;
