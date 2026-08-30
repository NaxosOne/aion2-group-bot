"""The legion dashboard embed aggregates the guild's live state. Run: pytest"""

from bot import i18n
from bot.cogs.dashboard import build_dashboard_embed
from bot.logic import COMPO_OPEN, COMPO_STANDARD


def event(
    message_id,
    title,
    activity="Dungeon",
    compo=COMPO_STANDARD,
    size=5,
    starts_at=None,
    status="open",
):
    return {
        "message_id": message_id,
        "title": title,
        "activity": activity,
        "compo": compo,
        "size": size,
        "starts_at": starts_at,
        "status": status,
    }


def signup(user_id, role):
    return {"user_id": user_id, "role": role, "joined_at": float(user_id)}


def profile(user_id, role, is_main=1):
    return {"user_id": user_id, "role": role, "is_main": is_main}


def field(embed, needle):
    return next(f for f in embed.fields if needle in f.name)


def build(**kwargs):
    base = dict(
        events=[],
        total_events=0,
        lfg_count=0,
        available_count=0,
        absences=[],
        recurring_count=0,
        profiles=[],
        lang="en",
        now=1000,
    )
    base.update(kwargs)
    return build_dashboard_embed(**base)


def test_events_field_shows_fill_and_missing_roles():
    ev = event(1, "Fire Temple", size=5)
    signups = [signup(1, "tank"), signup(2, "dps")]  # 2/5, needs heal + 2 dps
    embed = build(events=[(ev, signups)], total_events=1)
    events_field = field(embed, i18n.t("dashboard.events", "en"))
    assert "(1)" in events_field.name
    assert "Fire Temple" in events_field.value
    assert "2/5" in events_field.value
    assert "⚠️" in events_field.value  # roles still short


def test_full_event_has_no_warning():
    ev = event(1, "Full Run", compo=COMPO_OPEN, size=2)
    signups = [signup(1, "dps"), signup(2, "dps")]
    embed = build(events=[(ev, signups)], total_events=1)
    assert "⚠️" not in field(embed, i18n.t("dashboard.events", "en")).value


def test_no_events_shows_the_empty_line():
    embed = build(events=[], total_events=0)
    events_field = field(embed, i18n.t("dashboard.events", "en"))
    assert i18n.t("dashboard.no_events", "en") in events_field.value


def test_lfg_and_available_counts_are_shown():
    embed = build(lfg_count=3, available_count=2)
    lfg_field = field(embed, i18n.t("dashboard.lfg", "en"))
    assert "3" in lfg_field.value and "2" in lfg_field.value


def test_roster_counts_members_and_role_split():
    profiles = [profile(1, "tank"), profile(2, "dps"), profile(2, "heal", is_main=0)]
    embed = build(profiles=profiles)
    roster_field = field(embed, i18n.t("dashboard.roster", "en"))
    assert "2" in roster_field.value  # two distinct members


def test_absences_are_listed_with_a_count():
    absences = [{"user_id": 7}, {"user_id": 8}]
    embed = build(absences=absences)
    absences_field = field(embed, i18n.t("dashboard.absences", "en"))
    assert "(2)" in absences_field.name
    assert "<@7>" in absences_field.value and "<@8>" in absences_field.value


def test_total_count_reflects_all_events_not_just_shown():
    ev = event(1, "Shown", size=5)
    embed = build(events=[(ev, [])], total_events=12)
    assert "(12)" in field(embed, i18n.t("dashboard.events", "en")).name
