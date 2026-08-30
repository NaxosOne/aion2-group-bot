"""The LFG board embed: who's available now, then the pool by activity.

Run: pytest
"""

from bot import config, i18n
from bot.cogs.lfg import build_lfg_embed


def entry(user_id, activity, role, expires_at, note=None):
    return {
        "user_id": user_id,
        "activity": activity,
        "role": role,
        "expires_at": expires_at,
        "note": note,
    }


def available(user_id, expires_at):
    return {"user_id": user_id, "expires_at": expires_at}


def board_text(embed) -> str:
    return "\n".join(field.value for field in embed.fields)


def test_empty_board_shows_the_empty_hint():
    embed = build_lfg_embed([], [], "en", now=0)
    assert i18n.t("lfg.empty", "en") in (embed.description or "")
    assert not embed.fields


def test_groups_by_activity_with_counts():
    pool = [
        entry(1, "Dungeon", "tank", 1000),
        entry(2, "Dungeon", "dps", 1000),
        entry(3, "Raid", "heal", 1000),
    ]
    embed = build_lfg_embed(pool, [], "en", now=0)
    names = [f.name for f in embed.fields]
    assert any("Dungeon (2)" in n for n in names)
    assert any("Raid (1)" in n for n in names)


def test_expired_entries_are_not_shown():
    pool = [
        entry(1, "Dungeon", "tank", 500),  # expired at now=1000
        entry(2, "Dungeon", "dps", 5000),
    ]
    embed = build_lfg_embed(pool, [], "en", now=1000)
    text = board_text(embed)
    assert "<@2>" in text
    assert "<@1>" not in text


def test_note_is_shown_when_present():
    pool = [entry(1, "Raid", "dps", 1000, "hardmode")]
    embed = build_lfg_embed(pool, [], "en", now=0)
    assert "hardmode" in board_text(embed)


def test_available_now_leads_the_board():
    pool = [entry(1, "Dungeon", "tank", 1000)]
    avail = [available(7, 1000), available(8, 1000)]
    embed = build_lfg_embed(pool, avail, "en", now=0)
    first = embed.fields[0]
    assert i18n.t("lfg.available_title", "en") in first.name
    assert "(2)" in first.name
    assert "<@7>" in first.value and "<@8>" in first.value


def test_available_only_still_renders_without_a_pool():
    embed = build_lfg_embed([], [available(7, 1000)], "en", now=0)
    assert embed.fields
    assert "<@7>" in board_text(embed)


def test_expired_available_is_dropped():
    avail = [available(7, 500), available(8, 5000)]
    embed = build_lfg_embed([], avail, "en", now=1000)
    text = board_text(embed)
    assert "<@8>" in text
    assert "<@7>" not in text


def test_maxed_out_board_stays_within_the_total_limit():
    activities = config.ACTIVITIES
    pool = [
        entry(i, activities[i % len(activities)], "dps", 100000, "Averylongnote" * 4)
        for i in range(1, 400)
    ]
    avail = [available(1000 + i, 100000) for i in range(200)]
    embed = build_lfg_embed(pool, avail, "en", now=0)
    total = len(embed.title or "") + len(embed.description or "")
    total += sum(len(f.name) + len(f.value) for f in embed.fields)
    assert total <= 6000
