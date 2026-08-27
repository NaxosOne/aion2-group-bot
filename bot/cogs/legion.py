"""Legion life: absences (/away, /absences, /back), announcements (/announce)
and welcoming newcomers (/welcome)."""

import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from .. import config
from ..utils.time_parse import HELP_FORMATS_DATETIME, ParseError, parse_when_or_date


def _fmt_ts(ts: int, end: bool = False) -> str:
    """Date seule (<t:D>) pour une journée entière, date + heure (<t:f>) sinon.

    Une borne « journée entière » est stockée à 00:00 (début) ou 23:59 (fin).
    """
    dt = datetime.fromtimestamp(ts, config.TIMEZONE)
    day_boundary = (dt.hour, dt.minute) == ((23, 59) if end else (0, 0))
    return f"<t:{ts}:D>" if day_boundary else f"<t:{ts}:f>"


class AnnounceModal(discord.ui.Modal, title="Legion announcement"):
    """Pop-up form: allows a multi-line message."""

    announce_title = discord.ui.TextInput(label="Title", max_length=100)
    content = discord.ui.TextInput(
        label="Message",
        style=discord.TextStyle.paragraph,
        max_length=2000,
    )

    def __init__(self, ping: discord.Role | None):
        super().__init__()
        self.ping = ping

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"📯 {self.announce_title.value}",
            description=self.content.value,
            colour=discord.Colour.gold(),
        )
        embed.set_footer(
            text=f"Legion announcement • by {interaction.user.display_name}"
        )

        content = None
        if self.ping is not None:
            # The @everyone role is mentioned as "@everyone", not via <@&id>.
            content = "@everyone" if self.ping.is_default() else self.ping.mention

        await interaction.response.send_message(
            content=content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=True, roles=True),
        )


@app_commands.guild_only()
class Legion(commands.Cog):
    """Member absences, announcements and the welcome message."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----- Absences -----

    @app_commands.command(name="away", description="Let the legion know you'll be away")
    @app_commands.describe(
        start="First day away, time optional (e.g. “30/08”, “30/08 14:00”, “tomorrow 18h”)",
        until="Last day away, time optional (empty = same day as “start”)",
        reason="Optional: holidays, exams, IRL...",
    )
    async def away(
        self,
        interaction: discord.Interaction,
        start: str,
        until: str | None = None,
        reason: app_commands.Range[str, 1, 100] | None = None,
    ):
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

        await self.bot.db.add_absence(
            interaction.guild_id, interaction.user.id, start_ts, end_ts, reason
        )

        whole_single_day = (
            not start_has_time and not end_has_time
            and start_dt.date() == end_dt.date()
        )
        if whole_single_day:
            period = f"on <t:{start_ts}:D>"
        else:
            period = f"from {_fmt_ts(start_ts)} to {_fmt_ts(end_ts, end=True)}"
        await interaction.response.send_message(
            f"🏖️ {interaction.user.mention} will be away {period}"
            + (f" ({reason})" if reason else "")
            + ". Enjoy the break!",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="absences", description="See who's away or about to be")
    async def absences(self, interaction: discord.Interaction):
        now = int(time.time())
        absences = await self.bot.db.list_absences(interaction.guild_id, now)
        if not absences:
            await interaction.response.send_message(
                "Nobody's away — the legion is at full strength! 💪",
                ephemeral=True,
            )
            return

        lines = []
        for a in absences:
            ongoing = a["starts_on"] <= now
            state = "🔴 ongoing" if ongoing else f"starting {_fmt_ts(a['starts_on'])}"
            lines.append(
                f"• <@{a['user_id']}> — {state}, back after {_fmt_ts(a['ends_on'], end=True)}"
                + (f" *({a['reason']})*" if a["reason"] else "")
            )

        embed = discord.Embed(
            title="🏖️ Absences",
            description="\n".join(lines),
            colour=discord.Colour.orange(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="back", description="Cancel your absences (early return)")
    async def back(self, interaction: discord.Interaction):
        cancelled = await self.bot.db.clear_absences(
            interaction.guild_id, interaction.user.id, int(time.time())
        )
        if cancelled:
            await interaction.response.send_message(
                f"🎉 {interaction.user.mention} is back!",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        else:
            await interaction.response.send_message(
                "You had no current or upcoming absence.", ephemeral=True
            )

    # ----- Welcoming newcomers -----

    @app_commands.command(
        name="welcome",
        description="Automatically greet newcomers in this channel (moderators)",
    )
    @app_commands.describe(action="Enable in this channel, or disable")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Enable in this channel", value="on"),
            app_commands.Choice(name="Disable", value="off"),
        ]
    )
    @app_commands.default_permissions(manage_guild=True)
    async def welcome(
        self, interaction: discord.Interaction, action: app_commands.Choice[str]
    ):
        if action.value == "on":
            await self.bot.db.set_setting(
                interaction.guild_id, "welcome_channel_id", interaction.channel_id
            )
            await interaction.response.send_message(
                "👋 Got it: I'll greet new members here with the bot's how-to.",
                ephemeral=True,
            )
        else:
            await self.bot.db.set_setting(
                interaction.guild_id, "welcome_channel_id", None
            )
            await interaction.response.send_message(
                "Welcome message disabled.", ephemeral=True
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        settings = await self.bot.db.get_settings(member.guild.id)
        if settings is None or not settings["welcome_channel_id"]:
            return
        channel = member.guild.get_channel(settings["welcome_channel_id"])
        if channel is None:
            return

        embed = discord.Embed(
            title="Welcome to the legion! 👋",
            description=(
                "Here's how things work around here:\n"
                "• `/profile set` — register your character (class, role), "
                "it will show up in parties\n"
                "• `/events` — the scheduled events; sign up in one click "
                "(🛡️ Tank / 💚 Heal / 🗡️ DPS)\n"
                "• `/event` — start your own run: dungeon, PvP, abyss...\n"
                "• `/availability post` — tell us which evenings you can play "
                "this week\n\n"
                "Have fun! ⚔️"
            ),
            colour=discord.Colour.blurple(),
        )
        try:
            await channel.send(content=member.mention, embed=embed)
        except discord.HTTPException:
            pass  # channel permissions revoked

    # ----- Announcements -----

    @app_commands.command(
        name="announce", description="Publish a legion announcement (moderators)"
    )
    @app_commands.describe(ping="Optional: role to mention (e.g. @Aion2, @everyone)")
    @app_commands.default_permissions(manage_messages=True)
    async def announce(
        self, interaction: discord.Interaction, ping: discord.Role | None = None
    ):
        await interaction.response.send_modal(AnnounceModal(ping))


async def setup(bot: commands.Bot):
    await bot.add_cog(Legion(bot))
