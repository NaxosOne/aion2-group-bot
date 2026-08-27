"""Tests for the schedule parser. Run: pytest"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from bot.utils.time_parse import (
    ParseError,
    parse_date,
    parse_when,
    parse_when_or_date,
)

TZ = ZoneInfo("Europe/Paris")
# Freeze "now" for reproducible tests: Wednesday 26/08/2026, 18:00.
NOW = datetime(2026, 8, 26, 18, 0, tzinfo=TZ)


def p(text):
    return parse_when(text, TZ, now=NOW)


def test_time_only():
    assert p("21:00") == datetime(2026, 8, 26, 21, 0, tzinfo=TZ)
    assert p("21h") == datetime(2026, 8, 26, 21, 0, tzinfo=TZ)
    assert p("21h30") == datetime(2026, 8, 26, 21, 30, tzinfo=TZ)
    assert p("21:30") == datetime(2026, 8, 26, 21, 30, tzinfo=TZ)
    # 9:00 has already passed today -> tomorrow at 9:00.
    assert p("9:00") == datetime(2026, 8, 27, 9, 0, tzinfo=TZ)


def test_am_pm():
    assert p("9pm") == datetime(2026, 8, 26, 21, 0, tzinfo=TZ)
    assert p("9:30pm") == datetime(2026, 8, 26, 21, 30, tzinfo=TZ)
    assert p("9:30 PM") == datetime(2026, 8, 26, 21, 30, tzinfo=TZ)
    assert p("12am") == datetime(2026, 8, 27, 0, 0, tzinfo=TZ)  # midnight, passed
    assert p("tomorrow 12pm") == datetime(2026, 8, 27, 12, 0, tzinfo=TZ)


def test_keywords():
    assert p("tomorrow 21:00") == datetime(2026, 8, 27, 21, 0, tzinfo=TZ)
    assert p("today 20:30") == datetime(2026, 8, 26, 20, 30, tzinfo=TZ)
    # French keywords are kept as aliases.
    assert p("demain 21h") == datetime(2026, 8, 27, 21, 0, tzinfo=TZ)
    assert p("aujourd'hui 20h30") == datetime(2026, 8, 26, 20, 30, tzinfo=TZ)


def test_dates():
    assert p("30/08 21:00") == datetime(2026, 8, 30, 21, 0, tzinfo=TZ)
    assert p("30/08/2026 21:00") == datetime(2026, 8, 30, 21, 0, tzinfo=TZ)
    assert p("30/08 9pm") == datetime(2026, 8, 30, 21, 0, tzinfo=TZ)
    # 01/01 has passed this year -> next year.
    assert p("01/01 20:00") == datetime(2027, 1, 1, 20, 0, tzinfo=TZ)


def test_parse_date():
    pd = lambda t: parse_date(t, TZ, now=NOW)
    assert pd("30/08") == date(2026, 8, 30)
    assert pd("30/08/2026") == date(2026, 8, 30)
    assert pd("today") == date(2026, 8, 26)
    assert pd("tomorrow") == date(2026, 8, 27)
    assert pd("demain") == date(2026, 8, 27)  # French alias
    # Date without a year already passed this year -> next year.
    assert pd("01/01") == date(2027, 1, 1)
    for bad in ("", "yesterday", "32/01", "31/02", "01/01/2020"):
        try:
            pd(bad)
        except ParseError:
            pass
        else:
            raise AssertionError(f"{bad!r} should have been rejected")


def test_parse_when_or_date():
    pwd = lambda t: parse_when_or_date(t, TZ, now=NOW)
    # Whole days come back at midnight with has_time=False.
    assert pwd("30/08") == (datetime(2026, 8, 30, 0, 0, tzinfo=TZ), False)
    assert pwd("tomorrow") == (datetime(2026, 8, 27, 0, 0, tzinfo=TZ), False)
    # Exact moments keep their time.
    assert pwd("30/08 14:00") == (datetime(2026, 8, 30, 14, 0, tzinfo=TZ), True)
    assert pwd("tomorrow 18h") == (datetime(2026, 8, 27, 18, 0, tzinfo=TZ), True)
    assert pwd("21h") == (datetime(2026, 8, 26, 21, 0, tzinfo=TZ), True)
    for bad in ("", "gibberish", "30/08 25:00"):
        try:
            pwd(bad)
        except ParseError:
            pass
        else:
            raise AssertionError(f"{bad!r} should have been rejected")


def test_errors():
    for bad in ("", "gibberish", "25:00", "12:75", "31/02 20:00", "13pm", "21",
                "today 9:00", "tomorrow", "30/08/2020 21:00"):
        try:
            p(bad)
        except ParseError:
            pass
        else:
            raise AssertionError(f"{bad!r} should have been rejected")
