"""Actions shared between the slash commands and the panel's pop-up forms.

Both /event and the panel's "Create an event" button publish an event the
same way; both /away and the "Report an absence" button register an absence
the same way. The logic lives here once.
"""

import logging
from datetime import datetime

import discord

from . import config
from .embeds import build_event_embed
from .utils.time_parse import HELP_FORMATS_DATETIME, ParseError, parse_when_or_date
from .views import SignupView

log = logging.getLogger(__name__)


async def resolve_channel(interaction: discord.Interaction, setting: str):
    """The channel configured for this kind of message, or the current one.

    Lets a server keep the pinned /panel in one channel while events and
    absences land in their own channels instead of burying it.
    """
    settings = await interaction.client.db.get_settings(interaction.guild_id)
    channel_id = settings[setting] if settings else None
    if channel_id and channel_id != interaction.channel_id:
        channel = interaction.guild.get_channel(channel_id)
        if channel is not None:
            return channel
    return interaction.channel


async def publish_event(
    interaction: discord.Interaction, *,
    title: str, activity: str, comp_mode: str, size: int,
    starts_at: int | None, description: str | None,
) -> None:
    """Posts the event message in the configured (or current) channel."""
    channel = await resolve_channel(interaction, "event_channel_id")
    event = {
        "channel_id": channel.id,
        "guild_id": interaction.guild_id,
        "creator_id": interaction.user.id,
        "creator_name": interaction.user.display_name,
        "title": title,
        "activity": activity,
        "description": description,
        "compo": comp_mode,
        "size": size,
        "starts_at": starts_at,
        "status": "open",
    }
    # Send the message first so we know its ID, which is our key.
    embed = build_event_embed(event, [])
    await interaction.response.defer(ephemeral=True)
    try:
        message = await channel.send(embed=embed, view=SignupView())
    except discord.Forbidden:
        await interaction.followup.send(
            f"I'm not allowed to post in {channel.mention}. Give me the "
            "Send Messages and Embed Links permissions there, or point "
            "`/channels` at another channel.",
            ephemeral=True,
        )
        return
    try:
        await interaction.client.db.create_event(message_id=message.id, **event)
    except Exception:
        # The message (with live buttons) exists but has no backing row; delete
        # it so players don't click a dead event, and tell the creator.
        log.exception("Failed to persist event for message %s", message.id)
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        await interaction.followup.send(
            "Something went wrong saving this event — please try again.",
            ephemeral=True,
        )
        return
    await interaction.followup.send(
        f"Event created in {channel.mention} — {message.jump_url}", ephemeral=True
    )


def fmt_absence_ts(ts: int, end: bool = False) -> str:
    """Date only (<t:D>) for a whole day, date + time (<t:f>) otherwise.

    A whole-day bound is stored at 00:00 (start) or 23:59 (end).
    """
    dt = datetime.fromtimestamp(ts, config.TIMEZONE)
    day_boundary = (dt.hour, dt.minute) == ((23, 59) if end else (0, 0))
    return f"<t:{ts}:D>" if day_boundary else f"<t:{ts}:f>"


async def register_absence(
    interaction: discord.Interaction,
    start: str, until: str | None, reason: str | None,
) -> None:
    """Parses the bounds, stores the absence and announces it (or explains
    the input error ephemerally)."""
    tz = config.TIMEZONE
    try:
        start_dt, start_has_time = parse_when_or_date(start, tz)
        if until:
            end_dt, end_has_time = parse_when_or_date(until, tz)
        else:
            # No "until": away until the end of the starting day.
            end_dt, end_has_time = start_dt, False
    except ParseError as err:
        await interaction.response.send_message(
            f"{err} {HELP_FORMATS_DATETIME}", ephemeral=True
        )
        return

    start_ts = int(start_dt.timestamp())
    if end_has_time:
        end_ts = int(end_dt.timestamp())
    else:
        end_ts = int(
            datetime(end_dt.year, end_dt.month, end_dt.day, 23, 59, tzinfo=tz).timestamp()
        )
    if end_ts < start_ts:
        await interaction.response.send_message(
            "The return moment is before the departure. 🤔", ephemeral=True
        )
        return

    await interaction.client.db.add_absence(
        interaction.guild_id, interaction.user.id, start_ts, end_ts, reason
    )

    whole_single_day = (
        not start_has_time and not end_has_time
        and start_dt.date() == end_dt.date()
    )
    if whole_single_day:
        period = f"on <t:{start_ts}:D>"
    else:
        period = f"from {fmt_absence_ts(start_ts)} to {fmt_absence_ts(end_ts, end=True)}"
    announcement = (
        f"🏖️ {interaction.user.mention} will be away {period}"
        + (f" ({reason})" if reason else "")
        + ". Enjoy the break!"
    )
    quiet = discord.AllowedMentions.none()

    channel = await resolve_channel(interaction, "absence_channel_id")
    if channel.id == interaction.channel_id:
        await interaction.response.send_message(announcement, allowed_mentions=quiet)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        message = await channel.send(announcement, allowed_mentions=quiet)
    except discord.Forbidden:
        await interaction.followup.send(
            f"I'm not allowed to post in {channel.mention}. Give me the "
            "Send Messages permission there, or point `/channels` at "
            "another channel.",
            ephemeral=True,
        )
        return
    await interaction.followup.send(
        f"Absence registered in {channel.mention} — {message.jump_url}",
        ephemeral=True,
    )
