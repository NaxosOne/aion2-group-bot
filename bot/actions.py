"""Actions shared between the slash commands and the panel's pop-up forms.

Both /event and the panel's "Create an event" button publish an event the
same way; both /away and the "Report an absence" button register an absence
the same way. The logic lives here once.
"""

from datetime import datetime

import discord

from . import config
from .embeds import build_event_embed
from .utils.time_parse import HELP_FORMATS_DATETIME, ParseError, parse_when_or_date
from .views import SignupView


async def publish_event(
    interaction: discord.Interaction, *,
    title: str, activity: str, comp_mode: str, size: int,
    starts_at: int | None, description: str | None,
) -> None:
    """Posts the event message in the interaction's channel and stores it."""
    event = {
        "channel_id": interaction.channel_id,
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
    await interaction.response.send_message(embed=embed, view=SignupView())
    message = await interaction.original_response()
    await interaction.client.db.create_event(message_id=message.id, **event)


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
    await interaction.response.send_message(
        f"🏖️ {interaction.user.mention} will be away {period}"
        + (f" ({reason})" if reason else "")
        + ". Enjoy the break!",
        allowed_mentions=discord.AllowedMentions.none(),
    )
