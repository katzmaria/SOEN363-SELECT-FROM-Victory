-- Phase 1 query 20 on the integrated database.
-- Same question as Phase 1; renamed columns: examination_date_time -> exam_time, examination_type -> exam_type, procedure_date_time -> procedure_time, procedure_type -> procedure_name.
-- Query 20
-- Find all patients who underwent a surgical procedure and a radiology examination on
-- the same calendar day during the same admission. Display the patient name, admission
-- identifier, procedure type, radiology examination type, and the common date.

SELECT DISTINCT p.full_name,
       a.admission_id,
       s.procedure_name,
       r.exam_type,
       DATE(s.procedure_time) AS common_date
FROM SurgicalProcedure s

JOIN RadiologyExamination r
    ON r.admission_id = s.admission_id
    AND DATE(r.exam_time) = DATE(s.procedure_time)
JOIN Admission a ON a.admission_id = s.admission_id
JOIN Patient p ON p.patient_id = a.patient_id;
