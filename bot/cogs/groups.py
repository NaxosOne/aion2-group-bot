"""Slash commands (/event, /events), the reminder loop and the bot status."""

import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import config
from ..actions import publish_event
from ..embeds import ACTIVITY_EMOJI
from ..logic import COMPO_OPEN, COMPO_STANDARD, assign
from ..utils.time_parse import ParseError, parse_when


@app_commands.guild_only()
class Groups(commands.Cog):
    """Creating and listing events, plus reminders and the bot status."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.reminders.start()
        self.status.start()

    async def cog_unload(self):
        self.reminders.cancel()
        self.status.cancel()

    # ----- /event -----

    @app_commands.command(name="event", description="Create a group call (dungeon, PvP...)")
    @app_commands.rename(activity="type")
    @app_commands.describe(
        title="Name of the event (e.g. “Fire Temple HM”)",
        activity="Type of event",
        comp="Party of 5, party of 10 (raid/battleground), or open.",
        when="E.g. “21:00”, “9pm”, “tomorrow 20:30”, “30/08 21:00”. Empty = right now.",
        size="Number of slots in open mode (default: 5). Ignored for standard parties.",
        description="Extra info: required level, voice channel, etc.",
        ping="Optional: a role to notify (e.g. @Aion2). @everyone is moderators only.",
    )
    @app_commands.choices(
        activity=[
            app_commands.Choice(name="🏰 Dungeon", value="Dungeon"),
            app_commands.Choice(name="🐉 Raid", value="Raid"),
            app_commands.Choice(name="🚩 Battleground", value="Battleground"),
            app_commands.Choice(name="⚔️ PvP", value="PvP"),
            app_commands.Choice(name="🌀 Rift", value="Rift"),
            app_commands.Choice(name="🌌 Abyss", value="Abyss"),
            app_commands.Choice(name="🎲 Other", value="Other"),
        ],
        comp=[
            app_commands.Choice(
                name="Party of 5 — 1 tank / 1 heal / 3 DPS", value="standard5"
            ),
            app_commands.Choice(
                name="Party of 10 (raid/BG) — 2 tanks / 2 heals / 6 DPS",
                value="standard10",
            ),
            app_commands.Choice(name="Open — no role limits", value=COMPO_OPEN),
        ],
    )
    async def event(
        self,
        interaction: discord.Interaction,
        title: app_commands.Range[str, 1, 100],
        activity: app_commands.Choice[str],
        comp: app_commands.Choice[str],
        when: str | None = None,
        size: app_commands.Range[int, 2, 25] | None = None,
        description: app_commands.Range[str, 1, 500] | None = None,
        ping: discord.Role | None = None,
    ):
        starts_at = None
        if when:
            try:
                starts_at = int(parse_when(when, config.TIMEZONE).timestamp())
            except ParseError as err:
                await interaction.response.send_message(str(err), ephemeral=True)
                return

        # "standard5"/"standard10" are the same standard mode, only size differs.
        if comp.value == COMPO_OPEN:
            comp_mode, party_size = COMPO_OPEN, size or 5
        else:
            comp_mode, party_size = COMPO_STANDARD, 10 if comp.value == "standard10" else 5

        await publish_event(
            interaction,
            title=title,
            activity=activity.value,
            comp_mode=comp_mode,
            size=party_size,
            starts_at=starts_at,
            description=description,
            ping_role=ping,
        )

    # ----- /events -----

    @app_commands.command(name="events", description="See the upcoming events on this server")
    async def events(self, interaction: discord.Interaction):
        events = await self.bot.db.upcoming_events(interaction.guild_id, int(time.time()))
        if not events:
            await interaction.response.send_message(
                "No events scheduled yet. Start your own with `/event`!",
                ephemeral=True,
            )
            return

        lines = []
        for ev in events:
            signups = await self.bot.db.get_signups(ev["message_id"])
            party, waitlist = assign(ev["compo"], ev["size"], signups)
            when = f"<t:{ev['starts_at']}:R>" if ev["starts_at"] else "no time set"
            link = (
                f"https://discord.com/channels/{ev['guild_id']}"
                f"/{ev['channel_id']}/{ev['message_id']}"
            )
            lines.append(
                f"• [**{ev['title']}**]({link}) — {ev['activity']}, {when} — "
                f"{len(party)}/{ev['size']} signed up"
                + (f" (+{len(waitlist)} waitlisted)" if waitlist else "")
            )

        embed = discord.Embed(
            title="📅 Upcoming events",
            description="\n".join(lines),
            colour=discord.Colour.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ----- Automatic reminders -----

    @tasks.loop(seconds=60)
    async def reminders(self):
        now = int(time.time())
        events = await self.bot.db.events_to_remind(
            now, config.REMINDER_MINUTES * 60
        )
        for ev in events:
            await self.bot.db.mark_reminded(ev["message_id"])
            if ev["starts_at"] < now - 600:
                # The bot was offline and the event is long past: no point in
                # sending a late reminder.
                continue
            try:
                await self._send_reminder(ev)
            except discord.HTTPException:
                pass  # channel deleted or permissions revoked: skip

    @reminders.before_loop
    async def _wait_ready(self):
        await self.bot.wait_until_ready()

    async def _send_reminder(self, ev):
        channel = self.bot.get_channel(ev["channel_id"])
        if channel is None:
            channel = await self.bot.fetch_channel(ev["channel_id"])
        signups = await self.bot.db.get_signups(ev["message_id"])
        party, _ = assign(ev["compo"], ev["size"], signups)
        mentions = " ".join(f"<@{s['user_id']}>" for s in party)
        link = (
            f"https://discord.com/channels/{ev['guild_id']}"
            f"/{ev['channel_id']}/{ev['message_id']}"
        )
        await channel.send(
            f"⏰ Reminder: [**{ev['title']}**](<{link}>) starts "
            f"<t:{ev['starts_at']}:R>!"
            + (f"\n{mentions}" if mentions else " (nobody signed up 😢)")
        )

    # ----- Bot status: the next event -----

    DAYS_SHORT = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

    def _short_when(self, ts: int) -> str:
        """E.g. "today 21:00", "tomorrow 20:30", "Sat 30/08 21:00"."""
        dt = datetime.fromtimestamp(ts, config.TIMEZONE)
        today = datetime.now(config.TIMEZONE).date()
        hm = dt.strftime("%H:%M")
        days_away = (dt.date() - today).days
        if days_away == 0:
            return f"today {hm}"
        if days_away == 1:
            return f"tomorrow {hm}"
        return f"{self.DAYS_SHORT[dt.weekday()]} {dt.strftime('%d/%m')} {hm}"

    @tasks.loop(minutes=5)
    async def status(self):
        ev = await self.bot.db.next_upcoming_event(int(time.time()))
        if ev:
            emoji = ACTIVITY_EMOJI.get(
                ev["activity"], config.EMOJI_ACTIVITY["Other"]
            )
            text = f"{emoji} {ev['title']} — {self._short_when(ev['starts_at'])}"
        else:
            text = "/event to start a group"
        try:
            await self.bot.change_presence(activity=discord.Game(name=text[:100]))
        except discord.HTTPException:
            pass

    @status.before_loop
    async def _wait_ready_status(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Groups(bot))
