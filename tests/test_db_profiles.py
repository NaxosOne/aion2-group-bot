"""Tests for the character directory, its migration and member purge.

Run: pytest
"""

import asyncio
import sqlite3

from bot.db import Database


def run(coro_factory):
    return asyncio.run(coro_factory())


async def _fresh(tmp_path, name="p.db") -> Database:
    db = Database(str(tmp_path / name))
    await db.connect()
    return db


def test_first_character_becomes_the_main(tmp_path):
    async def go():
        db = await _fresh(tmp_path)
        await db.add_character(1, 42, "Kratos", "Templar", "tank")
        await db.add_character(1, 42, "Loki", "Assassin", "dps")
        rows = await db.get_profiles(1, 42)
        await db.close()
        return [(r["char_name"], r["is_main"]) for r in rows]

    assert run(go) == [("Kratos", 1), ("Loki", 0)]


def test_a_member_can_register_many_alts(tmp_path):
    async def go():
        db = await _fresh(tmp_path)
        for name in ("Kratos", "Loki", "Zed", "Nami", "Aatrox"):
            await db.add_character(1, 42, name, "Ranger", "dps")
        rows = await db.get_profiles(1, 42)
        await db.close()
        # Main first, then alphabetically.
        return [r["char_name"] for r in rows], sum(r["is_main"] for r in rows)

    names, mains = run(go)
    assert names == ["Kratos", "Aatrox", "Loki", "Nami", "Zed"]
    assert mains == 1


def test_same_name_updates_instead_of_duplicating(tmp_path):
    async def go():
        db = await _fresh(tmp_path)
        await db.add_character(1, 42, "Kratos", "Templar", "tank")
        await db.add_character(1, 42, "kratos", "Gladiator", "dps")  # different case
        rows = await db.get_profiles(1, 42)
        await db.close()
        return [(r["char_name"], r["char_class"], r["role"]) for r in rows]

    assert run(go) == [("kratos", "Gladiator", "dps")]


def test_promoting_a_main_demotes_the_previous_one(tmp_path):
    async def go():
        db = await _fresh(tmp_path)
        await db.add_character(1, 42, "Kratos", "Templar", "tank")
        loki = await db.add_character(1, 42, "Loki", "Assassin", "dps")
        promoted = await db.set_main_character(1, 42, loki)
        rows = await db.get_profiles(1, 42)
        classes = await db.get_main_classes(1, [42])
        await db.close()
        return promoted, [(r["char_name"], r["is_main"]) for r in rows], classes

    promoted, rows, classes = run(go)
    assert promoted is True
    assert rows == [("Loki", 1), ("Kratos", 0)]
    assert classes == {42: "Assassin"}


def test_characters_cannot_be_promoted_across_members(tmp_path):
    async def go():
        db = await _fresh(tmp_path)
        mine = await db.add_character(1, 42, "Kratos", "Templar", "tank")
        await db.add_character(1, 99, "Solo", "Ranger", "dps")
        stolen = await db.set_main_character(1, 99, mine)
        await db.close()
        return stolen

    assert run(go) is False


def test_deleting_the_main_promotes_another_character(tmp_path):
    async def go():
        db = await _fresh(tmp_path)
        kratos = await db.add_character(1, 42, "Kratos", "Templar", "tank")
        await db.add_character(1, 42, "Loki", "Assassin", "dps")
        removed = await db.delete_profile(1, 42, kratos)
        rows = await db.get_profiles(1, 42)
        await db.close()
        return removed, [(r["char_name"], r["is_main"]) for r in rows]

    assert run(go) == (1, [("Loki", 1)])


def test_delete_without_a_character_removes_them_all(tmp_path):
    async def go():
        db = await _fresh(tmp_path)
        for name in ("Kratos", "Loki", "Zed"):
            await db.add_character(1, 42, name, "Ranger", "dps")
        await db.add_character(2, 42, "Elsewhere", "Cleric", "heal")  # other guild
        await db.add_character(1, 99, "Someone", "Cleric", "heal")    # other member
        removed = await db.delete_profile(1, 42)
        counts = (
            len(await db.get_profiles(1, 42)),
            len(await db.get_profiles(2, 42)),
            len(await db.get_profiles(1, 99)),
        )
        await db.close()
        return removed, counts

    assert run(go) == (3, (0, 1, 1))


