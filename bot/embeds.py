"""Building the embed (the rich message) that displays an event."""

import discord

from . import config, i18n
from .logic import COMPO_STANDARD, ROLES, assign, standard_slots
from .utils.rsvp import rsvp_summary

def _with_legacy_labels(mapping: dict) -> dict:
    """Events created by earlier versions carry French activity labels."""
    return {
        **mapping,
        "Donjon": mapping["Dungeon"],
        "Abysses": mapping["Abyss"],
        "Autre": mapping["Other"],
    }


# Event-type emojis come from the config (.env EMOJI_DUNGEON etc.).
ACTIVITY_EMOJI = _with_legacy_labels(config.EMOJI_ACTIVITY)

# Same, forced to Unicode: Discord prints a bot's presence literally, so a
# custom emoji would show there as its raw <:name:id> code.
PRESENCE_ACTIVITY_EMOJI = _with_legacy_labels(config.DEFAULT_EMOJI_ACTIVITY)
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


def _class_suffix(signup, classes: dict, *, role_shown: bool = False) -> str:
    """Suffix " — 🛡️ Kratos (Templar)" naming the character brought along.

    The class icon leads so the party reads as a column of classes at a
    glance. Falls back to the member's main class when they signed up without
    picking a character, and to nothing at all when they have no profile.
    A class with no configured icon (free text) simply has none.

    `role_shown` says the line already starts with the role icon: with the
    Unicode defaults a class shares its glyph with a role (Templar and Tank
    are both 🛡️), and the same icon twice on one line reads as a mistake.
    Servers that installed the class icons never hit this.
    """
    name = _row_get(signup, "char_name")
    char_class = _row_get(signup, "char_class") or classes.get(signup["user_id"])
    icon = config.CLASS_EMOJI.get(char_class, "") if char_class else ""
    if icon and role_shown and icon == ROLE_EMOJI.get(signup["role"]):
        icon = ""
    if icon:
        icon += " "
    if name and char_class:
        return f" — {icon}*{name} ({char_class})*"
    if name:
        return f" — *{name}*"
    return f" — {icon}*{char_class}*" if char_class else ""


def _names(members: list, classes: dict) -> str:
    if not members:
        return "*—*"
    return "\n".join(
        f"• <@{s['user_id']}>{_class_suffix(s, classes)}" for s in members
    )


def build_event_embed(
    event, signups: list, classes: dict | None = None, lang: str = "en"
) -> discord.Embed:
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
        title = f"❌ {i18n.t('event.cancelled_prefix', lang)} {event['title']}"
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
            name=f"👥 {i18n.t('event.party', lang)} ({len(party)}/{event['size']})",
            value="\n".join(
                f"• {ROLE_EMOJI[s['role']]} <@{s['user_id']}>"
                f"{_class_suffix(s, classes, role_shown=True)}"
                for s in party
            )
            or "*—*",
            inline=False,
        )

    if waitlist:
        embed.add_field(
            name=f"⏳ {i18n.t('event.waitlist', lang)} ({len(waitlist)})",
            value="\n".join(
                f"{i}. {ROLE_EMOJI[s['role']]} <@{s['user_id']}>"
                f"{_class_suffix(s, classes, role_shown=True)}"
                for i, s in enumerate(waitlist, start=1)
            ),
            inline=False,
        )

    if completed:
        suffix = " • " + i18n.t("event.completed_suffix", lang)
    elif full and not cancelled:
        suffix = " • " + i18n.t("event.full", lang)
    else:
        suffix = ""
    embed.set_footer(
        text=i18n.t("event.footer_created_by", lang, name=event["creator_name"], suffix=suffix)
    )
    return embed


def build_rsvp_embed(event, party: list, rsvps: list) -> discord.Embed:
    """The 'are you coming?' prompt, with live confirmed/declined/awaiting."""
    responses = {r["user_id"]: r["status"] for r in rsvps}
    party_ids = [s["user_id"] for s in party]
    confirmed, declined, awaiting = rsvp_summary(party_ids, responses)

    emoji = ACTIVITY_EMOJI.get(event["activity"], config.EMOJI_ACTIVITY["Other"])
    when = f" • 🕘 <t:{event['starts_at']}:R>" if event["starts_at"] else ""
    embed = discord.Embed(
        title=f"{emoji} Are you coming? — {event['title']}",
        description=f"**{event['activity']}**{when}\nTap a button below to let the party know.",
        colour=discord.Colour.blurple(),
    )

    def _mentions(ids: list) -> str:
        return "\n".join(f"• <@{u}>" for u in ids) or "*—*"

    embed.add_field(
        name=f"✅ Coming ({len(confirmed)})", value=_mentions(confirmed), inline=True
    )
    embed.add_field(
        name=f"❌ Can't make it ({len(declined)})", value=_mentions(declined), inline=True
    )
    embed.add_field(
        name=f"⏳ No reply ({len(awaiting)})", value=_mentions(awaiting), inline=True
    )
    return embed
