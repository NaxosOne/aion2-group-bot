"""How the party list names each member's character. Run: pytest"""

from bot import config
from bot.embeds import ROLE_EMOJI, build_event_embed, build_rsvp_embed
from bot.logic import COMPO_OPEN, COMPO_STANDARD

EVENT = {
    "message_id": 1,
    "channel_id": 2,
    "guild_id": 3,
    "creator_id": 4,
    "creator_name": "Naxos",
    "title": "Fire Temple",
    "activity": "Dungeon",
    "description": None,
    "compo": COMPO_STANDARD,
    "size": 5,
    "starts_at": None,
    "status": "open",
}


def signup(user_id, role, char_name=None, char_class=None):
    return {
        "user_id": user_id,
        "role": role,
        "display_name": f"m{user_id}",
        "joined_at": float(user_id),
        "char_name": char_name,
        "char_class": char_class,
    }


def party_text(embed) -> str:
    return "\n".join(field.value for field in embed.fields)


def test_needs_summary_lists_the_open_roles():
    embed = build_event_embed(EVENT, [signup(10, "tank")])
    assert "Needs:" in (embed.description or "")


def test_open_seats_are_shown_in_role_fields():
    embed = build_event_embed(EVENT, [signup(10, "tank")])
    assert "◦ *open*" in party_text(embed)


def test_full_standard_party_has_no_needs_summary():
    full = [
        signup(1, "tank"),
        signup(2, "heal"),
        signup(3, "dps"),
        signup(4, "dps"),
        signup(5, "dps"),
    ]
    embed = build_event_embed(EVENT, full)
    assert "Needs" not in (embed.description or "")
    assert "open" not in party_text(embed)


def test_cancelled_event_has_no_needs_summary():
    embed = build_event_embed({**EVENT, "status": "cancelled"}, [signup(10, "tank")])
    assert "Needs" not in (embed.description or "")


def test_a_big_waitlist_stays_within_the_discord_field_limit():
    event = {**EVENT, "compo": COMPO_OPEN, "size": 1}
    signups = [signup(i, "dps") for i in range(1, 200)]  # 1 in party, rest waiting
    embed = build_event_embed(event, signups)
    for field in embed.fields:
        assert len(field.value) <= 1024


def test_multi_group_event_renders_one_field_per_group():
    event = {**EVENT, "compo": COMPO_OPEN, "size": 6, "groups": 3}
    signups = [signup(i, "dps") for i in range(1, 6)]  # 5 of 6 seats
    embed = build_event_embed(event, signups)
    names = [f.name for f in embed.fields]
    assert sum("Group" in n for n in names) == 3
    # 2 per group: group 1 = m1,m2 ; group 3 empty.
    assert "(2/2)" in names[0]
    text = party_text(embed)
    assert "<@1>" in text and "<@5>" in text


def test_the_chosen_character_is_named():
    embed = build_event_embed(EVENT, [signup(10, "tank", "Kratos", "Templar")])
    assert "*Kratos (Templar)*" in party_text(embed)


def test_falls_back_to_the_main_class_when_no_character_was_picked():
    # Signed up before the character menus existed, or straight from a profile
    # with a single character: the main's class still shows.
    embed = build_event_embed(EVENT, [signup(10, "tank")], {10: "Templar"})
    text = party_text(embed)
    assert "*Templar*" in text and "(" not in text.split("*Templar*")[0][-3:]


def test_a_member_without_a_profile_is_listed_plainly():
    embed = build_event_embed(EVENT, [signup(10, "tank")])
    line = next(x for x in party_text(embed).split("\n") if "<@10>" in x)
    assert line == "• <@10>"


def test_open_parties_name_characters_too():
    event = {**EVENT, "compo": COMPO_OPEN}
    embed = build_event_embed(event, [signup(10, "dps", "Loki", "Assassin")])
    assert "*Loki (Assassin)*" in party_text(embed)


