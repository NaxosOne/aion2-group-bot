"""Persistence behind redeploying panels and events: remembering the panel
message and listing a guild's open events. Run: pytest
"""

import asyncio

from bot.db import Database

REQUIRED = dict(
    channel_id=2, guild_id=1, creator_id=4, creator_name="n",
    title="t", activity="Dungeon", description=None,
    compo="standard", size=5, starts_at=None,
)


def test_panel_location_round_trips(tmp_path):
    async def go():
        db = Database(str(tmp_path / "p.db"))
        await db.connect()  # the panel_* columns are applied here
        before = await db.get_panel(1)
        await db.set_panel(1, 111, 222)
        after = await db.get_panel(1)
        await db.close()
        return before, after

    before, after = asyncio.run(go())
    assert before is None
    assert after == (111, 222)


def test_set_panel_overwrites_a_previous_location(tmp_path):
    async def go():
        db = Database(str(tmp_path / "p.db"))
        await db.connect()
        await db.set_panel(1, 111, 222)
        await db.set_panel(1, 333, 444)
        after = await db.get_panel(1)
        await db.close()
        return after

    assert asyncio.run(go()) == (333, 444)


def test_get_open_events_returns_only_the_guilds_open_events(tmp_path):
    async def go():
        db = Database(str(tmp_path / "e.db"))
        await db.connect()
        await db.create_event(message_id=10, status="open", **REQUIRED)
        await db.create_event(message_id=11, status="done", **REQUIRED)
        await db.create_event(message_id=12, status="cancelled", **REQUIRED)
        other = {**REQUIRED, "guild_id": 999}
        await db.create_event(message_id=13, status="open", **other)
        rows = await db.get_open_events(1)
        await db.close()
        return sorted(r["message_id"] for r in rows)

    assert asyncio.run(go()) == [10]
