"""
Field-level normalisation: missing values, text, names, categories, dates and
timestamps, numbers and units, ICD-9 codes. Pure functions; each returns the
normalised value plus a list of Issue tuples describing what was done.

Issue = (field, code, action, before, after)
   action is one of:
     corrected  value changed to a standard form or repaired with evidence
     nulled     value was invalid and replaced by NULL (original kept in the log)
     flagged    value kept, but it is suspicious / an assumption was applied
     missing    value is absent (optional fields)
"""

import re
import unicodedata
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from config import (BP_RANGES, DECIMAL_COMMA, EVENT_MAX, EVENT_MIN, MISSING_MARKERS, REFERENCE_DATE,
                    SHARED_VOCAB, SOURCE_CODEBOOKS, SOURCES, SPO2_UNIT, TEMPERATURE_UNIT, VITAL_RANGES)

UTC = timezone.utc
MISSING = object()   # sentinel: value is missing (as opposed to invalid)
INVALID = object()   # sentinel: value present but unusable


def fmt_utc(dt):
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def show(v):
    """Printable form of a raw value for the log."""
    if v is None:
        return "<absent/null>"
    return repr(v) if isinstance(v, str) else str(v)


# ---------------------------------------------------------------------------
# Missing values and text
# ---------------------------------------------------------------------------

def is_missing(v, source):
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() in MISSING_MARKERS[source]
    return False


