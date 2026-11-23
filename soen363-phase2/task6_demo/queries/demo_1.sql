-- Demo 1: integrated patient and admission counts by source and continent.
-- "source records" = rows in IdMapping (what each source exported and Task 2 kept).
-- "integrated" = distinct rows in the final tables. They differ only where cross-source matching merged records
-- (the 'All' row counts a merged patient once, so it can be lower than the sum of the four sources).
SELECT * FROM (
    SELECT s.source_system AS source,
           s.continent,
           (SELECT COUNT(*) FROM IdMapping m
             WHERE m.entity_type = 'Patient' AND m.source_system = s.source_system)             AS patient_source_records,
           (SELECT COUNT(DISTINCT m.integrated_id) FROM IdMapping m
             WHERE m.entity_type = 'Patient' AND m.source_system = s.source_system)             AS integrated_patients,
           (SELECT COUNT(*) FROM IdMapping m
             WHERE m.entity_type = 'Admission' AND m.source_system = s.source_system)           AS admission_source_records,
           (SELECT COUNT(*) FROM Admission a WHERE a.source_system = s.source_system)           AS integrated_admissions
    FROM SourceSystem s
    UNION ALL
    SELECT 'All', 'All',
           (SELECT COUNT(*) FROM IdMapping WHERE entity_type = 'Patient'),
           (SELECT COUNT(*) FROM Patient),
           (SELECT COUNT(*) FROM IdMapping WHERE entity_type = 'Admission'),
           (SELECT COUNT(*) FROM Admission)
)
ORDER BY CASE source WHEN 'All' THEN 1 ELSE 0 END, source;
