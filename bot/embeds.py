"""Building the embed (the rich message) that displays an event."""

import discord

from . import config
from .logic import COMPO_STANDARD, ROLES, assign, standard_slots

# Event-type emojis come from the config (.env EMOJI_DUNGEON etc.); the
# legacy French labels keep working for events created by earlier versions.
ACTIVITY_EMOJI = {
    **config.EMOJI_ACTIVITY,
    "Donjon": config.EMOJI_ACTIVITY["Dungeon"],
    "Abysses": config.EMOJI_ACTIVITY["Abyss"],
    "Autre": config.EMOJI_ACTIVITY["Other"],
}
# Role emojis are configurable (.env EMOJI_TANK/HEAL/DPS) so servers can use
# their own custom emojis instead of the Unicode defaults.
ROLE_EMOJI = {
    "tank": config.EMOJI_TANK,
    "heal": config.EMOJI_HEAL,
    "dps": config.EMOJI_DPS,
}
ROLE_LABEL = {"tank": "Tank", "heal": "Heal", "dps": "DPS"}

COLOUR_OPEN = discord.Colour.blurple()
COLOUR_FULL = discord.Colour.green()
COLOUR_CANCELLED = discord.Colour.red()


def _row_get(row, key: str):
    """sqlite3.Row has no .get(), and the tests pass plain dicts."""
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


def _class_suffix(signup, classes: dict) -> str:
    """Suffix " — Kratos (Templar)" naming the character brought along.

    Falls back to the member's main class when they signed up without picking
    a character, and to nothing at all when they have no profile.
    """
    name = _row_get(signup, "char_name")
    char_class = _row_get(signup, "char_class") or classes.get(signup["user_id"])
    if name and char_class:
        return f" — *{name} ({char_class})*"
    if name:
        return f" — *{name}*"
    return f" — *{char_class}*" if char_class else ""


def _names(members: list, classes: dict) -> str:
    if not members:
        return "*—*"
    return "\n".join(
        f"• <@{s['user_id']}>{_class_suffix(s, classes)}" for s in members
    )


def build_event_embed(event, signups: list, classes: dict | None = None) -> discord.Embed:
    """Builds an event's embed from its database row.

    `classes`: {user_id: main character's class} to display the class of
    members who filled in their /profile.
    """
    classes = classes or {}
    party, waitlist = assign(event["compo"], event["size"], signups)
    cancelled = event["status"] == "cancelled"
    completed = event["status"] == "done"
    size = event["size"]
    full = len(party) >= size

    # A member can name an "Other" event freely: fall back to its icon.
    emoji = ACTIVITY_EMOJI.get(event["activity"], config.EMOJI_ACTIVITY["Other"])
    title = f"{emoji} {event['title']}"
    if cancelled:
        title = f"❌ [CANCELLED] {event['title']}"
    elif completed:
        title = f"✅ {event['title']}"

    # The role fields below already show the layout, so no "Setup" line —
    # just the event type in clear text, with the schedule when there is one.
    header = f"**{event['activity']}**"
    if event["starts_at"]:
        header += f" • 🕘 <t:{event['starts_at']}:F> (<t:{event['starts_at']}:R>)"
    lines = [header]
    if event["description"]:
        lines.append(event["description"])

    if cancelled:
        colour = COLOUR_CANCELLED
    elif completed:
        colour = discord.Colour.gold()
    elif full:
        colour = COLOUR_FULL
    else:
        colour = COLOUR_OPEN

    embed = discord.Embed(title=title, description="\n".join(lines), colour=colour)

    if event["compo"] == COMPO_STANDARD:
        slots = standard_slots(event["size"])
        by_role = {role: [s for s in party if s["role"] == role] for role in ROLES}
        for role in ROLES:
            embed.add_field(
                name=(
                    f"{ROLE_EMOJI[role]} {ROLE_LABEL[role]} "
                    f"({len(by_role[role])}/{slots[role]})"
                ),
                value=_names(by_role[role], classes),
                inline=True,
            )
    else:
        embed.add_field(
            name=f"👥 Party ({len(party)}/{event['size']})",
            value="\n".join(
                f"• {ROLE_EMOJI[s['role']]} <@{s['user_id']}>"
                f"{_class_suffix(s, classes)}"
                for s in party
            )
            or "*—*",
            inline=False,
        )

    if waitlist:
        embed.add_field(
            name=f"⏳ Waitlist ({len(waitlist)})",
            value="\n".join(
                f"{i}. {ROLE_EMOJI[s['role']]} <@{s['user_id']}>"
                f"{_class_suffix(s, classes)}"
                for i, s in enumerate(waitlist, start=1)
            ),
            inline=False,
        )

    if completed:
        suffix = " • Completed 🎉"
    elif full and not cancelled:
        suffix = " • FULL"
    else:
        suffix = ""
    embed.set_footer(text=f"Created by {event['creator_name']}{suffix}")
    return embed
