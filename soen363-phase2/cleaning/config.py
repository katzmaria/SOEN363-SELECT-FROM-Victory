"""
Cleaning configuration: every documented rule lives here as data so that the
rules are reviewable in one place and the pipeline code stays generic.

Nothing in this file is derived from the injection manifest; the manifest is
only used afterwards by report.py to check how many problems were detected.
"""

from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "output" / "raw"
OUT_CLEAN = ROOT / "output" / "clean"
OUT_QUARANTINE = ROOT / "output" / "quarantine"
OUT_LOG = ROOT / "output" / "cleaning_log"
REPORT = ROOT / "output" / "cleaning_report.md"
# The manifest may sit in output/ (as generated) or in output/raw/.
MANIFEST = next((p for p in (ROOT / "output" / "injection_manifest.json",
                             ROOT / "output" / "raw" / "injection_manifest.json") if p.exists()),
                ROOT / "output" / "injection_manifest.json")

# Fixed reference date so that every run gives the same result (the data set
# covers 2023-01-01 .. 2026-10-31). Dates of birth after it are invalid.
REFERENCE_DATE = date(2026, 11, 1)
# Clinical event timestamps outside this window are treated as invalid.
EVENT_MIN = datetime(2000, 1, 1, tzinfo=timezone.utc)
EVENT_MAX = datetime(2027, 1, 1, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# Sources, time zones and missing-value markers
# ---------------------------------------------------------------------------

SOURCES = {
    "A": {"label": "A - Europe (TXT)", "tz": "Europe/Paris",
          "ts_format": "DD/MM/YYYY HH:MM, local wall-clock time, no offset",
          "tz_rule": "Interpreted as Europe/Paris local time (CET/CEST) and converted to UTC."},
    "B": {"label": "B - North America (CSV)", "tz": "America/Toronto",
          "ts_format": "MM/DD/YYYY hh:mm AM/PM, local wall-clock time, no offset",
          "tz_rule": "Interpreted as America/Toronto local time (EST/EDT) and converted to UTC."},
    "C": {"label": "C - Asia (XML)", "tz": "Asia/Singapore",
          "ts_format": "ISO 8601 with explicit +08:00 offset",
          "tz_rule": "Explicit offset used. A value without an offset would be assumed Asia/Singapore and flagged."},
    "D": {"label": "D - Africa (JSON)", "tz": "Africa/Johannesburg",
          "ts_format": "ISO 8601 UTC ('Z'); some values without zone; some Unix epoch seconds",
          "tz_rule": "'Z'/offset values used as written. Epoch seconds are UTC by definition. "
                     "Values without a zone are assumed to be facility local time "
                     "(Africa/Johannesburg, UTC+2, no DST) and flagged 'timezone_assumed_local'."},
}

# Exact (case-sensitive, after trimming) tokens that mean "no value".
# Note: "None" / "None known" are NOT missing markers - they are clinical
# statements (no medication / no known allergies) and are kept.
# Note: "Unknown" (capital U) is a valid sex label in source B, while
# "unknown" (lower case) is B's missing marker.
MISSING_MARKERS = {
    "A": {"", "N/A"},
    "B": {"", "NULL", "unknown"},
    "C": {""},                      # plus: element absent / empty element
    "D": {"", "unknown"},           # plus: null / key absent
}

# ---------------------------------------------------------------------------
# Target schema. (field, kind, required)
#   id        local integer identifier of this record or of a parent
#   prof      reference to a healthcare professional (S001 / PR-1 / 1 -> 1)
#   name      person name: whitespace + case normalisation
#   text      free text: whitespace normalisation only
#   cat:<v>   categorical value mapped through codebook <v>
#   ts        timestamp -> UTC ISO 8601 'YYYY-MM-DDTHH:MM:SSZ'
#   dob       date of birth (source-specific format) -> 'YYYY-MM-DD'
#   date      ISO calendar date -> 'YYYY-MM-DD'
#   icd9      ICD-9-CM code kept as a string
#   bp        blood pressure 'sys/dia' -> two integer columns
#   vital:<v> numeric vital sign, unit-converted and range-checked
# Required = without it the record cannot be used and is quarantined.
# ---------------------------------------------------------------------------

SCHEMA = {
    "professionals": [
        ("professional_id", "id", True), ("full_name", "text", True), ("role", "cat:role", True),
    ],
    "icd9_codes": [
        ("icd9_code", "icd9", True), ("title", "text", True), ("category", "text", False),
    ],
    "patients": [
        ("patient_id", "id", True), ("family_name", "name", True), ("given_name", "name", True),
        ("birth_date", "dob", True), ("sex", "cat:sex", True), ("address", "text", False),
        ("phone", "text", False), ("emergency_contact", "text", False),
        ("life_status", "cat:life_status", True),
    ],
    "admissions": [
        ("admission_id", "id", True), ("patient_id", "id", True),
        ("admitting_professional_id", "prof", True), ("admit_time_utc", "ts", True),
        ("admission_type", "cat:admission_type", True), ("reason", "text", False),
        ("arrival_mode", "cat:arrival_mode", False), ("insurance", "text", False),
        ("discharge_time_utc", "ts", False), ("status", "cat:admission_status", True),
    ],
    "triage": [
        ("triage_id", "id", True), ("admission_id", "id", True), ("nurse_id", "prof", True),
        ("assessed_at_utc", "ts", True), ("blood_pressure", "bp", False),
        ("heart_rate_bpm", "vital:heart_rate", False), ("resp_rate_per_min", "vital:resp_rate", False),
        ("temperature_c", "vital:temperature", False), ("spo2_pct", "vital:spo2", False),
        ("pain_score", "vital:pain", False), ("symptoms", "text", False),
        ("allergies", "text", False), ("home_medications", "text", False),
        ("priority", "cat:triage_priority", True),
    ],
    "unit_stays": [
        ("stay_id", "id", True), ("admission_id", "id", True),
        ("responsible_professional_id", "prof", True), ("unit_type", "cat:unit_type", True),
        ("room", "text", False), ("bed", "text", False), ("entry_time_utc", "ts", True),
        ("exit_time_utc", "ts", False), ("transfer_reason", "text", False),
    ],
    "diagnoses": [
        ("diagnosis_id", "id", True), ("patient_id", "id", True), ("admission_id", "id", True),
        ("icd9_code", "icd9", True), ("professional_id", "prof", True),
        ("diagnosed_at_utc", "ts", False), ("rank", "cat:dx_rank", True),
    ],
    "orders": [
        ("order_id", "id", True), ("admission_id", "id", True), ("requester_id", "prof", True),
        ("ordered_at_utc", "ts", True), ("exam", "cat:exam", True), ("indication", "text", False),
        ("status", "cat:order_status", True), ("priority", "cat:order_priority", True),
    ],
    "radiology": [
        ("exam_id", "id", True), ("admission_id", "id", True), ("order_id", "id", True),
        ("referrer_id", "prof", True), ("technician_id", "prof", True),
        ("exam_type", "cat:exam", True), ("performed_at_utc", "ts", True),
        ("body_area", "cat:body_area", False), ("status", "cat:radiology_status", True),
        ("image_link", "text", False), ("findings", "text", False),
    ],
    "procedures": [
        ("procedure_id", "id", True), ("admission_id", "id", True), ("surgeon_id", "prof", True),
        ("procedure", "cat:procedure", True), ("performed_at_utc", "ts", True),
        ("outcome", "cat:surgery_outcome", False),
    ],
    "notes": [
        ("note_id", "id", True), ("admission_id", "id", True), ("author_id", "prof", True),
        ("note_type", "cat:note_type", True), ("written_at_utc", "ts", True), ("text", "text", True),
    ],
    "discharges": [
        ("discharge_id", "id", True), ("admission_id", "id", True), ("authorizer_id", "prof", True),
        ("discharge_time_utc", "ts", True), ("destination", "cat:destination", False),
        ("condition", "cat:discharge_condition", False), ("prescriptions", "text", False),
        ("instructions", "text", False), ("follow_up_date", "date", False),
    ],
}
ENTITY_ORDER = list(SCHEMA)
KEY = {e: fields[0][0] for e, fields in SCHEMA.items()}
CHILD_ENTITIES = ["triage", "unit_stays", "diagnoses", "orders", "radiology", "procedures", "notes", "discharges"]

# ---------------------------------------------------------------------------
# Codebooks: source label (case-folded, whitespace-collapsed) -> common value
# ---------------------------------------------------------------------------

SOURCE_CODEBOOKS = {
    "admission_type": {
        "A": {"emer": "emergency", "urg": "urgent", "elec": "elective", "amb": "outpatient", "nn": "newborn"},
        "B": {"emergency": "emergency", "urgent": "urgent", "elective": "elective", "outpatient": "outpatient", "newborn": "newborn"},
        "C": {"er": "emergency", "urgent care": "urgent", "scheduled": "elective", "ambulatory": "outpatient", "birth": "newborn"},
        "D": {"1": "emergency", "2": "urgent", "3": "elective", "4": "outpatient", "5": "newborn"},
    },
    "triage_priority": {
        "A": {"1": "high", "2": "medium", "3": "low"},
        "B": {"high": "high", "medium": "medium", "low": "low"},
        "C": {"red": "high", "yellow": "medium", "green": "low"},
        "D": {"p1": "high", "p2": "medium", "p3": "low"},
    },
    "unit_type": {
        "A": {"urgences": "Emergency Department", "rea": "ICU", "usic": "CCU", "rea-med": "MICU",
              "rea-chir": "SICU", "med": "General Ward"},
        "B": {"emergency department": "Emergency Department", "intensive care unit": "ICU",
              "coronary care unit": "CCU", "medical icu": "MICU", "surgical icu": "SICU",
              "general ward": "General Ward"},
        "C": {"emergency room": "Emergency Department", "icu": "ICU", "ccu": "CCU", "medical icu": "MICU",
              "surgical icu": "SICU", "ward": "General Ward"},
        "D": {"emergency": "Emergency Department", "icu": "ICU", "ccu": "CCU", "micu": "MICU",
              "sicu": "SICU", "ward": "General Ward"},
    },
    "admission_status": {
        "A": {"sorti": "discharged", "decede": "deceased", "en cours": "active"},
        "B": {"discharged": "discharged", "expired": "deceased", "in house": "active"},
        "C": {"discharged": "discharged", "died": "deceased", "admitted": "active"},
        "D": {"discharged": "discharged", "died": "deceased", "inpatient": "active"},
    },
    "sex": {
        "A": {"f": "female", "h": "male", "i": "unspecified"},
        "B": {"female": "female", "male": "male", "unknown": "unspecified"},
        "C": {"female": "female", "male": "male", "unspecified": "unspecified"},
        "D": {"f": "female", "m": "male", "o": "unspecified"},
    },
    "life_status": {
        "A": {"vivant": "alive", "decede": "deceased"},
        "B": {"n": "alive", "y": "deceased"},
        "C": {"living": "alive", "dead": "deceased"},
        "D": {"false": "alive", "true": "deceased"},
    },
    "dx_rank": {
        "A": {"p": "primary", "s": "secondary"},
        "B": {"principal": "primary", "secondary": "secondary"},
        "C": {"primary": "primary", "secondary": "secondary"},
        "D": {"true": "primary", "false": "secondary"},
    },
}

# Vocabularies whose labels are the same words in every source (only case,
# spaces and '_' differ). Key = normalised label, value = common value.
def _vocab(*values, extra=None):
    m = {v.lower().replace("_", " "): v for v in values}
    m.update(extra or {})
    return m

SHARED_VOCAB = {
    "role": _vocab("physician", "nurse", "surgeon", "radiologist", "radiology technician"),
    "arrival_mode": _vocab("walk-in", "ambulance", "physician referral", "transfer"),
    "exam": _vocab("Chest X-ray", "CT scan", "MRI", "Ultrasound", "ECG", "Blood panel"),
    "body_area": _vocab("Chest", "Abdomen", "Head"),
    "order_status": _vocab("completed", "pending", "in_progress", "cancelled"),
    "order_priority": _vocab("routine", "urgent", "stat"),
    "radiology_status": _vocab("completed", "scheduled"),
    "procedure": _vocab("Appendectomy", "Cholecystectomy", "Hip fracture repair",
                        "Coronary artery bypass graft", "Cardiac catheterization", "Hernia repair"),
    "surgery_outcome": _vocab("successful", "complications", "unsuccessful"),
    "note_type": _vocab("operative_note", "discharge_summary"),
    "destination": _vocab("home", "home with support", "rehabilitation facility", "long-term care",
                          "transfer to another hospital", "morgue"),
    "discharge_condition": _vocab("stable", "improved", "fair", "deceased"),
}

# ---------------------------------------------------------------------------
# Numeric plausibility ranges (after unit conversion). Outside -> invalid.
# ---------------------------------------------------------------------------

VITAL_RANGES = {
    "heart_rate": (20, 300, "bpm"),
    "resp_rate": (4, 80, "breaths/min"),
    "temperature": (25.0, 45.0, "degC"),
    "spo2": (50, 100, "%"),
    "pain": (0, 10, "(pain scale)"),
}
BP_RANGES = {"systolic": (50, 300), "diastolic": (20, 200)}

# Source-specific units (converted to the common unit before range checks).
TEMPERATURE_UNIT = {"A": "C", "B": "F", "C": "C", "D": "C"}
SPO2_UNIT = {"A": "percent", "B": "percent", "C": "fraction", "D": "percent"}
DECIMAL_COMMA = {"A": True, "B": False, "C": False, "D": False}

# Chronology tolerance when a timestamp fell into a DST transition window.
DST_SLACK_SECONDS = 3600
# A child event may refer to the admission's ambiguous date: an alternative
# reading must put the child within this window after admission to count.
TRIAGE_WINDOW_SECONDS = 2 * 3600

# Optional fields whose absence is logged ("retained with NULL"). Other
# optional fields are NULL by design (e.g. exit time of an ongoing unit stay,
# transfer reason of the first unit stay) and are not reported as missing.
TRACK_MISSING_OPTIONAL = {
    "patients": {"address", "phone", "emergency_contact"},
    "admissions": {"insurance"},
    "triage": {"allergies"},
}
# Optional timestamps where NULL carries meaning ("still in the unit" /
# "not yet discharged"): an INVALID value cannot be nulled without inventing
# that meaning, so the record is quarantined instead.
NULL_HAS_MEANING = {("unit_stays", "exit_time_utc"), ("admissions", "discharge_time_utc")}

# An admission whose (local) date is before the patient's date of birth is an
# impossible timeline. "quarantine": the admission (and its children) go to
# quarantine. "flag": kept and only logged. The generator did not inject this
# problem on purpose; it comes from random birth dates up to the generation
# date, so 52 patients have admissions before their recorded birth.
ADMISSION_BEFORE_BIRTH_POLICY = "quarantine"