def test_rows_missing_the_column_do_not_break_the_embed():
    # sqlite3.Row raises IndexError rather than KeyError on an unknown column.
    legacy = {"user_id": 10, "role": "tank", "joined_at": 1.0}
    embed = build_event_embed(EVENT, [legacy], {10: "Cleric"})
    assert "*Cleric*" in party_text(embed)


def test_the_class_icon_leads_the_party_line():
    embed = build_event_embed(EVENT, [signup(10, "tank", "Kratos", "Templar")])
    icon = config.CLASS_EMOJI["Templar"]
    assert f"{icon} *Kratos (Templar)*" in party_text(embed)


def test_the_icon_shows_on_the_main_class_fallback_too():
    embed = build_event_embed(EVENT, [signup(10, "tank")], {10: "Cleric"})
    assert f"{config.CLASS_EMOJI['Cleric']} *Cleric*" in party_text(embed)


def test_a_class_with_no_icon_renders_without_one():
    # /profile set accepts free text, so a class may have no configured icon.
    embed = build_event_embed(EVENT, [signup(10, "tank", "Kratos", "Homebrew")])
    line = next(x for x in party_text(embed).split("\n") if "<@10>" in x)
    assert line == "• <@10> — *Kratos (Homebrew)*"


def test_the_waitlist_shows_icons_as_well():
    full = [signup(i, "tank", f"C{i}", "Templar") for i in range(1, 4)]
    embed = build_event_embed(EVENT, full)
    waitlisted = [f for f in embed.fields if "Waitlist" in f.name]
    assert waitlisted and config.CLASS_EMOJI["Templar"] in waitlisted[0].value


def test_a_class_icon_is_not_repeated_next_to_the_same_role_icon():
    # Unicode defaults: Templar and Tank are both 🛡️. On an open-party line,
    # which already starts with the role icon, the class icon is dropped.
    event = {**EVENT, "compo": COMPO_OPEN}
    embed = build_event_embed(event, [signup(10, "tank", "Kratos", "Templar")])
    line = next(x for x in party_text(embed).split("\n") if "<@10>" in x)
    assert line == f"• {config.CLASS_EMOJI['Templar']} <@10> — *Kratos (Templar)*"


def test_a_different_class_icon_is_kept_next_to_the_role_icon():
    event = {**EVENT, "compo": COMPO_OPEN}
    embed = build_event_embed(event, [signup(10, "dps", "Zed", "Ranger")])
    line = next(x for x in party_text(embed).split("\n") if "<@10>" in x)
    assert line == (
        f"• {ROLE_EMOJI['dps']} <@10> — {config.CLASS_EMOJI['Ranger']} *Zed (Ranger)*"
    )


def test_field_names_follow_the_language():
    full = [signup(i, "tank", f"C{i}", "Templar") for i in range(1, 4)]
    embed = build_event_embed(EVENT, full, lang="fr")
    names = [f.name for f in embed.fields]
    assert any("Liste d'attente" in n for n in names)


def test_cancelled_prefix_is_translated():
    cancelled = {**EVENT, "status": "cancelled"}
    embed = build_event_embed(cancelled, [], lang="fr")
    assert "[ANNULÉ]" in embed.title


def test_rsvp_embed_defaults_to_english():
    event = {"activity": "Dungeon", "title": "Fire Temple", "starts_at": None}
    embed = build_rsvp_embed(event, [], [])
    assert "Are you coming?" in embed.title
    assert any("Coming (0)" in f.name for f in embed.fields)


def test_rsvp_embed_follows_language():
    event = {"activity": "Dungeon", "title": "Fire Temple", "starts_at": None}
    embed = build_rsvp_embed(event, [], [], lang="fr")
    assert "Tu viens ?" in embed.title
    assert any("Présents (0)" in f.name for f in embed.fields)
    assert any("Sans réponse (0)" in f.name for f in embed.fields)
