-- Demo 2: admission counts by standardized admission type across continents.
-- The four sources use different labels; Task 2 mapped them to the five common values stored in
-- Admission.admission_type (see output/cleaning_log/label_mappings.csv).
SELECT a.admission_type,
       SUM(s.continent = 'Europe')  AS Europe,
       SUM(s.continent = 'Africa')  AS Africa,
       SUM(s.continent = 'Asia')    AS Asia,
       SUM(s.continent = 'Oceania') AS Oceania,
       COUNT(*)                     AS total
FROM Admission a
JOIN SourceSystem s ON s.source_system = a.source_system
GROUP BY a.admission_type
ORDER BY total DESC, a.admission_type;
