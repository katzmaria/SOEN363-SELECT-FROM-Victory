-- Query 19
-- List all admissions where the patient's discharge status or discharge condition indicates
-- that the patient died during the hospital stay. Display the patient name, admission
-- date, recorded date of death, and associated primary ICD-9 diagnosis.
SELECT
    p.full_name,
    a.admission_date_time,
    a.discharge_date_time AS date_of_death,
    d.icd9_code,
    i.official_title
FROM Patient p
JOIN Admission a       ON a.patient_id = p.patient_id
JOIN DischargeRecord dr ON dr.admission_id = a.admission_id
JOIN Diagnosis d       ON d.admission_id = a.admission_id
JOIN ICD9Dictionary i  ON i.icd9_code = d.icd9_code
WHERE d.diagnosis_type = 'primary'
  AND (a.final_admission_status = 'deceased'
       OR dr.condition_at_discharge = 'deceased')
ORDER BY a.admission_date_time;