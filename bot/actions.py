"""Actions shared between the slash commands and the panel's pop-up forms.

Both /event and the panel's "Create an event" button publish an event the
same way; both /away and the "Report an absence" button register an absence
the same way. The logic lives here once.
"""

import logging
from datetime import datetime

import discord

from . import config, i18n
from .embeds import build_event_embed
from .utils.mentions import ping_permitted
from .utils.permissions import member_is_moderator
from .utils.threads import event_thread_name
from .utils.time_parse import ParseError, parse_when_or_date
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
        # Forum and category channels have no send(): fall back rather than
        # crash on a destination that can't hold a message.
        if channel is not None and hasattr(channel, "send"):
            return channel
    return interaction.channel


async def post_event(
    client, channel, event: dict, lang: str, ping_role=None
) -> "discord.Message":
    """Sends the event message, persists it and opens its discussion thread.

    `event` holds the DB row fields (no message_id). Shared by the /event
    command and the recurring-events loop. Raises on failure; on a persistence
    failure the just-sent message is deleted so no orphan buttons remain.
    """
    embed = build_event_embed(event, [], lang=lang)
    if ping_role is not None:
        content = ping_role.mention
        mentions = discord.AllowedMentions(
            roles=[ping_role], everyone=ping_role.is_default()
        )
    else:
        content = None
        mentions = discord.AllowedMentions.none()
    # Send the message first so we know its ID, which is our key.
    message = await channel.send(
        content=content, embed=embed, view=SignupView(lang), allowed_mentions=mentions
    )
    try:
        await client.db.create_event(message_id=message.id, **event)
    except Exception:
        # The message (with live buttons) exists but has no backing row; delete
        # it so players don't click a dead event.
        log.exception("Failed to persist event for message %s", message.id)
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        raise
    await _open_event_thread(message, event["title"], lang)
    return message


async def publish_event(
    interaction: discord.Interaction,
    *,
    title: str,
    activity: str,
    comp_mode: str,
    size: int,
    starts_at: int | None,
    description: str | None,
    ping_role: "discord.Role | None" = None,
    groups: int = 1,
) -> None:
    """Posts the event message in the configured (or current) channel.

    If `ping_role` is given, the message mentions that role so the legion is
    notified. Pinging @everyone is reserved to moderators (mentioning through
    the bot bypasses the member's own permissions).
    """
    lang = await i18n.resolve_lang(interaction.client.db, interaction.guild)
    if ping_role is not None:
        is_moderator = await member_is_moderator(
            interaction.client.db, interaction.user
        )
        if not ping_permitted(
            is_default_role=ping_role.is_default(), is_moderator=is_moderator
        ):
            await interaction.response.send_message(
                i18n.t("event.mod_only_everyone", lang),
                ephemeral=True,
            )
            return

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
        "groups": groups,
    }
    await interaction.response.defer(ephemeral=True)
    try:
        message = await post_event(interaction.client, channel, event, lang, ping_role)
    except discord.Forbidden:
        await interaction.followup.send(
            i18n.t("event.post_forbidden", lang, channel=channel.mention),
            ephemeral=True,
        )
        return
    except discord.HTTPException as err:
        log.exception("Could not post the event in channel %s", channel.id)
        await interaction.followup.send(
            i18n.t(
                "event.post_failed",
                lang,
                channel=channel.mention,
                error=(err.text or err),
            ),
            ephemeral=True,
        )
        return
    except Exception:
        await interaction.followup.send(
            i18n.t("event.save_failed", lang), ephemeral=True
        )
        return
    await interaction.followup.send(
        i18n.t("event.created", lang, channel=channel.mention, link=message.jump_url),
        ephemeral=True,
    )


async def _open_event_thread(message: discord.Message, title: str, lang: str) -> None:
    """Attaches a discussion thread to the event message (best-effort).

    Skips silently if the bot lacks the Create Public Threads permission, so a
    missing permission never blocks event creation.
    """
    try:
        thread = await message.create_thread(
            name=event_thread_name(title),
            auto_archive_duration=4320,  # keep it alive ~3 days around the event
        )
    except discord.HTTPException:
        log.info("Could not open a thread for event %s (missing perms?)", message.id)
        return
    try:
        # The title is member-supplied: an "@everyone" title must not turn the
        # thread intro into a mass ping.
        await thread.send(
            i18n.t("event.thread_intro", lang, title=title),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except discord.HTTPException:
        pass


def fmt_absence_ts(ts: int, end: bool = False) -> str:
    """Date only (<t:D>) for a whole day, date + time (<t:f>) otherwise.

    A whole-day bound is stored at 00:00 (start) or 23:59 (end).
    """
    dt = datetime.fromtimestamp(ts, config.TIMEZONE)
    day_boundary = (dt.hour, dt.minute) == ((23, 59) if end else (0, 0))
    return f"<t:{ts}:D>" if day_boundary else f"<t:{ts}:f>"


async def register_absence(
    interaction: discord.Interaction,
    start: str,
    until: str | None,
    reason: str | None,
) -> None:
    """Parses the bounds, stores the absence and announces it (or explains
    the input error ephemerally)."""
    tz = config.TIMEZONE
    lang = await i18n.resolve_lang(interaction.client.db, interaction.guild)
    try:
        start_dt, start_has_time = parse_when_or_date(start, tz, lang=lang)
        if until:
            end_dt, end_has_time = parse_when_or_date(until, tz, lang=lang)
        else:
            # No "until": away until the end of the starting day.
            end_dt, end_has_time = start_dt, False
    except ParseError as err:
        await interaction.response.send_message(str(err), ephemeral=True)
        return

    start_ts = int(start_dt.timestamp())
    if end_has_time:
        end_ts = int(end_dt.timestamp())
    else:
        end_ts = int(
            datetime(
                end_dt.year, end_dt.month, end_dt.day, 23, 59, tzinfo=tz
            ).timestamp()
        )
    if end_ts < start_ts:
        await interaction.response.send_message(
            i18n.t("absence.end_before_start", lang), ephemeral=True
        )
        return

    await interaction.client.db.add_absence(
        interaction.guild_id, interaction.user.id, start_ts, end_ts, reason
    )

    whole_single_day = (
        not start_has_time and not end_has_time and start_dt.date() == end_dt.date()
    )
    if whole_single_day:
        period = i18n.t("absence.period_single", lang, date=f"<t:{start_ts}:D>")
    else:
        period = i18n.t(
            "absence.period_range",
            lang,
            start=fmt_absence_ts(start_ts),
            end=fmt_absence_ts(end_ts, end=True),
        )
    announcement = i18n.t(
        "absence.announcement",
        lang,
        mention=interaction.user.mention,
        period=period,
        reason=(f" ({reason})" if reason else ""),
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
            i18n.t("absence.post_forbidden", lang, channel=channel.mention),
            ephemeral=True,
        )
        return
    await interaction.followup.send(
        i18n.t(
            "absence.registered", lang, channel=channel.mention, link=message.jump_url
        ),
        ephemeral=True,
    )
