"""
Value parsers shared by profiling and cleaning. Each parser returns a small result object instead of
raising, so the caller can decide whether a problem means "fix", "NULL + flag" or "reject".
"""

from __future__ import annotations

PIPELINE_VERSION = "2026.11.17-tasks"   # run_all.py checks that every file has the same version

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass, field

from common.standards import NONE_KNOWN, NUMERIC_PLACEHOLDERS, PLACEHOLDERS

UTC = dt.timezone.utc


class _RuleZone(dt.tzinfo):
    """Fixed daylight-saving rules for the zones of the sources, implementing PEP 495 `fold` like zoneinfo.
    Used only when the system has no time-zone database (e.g. Windows without the `tzdata` package).
    Europe/Paris (since 1996): CET UTC+1 / CEST UTC+2, summer time from the last Sunday of March 01:00 UTC
    to the last Sunday of October 01:00 UTC.
    Australia/Sydney (since 2008): AEST UTC+10 / AEDT UTC+11, summer time from the first Sunday of October
    02:00 AEST to the first Sunday of April 03:00 AEDT (both 16:00 UTC the day before)."""

    def __init__(self, name):
        self.name = name
        self.STD, self.DST = ((dt.timedelta(hours=1), dt.timedelta(hours=2)) if name == "Europe/Paris"
                              else (dt.timedelta(hours=10), dt.timedelta(hours=11)))

    @staticmethod
    def _sunday(year, month, last):
        if last:
            d = dt.datetime(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
            return d - dt.timedelta(days=(d.weekday() + 1) % 7)
        d = dt.datetime(year, month, 1)
        return d + dt.timedelta(days=(6 - d.weekday()) % 7)

    def _bounds_utc(self, year):
        """(summer time starts, summer time ends) in UTC, within this calendar year."""
        if self.name == "Europe/Paris":
            return self._sunday(year, 3, True).replace(hour=1), self._sunday(year, 10, True).replace(hour=1)
        return (self._sunday(year, 10, False) - dt.timedelta(hours=8),     # Sunday 02:00 AEST = Sat 16:00 UTC
                self._sunday(year, 4, False) - dt.timedelta(hours=8))      # Sunday 03:00 AEDT = Sat 16:00 UTC

    def _is_dst_utc(self, u):
        start, end = self._bounds_utc(u.year)
        return start <= u < end if start < end else (u >= start or u < end)

    def utcoffset(self, d):
        if d is None:
            return self.STD
        start, end = self._bounds_utc(d.year)
        wall = d.replace(tzinfo=None, fold=0)
        if start + self.STD <= wall < start + self.DST:                    # spring gap
            return self.STD if d.fold == 0 else self.DST
        if end + self.STD <= wall < end + self.DST:                        # autumn repeated hour
            return self.DST if d.fold == 0 else self.STD
        in_dst_n = start + self.DST <= wall < end + self.STD
        in_dst = in_dst_n if start < end else (wall >= start + self.DST or wall < end + self.STD)
        return self.DST if in_dst else self.STD

    def dst(self, d):
        return self.utcoffset(d) - self.STD

    def tzname(self, d):
        return self.name

    def fromutc(self, d):
        u = d.replace(tzinfo=None)
        _, end = self._bounds_utc(u.year)
        if self._is_dst_utc(u):
            return (u + self.DST).replace(tzinfo=self)
        return (u + self.STD).replace(tzinfo=self, fold=1 if end <= u < end + dt.timedelta(hours=1) else 0)

    def __str__(self):
        return self.name


def _fixed(hours, name):
    return lambda: dt.timezone(dt.timedelta(hours=hours), name)


_FALLBACK = {"Europe/Paris": lambda: _RuleZone("Europe/Paris"),
             "Australia/Sydney": lambda: _RuleZone("Australia/Sydney"),
             "Asia/Singapore": _fixed(8, "Asia/Singapore"), "Africa/Kampala": _fixed(3, "Africa/Kampala")}


def get_tz(name):
    """zoneinfo when the time-zone database is available, else the built-in rules above."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        if name in _FALLBACK:
            return _FALLBACK[name]()
        raise SystemExit(f"Time zone {name!r} not found. Install it with:  pip install tzdata")


# -----------------------------------------------------------------------------
# Missing values and text
# -----------------------------------------------------------------------------
def collapse_ws(s):
    return re.sub(r"\s+", " ", s).strip()


def is_missing(raw, numeric=False):
    """True for None, empty, whitespace and the placeholder tokens."""
    if raw is None:
        return True
    if isinstance(raw, float) and raw != raw:          # NaN
        return True
    s = collapse_ws(str(raw)).lower()
    return s in PLACEHOLDERS or (numeric and s in NUMERIC_PLACEHOLDERS)


def missing_kind(raw, numeric=False):
    """'absent' / 'empty' / 'placeholder' / None (not missing). Used by the profile."""
    if raw is None or (isinstance(raw, float) and raw != raw):
        return "absent"
    s = collapse_ws(str(raw))
    if s == "":
        return "empty"
    if s.lower() in PLACEHOLDERS or (numeric and s.lower() in NUMERIC_PLACEHOLDERS):
        return "placeholder"
    return None


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


PARTICLES = {"bin", "binte", "binti", "s/o", "d/o", "de", "du", "des", "van", "von", "der", "del", "di"}


def smart_title(name):
    """'mARTIN' -> 'Martin', 'o'neill' -> "O'Neill", 'saint-clair' -> 'Saint-Clair', 'DE LA TOUR' -> 'de La Tour',
    'kavitha D/O raman' -> 'Kavitha d/o Raman'. Only the case changes, never the letters."""
    out = []
    for i, tok in enumerate(collapse_ws(name).split(" ")):
        low = tok.lower()
        if low in PARTICLES and i > 0 or low in {"s/o", "d/o", "bin", "binte"}:
            out.append(low)
            continue
        out.append(re.sub(r"[^\W\d_]+", lambda m: m.group(0)[0].upper() + m.group(0)[1:].lower(), tok))
    return " ".join(out)


def case_inverted(s):
    """'cHEST pAIN', 'fOLLOW UP WITH THE gp': starts lower case although most letters are capitals."""
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 3 or not letters[0].islower():
        return False
    return sum(c.isupper() for c in letters) / len(letters) > 0.6


def case_damaged(s):
    """All capitals (3+ letters) or inverted case."""
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 3:
        return False
    return s.isupper() or case_inverted(s)


def all_lower(s):
    letters = [c for c in s if c.isalpha()]
    return len(letters) >= 3 and s.islower() and " " in s.strip()


# -----------------------------------------------------------------------------
# Identifiers
# -----------------------------------------------------------------------------
def parse_id(raw):
    """'12' -> 12, 'P000012' -> 12, 'E000012' -> 12, 'S0012' -> 12. None if not an identifier."""
    if is_missing(raw):
        return None
    m = re.fullmatch(r"[A-Za-z]{0,2}0*(\d+)", collapse_ws(str(raw)))
    return int(m.group(1)) if m else None


# -----------------------------------------------------------------------------
# Dates and timestamps
# -----------------------------------------------------------------------------
MONTHS = {"jan": 1, "janv": 1, "january": 1, "janvier": 1, "feb": 2, "fev": 2, "fevr": 2, "february": 2,
          "fevrier": 2, "mar": 3, "mars": 3, "march": 3, "apr": 4, "avr": 4, "april": 4, "avril": 4, "may": 5,
          "mai": 5, "jun": 6, "juin": 6, "june": 6, "jul": 7, "juil": 7, "july": 7, "juillet": 7, "aug": 8,
          "aout": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "septembre": 9, "oct": 10, "october": 10,
          "octobre": 10, "nov": 11, "november": 11, "novembre": 11, "dec": 12, "december": 12, "decembre": 12}


@dataclass
class DateResult:
    status: str                     # ok | missing | invalid | ambiguous
    value: object = None            # datetime (UTC, aware) or date
    fmt: str = ""                   # name of the format that matched
    flags: list = field(default_factory=list)
    detail: str = ""


_TIME = r"(?:[ T](\d{1,2})[:h](\d{2})(?::(\d{2})(?:\.\d+)?)?(?:\s?([AaPp]\.?[Mm]\.?))?)"
_TZ = r"\s*(Z|[+-]\d{2}:?\d{2})?"
DT_PATTERNS = [
    ("iso", re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})" + _TIME + "?" + _TZ)),
    ("slash", re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})" + _TIME + "?" + _TZ)),
    ("dot", re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})" + _TIME + "?" + _TZ)),
    ("dash_nn", re.compile(r"(\d{1,2})-(\d{1,2})-(\d{4})" + _TIME + "?" + _TZ)),
    ("text_month", re.compile(r"(\d{1,2})[\s-]+([^\W\d_]+\.?)[\s-]+(\d{4})" + _TIME + "?" + _TZ)),
]
EPOCH = re.compile(r"-?\d{9,13}")
YEAR_MIN, YEAR_MAX = 1900, 2100          # a year outside this range is a typo (e.g. 0202, 20225), not a real date


def _localize(naive, tz):
    """Local wall-clock -> aware datetime. Returns (aware, flags)."""
    a = naive.replace(tzinfo=tz, fold=0)
    b = naive.replace(tzinfo=tz, fold=1)
    if a.utcoffset() == b.utcoffset():
        return a, []
    back = a.astimezone(UTC).astimezone(tz).replace(tzinfo=None)
    if back != naive:      # spring-forward gap: this wall time never existed
        return a.astimezone(UTC).astimezone(tz), ["dst_nonexistent_time_shifted"]
    return a, ["dst_ambiguous_time_assumed_first"]   # autumn repeated hour: take the first (summer-time) one


def _either_order(a, b, s, name):
    """NN?NN?YYYY written in either order: readable only if one part is over 12 (or both are equal)."""
    if a > 12 and b <= 12:
        return (a, b, name + "_dmy"), None
    if b > 12 and a <= 12:
        return (b, a, name + "_mdy"), None
    if a == b:
        return (a, b, name), None
    if a <= 12 and b <= 12:
        return None, DateResult("ambiguous", fmt=name, detail=f"{s!r}: day/month order cannot be decided")
    return None, DateResult("invalid", fmt=name, detail=f"{s!r}: no valid day/month")


def parse_temporal(raw, tz=None, want_time=True, opts=None):
    """Parse a date or timestamp written in any of the formats found in the sources.

    Timestamps: returned as aware UTC datetimes. A value with an explicit offset or 'Z' uses it; a value
    without one is local time of the source time zone `tz`.
    Source conventions (`opts`, see common/standards.py SOURCES[..]["dates"]):
        slash_ampm  'mdy' -> a slash date WITH AM/PM is month-first (Source B); default day-first
        dot         'either' -> dot dates come in both orders (Source D); default day-first
        epoch       True -> 9-13 digit numbers are Unix seconds / milliseconds (Source D)
    Dash dates NN-NN-YYYY (and 'either' dot dates): day-first if the first number > 12, month-first if the
    second > 12, and AMBIGUOUS if both are <= 12 and different (we do not guess).
    """
    opts = opts or {}
    if is_missing(raw):
        return DateResult("missing")
    s = collapse_ws(str(raw))
    if opts.get("epoch") and EPOCH.fullmatch(s):
        n = int(s)
        secs = n / 1000 if len(s.lstrip("-")) >= 12 else n
        inst = dt.datetime(1970, 1, 1, tzinfo=UTC) + dt.timedelta(seconds=secs)
        if not YEAR_MIN <= inst.year <= YEAR_MAX:
            return DateResult("invalid", fmt="epoch", detail=f"{s!r}: year {inst.year} outside {YEAR_MIN}-{YEAR_MAX}")
        fmt = "epoch_ms" if len(s.lstrip("-")) >= 12 else "epoch_s"
        if not want_time:                  # a date sent as the instant of local midnight
            return DateResult("ok", inst.astimezone(tz).date(), fmt, ["unix_timestamp_converted"])
        return DateResult("ok", inst, fmt, ["unix_timestamp_converted"])
    for name, rx in DT_PATTERNS:
        m = rx.fullmatch(s)
        if not m:
            continue
        g = m.groups()
        ampm = g[6]
        if name == "iso":
            y, mo, d = int(g[0]), int(g[1]), int(g[2])
        elif name == "slash":
            a, b, y = int(g[0]), int(g[1]), int(g[2])
            if ampm and opts.get("slash_ampm") == "mdy":
                d, mo, name = b, a, "slash_mdy_ampm"
            else:
                d, mo, name = a, b, "slash_dmy"
        elif name == "dot" and opts.get("dot") != "either":
            d, mo, y, name = int(g[0]), int(g[1]), int(g[2]), "dot_dmy"
        elif name in ("dot", "dash_nn"):
            res, err = _either_order(int(g[0]), int(g[1]), s, name)
            if err:
                return err
            d, mo, name = res
            y = int(g[2])
        else:
            key = strip_accents(g[1]).lower().rstrip(".")
            if key not in MONTHS:
                return DateResult("invalid", fmt=name, detail=f"unknown month {g[1]!r}")
            d, mo, y = int(g[0]), MONTHS[key], int(g[2])
        hh, mi, ss, off = g[3], g[4], g[5], g[7]
        if not YEAR_MIN <= y <= YEAR_MAX:
            return DateResult("invalid", fmt=name, detail=f"{s!r}: year {y} outside {YEAR_MIN}-{YEAR_MAX}")
        try:
            day = dt.date(y, mo, d)
        except ValueError as exc:
            return DateResult("invalid", fmt=name, detail=f"{s!r}: {exc}")
        if not want_time:
            if hh is not None:
                return DateResult("ok", day, name, ["time_part_dropped"])
            return DateResult("ok", day, name)
        if hh is None:
            return DateResult("invalid", fmt=name, detail=f"{s!r}: time of day is missing")
        h, mn, sc = int(hh), int(mi), int(ss or 0)
        if ampm:
            if not 1 <= h <= 12:
                return DateResult("invalid", fmt=name, detail=f"{s!r}: hour {h} with AM/PM")
            h = h % 12 + (12 if ampm.lower().startswith("p") else 0)
        try:
            naive = dt.datetime(y, mo, d, h, mn, sc)
        except ValueError as exc:
            return DateResult("invalid", fmt=name, detail=f"{s!r}: {exc}")
        flags = []
        if off:
            if off == "Z":
                aware = naive.replace(tzinfo=UTC)
                flags.append("written_in_utc")
            else:
                sign = 1 if off[0] == "+" else -1
                hhmm = off[1:].replace(":", "")
                aware = naive.replace(tzinfo=dt.timezone(sign * dt.timedelta(hours=int(hhmm[:2]),
                                                                              minutes=int(hhmm[2:]))))
        else:
            aware, f2 = _localize(naive, tz)
            flags += f2
        return DateResult("ok", aware.astimezone(UTC), name + ("+offset" if off else ""), flags)
    return DateResult("invalid", detail=f"{s!r}: not a recognised date format")


def iso_utc(d):
    return d.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if d is not None else None


def date_shape(raw):
    """A readable 'shape' of a value: digits -> 9, letters -> a, kept punctuation. For the profile."""
    if raw is None:
        return "<absent>"
    s = str(raw)
    return re.sub(r"[^\W\d_]+", "a", re.sub(r"\d", "9", s)) if s.strip() else "<empty>"


# -----------------------------------------------------------------------------
# Numbers, units and vital signs
# -----------------------------------------------------------------------------
@dataclass
class NumResult:
    status: str                     # ok | missing | invalid
    value: object = None
    unit: str = ""
    detail: str = ""
    flags: list = field(default_factory=list)


_NUM = re.compile(r"([+-]?\d+(?:[.,]\d+)?)\s*(°\s*[CcFf]|[CcFf]|bpm|/min|c/min|%|/10|mmhg)?", re.I)


def parse_number(raw, numeric_placeholder=True):
    if is_missing(raw, numeric=numeric_placeholder):
        return NumResult("missing")
    s = collapse_ws(str(raw))
    m = _NUM.fullmatch(s)
    if not m:
        return NumResult("invalid", detail=f"{s!r} is not a number")
    num = m.group(1)
    flags = []
    if "," in num:
        flags.append("decimal_comma")
        num = num.replace(",", ".")
    unit = (m.group(2) or "").replace("°", "").replace(" ", "").lower()
    if unit:
        flags.append(f"unit_text_removed:{m.group(2).strip()}")
    return NumResult("ok", float(num), unit, flags=flags)


def parse_bp(raw):
    if is_missing(raw):
        return NumResult("missing")
    s = collapse_ws(str(raw))
    m = re.fullmatch(r"(\d{1,3})\s*[/-]\s*(\d{1,4})\s*(mmhg)?", s, re.I)
    if not m:
        return NumResult("invalid", detail=f"{s!r} is not systolic/diastolic")
    flags = ["bp_format_normalised"] if s != f"{m.group(1)}/{m.group(2)}" else []
    return NumResult("ok", (int(m.group(1)), int(m.group(2))), flags=flags)


def parse_temperature(raw, unit_attr=None):
    """-> Celsius. Unit from the attribute, else from the text, else inferred from the value:
    30-45 = Celsius, 86-113 = Fahrenheit (body temperatures cannot fall in the other range)."""
    r = parse_number(raw)
    if r.status != "ok":
        return r
    unit = (unit_attr or "").strip().upper() or r.unit.upper()
    unit = "F" if "F" in unit else "C" if "C" in unit else unit          # degF / °F / Cel / °C
    v = r.value
    if unit == "F" or (not unit and 86 <= v <= 113):
        c = round((v - 32) * 5 / 9, 1)
        r.flags.append("fahrenheit_converted_to_celsius" + ("" if unit else "_unit_inferred"))
        return NumResult("ok", c, "C", flags=r.flags)
    if unit in ("", "C"):
        return NumResult("ok", round(v, 1), "C", flags=r.flags)
    return NumResult("invalid", detail=f"unknown temperature unit {unit!r}")


def parse_spo2(raw, scale):
    """-> percent. Source C stores a fraction (0.97) unless a % sign is written."""
    r = parse_number(raw)
    if r.status != "ok":
        return r
    if r.unit == "%" or scale == "percent":
        return NumResult("ok", r.value, "%", flags=r.flags)
    r.flags.append("fraction_converted_to_percent")
    return NumResult("ok", round(r.value * 100, 1), "%", flags=r.flags)


# -----------------------------------------------------------------------------
# ICD-9, phone, contact
# -----------------------------------------------------------------------------
def normalize_icd9(raw):
    """-> (code or None, list of fixes). Dotted ICD-9-CM form: 3 digits before the dot (V: 2, E: 3)."""
    if is_missing(raw):
        return None, []
    s0 = str(raw)
    s = s0.strip().upper().replace(" ", "")
    fixes = ["whitespace_trimmed"] if s != s0 else []
    m = re.fullmatch(r"(\d{1,3})(?:\.(\d{1,2}))?", s)
    if m:
        head = m.group(1).zfill(3)
        if head != m.group(1):
            fixes.append("leading_zero_restored")
        return head + (f".{m.group(2)}" if m.group(2) else ""), fixes
    m = re.fullmatch(r"(\d{3})(\d{1,2})", s)
    if m:
        return f"{m.group(1)}.{m.group(2)}", fixes + ["decimal_point_restored"]
    m = re.fullmatch(r"V(\d{2})(?:\.?(\d{1,2}))?", s)
    if m:
        out = f"V{m.group(1)}" + (f".{m.group(2)}" if m.group(2) else "")
        return out, fixes + (["decimal_point_restored"] if m.group(2) and "." not in s else [])
    m = re.fullmatch(r"E(\d{3})(?:\.?(\d))?", s)
    if m:
        out = f"E{m.group(1)}" + (f".{m.group(2)}" if m.group(2) else "")
        return out, fixes + (["decimal_point_restored"] if m.group(2) and "." not in s else [])
    return "INVALID:" + s, fixes


def normalize_phone(raw, country, national_len, trunk):
    """-> E.164 string ('+33612345678') or None if it cannot be read."""
    if is_missing(raw):
        return None
    digits = re.sub(r"\D", "", str(raw))
    if trunk and digits.startswith(trunk) and len(digits) == national_len + 1:
        digits = digits[1:]
    elif digits.startswith(country) and len(digits) == len(country) + national_len:
        digits = digits[len(country):]
    if len(digits) != national_len:
        return None
    return f"+{country}{digits}"


_PHONE_IN_TEXT = re.compile(r"(\+?\(?\d[\d\s().-]{6,}\d)")


def split_contact(raw):
    """'Juliette Garcia (06 53 52 59 67)' -> ('Juliette Garcia', None, '06 53 52 59 67')
    'Immaculate Nyakato (Sister) 0756 523462' -> ('Immaculate Nyakato', 'Sister', '0756 523462')."""
    if is_missing(raw):
        return None, None, None
    s = collapse_ws(str(raw))
    phone = None
    m = re.search(r"\(\s*(\+?[\d\s.-]{7,}?)\s*\)", s)          # phone alone in brackets: 'Name (06 12 ..)'
    if m and sum(c.isdigit() for c in m.group(1)) >= 7:
        phone = m.group(1).strip()
        s = s[:m.start()] + s[m.end():]
        m = None
    else:
        m = _PHONE_IN_TEXT.search(s)
    if m and sum(c.isdigit() for c in m.group(1)) >= 7:
        phone = m.group(1).strip()
        s = (s[:m.start()] + s[m.end():]).replace("()", "")
    rel = None
    m = re.search(r"\(([^()]*)\)", s)
    if m and m.group(1).strip():
        rel = m.group(1).strip()
        s = s[:m.start()] + s[m.end():]
    name = collapse_ws(s).strip(" ,;-") or None
    return name, rel, phone


def none_known(raw):
    return collapse_ws(str(raw)).lower() in NONE_KNOWN
