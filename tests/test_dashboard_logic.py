"""Pure dashboard aggregation: roster size and role split. Run: pytest"""

from bot.utils.dashboard import roster_stats


def profile(user_id, role, is_main=1):
    return {"user_id": user_id, "role": role, "is_main": is_main}


def test_roster_counts_distinct_members():
    profiles = [
        profile(1, "tank"),
        profile(1, "dps", is_main=0),  # an alt of member 1
        profile(2, "heal"),
    ]
    members, _ = roster_stats(profiles)
    assert members == 2


def test_role_distribution_counts_mains_only():
    profiles = [
        profile(1, "tank"),
        profile(1, "dps", is_main=0),
        profile(2, "dps"),
        profile(3, "dps"),
        profile(4, "heal"),
    ]
    _, distribution = roster_stats(profiles)
    assert distribution == {"tank": 1, "heal": 1, "dps": 2}


def test_empty_roster_is_all_zero():
    members, distribution = roster_stats([])
    assert members == 0
    assert distribution == {"tank": 0, "heal": 0, "dps": 0}


def test_member_without_a_flagged_main_still_counts():
    members, distribution = roster_stats([profile(5, "dps", is_main=0)])
    assert members == 1
    assert distribution == {"tank": 0, "heal": 0, "dps": 0}
