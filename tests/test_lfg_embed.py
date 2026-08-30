"""The LFG board embed groups the live pool by activity. Run: pytest"""

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


def board_text(embed) -> str:
    return "\n".join(field.value for field in embed.fields)


def test_empty_pool_shows_the_empty_hint():
    embed = build_lfg_embed([], "en", now=0)
    assert i18n.t("lfg.empty", "en") in (embed.description or "")
    assert not embed.fields


def test_groups_by_activity_with_counts():
    pool = [
        entry(1, "Dungeon", "tank", 1000),
        entry(2, "Dungeon", "dps", 1000),
        entry(3, "Raid", "heal", 1000),
    ]
    embed = build_lfg_embed(pool, "en", now=0)
    names = [f.name for f in embed.fields]
    assert any("Dungeon (2)" in n for n in names)
    assert any("Raid (1)" in n for n in names)


def test_expired_entries_are_not_shown():
    pool = [
        entry(1, "Dungeon", "tank", 500),  # expired at now=1000
        entry(2, "Dungeon", "dps", 5000),
    ]
    embed = build_lfg_embed(pool, "en", now=1000)
    text = board_text(embed)
    assert "<@2>" in text
    assert "<@1>" not in text


def test_note_is_shown_when_present():
    embed = build_lfg_embed([entry(1, "Raid", "dps", 1000, "hardmode")], "en", now=0)
    assert "hardmode" in board_text(embed)


def test_maxed_out_pool_stays_within_the_total_limit():
    activities = config.ACTIVITIES
    pool = [
        entry(i, activities[i % len(activities)], "dps", 100000, "Averylongnote" * 4)
        for i in range(1, 400)
    ]
    embed = build_lfg_embed(pool, "en", now=0)
    total = len(embed.title or "") + len(embed.description or "")
    total += sum(len(f.name) + len(f.value) for f in embed.fields)
    assert total <= 6000
