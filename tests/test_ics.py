"""The iCalendar export: a pure VCALENDAR/VEVENT builder. Run: pytest"""

from bot.utils.ics import build_calendar

# 2023-11-14 22:13:20 UTC
START = 1_700_000_000
STAMP = 1_699_999_999  # 22:13:19 UTC


def ev(message_id, starts_at, title="Fire Temple", description=None):
    return {
        "message_id": message_id, "title": title,
        "starts_at": starts_at, "description": description,
    }


def test_wraps_events_in_a_vcalendar():
    out = build_calendar([ev(1, START)], dtstamp_ts=STAMP)
    assert out.startswith("BEGIN:VCALENDAR\r\n")
    assert out.rstrip("\r\n").endswith("END:VCALENDAR")


def test_uses_crlf_line_endings():
    out = build_calendar([ev(1, START)], dtstamp_ts=STAMP)
    assert "\r\n" in out
    assert "\n" not in out.replace("\r\n", "")


def test_event_carries_utc_start_end_and_summary():
    out = build_calendar([ev(1, START)], default_duration_s=3600, dtstamp_ts=STAMP)
    assert "BEGIN:VEVENT\r\n" in out
    assert "UID:1@kisk\r\n" in out
    assert "DTSTAMP:20231114T221319Z\r\n" in out
    assert "DTSTART:20231114T221320Z\r\n" in out
    assert "DTEND:20231114T231320Z\r\n" in out
    assert "SUMMARY:Fire Temple\r\n" in out


def test_events_without_a_schedule_are_skipped():
    out = build_calendar([ev(1, None)], dtstamp_ts=STAMP)
    assert "BEGIN:VEVENT" not in out
    assert "BEGIN:VCALENDAR" in out


def test_text_values_are_escaped():
    out = build_calendar(
        [ev(1, START, title="Raid; HM", description="Bring pots, and gear\nlevel 50")],
        dtstamp_ts=STAMP,
    )
    assert "SUMMARY:Raid\\; HM\r\n" in out
    assert "DESCRIPTION:Bring pots\\, and gear\\nlevel 50\r\n" in out


def test_description_is_omitted_when_empty():
    out = build_calendar([ev(1, START, description=None)], dtstamp_ts=STAMP)
    assert "DESCRIPTION" not in out


def test_multiple_events_produce_multiple_vevents():
    out = build_calendar([ev(1, START), ev(2, START + 86400)], dtstamp_ts=STAMP)
    assert out.count("BEGIN:VEVENT") == 2
