-- Query 15
-- Count the total number of transfers between hospital units for each patient. The
-- patient's first unit placement is not considered a transfer; each subsequent unit stay
-- within the same admission represents one transfer.

SELECT
    p.full_name,
    SUM(t.transfers) AS total_transfers
FROM Patient p
INNER JOIN (
    SELECT
        a.patient_id,
        COUNT(us.unit_stay_id) - 1 AS transfers
    FROM Admission a
    INNER JOIN UnitStay us
        ON a.admission_id = us.admission_id
    GROUP BY
        a.patient_id,
        a.admission_id
) t
    ON p.patient_id = t.patient_id
GROUP BY
    p.patient_id,
    p.full_name;
