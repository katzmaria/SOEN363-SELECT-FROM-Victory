-- Query 18
-- Retrieve the latest clinical note for each patient. Display the patient name, note
-- type, note creation date and time, and note contents.

SELECT full_name, note_type, creation_date_time, contents
FROM (
    SELECT p.full_name,
           c.note_type,
           c.creation_date_time,
           c.contents,
           ROW_NUMBER() OVER (PARTITION BY p.patient_id
                              ORDER BY c.creation_date_time DESC, c.note_id DESC) AS rn
    FROM Patient p

    JOIN Admission a ON a.patient_id = p.patient_id
    JOIN ClinicalNote c ON c.admission_id = a.admission_id
) 

WHERE rn = 1;