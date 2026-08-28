"""The daily sweep that forgets members who left unseen. Run: pytest

This code deletes data, so the cases that must NOT delete are covered as
carefully as the one that must.
"""

import asyncio

import discord

from bot.cogs.profiles import PRUNE_BATCH, Profile


class Response:
    def __init__(self, status, reason):
        self.status, self.reason = status, reason


def not_found():
    return discord.NotFound(Response(404, "Not Found"), "Unknown Member")


def server_error():
    return discord.HTTPException(Response(500, "Server Error"), "boom")


class FakeGuild:
    """cached: ids in the member cache. present: ids the API still knows."""

    def __init__(self, guild_id, cached=(), present=(), error=None):
        self.id, self.name = guild_id, f"guild-{guild_id}"
        self.cached, self.present, self.error = set(cached), set(present), error
        self.fetched = []

    def get_member(self, user_id):
        return object() if user_id in self.cached else None

    async def fetch_member(self, user_id):
        self.fetched.append(user_id)
        if self.error is not None:
            raise self.error
        if user_id in self.present:
            return object()
        raise not_found()


class FakeDB:
    def __init__(self, profiles):
        self.profiles = {gid: list(ids) for gid, ids in profiles.items()}
        self.purged = []

    async def profile_user_ids(self, guild_id):
        return list(self.profiles.get(guild_id, []))

    async def purge_member(self, guild_id, user_id):
        self.purged.append((guild_id, user_id))
        self.profiles[guild_id].remove(user_id)


class FakeBot:
    def __init__(self, guilds, db):
        self.guilds, self.db = guilds, db


def sweep(guilds, profiles):
    db = FakeDB(profiles)
    cog = Profile.__new__(Profile)          # no cog machinery needed here
    cog.bot = FakeBot(guilds, db)
    asyncio.run(Profile.prune_departed.coro(cog))
    return db


def test_a_member_still_in_the_cache_is_left_alone():
    guild = FakeGuild(1, cached=[42])
    db = sweep([guild], {1: [42]})
    assert db.purged == []
    assert guild.fetched == []              # no API call for a cache hit


def test_a_member_the_api_no_longer_knows_is_purged():
    guild = FakeGuild(1, cached=[], present=[])
    db = sweep([guild], {1: [42]})
    assert db.purged == [(1, 42)]
    assert guild.fetched == [42]


def test_a_cold_cache_does_not_wipe_the_roster():
    # Nobody is cached, but the API still knows all of them: a cache that
    # never filled must cost API calls, never profiles.
    guild = FakeGuild(1, cached=[], present=[1, 2, 3])
    db = sweep([guild], {1: [1, 2, 3]})
    assert db.purged == []
    assert sorted(guild.fetched) == [1, 2, 3]


def test_a_transient_api_error_keeps_the_profile():
    # A 500 or a rate limit is not proof of departure: try again tomorrow.
    guild = FakeGuild(1, cached=[], error=server_error())
    db = sweep([guild], {1: [42]})
    assert db.purged == []


def test_each_pass_confirms_at_most_one_batch():
    absent = list(range(100))
    guild = FakeGuild(1, cached=[], present=absent)
    db = sweep([guild], {1: absent})
    assert len(guild.fetched) == PRUNE_BATCH
    assert db.purged == []


def test_successive_passes_get_through_a_long_backlog():
    departed = list(range(PRUNE_BATCH * 2))
    guild = FakeGuild(1, cached=[], present=[])
    db = FakeDB({1: departed})
    cog = Profile.__new__(Profile)
    cog.bot = FakeBot([guild], db)
    for _ in range(3):
        asyncio.run(Profile.prune_departed.coro(cog))
    assert db.profiles[1] == []


def test_guilds_are_swept_independently():
    here = FakeGuild(1, cached=[], present=[])       # 42 left this server
    elsewhere = FakeGuild(2, cached=[42])            # but is still on that one
    db = sweep([here, elsewhere], {1: [42], 2: [42]})
    assert db.purged == [(1, 42)]
    assert db.profiles[2] == [42]


def test_the_sweep_survives_a_guild_with_no_profiles():
    guild = FakeGuild(1, cached=[])
    db = sweep([guild], {})
    assert db.purged == []
    assert guild.fetched == []
