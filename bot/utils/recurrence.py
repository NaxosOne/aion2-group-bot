"""Pure helpers for recurring events — no Discord dependency.

Only weekly recurrence for now: given an occurrence, find the next one, and
decide whether an occurrence is close enough to post its event.
"""

WEEK_SECONDS = 7 * 24 * 60 * 60


def next_weekly(occurrence_ts: int, now_ts: int) -> int:
    """The first weekly occurrence strictly after `now_ts`.

    One week after the given occurrence normally; after downtime it skips the
    occurrences that were missed rather than firing them all at once.
    """
    weeks = max(1, (now_ts - occurrence_ts) // WEEK_SECONDS + 1)
    return occurrence_ts + weeks * WEEK_SECONDS


def recurrence_due(next_at: int, now: int, lead_s: int) -> bool:
    """Whether the next occurrence is close enough to post its event now."""
    return now >= next_at - lead_s
