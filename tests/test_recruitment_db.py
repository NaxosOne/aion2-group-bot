"""The applications table: create, find-pending, decide, delete."""

import asyncio

from bot.db import Database

APP = dict(
    guild_id=1,
    user_id=42,
    char_name="Kratos",
    char_class="Sorcerer",
    role="dps",
    level_cp="55 / 4.2k CP",
    experience="cleared everything",
    availability="weeknights, CET",
    motivation="wanna raid",
)


def test_create_returns_id_and_pending_is_findable():
    async def go():
        db = Database(":memory:")
        await db.connect()
        app_id = await db.create_application(**APP)
        assert isinstance(app_id, int)
        pending = await db.get_pending_application(1, 42)
        assert pending is not None
        assert pending["char_name"] == "Kratos"
        assert pending["status"] == "pending"

    asyncio.run(go())


def test_second_pending_blocked_but_reapply_after_decision_allowed():
    async def go():
        db = Database(":memory:")
        await db.connect()
        first = await db.create_application(**APP)
        assert await db.get_pending_application(1, 42) is not None
        await db.set_application_status(first, "rejected", reviewer_id=7, reason="low")
        assert await db.get_pending_application(1, 42) is None
        second = await db.create_application(**APP)
        assert second != first
        assert await db.get_pending_application(1, 42) is not None

    asyncio.run(go())


def test_set_status_records_decision_and_delete_removes_row():
    async def go():
        db = Database(":memory:")
        await db.connect()
        app_id = await db.create_application(**APP)
        await db.set_application_status(app_id, "accepted", reviewer_id=7, reason=None)
        row = await db.get_application(app_id)
        assert row["status"] == "accepted"
        assert row["reviewer_id"] == 7
        assert row["decided_at"] is not None
        await db.delete_application(app_id)
        assert await db.get_application(app_id) is None

    asyncio.run(go())


def test_recruit_channel_id_setting_roundtrips():
    async def go():
        db = Database(":memory:")
        await db.connect()
        await db.set_setting(1, "recruit_channel_id", 999)
        row = await db.get_settings(1)
        assert row["recruit_channel_id"] == 999

    asyncio.run(go())