def test_signups_carry_the_character_brought_along(tmp_path):
    async def go():
        db = await _fresh(tmp_path)
        loki = await db.add_character(1, 42, "Loki", "Assassin", "dps")
        await db.create_event(
            message_id=555, channel_id=7, guild_id=1, creator_id=42,
            creator_name="Kratos", title="Run", activity="Dungeon",
            compo="standard", size=5,
        )
        await db.upsert_signup(555, 42, "Kratos", "dps", 1.0, loki)
        joined = (await db.get_signups(555))[0]

        # Swapping character keeps the queue position...
        kratos = await db.add_character(1, 42, "Kratos", "Templar", "tank")
        await db.set_signup_character(555, 42, kratos)
        swapped = (await db.get_signups(555))[0]

        # ...and a deleted character leaves the sign-up standing.
        await db.delete_profile(1, 42, kratos)
        orphan = (await db.get_signups(555))[0]
        await db.close()
        return (
            (joined["char_name"], joined["char_class"]),
            (swapped["char_name"], swapped["joined_at"]),
            (orphan["char_name"], orphan["role"]),
        )

    joined, swapped, orphan = run(go)
    assert joined == ("Loki", "Assassin")
    assert swapped == ("Kratos", 1.0)
    assert orphan == (None, "dps")


def test_signup_without_a_profile_still_works(tmp_path):
    async def go():
        db = await _fresh(tmp_path)
        await db.create_event(
            message_id=555, channel_id=7, guild_id=1, creator_id=42,
            creator_name="Nobody", title="Run", activity="Dungeon",
            compo="standard", size=5,
        )
        await db.upsert_signup(555, 42, "Nobody", "tank", 1.0)
        row = (await db.get_signups(555))[0]
        await db.close()
        return row["role"], row["char_name"], row["character_id"]

    assert run(go) == ("tank", None, None)


def test_purge_member_removes_profile_absence_and_signup(tmp_path):
    async def go():
        db = await _fresh(tmp_path)
        await db.add_character(1, 42, "Kratos", "Templar", "tank")
        await db.add_character(1, 42, "Loki", "Assassin", "dps")
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

    assert run(go) == (0, 0, 0)


# ----- Migration from the old main/alt table -----


def _legacy_database(path) -> None:
    """A database as written by the versions capped at one main + one alt."""
    old = sqlite3.connect(path)
    old.executescript(
        """
        CREATE TABLE profiles (
            guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, slot TEXT NOT NULL,
            char_name TEXT NOT NULL, char_class TEXT NOT NULL, role TEXT NOT NULL,
            PRIMARY KEY (guild_id, user_id, slot));
        INSERT INTO profiles VALUES (1, 42, 'main', 'Kratos', 'Templar',  'tank');
        INSERT INTO profiles VALUES (1, 42, 'alt',  'Loki',   'Assassin', 'dps');
        INSERT INTO profiles VALUES (1, 99, 'alt',  'Solo',   'Ranger',   'dps');
        """
    )
    old.commit()
    old.close()


def test_migration_keeps_characters_and_seats_the_main(tmp_path):
    async def go():
        path = str(tmp_path / "legacy.db")
        _legacy_database(path)
        db = Database(path)
        await db.connect()
        kept = [(r["char_name"], r["is_main"]) for r in await db.get_profiles(1, 42)]
        # A member who only ever set an alt still ends up with a main.
        alt_only = [(r["char_name"], r["is_main"]) for r in await db.get_profiles(1, 99)]
        onboarded = await db.has_main_profile(1, 99)
        leftover = await db.conn.execute_fetchall(
            "SELECT name FROM sqlite_master WHERE name = 'profiles_slots'"
        )
        await db.close()
        return kept, alt_only, onboarded, leftover

    kept, alt_only, onboarded, leftover = run(go)
    assert kept == [("Kratos", 1), ("Loki", 0)]
    assert alt_only == [("Solo", 1)]
    assert onboarded is True
    assert leftover == []


def test_migration_runs_once_and_alts_can_be_added_after(tmp_path):
    async def go():
        path = str(tmp_path / "legacy.db")
        _legacy_database(path)
        db = Database(path)
        await db.connect()
        await db.close()

        db = Database(path)          # restart: the migration must be a no-op
        await db.connect()
        await db.add_character(1, 42, "Zed", "Assassin", "dps")
        rows = await db.get_profiles(1, 42)
        await db.close()
        return [(r["char_name"], r["is_main"]) for r in rows]

    assert run(go) == [("Kratos", 1), ("Loki", 0), ("Zed", 0)]
