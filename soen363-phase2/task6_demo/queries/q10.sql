-- Phase 1 query 10 on the integrated database.
-- Same question as Phase 1; renamed columns: procedure_date_time -> procedure_time, entry_date_time -> entry_time.
-- Query 10
-- List all patients who underwent a surgical procedure before
-- entering an ICU or CCU during the same admission. Critical care
-- units are ICU, CCU, MICU and SICU (per the handout). Display the
-- patient name, procedure date and time, critical care unit type,
-- and unit entry time.
SELECT
    p.full_name,
    sp.procedure_time,
    us.unit_type,
    us.entry_time AS unit_entry_time
FROM SurgicalProcedure sp
JOIN Admission a ON a.admission_id = sp.admission_id
JOIN Patient p ON p.patient_id = a.patient_id
JOIN UnitStay us ON us.admission_id = sp.admission_id
WHERE us.unit_type IN ('ICU', 'CCU', 'MICU', 'SICU')
  AND sp.procedure_time < us.entry_time
ORDER BY sp.procedure_time;
