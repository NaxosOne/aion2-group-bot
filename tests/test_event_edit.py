"""Pure helpers behind editing a posted event: prefilling the schedule field
and deciding when a reschedule must re-arm the reminder / RSVP prompts. Run: pytest
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from bot.utils.time_parse import (
    format_when_for_edit,
    parse_when,
    should_rearm_after_reschedule,
)

TZ = ZoneInfo("Europe/Paris")


def test_format_when_for_edit_roundtrips_through_parse_when():
    # What we prefill into the edit modal must parse back to the same instant.
    moment = datetime(2026, 9, 15, 21, 0, tzinfo=TZ)
    starts_at = int(moment.timestamp())
    text = format_when_for_edit(starts_at, TZ)
    parsed = parse_when(text, TZ, now=datetime(2026, 9, 1, 12, 0, tzinfo=TZ))
    assert int(parsed.timestamp()) == starts_at


def test_format_when_for_edit_none_is_empty():
    # No schedule prefills an empty field, which the handler reads as "no time".
    assert format_when_for_edit(None, TZ) == ""


def test_rearm_when_rescheduled_to_a_future_time():
    assert should_rearm_after_reschedule(100, 5000, now_ts=1000) is True


def test_rearm_when_moved_earlier_but_still_future():
    # Pulling an event forward still needs the reminder recomputed.
    assert should_rearm_after_reschedule(9000, 3000, now_ts=1000) is True


def test_no_rearm_when_time_is_unchanged():
    assert should_rearm_after_reschedule(5000, 5000, now_ts=1000) is False


def test_no_rearm_when_schedule_is_cleared():
    assert should_rearm_after_reschedule(5000, None, now_ts=1000) is False


def test_no_rearm_when_new_time_is_in_the_past():
    assert should_rearm_after_reschedule(100, 500, now_ts=1000) is False
