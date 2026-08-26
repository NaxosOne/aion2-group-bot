"""Building the embed (the rich message) that displays an event."""

import discord

from .logic import COMPO_STANDARD, ROLES, assign, standard_slots

ACTIVITY_EMOJI = {
    "Dungeon": "🏰",
    "Raid": "🐉",
    "Battleground": "🚩",
    "PvP": "⚔️",
    "Rift": "🌀",
    "Abyss": "🌌",
    "Other": "🎲",
    # Legacy French labels, kept so events created by earlier versions
    # still show their emoji.
    "Donjon": "🏰",
    "Abysses": "🌌",
    "Autre": "🎲",
}
ROLE_EMOJI = {"tank": "🛡️", "heal": "💚", "dps": "🗡️"}
ROLE_LABEL = {"tank": "Tank", "heal": "Heal", "dps": "DPS"}

COLOUR_OPEN = discord.Colour.blurple()
COLOUR_FULL = discord.Colour.green()
COLOUR_CANCELLED = discord.Colour.red()


def _class_suffix(classes: dict, user_id: int) -> str:
    """Suffix " — Class" when the member has filled in their /profile."""
    return f" — *{classes[user_id]}*" if user_id in classes else ""


def _names(members: list, classes: dict) -> str:
    if not members:
        return "*—*"
    return "\n".join(
        f"• <@{s['user_id']}>{_class_suffix(classes, s['user_id'])}" for s in members
    )


def standard_setup_text(slots: dict) -> str:
    """E.g. "1 tank / 1 heal / 3 DPS" or "2 tanks / 2 heals / 6 DPS"."""
    t, h, d = slots["tank"], slots["heal"], slots["dps"]
    return (
        f"{t} tank{'s' if t > 1 else ''} / "
        f"{h} heal{'s' if h > 1 else ''} / {d} DPS"
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

    emoji = ACTIVITY_EMOJI.get(event["activity"], "📣")
    title = f"{emoji} {event['title']}"
    if cancelled:
        title = f"❌ [CANCELLED] {event['title']}"
    elif completed:
        title = f"✅ {event['title']}"

    lines = []
    if event["description"]:
        lines.append(event["description"])
    if event["starts_at"]:
        lines.append(f"🕘 <t:{event['starts_at']}:F> (<t:{event['starts_at']}:R>)")
    if event["compo"] == COMPO_STANDARD:
        slots = standard_slots(event["size"])
        lines.append(f"Setup: **standard** ({standard_setup_text(slots)})")
    else:
        lines.append(f"Setup: **open** ({event['size']} slots)")

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
                f"{_class_suffix(classes, s['user_id'])}"
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
    embed.set_footer(
        text=f"{event['activity']} • Created by {event['creator_name']}{suffix}"
    )
    return embed
