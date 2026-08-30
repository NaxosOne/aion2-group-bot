"""Storage for the legion dashboard location. Run: pytest"""

import asyncio

from bot.db import Database


def test_dashboard_location_round_trips(tmp_path):
    async def go():
        db = Database(str(tmp_path / "dash.db"))
        await db.connect()
        before = await db.get_dashboard(1)
        await db.set_dashboard(1, 111, 222)
        stored = await db.get_dashboard(1)
        with_board = [row["guild_id"] for row in await db.guilds_with_dashboard()]
        await db.close()
        return before, stored, with_board

    before, stored, with_board = asyncio.run(go())
    assert before is None
    assert stored == (111, 222)
    assert with_board == [1]


def test_dashboard_can_be_cleared(tmp_path):
    async def go():
        db = Database(str(tmp_path / "dash2.db"))
        await db.connect()
        await db.set_dashboard(1, 111, 222)
        await db.set_dashboard(1, None, None)
        stored = await db.get_dashboard(1)
        listed = await db.guilds_with_dashboard()
        await db.close()
        return stored, listed

    stored, listed = asyncio.run(go())
    assert stored is None
    assert listed == []
