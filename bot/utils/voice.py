"""Pure helpers for temporary event voice channels.

The scheduler loop in cogs/groups.py creates a voice channel a short while
before a scheduled event and cleans it up once the event is over. These
predicates keep the timing and naming decisions testable and Discord-free.
"""

# Discord caps a channel name at 100 characters.
_NAME_LIMIT = 100


def voice_due(starts_at, now: int, lead_s: int) -> bool:
    """Whether a scheduled event's voice channel should exist yet."""
    return starts_at is not None and now >= starts_at - lead_s


def voice_channel_name(title: str) -> str:
    """The temporary channel's name: a speaker glyph and the event title."""
    return f"🔊 {title}"[:_NAME_LIMIT]


def voice_is_stale(status: str, starts_at, now: int, grace_s: int) -> bool:
    """Whether a temporary channel should be cleaned up.

    Stale once the event is done or cancelled, or long enough past its start
    that it is certainly over even if nobody pressed Done.
    """
    if status in ("done", "cancelled"):
        return True
    return starts_at is not None and now > starts_at + grace_s
