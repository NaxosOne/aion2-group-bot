"""Tests for per-guild channel settings. Run: pytest"""

import asyncio

from bot.db import Database


def test_rsvp_channel_setting_round_trips(tmp_path):
    async def go():
        db = Database(str(tmp_path / "s.db"))
        await db.connect()  # the rsvp_channel_id column is applied here
        await db.set_setting(1, "rsvp_channel_id", 999)
        settings = await db.get_settings(1)
        value = settings["rsvp_channel_id"]
        await db.close()
        return value

    assert asyncio.run(go()) == 999
