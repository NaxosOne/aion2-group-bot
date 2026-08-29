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


def test_admin_role_setting_round_trips(tmp_path):
    async def go():
        db = Database(str(tmp_path / "admin.db"))
        await db.connect()  # the admin_role_id column is applied here
        before = (await db.get_settings(1))
        await db.set_setting(1, "admin_role_id", 4242)
        after = (await db.get_settings(1))["admin_role_id"]
        await db.set_setting(1, "admin_role_id", None)  # clear
        cleared = (await db.get_settings(1))["admin_role_id"]
        await db.close()
        return (before is None or before["admin_role_id"] is None), after, cleared

    unset_first, after, cleared = asyncio.run(go())
    assert unset_first is True
    assert after == 4242
    assert cleared is None


def test_language_setting_round_trips(tmp_path):
    async def go():
        db = Database(str(tmp_path / "lang.db"))
        await db.connect()  # the language column is applied here
        first = await db.get_language(1)
        await db.set_language(1, "fr")
        after_set = await db.get_language(1)
        await db.set_language(1, None)  # reset to auto-detect
        after_reset = await db.get_language(1)
        await db.close()
        return first, after_set, after_reset

    assert asyncio.run(go()) == (None, "fr", None)
