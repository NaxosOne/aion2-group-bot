"""Tests for the RSVP storage / due-event query. Run: pytest"""

import asyncio

from bot.db import Database


def test_rsvp_due_claim_prompt_and_responses(tmp_path):
    async def go():
        db = Database(str(tmp_path / "r.db"))
        await db.connect()
        await db.create_event(
            message_id=100,
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

        # Due: starts_at (1000) is within now (0) + window (2000).
        due = await db.events_to_rsvp(now_ts=0, window_s=2000)
        assert [e["message_id"] for e in due] == [100]

        # Claiming it removes it from the due set (posted at most once).
        await db.mark_rsvp_sent(100)
        assert await db.events_to_rsvp(now_ts=0, window_s=2000) == []

        # The prompt id links a prompt message back to its event.
        await db.set_rsvp_prompt_id(100, 555)
        ev = await db.get_event_by_rsvp_prompt(555)
        assert ev["message_id"] == 100

        # Responses upsert per user.
        await db.set_rsvp(100, 42, "yes")
        await db.set_rsvp(100, 42, "no")
        rows = await db.get_rsvps(100)
        await db.close()
        return len(rows), rows[0]["status"]

    count, status = asyncio.run(go())
    assert count == 1
    assert status == "no"
