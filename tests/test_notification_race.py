"""The reminder / RSVP claim must refuse events that are no longer open.

A moderator often cancels an event right before it starts — exactly when the
reminder / RSVP loops fire. If the claim still succeeded on a cancelled event,
the loop would ping the party for an event that is already off. The claim is
therefore conditional on `status = 'open'` and reports whether it actually
claimed, so the loop can skip. Run: pytest
"""

import asyncio

from bot.db import Database


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


def test_mark_reminded_claims_open_once_and_refuses_cancelled(tmp_path):
    async def go():
        db = Database(str(tmp_path / "r.db"))
        await db.connect()
        await _open_event(db, 1)
        first = await db.mark_reminded(1)  # open + unreminded -> claims
        second = await db.mark_reminded(1)  # already reminded -> refuses
        await _open_event(db, 2)
        await db.set_status(2, "cancelled")
        cancelled = await db.mark_reminded(2)  # not open -> refuses
        await db.close()
        return first, second, cancelled

    assert asyncio.run(go()) == (True, False, False)


def test_mark_rsvp_sent_claims_open_once_and_refuses_cancelled(tmp_path):
    async def go():
        db = Database(str(tmp_path / "r.db"))
        await db.connect()
        await _open_event(db, 1)
        first = await db.mark_rsvp_sent(1)  # open + unsent -> claims
        second = await db.mark_rsvp_sent(1)  # already sent -> refuses
        await _open_event(db, 2)
        await db.set_status(2, "cancelled")
        cancelled = await db.mark_rsvp_sent(2)  # not open -> refuses
        await db.close()
        return first, second, cancelled

    assert asyncio.run(go()) == (True, False, False)
