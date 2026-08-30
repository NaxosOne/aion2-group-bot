"""Persistence behind recurring events: create, due window, atomic advance,
list and deactivate. Run: pytest
"""

import asyncio

from bot.db import Database


def rec(**over):
    row = dict(
        guild_id=1,
        channel_id=2,
        creator_id=3,
        creator_name="n",
        title="Raid",
        activity="Raid",
        description=None,
        compo="standard",
        size=5,
        ping_role_id=None,
        next_at=1000,
    )
    row.update(over)
    return row


def test_create_and_due_window(tmp_path):
    async def go():
        db = Database(str(tmp_path / "r.db"))
        await db.connect()
        rid = await db.create_recurrence(**rec(next_at=1000))
        await db.create_recurrence(**rec(next_at=100000))  # far off
        due = await db.recurrences_due(now_ts=900, lead_s=200)  # 1000 <= 900+200
        await db.close()
        return rid, sorted(r["next_at"] for r in due)

    rid, due = asyncio.run(go())
    assert rid == 1
    assert due == [1000]


def test_siege_groups_are_stored_and_default_to_one(tmp_path):
    async def go():
        db = Database(str(tmp_path / "r.db"))
        await db.connect()
        await db.create_recurrence(**rec(next_at=1000))  # no groups -> defaults to 1
        await db.create_recurrence(**rec(next_at=1000, size=200, groups=8))
        due = await db.recurrences_due(now_ts=1000, lead_s=0)
        listed = {r["id"]: r["groups"] for r in await db.list_recurrences(1)}
        await db.close()
        return sorted(r["groups"] for r in due), listed

    from_due, from_list = asyncio.run(go())
    assert from_due == [1, 8]
    assert from_list == {1: 1, 2: 8}


def test_advance_recurrence_claims_once(tmp_path):
    async def go():
        db = Database(str(tmp_path / "r.db"))
        await db.connect()
        rid = await db.create_recurrence(**rec(next_at=1000))
        first = await db.advance_recurrence(rid, 1000, 2000)
        second = await db.advance_recurrence(rid, 1000, 2000)  # already moved
        await db.close()
        return first, second

    assert asyncio.run(go()) == (True, False)


def test_list_and_deactivate(tmp_path):
    async def go():
        db = Database(str(tmp_path / "r.db"))
        await db.connect()
        rid = await db.create_recurrence(**rec())
        before = [r["id"] for r in await db.list_recurrences(1)]
        ok = await db.deactivate_recurrence(rid, 1)
        after = [r["id"] for r in await db.list_recurrences(1)]
        wrong_guild = await db.deactivate_recurrence(rid, 999)
        await db.close()
        return before, ok, after, wrong_guild

    before, ok, after, wrong_guild = asyncio.run(go())
    assert before == [1]
    assert ok is True
    assert after == []
    assert wrong_guild is False
