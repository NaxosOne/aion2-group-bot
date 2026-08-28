"""How the party list names each member's character. Run: pytest"""

from bot.embeds import build_event_embed
from bot.logic import COMPO_OPEN, COMPO_STANDARD

EVENT = {
    "message_id": 1, "channel_id": 2, "guild_id": 3, "creator_id": 4,
    "creator_name": "Naxos", "title": "Fire Temple", "activity": "Dungeon",
    "description": None, "compo": COMPO_STANDARD, "size": 5,
    "starts_at": None, "status": "open",
}


def signup(user_id, role, char_name=None, char_class=None):
    return {
        "user_id": user_id, "role": role, "display_name": f"m{user_id}",
        "joined_at": float(user_id), "char_name": char_name,
        "char_class": char_class,
    }


def party_text(embed) -> str:
    return "\n".join(field.value for field in embed.fields)


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
