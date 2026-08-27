"""Parsing of the schedule text typed in /event.

Accepted formats (time is required, the date is optional):
    "21:00"  "21h30"  "9pm"  "9:30pm"   -> today, or tomorrow if already past
    "tomorrow 21:00"  "today 8:30pm"
    "30/08 21:00"  "30/08/2026 9pm"     -> day/month; year inferred if absent

French keywords (aujourd'hui, demain) and the "21h30" style also work.
"""

import re
from datetime import date, datetime, timedelta

HELP_FORMATS = (
    "Accepted formats: `21:00`, `21h30`, `9pm`, `tomorrow 21:00`, "
    "`30/08 21:00` (day/month — the time is required)."
)

HELP_FORMATS_DATE = (
    "Accepted formats: `30/08` (day/month), `30/08/2026`, `today`, `tomorrow`."
)

HELP_FORMATS_DATETIME = (
    "Accepted formats: `30/08`, `tomorrow` (whole days) or `30/08 14:00`, "
    "`tomorrow 18h` (exact time)."
)

# English first, French kept as aliases.
DAY_KEYWORDS = {
    "today": 0,
    "tomorrow": 1,
    "aujourd'hui": 0,
    "aujourdhui": 0,
    "auj": 0,
    "demain": 1,
}


class ParseError(ValueError):
    """Parsing error, with a message that can be shown to the user."""


_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?:\s+|$)")
_TIME_RE = re.compile(r"^(\d{1,2})(?:\s*[h:]\s*(\d{2})?)?\s*(am|pm)?$")


def _parse_time(s: str) -> tuple[int, int]:
    """Converts "21:00", "21h30", "9pm" or "9:30pm" into (hour, minute)."""
    m = _TIME_RE.match(s)
    # A bare number like "21" is ambiguous: require a separator or am/pm.
    if not m or (m.group(3) is None and not re.search(r"[h:]", s)):
        raise ParseError(f"I couldn't understand that time. {HELP_FORMATS}")
    hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ampm:
        if not 1 <= hour <= 12:
            raise ParseError(f"Invalid time: `{hour}{ampm}`.")
        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
    if hour > 23 or minute > 59:
        raise ParseError(f"Invalid time: `{hour:02d}:{minute:02d}`.")
    return hour, minute


def parse_when(text: str, tz, now: datetime | None = None) -> datetime:
    """Converts text like "tomorrow 9pm" into a timezone-aware datetime."""
    now = (now or datetime.now(tz)).astimezone(tz)
    s = " ".join(text.strip().lower().split())
    if not s:
        raise ParseError(f"Empty schedule. {HELP_FORMATS}")

    # 1) The date part: keyword, numeric date, or nothing (= today).
    offset = None  # day offset for "today"/"tomorrow"
    date_part = None  # (day, month, year or None)
    for keyword, days in DAY_KEYWORDS.items():
        if s == keyword or s.startswith(keyword + " "):
            offset = days
            s = s[len(keyword):].strip()
            break
    if offset is None:
        m = _DATE_RE.match(s)
        if m:
            day, month = int(m.group(1)), int(m.group(2))
            year = m.group(3)
            if year is not None:
                year = int(year)
                if year < 100:
                    year += 2000
            date_part = (day, month, year)
            s = s[m.end():].strip()

    # 2) The time part, required.
    hour, minute = _parse_time(s)

    # 3) Assembly.
    if date_part is not None:
        day, month, year = date_part
        try:
            dt = datetime(year or now.year, month, day, hour, minute, tzinfo=tz)
        except ValueError:
            raise ParseError(f"Invalid date: `{day:02d}/{month:02d}`.") from None
        if dt <= now:
            if year is None:
                # "30/08 21:00" typed in September -> next year.
                dt = dt.replace(year=now.year + 1)
            else:
                raise ParseError("That date is already in the past.")
        return dt

    base = now.date() + timedelta(days=offset or 0)
    dt = datetime(base.year, base.month, base.day, hour, minute, tzinfo=tz)
    if dt <= now:
        if offset is None:
            # "21:00" when it's 22:00 -> tomorrow at 21:00.
            dt += timedelta(days=1)
        else:
            raise ParseError("That time is already in the past.")
    return dt


_DATE_ONLY_RE = re.compile(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$")


def parse_date(text: str, tz, now: datetime | None = None) -> date:
    """Converts "30/08", "30/08/2026", "today" or "tomorrow" into a date."""
    now = (now or datetime.now(tz)).astimezone(tz)
    s = " ".join(text.strip().lower().split())
    if s in DAY_KEYWORDS:
        return now.date() + timedelta(days=DAY_KEYWORDS[s])

    m = _DATE_ONLY_RE.match(s)
    if not m:
        raise ParseError(f"I couldn't understand that date. {HELP_FORMATS_DATE}")
    day, month = int(m.group(1)), int(m.group(2))
    year = m.group(3)
    if year is not None:
        year = int(year)
        if year < 100:
            year += 2000
    try:
        d = date(year or now.year, month, day)
        if d < now.date() and year is None:
            # "01/01" typed in August -> next year.
            d = date(now.year + 1, month, day)
    except ValueError:
        raise ParseError(f"Invalid date: `{day:02d}/{month:02d}`.") from None
    if d < now.date():
        raise ParseError("That date is already in the past.")
    return d


def parse_when_or_date(text: str, tz, now: datetime | None = None) -> tuple[datetime, bool]:
    """Accepts a whole day ("30/08", "tomorrow") or an exact moment
    ("30/08 14:00", "tomorrow 18h"). Returns (datetime, has_time); a whole
    day comes back at 00:00 with has_time=False."""
    s = " ".join(text.strip().lower().split())
    if s in DAY_KEYWORDS or _DATE_ONLY_RE.match(s):
        d = parse_date(s, tz, now)
        return datetime(d.year, d.month, d.day, tzinfo=tz), False
    return parse_when(text, tz, now), True
