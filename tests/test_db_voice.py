"""Persistence behind temporary voice channels: due-for-creation and
stale-for-cleanup queries, plus the atomic claim. Run: pytest
"""

import asyncio

from bot.db import Database

NOW = 1_000_000
LEAD = 15 * 60
GRACE = 3 * 60 * 60


def base(**over):
    row = dict(
        channel_id=2, guild_id=1, creator_id=4, creator_name="n",
        title="t", activity="Dungeon", description=None,
        compo="standard", size=5, starts_at=NOW + 600,
    )
    row.update(over)
    return row


def test_events_due_for_voice_only_inside_the_window(tmp_path):
    async def go():
        db = Database(str(tmp_path / "v.db"))
        await db.connect()
        await db.create_event(message_id=10, **base(starts_at=NOW + 600))     # soon
        await db.create_event(message_id=11, **base(starts_at=NOW + 7200))    # far off
        await db.create_event(message_id=12, **base(starts_at=None))          # no time
        rows = await db.events_due_for_voice(NOW, LEAD, GRACE)
        await db.close()
        return sorted(r["message_id"] for r in rows)

    assert asyncio.run(go()) == [10]


def test_mark_voice_created_claims_once(tmp_path):
    async def go():
        db = Database(str(tmp_path / "v.db"))
        await db.connect()
        await db.create_event(message_id=10, **base())
        first = await db.mark_voice_created(10)
        second = await db.mark_voice_created(10)
        await db.close()
        return first, second

    assert asyncio.run(go()) == (True, False)


def test_stale_voice_lists_and_clears(tmp_path):
    async def go():
        db = Database(str(tmp_path / "v.db"))
        await db.connect()
        await db.create_event(message_id=10, **base())
        await db.set_status(10, "done")
        await db.set_voice_channel(10, 999)
        listed = [r["message_id"] for r in await db.events_with_stale_voice(NOW, GRACE)]
        await db.clear_voice_channel(10)
        after = [r["message_id"] for r in await db.events_with_stale_voice(NOW, GRACE)]
        await db.close()
        return listed, after

    listed, after = asyncio.run(go())
    assert listed == [10]
    assert after == []
