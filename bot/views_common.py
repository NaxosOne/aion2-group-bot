"""Shared event-view helpers: redraw the event message and one character option."""

import discord

from . import config, i18n
from .embeds import ROLE_LABEL, build_event_embed


async def refresh_event_message(client, event) -> list:
    """Redraws an event's message from the database; returns its sign-ups.

    Edits the message by id rather than through the interaction, so the party
    list also updates when the click came from an ephemeral character picker
    rather than from the event message itself. Passing no `view` leaves the
    buttons exactly as they are.
    """
    signups = await client.db.get_signups(event["message_id"])
    classes = await client.db.get_main_classes(
        event["guild_id"], [s["user_id"] for s in signups]
    )
    guild = client.get_guild(event["guild_id"])
    lang = await i18n.resolve_lang(client.db, guild)
    embed = build_event_embed(event, signups, classes, lang)
    channel = client.get_channel(event["channel_id"])
    if channel is None:
        channel = await client.fetch_channel(event["channel_id"])
    await channel.get_partial_message(event["message_id"]).edit(embed=embed)
    return signups


def character_option(row, *, default: bool = False) -> discord.SelectOption:
    """One character as a dropdown entry."""
    return discord.SelectOption(
        label=row["char_name"][:100],
        value=str(row["id"]),
        description=f"{row['char_class']} · {ROLE_LABEL[row['role']]}"[:100],
        emoji=config.CLASS_EMOJI.get(row["char_class"]),
        default=default,
    )
