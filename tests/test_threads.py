"""Tests for the event-thread name helper. Run: pytest"""

from bot.utils.threads import THREAD_NAME_LIMIT, event_thread_name


def test_event_thread_name_trims_whitespace():
    assert event_thread_name("  Fire Temple HM  ") == "Fire Temple HM"


def test_event_thread_name_caps_length():
    long = "x" * 150
    capped = event_thread_name(long)
    assert capped == "x" * THREAD_NAME_LIMIT
    assert len(capped) == THREAD_NAME_LIMIT
