-- Demo 5a: the same local patient ID in each source is a different integrated patient.
-- Every source numbers its patients from 1, so local patient 1, 2 and 3 exist in all four sources.
SELECT m.source_local_id AS local_patient_id,
       s.continent,
       m.source_system   AS source,
       m.source_record_id AS original_id,
       m.integrated_id   AS integrated_patient_id,
       (SELECT COUNT(*) FROM Admission a WHERE a.patient_id = m.integrated_id) AS admissions
FROM IdMapping m
JOIN SourceSystem s ON s.source_system = m.source_system
WHERE m.entity_type = 'Patient' AND m.source_local_id <= 3
ORDER BY m.source_local_id, m.source_system;
