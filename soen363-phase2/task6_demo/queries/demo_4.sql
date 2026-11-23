-- Demo 4: average completed admission duration (days) by continent.
-- Completed = status discharged or deceased with a recorded discharge time.
-- Times are UTC in every source, so the durations are comparable across continents.
SELECT s.continent,
       COUNT(*) AS completed_admissions,
       ROUND(AVG(JULIANDAY(a.discharge_time) - JULIANDAY(a.admit_time)), 2) AS avg_duration_days,
       ROUND(MIN(JULIANDAY(a.discharge_time) - JULIANDAY(a.admit_time)), 2) AS min_days,
       ROUND(MAX(JULIANDAY(a.discharge_time) - JULIANDAY(a.admit_time)), 2) AS max_days
FROM Admission a
JOIN SourceSystem s ON s.source_system = a.source_system
WHERE a.admission_status IN ('discharged', 'deceased')
  AND a.discharge_time IS NOT NULL
GROUP BY s.continent
ORDER BY s.continent;
