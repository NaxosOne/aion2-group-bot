"""Storage for the LFG pool and board. Run: pytest"""

import asyncio

from bot.db import Database


def _db(tmp_path, name="lfg.db"):
    return Database(str(tmp_path / name))


def test_looking_entry_round_trips_and_is_scoped_to_the_guild(tmp_path):
    async def go():
        db = _db(tmp_path)
        await db.connect()
        await db.set_lfg_looking(1, 10, "Dungeon", "tank", "hardmode", expires_at=5000)
        pool = await db.get_lfg_pool(1, now_ts=0)
        other_guild = await db.get_lfg_pool(2, now_ts=0)
        await db.close()
        return pool, other_guild

    pool, other_guild = asyncio.run(go())
    assert len(pool) == 1
    row = pool[0]
    assert (row["user_id"], row["activity"], row["role"], row["note"]) == (
        10,
        "Dungeon",
        "tank",
        "hardmode",
    )
    assert other_guild == []


def test_re_signalling_the_same_activity_refreshes_rather_than_duplicates(tmp_path):
    async def go():
        db = _db(tmp_path)
        await db.connect()
        await db.set_lfg_looking(1, 10, "Dungeon", "tank", None, expires_at=1000)
        await db.set_lfg_looking(1, 10, "Dungeon", "dps", "switched", expires_at=2000)
        pool = await db.get_lfg_pool(1, now_ts=0)
        await db.close()
        return pool

    pool = asyncio.run(go())
    assert len(pool) == 1
    assert pool[0]["role"] == "dps"
    assert pool[0]["note"] == "switched"
    assert pool[0]["expires_at"] == 2000


def test_a_member_can_look_for_several_activities_at_once(tmp_path):
    async def go():
        db = _db(tmp_path)
        await db.connect()
        await db.set_lfg_looking(1, 10, "Dungeon", "tank", None, expires_at=2000)
        await db.set_lfg_looking(1, 10, "Raid", "dps", None, expires_at=2000)
        pool = await db.get_lfg_pool(1, now_ts=0)
        await db.close()
        return {row["activity"] for row in pool}

    assert asyncio.run(go()) == {"Dungeon", "Raid"}


def test_get_pool_hides_expired_and_prune_deletes_them(tmp_path):
    async def go():
        db = _db(tmp_path)
        await db.connect()
        await db.set_lfg_looking(1, 10, "Dungeon", "tank", None, expires_at=500)
        await db.set_lfg_looking(1, 11, "Dungeon", "dps", None, expires_at=5000)
        live = await db.get_lfg_pool(1, now_ts=1000)
        pruned = await db.prune_lfg(now_ts=1000)
        remaining = await db.get_lfg_pool(1, now_ts=0)
        await db.close()
        return live, pruned, remaining

    live, pruned, remaining = asyncio.run(go())
    assert [row["user_id"] for row in live] == [11]
    assert pruned == 1
    assert [row["user_id"] for row in remaining] == [11]


def test_remove_lfg_targets_one_activity_or_all(tmp_path):
    async def go():
        db = _db(tmp_path)
        await db.connect()
        await db.set_lfg_looking(1, 10, "Dungeon", "tank", None, expires_at=2000)
        await db.set_lfg_looking(1, 10, "Raid", "dps", None, expires_at=2000)
        one = await db.remove_lfg(1, 10, "Dungeon")
        after_one = await db.get_lfg_pool(1, now_ts=0)
        rest = await db.remove_lfg(1, 10)
        after_all = await db.get_lfg_pool(1, now_ts=0)
        await db.close()
        return one, [r["activity"] for r in after_one], rest, after_all

    one, after_one, rest, after_all = asyncio.run(go())
    assert one == 1
    assert after_one == ["Raid"]
    assert rest == 1
    assert after_all == []


def test_lfg_board_location_round_trips(tmp_path):
    async def go():
        db = _db(tmp_path)
        await db.connect()
        before = await db.get_lfg_board(1)
        await db.set_lfg_board(1, 111, 222)
        stored = await db.get_lfg_board(1)
        with_board = [row["guild_id"] for row in await db.guilds_with_lfg_board()]
        await db.close()
        return before, stored, with_board

    before, stored, with_board = asyncio.run(go())
    assert before is None
    assert stored == (111, 222)
    assert with_board == [1]
