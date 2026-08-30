"""Legion dashboard (/dashboard): an at-a-glance overview for organisers.

A moderator posts one dashboard per server; it then refreshes itself on a short
timer, so upcoming events, the LFG pool, absences, recurring series and roster
health stay current without anyone re-running a command. Read-only (no buttons),
so nothing to persist as a view. Implements ROADMAP Phase 4 — Legion dashboard.
"""

import logging
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import config, i18n
from ..branding import brand
from ..embeds import ROLE_EMOJI
from ..logic import ROLES, assign, missing_slots
from ..utils.dashboard import roster_stats
from ..utils.text import truncate_field

log = logging.getLogger(__name__)

# The dashboard shows the soonest events and a slice of the absences; the counts
# in the field titles always reflect the full totals.
MAX_EVENTS = 6
MAX_ABSENCES = 20
REFRESH_MINUTES = 2


def build_dashboard_embed(
    events: list,
    total_events: int,
    lfg_count: int,
    available_count: int,
    absences: list,
    recurring_count: int,
    profiles: list,
    lang: str,
    now: int,
) -> discord.Embed:
    """The organiser overview. ``events`` is the displayed slice as
    ``(event_row, signups)`` pairs; ``total_events`` is the full open count."""
    embed = discord.Embed(
        title="📊 " + i18n.t("dashboard.title", lang),
        description=i18n.t("dashboard.subtitle", lang),
        colour=discord.Colour.blurple(),
    )
    brand(embed)

    # Upcoming events, with fill and the roles still short.
    if events:
        lines = []
        for event, signups in events:
            party, _ = assign(event["compo"], event["size"], signups)
            if event["starts_at"]:
                when = f"<t:{event['starts_at']}:R>"
            else:
                when = i18n.t("dashboard.no_time", lang)
            emoji = config.EMOJI_ACTIVITY.get(
                event["activity"], config.EMOJI_ACTIVITY["Other"]
            )
            line = (
                f"{emoji} **{event['title']}** — {when} · {len(party)}/{event['size']}"
            )
            missing = missing_slots(event["compo"], event["size"], signups)
            if missing:
                needs = " ".join(
                    f"{ROLE_EMOJI[role]}{missing[role]}"
                    for role in ROLES
                    if role in missing
                )
                line += f" · ⚠️ {needs}"
            lines.append(line)
        events_value = truncate_field("\n".join(lines))
    else:
        events_value = i18n.t("dashboard.no_events", lang)
    embed.add_field(
        name=f"📅 {i18n.t('dashboard.events', lang)} ({total_events})",
        value=events_value,
        inline=False,
    )

    embed.add_field(
        name=f"🔎 {i18n.t('dashboard.lfg', lang)}",
        value=i18n.t(
            "dashboard.lfg_line", lang, looking=lfg_count, available=available_count
        ),
        inline=True,
    )
    embed.add_field(
        name=f"🔁 {i18n.t('dashboard.recurring', lang)}",
        value=str(recurring_count),
        inline=True,
    )

    if absences:
        away = " ".join(f"<@{row['user_id']}>" for row in absences[:MAX_ABSENCES])
        absences_value = truncate_field(away)
    else:
        absences_value = i18n.t("dashboard.no_absences", lang)
    embed.add_field(
        name=f"🏖️ {i18n.t('dashboard.absences', lang)} ({len(absences)})",
        value=absences_value,
        inline=False,
    )

    members, distribution = roster_stats(profiles)
    split = (
        f"{ROLE_EMOJI['tank']} {distribution['tank']}  "
        f"{ROLE_EMOJI['heal']} {distribution['heal']}  "
        f"{ROLE_EMOJI['dps']} {distribution['dps']}"
    )
    header = i18n.t("dashboard.roster_members", lang, members=members)
    roster_value = f"{header}\n{split}"
    embed.add_field(
        name=f"👥 {i18n.t('dashboard.roster', lang)}",
        value=roster_value,
        inline=False,
    )

    embed.set_footer(text=i18n.t("dashboard.footer", lang, updated=f"<t:{now}:R>"))
    return embed


async def _build_from_db(db, guild_id: int, lang: str) -> discord.Embed:
    """Gathers the guild's live state and renders the dashboard embed."""
    now = int(time.time())
    events_rows = await db.upcoming_events(guild_id, now)
    events = [
        (event, await db.get_signups(event["message_id"]))
        for event in events_rows[:MAX_EVENTS]
    ]
    lfg_count = len(await db.get_lfg_pool(guild_id, now))
    available_count = len(await db.get_available(guild_id, now))
    absences = await db.list_absences(guild_id, now)
    recurring_count = len(await db.list_recurrences(guild_id))
    profiles = await db.all_profiles(guild_id)
    return build_dashboard_embed(
        events,
        len(events_rows),
        lfg_count,
        available_count,
        absences,
        recurring_count,
        profiles,
        lang,
        now,
    )


async def refresh_dashboard(client, guild_id: int, lang: str) -> None:
    """Redraws the guild's dashboard in place, if one has been posted."""
    stored = await client.db.get_dashboard(guild_id)
    if stored is None:
        return
    channel_id, message_id = stored
    channel = client.get_channel(channel_id)
    if channel is None:
        try:
            channel = await client.fetch_channel(channel_id)
        except discord.HTTPException:
            return
    embed = await _build_from_db(client.db, guild_id, lang)
    try:
        await channel.get_partial_message(message_id).edit(embed=embed)
    except discord.HTTPException:
        pass  # message deleted or permissions revoked


@app_commands.guild_only()
class Dashboard(commands.Cog):
    """The /dashboard command and its auto-refresh loop."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.refresh_loop.start()

    async def cog_unload(self):
        self.refresh_loop.cancel()

    @app_commands.command(
        name="dashboard",
        description="Post the legion dashboard here, or refresh it (moderators)",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def dashboard(self, interaction: discord.Interaction):
        db = self.bot.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        embed = await _build_from_db(db, interaction.guild_id, lang)

        # Refresh the remembered dashboard in place (mirrors /panel).
        stored = await db.get_dashboard(interaction.guild_id)
        if stored is not None:
            channel_id, message_id = stored
            channel = self.bot.get_channel(channel_id)
            if channel is not None:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed)
                    await interaction.response.send_message(
                        i18n.t("dashboard.refreshed", lang, link=message.jump_url),
                        ephemeral=True,
                    )
                    return
                except discord.NotFound:
                    pass  # deleted: fall through and post a fresh one
                except discord.Forbidden:
                    await interaction.response.send_message(
                        i18n.t("dashboard.forbidden", lang), ephemeral=True
                    )
                    return

        message = await interaction.channel.send(embed=embed)
        await db.set_dashboard(interaction.guild_id, interaction.channel_id, message.id)
        await interaction.response.send_message(
            i18n.t("dashboard.posted", lang, link=message.jump_url), ephemeral=True
        )

    @tasks.loop(minutes=REFRESH_MINUTES)
    async def refresh_loop(self):
        """Keeps every posted dashboard current."""
        for row in await self.bot.db.guilds_with_dashboard():
            # One guild's failure must never kill the loop for every server.
            try:
                guild = self.bot.get_guild(row["guild_id"])
                lang = await i18n.resolve_lang(self.bot.db, guild)
                await refresh_dashboard(self.bot, row["guild_id"], lang)
            except Exception:
                log.exception(
                    "Failed to refresh the dashboard for guild %s", row["guild_id"]
                )

    @refresh_loop.before_loop
    async def _wait_ready(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Dashboard(bot))
