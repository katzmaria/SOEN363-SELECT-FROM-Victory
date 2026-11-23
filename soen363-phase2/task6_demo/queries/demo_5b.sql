-- Demo 5b: how duplicate source identifiers were resolved (counts).
SELECT 'Patient local IDs used by more than one source' AS measure, COUNT(*) AS value
FROM (SELECT source_local_id FROM IdMapping WHERE entity_type = 'Patient'
      GROUP BY source_local_id HAVING COUNT(DISTINCT source_system) > 1)
UNION ALL
SELECT 'Admission local IDs used by more than one source', COUNT(*)
FROM (SELECT source_local_id FROM IdMapping WHERE entity_type = 'Admission'
      GROUP BY source_local_id HAVING COUNT(DISTINCT source_system) > 1)
UNION ALL
SELECT 'Patient source records (IdMapping rows)', COUNT(*) FROM IdMapping WHERE entity_type = 'Patient'
UNION ALL
SELECT 'Integrated patients (Patient rows)', COUNT(*) FROM Patient
UNION ALL
SELECT 'Integrated patients made from more than one source record (merged)', COUNT(*)
FROM (SELECT integrated_id FROM IdMapping WHERE entity_type = 'Patient'
      GROUP BY integrated_id HAVING COUNT(*) > 1)
UNION ALL
SELECT 'Cross-source match pairs kept separate (uncertain)', COUNT(*)
FROM PatientMatchCandidate WHERE decision = 'uncertain'
UNION ALL
SELECT 'Admissions pointing at a patient of another source (must be 0)', COUNT(*)
FROM Admission a
WHERE NOT EXISTS (SELECT 1 FROM IdMapping mp
                   WHERE mp.entity_type = 'Patient' AND mp.integrated_id = a.patient_id
                     AND mp.source_system = a.source_system);
