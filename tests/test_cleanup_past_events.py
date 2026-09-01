"""Past events are removed from the channel after a grace period.

Covers the query that selects them (scheduled events by start time; unscheduled
or closed ones by the message's own age, read from its snowflake) and the delete
that also clears the event's sign-ups and RSVP responses. Run: pytest
"""

import asyncio

from bot.db import Database

DISCORD_EPOCH_MS = 1420070400000


def _snowflake_at(ts_ms: int) -> int:
    """A message id whose embedded creation time is ts_ms."""
    return (ts_ms - DISCORD_EPOCH_MS) << 22


def _event(db, message_id, *, starts_at, status="open"):
    return db.create_event(
        message_id=message_id,
        channel_id=7,
        guild_id=1,
        creator_id=1,
        creator_name="A",
        title="Run",
        activity="Dungeon",
        compo="standard",
        size=5,
        starts_at=starts_at,
        status=status,
    )


NOW = 2_000_000_000
GRACE = 24 * 3600
CUTOFF = NOW - GRACE
OLD_MS = (CUTOFF - 100) * 1000
FRESH_MS = NOW * 1000


def test_events_to_clean_selects_only_the_past_ones(tmp_path):
    async def go():
        db = Database(str(tmp_path / "c.db"))
        await db.connect()
        await _event(db, 1, starts_at=CUTOFF - 100)  # scheduled, long past
        await _event(db, 2, starts_at=NOW + 3600)  # scheduled, still upcoming
        await _event(db, _snowflake_at(OLD_MS), starts_at=None)  # unscheduled, old
        await _event(db, _snowflake_at(FRESH_MS), starts_at=None)  # unscheduled, fresh
        # cancelled before a future start, but posted long ago
        await _event(
            db, _snowflake_at(OLD_MS) + 1, starts_at=NOW + 7200, status="cancelled"
        )
        ids = {e["message_id"] for e in await db.events_to_clean(NOW, GRACE)}
        await db.close()
        return ids

    ids = asyncio.run(go())
    assert 1 in ids
    assert 2 not in ids
    assert _snowflake_at(OLD_MS) in ids
    assert _snowflake_at(FRESH_MS) not in ids
    assert _snowflake_at(OLD_MS) + 1 in ids


def test_delete_event_also_clears_signups_and_rsvps(tmp_path):
    async def go():
        db = Database(str(tmp_path / "d.db"))
        await db.connect()
        await _event(db, 10, starts_at=1000)
        await db.upsert_signup(10, 42, "m42", "tank", 1.0)
        await db.set_rsvp(10, 42, "yes")
        await db.delete_event(10)
        gone = await db.get_event(10)
        signups = await db.get_signups(10)
        rsvps = await db.get_rsvps(10)
        await db.close()
        return gone, len(signups), len(rsvps)

    gone, n_signups, n_rsvps = asyncio.run(go())
    assert gone is None
    assert n_signups == 0
    assert n_rsvps == 0
