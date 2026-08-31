"""Deleting an event's Discord message cancels the event, so the reminder and
RSVP loops stop firing for a message that no longer exists (its buttons are
gone too). Only open events are touched. Run: pytest
"""

import asyncio

from bot.cogs.groups import Groups
from bot.db import Database


class _Payload:
    def __init__(self, message_id):
        self.message_id = message_id


class _Bot:
    def __init__(self, db):
        self.db = db


def _cog(db):
    cog = Groups.__new__(Groups)  # no cog machinery needed here
    cog.bot = _Bot(db)
    return cog


def _open_event(db, message_id):
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
        starts_at=1000,
        status="open",
    )


def test_deleting_event_message_cancels_it(tmp_path):
    async def go():
        db = Database(str(tmp_path / "d.db"))
        await db.connect()
        cog = _cog(db)
        await _open_event(db, 100)
        await cog.on_raw_message_delete(_Payload(100))  # the event's message is gone
        after = (await db.get_event(100))["status"]
        # A deletion of some unrelated (non-event) message is a harmless no-op.
        await cog.on_raw_message_delete(_Payload(999))
        await db.close()
        return after

    assert asyncio.run(go()) == "cancelled"


def test_deleting_message_of_a_finished_event_leaves_it(tmp_path):
    async def go():
        db = Database(str(tmp_path / "d2.db"))
        await db.connect()
        cog = _cog(db)
        await _open_event(db, 200)
        await db.set_status(200, "done")
        await cog.on_raw_message_delete(_Payload(200))  # only open events are touched
        after = (await db.get_event(200))["status"]
        await db.close()
        return after

    assert asyncio.run(go()) == "done"