def clean_ws(s):
    """Unicode NFC, collapse every whitespace run to one space, trim."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def _title_token(tok):
    return tok[:1].upper() + tok[1:].lower() if tok else tok


def smart_title(s):
    # Title-case each part, keeping hyphens and apostrophes as separators:
    # "jean-pierre" -> "Jean-Pierre", "o'neil" -> "O'Neil".
    return re.sub(r"[^\s\-']+", lambda m: _title_token(m.group(0)), s)


def norm_name(s):
    """Whitespace always; case only when the whole value is in ONE case.
    Mixed-case values (e.g. 'McKenzie', 'DuPont') are already deliberate."""
    out = clean_ws(s)
    letters = [c for c in out if c.isalpha()]
    if letters and (out == out.upper() or out == out.lower()):
        out = smart_title(out)
    return out


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

def cat_key(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return clean_ws(str(v)).casefold().replace("_", " ")


def map_category(vocab, v, source):
    """Return (common_value | INVALID, was_messy)."""
    key = cat_key(v)
    if vocab in SOURCE_CODEBOOKS:
        table = SOURCE_CODEBOOKS[vocab][source]
        canonical_labels = set(table)
    else:
        table = SHARED_VOCAB[vocab]
        canonical_labels = None
    if key not in table:
        return INVALID, False
    # "messy" = the raw label differed from a clean label only by case/spacing.
    raw = v if isinstance(v, str) else None
    messy = False
    if raw is not None:
        if raw != raw.strip() or "  " in raw:
            messy = True
        elif canonical_labels is not None:
            messy = raw not in _source_labels(vocab, source)
    return table[key], messy


# Labels exactly as each source's documentation writes them (README codebook).
_DOC_LABELS = {
    ("admission_type", "A"): {"EMER", "URG", "ELEC", "AMB", "NN"},
    ("admission_type", "B"): {"Emergency", "Urgent", "Elective", "Outpatient", "Newborn"},
    ("admission_type", "C"): {"ER", "Urgent Care", "Scheduled", "Ambulatory", "Birth"},
    ("triage_priority", "A"): {"1", "2", "3"},
    ("triage_priority", "B"): {"High", "Medium", "Low"},
    ("triage_priority", "C"): {"Red", "Yellow", "Green"},
    ("triage_priority", "D"): {"P1", "P2", "P3"},
    ("unit_type", "A"): {"URGENCES", "REA", "USIC", "REA-MED", "REA-CHIR", "MED"},
    ("unit_type", "B"): {"Emergency Department", "Intensive Care Unit", "Coronary Care Unit", "Medical ICU",
                         "Surgical ICU", "General Ward"},
    ("unit_type", "C"): {"Emergency Room", "ICU", "CCU", "Medical ICU", "Surgical ICU", "Ward"},
    ("unit_type", "D"): {"emergency", "icu", "ccu", "micu", "sicu", "ward"},
    ("admission_status", "A"): {"SORTI", "DECEDE", "EN COURS"},
    ("admission_status", "B"): {"Discharged", "Expired", "In House"},
    ("admission_status", "C"): {"Discharged", "Died", "Admitted"},
    ("admission_status", "D"): {"discharged", "died", "inpatient"},
    ("sex", "A"): {"F", "H", "I"}, ("sex", "B"): {"Female", "Male", "Unknown"},
    ("sex", "C"): {"female", "male", "unspecified"}, ("sex", "D"): {"f", "m", "o"},
    ("life_status", "A"): {"VIVANT", "DECEDE"}, ("life_status", "B"): {"Y", "N"},
    ("life_status", "C"): {"living", "dead"},
    ("dx_rank", "A"): {"P", "S"}, ("dx_rank", "B"): {"Principal", "Secondary"},
    ("dx_rank", "C"): {"PRIMARY", "SECONDARY"},
}


def _source_labels(vocab, source):
    # D's admission type / life status / rank are numbers or booleans, never strings.
    return _DOC_LABELS.get((vocab, source), set())


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------

def parse_id(v):
    """Local integer id. Accepts 12, '12', 'S012', 'PR-12'."""
    if isinstance(v, bool) or v is None:
        return INVALID
    if isinstance(v, int):
        return v
    m = re.fullmatch(r"\s*(?:S|PR-)?0*(\d+)\s*", str(v))
    return int(m.group(1)) if m else INVALID


# ---------------------------------------------------------------------------
# Dates and timestamps
# ---------------------------------------------------------------------------

def local_to_utc(naive, tzname):
    """Attach a named zone to a wall-clock time and convert to UTC.
    Returns (utc_datetime, dst_flag) where dst_flag is
      'dst_ambiguous'   the wall time occurred twice (autumn fall-back);
                        the first occurrence (fold=0, summer time) is used
      'dst_nonexistent' the wall time never happened (spring gap); interpreted
                        with the pre-transition offset (PEP 495 fold=0), i.e.
                        effectively shifted forward by the gap
      None              unambiguous
    """
    tz = ZoneInfo(tzname)
    a = naive.replace(tzinfo=tz, fold=0)
    b = naive.replace(tzinfo=tz, fold=1)
    flag = None
    if a.utcoffset() != b.utcoffset():
        back = a.astimezone(UTC).astimezone(tz).replace(tzinfo=None)
        flag = "dst_nonexistent" if back != naive else "dst_ambiguous"
    return a.astimezone(UTC), flag


_A_TS = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4}) (\d{1,2}):(\d{2})")


def _mk(y, mo, d, h, mi):
    try:
        return datetime(y, mo, d, h, mi)
    except ValueError:
        return None


def parse_ts(v, source):
    """Return dict(value=utc|MISSING|INVALID, alt=utc|None, flags=[...]).

    alt is only set for source A when the written day and month are both <= 12
    (and differ): the value could be DD/MM (documented) or MM/DD (US style).
    """
    res = {"value": MISSING, "alt": None, "flags": []}
    if is_missing(v, source):
        return res
    tzname = SOURCES[source]["tz"]
    naive = None
    try:
        if source == "A":
            m = _A_TS.fullmatch(clean_ws(str(v)))
            if m:
                g1, g2, y, h, mi = map(int, m.groups())
                naive = _mk(y, g2, g1, h, mi)          # documented DD/MM
                swapped = _mk(y, g1, g2, h, mi) if g1 != g2 else None
                if naive is None and swapped is not None:
                    naive = swapped                      # only readable as MM/DD
                    res["flags"].append("date_written_mm_dd")
                elif naive is not None and swapped is not None:
                    res["alt"], _ = local_to_utc(swapped, tzname)
        elif source == "B":
            naive = datetime.strptime(clean_ws(str(v)), "%m/%d/%Y %I:%M %p")
        elif source in ("C", "D"):
            if source == "D" and (isinstance(v, (int, float)) and not isinstance(v, bool)
                                  or (isinstance(v, str) and v.strip().isdigit())):
                dt = datetime.fromtimestamp(int(v), UTC)
                res["flags"].append("timestamp_from_epoch_seconds")
            else:
                dt = datetime.fromisoformat(clean_ws(str(v)).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                naive = dt
                res["flags"].append("timezone_assumed_local")
            else:
                res["value"] = dt.astimezone(UTC)
    except (ValueError, OverflowError, OSError):
        naive = None
    if naive is not None:
        res["value"], dst = local_to_utc(naive, tzname)
        if dst:
            res["flags"].append(dst)
    if res["value"] is MISSING:
        res["value"] = INVALID
    elif not (EVENT_MIN <= res["value"] < EVENT_MAX):
        res["value"] = INVALID
        res["flags"].append("timestamp_out_of_range")
    return res


DOB_FORMATS = {"A": "%d/%m/%Y", "B": "%m/%d/%Y", "C": "%Y-%m-%d", "D": "%Y-%m-%d"}


def parse_date(v, source, fmt=None):
    if is_missing(v, source):
        return MISSING
    try:
        d = datetime.strptime(clean_ws(str(v)), fmt or "%Y-%m-%d").date()
    except ValueError:
        return INVALID
    if not (date(1900, 1, 1) <= d <= REFERENCE_DATE.replace(year=REFERENCE_DATE.year + 1)):
        return INVALID
    return d


# ---------------------------------------------------------------------------
# Numbers and units
# ---------------------------------------------------------------------------

def parse_number(v, source):
    if isinstance(v, bool):
        return INVALID
    if isinstance(v, (int, float)):
        return float(v)
    s = clean_ws(str(v))
    if DECIMAL_COMMA[source]:
        s = s.replace(",", ".")
    if re.fullmatch(r"[+-]?\d+(\.\d+)?", s):
        return float(s)
    return INVALID


def num_out(x):
    """Integers are written without '.0'."""
    return int(x) if float(x).is_integer() else round(x, 1)


def norm_vital(kind, v, source, field):
    """Return (value|None, issues, transformation_note|None)."""
    issues, note = [], None
    if is_missing(v, source):
        return None, issues, None
    x = parse_number(v, source)
    if x is INVALID:
        issues.append((field, "non_numeric_value", "nulled", show(v), None))
        return None, issues, None
    if isinstance(v, str) and source == "D":
        note = "string_to_number"
    if kind == "temperature" and TEMPERATURE_UNIT[source] == "F":
        x = round((x - 32) * 5 / 9, 1)
        note = "fahrenheit_to_celsius"
    if kind == "spo2" and SPO2_UNIT[source] == "fraction":
        # Values up to 1.5 are read as fractions (1.05 -> 105 %, then rejected by
        # the range check). Larger values cannot be fractions: read as percent.
        if x <= 1.5:
            x = round(x * 100, 1)
            note = "fraction_to_percent"
        else:
            issues.append((field, "spo2_unit_not_fraction", "flagged", show(v),
                           "value > 1.5 cannot be a fraction; read as percent"))
    lo, hi, unit = VITAL_RANGES[kind]
    if kind == "pain" and not float(x).is_integer():
        issues.append((field, "invalid_pain_level", "nulled", show(v), None))
        return None, issues, note
    if not (lo <= x <= hi):
        code = {"heart_rate": "invalid_heart_rate", "resp_rate": "invalid_respiratory_rate",
                "temperature": "invalid_temperature", "spo2": "invalid_oxygen_saturation",
                "pain": "invalid_pain_level"}[kind]
        conv = f" (= {num_out(x)} {unit})" if note else ""
        issues.append((field, code, "nulled", f"{show(v)}{conv}", f"NULL (allowed {lo}-{hi} {unit})"))
        return None, issues, note
    return num_out(x), issues, note


def norm_bp(v, source, field):
    """'120/80' -> (120, 80). Returns (sys, dia, issues)."""
    if is_missing(v, source):
        return None, None, []
    m = re.fullmatch(r"(\d{2,3})\s*/\s*(\d{2,3})", clean_ws(str(v)))
    if not m:
        return None, None, [(field, "invalid_blood_pressure", "nulled", show(v), None)]
    s, d = int(m.group(1)), int(m.group(2))
    if not (BP_RANGES["systolic"][0] <= s <= BP_RANGES["systolic"][1]
            and BP_RANGES["diastolic"][0] <= d <= BP_RANGES["diastolic"][1]):
        return None, None, [(field, "invalid_blood_pressure", "nulled", show(v), None)]
    issues = []
    if s <= d:
        issues.append((field, "bp_systolic_not_above_diastolic", "flagged", show(v),
                       "kept as recorded (physiologically implausible, needs review)"))
    return s, d, issues


# ---------------------------------------------------------------------------
# ICD-9
# ---------------------------------------------------------------------------

def norm_icd9(v, source, dictionary):
    """Return (code|MISSING|INVALID, issues). Codes are strings; never floats."""
    if is_missing(v, source):
        return MISSING, []
    code = clean_ws(str(v)).upper()
    if code in dictionary:
        return code, []
    # Leading zero lost (e.g. a spreadsheet turned '038.9' into '38.9'):
    # restore only when the zero-padded code exists in the dictionary.
    m = re.fullmatch(r"(\d{1,2})(\.\d+)?", code)
    if m:
        padded = m.group(1).zfill(3) + (m.group(2) or "")
        if padded in dictionary:
            return padded, [("icd9_code", "icd9_leading_zero_lost", "corrected", show(v), padded)]
    return INVALID, [("icd9_code", "unknown_icd9_code", "quarantined", show(v), None)]
