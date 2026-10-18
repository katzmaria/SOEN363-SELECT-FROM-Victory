-- Query 11
-- Retrieve the name of each patient and the total number of radiology examinations
-- received across all admissions. Include patients who have not received any radiology
-- examinations and display zero for their examination count.

SELECT p.full_name,
       COUNT(r.examination_id) AS radiology_exam_count
FROM Patient p

LEFT JOIN Admission a ON a.patient_id = p.patient_id
LEFT JOIN RadiologyExamination r ON r.admission_id = a.admission_id

GROUP BY p.patient_id, p.full_name;