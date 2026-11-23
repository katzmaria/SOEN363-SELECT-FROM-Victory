-- Phase 1 query 15 on the integrated database.
-- Same question as Phase 1; renamed columns: unit_stay_id -> stay_id.
-- Query 15
-- Count the total number of transfers between hospital units for each patient. The
-- patient's first unit placement is not considered a transfer; each subsequent unit stay
-- within the same admission represents one transfer.

SELECT
    p.full_name,
    COALESCE(SUM(t.transfers), 0) AS total_transfers
FROM Patient p
LEFT JOIN (
    SELECT
        a.patient_id,
        COUNT(us.stay_id) - 1 AS transfers
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
    p.full_name
ORDER BY total_transfers DESC;
