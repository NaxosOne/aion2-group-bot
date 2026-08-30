"""Pure helpers behind recurring events: the next weekly occurrence and
whether one is due to be posted. Run: pytest
"""

from bot.utils.recurrence import WEEK_SECONDS, next_weekly, recurrence_due

BASE = 1_000_000


def test_next_weekly_is_one_week_after_the_occurrence():
    assert next_weekly(BASE, now_ts=BASE) == BASE + WEEK_SECONDS


def test_next_weekly_skips_missed_occurrences_after_downtime():
    # Two weeks and a bit have passed: jump straight to the next future one.
    assert (
        next_weekly(BASE, now_ts=BASE + 2 * WEEK_SECONDS + 5) == BASE + 3 * WEEK_SECONDS
    )


def test_next_weekly_is_strictly_after_now():
    nxt = next_weekly(BASE, now_ts=BASE + 5 * WEEK_SECONDS)
    assert nxt > BASE + 5 * WEEK_SECONDS


def test_recurrence_due_within_the_lead_window():
    lead = 24 * 3600
    assert recurrence_due(BASE, now=BASE - lead + 1, lead_s=lead) is True


def test_recurrence_not_due_before_the_lead_window():
    lead = 24 * 3600
    assert recurrence_due(BASE, now=BASE - lead - 1, lead_s=lead) is False
