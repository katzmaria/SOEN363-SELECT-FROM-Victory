-- Demo 3: the three most frequently assigned primary ICD-9 diagnoses in each continent.
-- Ties are broken by ICD-9 code so the result is the same on every run.
WITH counts AS (
    SELECT s.continent, d.icd9_code, i.official_title, COUNT(*) AS times_assigned
    FROM Diagnosis d
    JOIN SourceSystem s    ON s.source_system = d.source_system
    JOIN ICD9Dictionary i  ON i.icd9_code = d.icd9_code
    WHERE d.diagnosis_type = 'primary'
    GROUP BY s.continent, d.icd9_code, i.official_title
), ranked AS (
    SELECT counts.*,
           ROW_NUMBER() OVER (PARTITION BY continent ORDER BY times_assigned DESC, icd9_code) AS position
    FROM counts
)
SELECT continent, position, icd9_code, official_title, times_assigned
FROM ranked
WHERE position <= 3
ORDER BY continent, position;
