-- Query 13
-- List all admissions in which the patient had at least one radiology examination but
-- had no recorded ICU or CCU stay.

SELECT a.*
FROM Admission a

WHERE EXISTS (
    SELECT 1
    FROM RadiologyExamination r
    
    WHERE r.admission_id = a.admission_id
)

AND NOT EXISTS (
    SELECT 1
    FROM UnitStay u
    
    WHERE u.admission_id = a.admission_id
    AND u.unit_type IN ('ICU', 'CCU', 'MICU', 'SICU')
);