-- Query 9
-- Calculate the average length of stay for each critical care unit type, such as MICU,
-- SICU, ICU, and CCU. Display the unit type and its average length of stay.

SELECT
    us.unit_type,
    ROUND(
        AVG(
            JULIANDAY(us.exit_date_time)
            - JULIANDAY(us.entry_date_time)
        ),
        1
    ) AS average_length_of_stay
FROM UnitStay us
WHERE us.unit_type IN ('MICU', 'SICU', 'ICU', 'CCU')
    AND us.exit_date_time IS NOT NULL
GROUP BY us.unit_type;
