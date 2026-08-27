"""Tests for profile deletion and member purge. Run: pytest"""

import asyncio

from bot.db import Database


def test_delete_profile_by_slot_then_all(tmp_path):
    async def go():
        db = Database(str(tmp_path / "p.db"))
        await db.connect()
        await db.set_profile(1, 42, "main", "Kratos", "Templar", "tank")
        await db.set_profile(1, 42, "alt", "Loki", "Assassin", "dps")

        removed_alt = await db.delete_profile(1, 42, slot="alt")
        remaining = await db.get_profiles(1, 42)
        removed_rest = await db.delete_profile(1, 42)
        empty = await db.get_profiles(1, 42)
        await db.close()
        return removed_alt, [r["slot"] for r in remaining], removed_rest, list(empty)

    removed_alt, remaining_slots, removed_rest, empty = asyncio.run(go())
    assert removed_alt == 1
    assert remaining_slots == ["main"]
    assert removed_rest == 1
    assert empty == []


def test_delete_profile_is_scoped_to_guild_and_user(tmp_path):
    async def go():
        db = Database(str(tmp_path / "p.db"))
        await db.connect()
        await db.set_profile(1, 42, "main", "A", "Templar", "tank")
        await db.set_profile(2, 42, "main", "B", "Templar", "tank")  # other guild
        await db.set_profile(1, 99, "main", "C", "Templar", "tank")  # other member
        await db.delete_profile(1, 42)
        counts = (
            len(await db.get_profiles(1, 42)),
            len(await db.get_profiles(2, 42)),
            len(await db.get_profiles(1, 99)),
        )
        await db.close()
        return counts

    assert asyncio.run(go()) == (0, 1, 1)


def test_purge_member_removes_profile_absence_and_signup(tmp_path):
    async def go():
        db = Database(str(tmp_path / "p.db"))
        await db.connect()
        await db.set_profile(1, 42, "main", "Kratos", "Templar", "tank")
        await db.add_absence(1, 42, 1000, 10_000_000_000, "holiday")
        await db.create_event(
            message_id=555, channel_id=7, guild_id=1, creator_id=42,
            creator_name="Kratos", title="Run", activity="Dungeon",
            compo="standard", size=5,
        )
        await db.upsert_signup(555, 42, "Kratos", "tank", 1.0)

        await db.purge_member(1, 42)

        counts = (
            len(await db.get_profiles(1, 42)),
            len(await db.list_absences(1, 0)),
            len(await db.get_signups(555)),
        )
        await db.close()
        return counts

    assert asyncio.run(go()) == (0, 0, 0)
