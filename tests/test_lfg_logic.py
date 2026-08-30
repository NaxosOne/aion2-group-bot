"""Pure LFG-pool logic: expiry, grouping and event matching. Run: pytest"""

from bot.utils.lfg import (
    DEFAULT_DURATION,
    LFG_DURATIONS,
    active_entries,
    group_by_activity,
    matching_pool,
)


def entry(user_id, activity, role, expires_at, note=None):
    return {
        "user_id": user_id,
        "activity": activity,
        "role": role,
        "expires_at": expires_at,
        "note": note,
    }


def test_active_entries_drops_expired_and_the_exact_boundary():
    now = 1000
    pool = [
        entry(1, "Dungeon", "tank", 1500),
        entry(2, "Raid", "dps", 900),
        entry(3, "PvP", "heal", 1000),  # expires exactly now -> gone (strict)
    ]
    assert [e["user_id"] for e in active_entries(pool, now)] == [1]


def test_group_by_activity_keeps_order_and_skips_empty():
    pool = [
        entry(1, "Raid", "dps", 2000),
        entry(2, "Dungeon", "tank", 2000),
        entry(3, "Raid", "heal", 2000),
    ]
    grouped = group_by_activity(pool, ("Dungeon", "Raid", "PvP"))
    assert [activity for activity, _ in grouped] == ["Dungeon", "Raid"]
    assert [m["user_id"] for m in dict(grouped)["Raid"]] == [1, 3]


def test_matching_pool_filters_by_activity_and_roles():
    pool = [
        entry(1, "Dungeon", "tank", 100),
        entry(2, "Dungeon", "dps", 100),
        entry(3, "Raid", "tank", 100),
        entry(4, "Dungeon", "heal", 100),
    ]
    matched = matching_pool(pool, "Dungeon", {"tank", "heal"}, now=0)
    assert sorted(e["user_id"] for e in matched) == [1, 4]


def test_matching_pool_none_roles_matches_any_role():
    pool = [
        entry(1, "Dungeon", "tank", 100),
        entry(2, "Dungeon", "dps", 100),
        entry(3, "Raid", "tank", 100),
    ]
    matched = matching_pool(pool, "Dungeon", None, now=0)
    assert sorted(e["user_id"] for e in matched) == [1, 2]


def test_matching_pool_ignores_expired_entries():
    pool = [
        entry(1, "Dungeon", "tank", 50),  # expired
        entry(2, "Dungeon", "tank", 500),
    ]
    matched = matching_pool(pool, "Dungeon", {"tank"}, now=100)
    assert [e["user_id"] for e in matched] == [2]


def test_default_duration_is_a_known_option():
    assert DEFAULT_DURATION in LFG_DURATIONS
    assert LFG_DURATIONS["3h"] == 10800
