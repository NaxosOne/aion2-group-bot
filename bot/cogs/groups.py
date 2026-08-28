"""Slash commands (/event, /events), the reminder loop and the bot status."""

import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import config, i18n
from ..actions import publish_event
from ..embeds import PRESENCE_ACTIVITY_EMOJI, build_rsvp_embed
from ..logic import COMPO_OPEN, COMPO_STANDARD, assign
from ..utils.messages import parse_message_id
from ..utils.time_parse import ParseError, parse_when
from ..views import RSVPView


@app_commands.guild_only()
class Groups(commands.Cog):
    """Creating and listing events, plus reminders and the bot status."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.reminders.start()
        self.rsvp_prompts.start()
        self.status.start()

    async def cog_unload(self):
        self.reminders.cancel()
        self.rsvp_prompts.cancel()
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
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        events = await self.bot.db.upcoming_events(interaction.guild_id, int(time.time()))
        if not events:
            await interaction.response.send_message(
                i18n.t("events.none", lang),
                ephemeral=True,
            )
            return

        lines = []
        for ev in events:
            signups = await self.bot.db.get_signups(ev["message_id"])
            party, waitlist = assign(ev["compo"], ev["size"], signups)
            when = (
                f"<t:{ev['starts_at']}:R>"
                if ev["starts_at"]
                else i18n.t("events.no_time", lang)
            )
            link = (
                f"https://discord.com/channels/{ev['guild_id']}"
                f"/{ev['channel_id']}/{ev['message_id']}"
            )
            line = i18n.t(
                "events.line",
                lang,
                title=ev["title"],
                link=link,
                activity=ev["activity"],
                when=when,
                signed=len(party),
                size=ev["size"],
            )
            if waitlist:
                line += i18n.t("events.waitlist_suffix", lang, n=len(waitlist))
            lines.append(line)

        embed = discord.Embed(
            title=i18n.t("events.title", lang),
            description="\n".join(lines),
            colour=discord.Colour.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ----- /rsvp: post the "are you coming?" prompt on demand -----

    @app_commands.command(
        name="rsvp",
        description="Post the 'are you coming?' prompt for an event now (moderators)",
    )
    @app_commands.describe(event="The event message — paste its link or ID")
    @app_commands.default_permissions(manage_messages=True)
    async def rsvp(self, interaction: discord.Interaction, event: str):
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        message_id = parse_message_id(event)
        if message_id is None:
            await interaction.response.send_message(
                i18n.t("rsvp.need_id", lang), ephemeral=True
            )
            return
        ev = await self.bot.db.get_event(message_id)
        if ev is None or ev["guild_id"] != interaction.guild_id:
            await interaction.response.send_message(
                i18n.t("rsvp.not_found_here", lang), ephemeral=True
            )
            return
        signups = await self.bot.db.get_signups(ev["message_id"])
        party, _ = assign(ev["compo"], ev["size"], signups)
        if not party:
            await interaction.response.send_message(
                i18n.t("rsvp.nobody_signed_up", lang), ephemeral=True
            )
            return
        try:
            prompt = await self._send_rsvp(ev, party)
        except discord.HTTPException:
            await interaction.response.send_message(
                i18n.t("rsvp.post_failed", lang), ephemeral=True
            )
            return
        await self.bot.db.mark_rsvp_sent(ev["message_id"])
        await self.bot.db.set_rsvp_prompt_id(ev["message_id"], prompt.id)
        await interaction.response.send_message(
            i18n.t("rsvp.posted", lang, link=prompt.jump_url), ephemeral=True
        )

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
        lang = await i18n.resolve_lang(
            self.bot.db, self.bot.get_guild(ev["guild_id"])
        )
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
        text = i18n.t(
            "reminder.text",
            lang,
            title=ev["title"],
            link=link,
            when=f"<t:{ev['starts_at']}:R>",
        )
        await channel.send(
            text
            + (f"\n{mentions}" if mentions else i18n.t("reminder.nobody", lang))
        )

    # ----- RSVP prompts ("are you coming?") -----

    @tasks.loop(seconds=60)
    async def rsvp_prompts(self):
        now = int(time.time())
        events = await self.bot.db.events_to_rsvp(now, config.RSVP_MINUTES * 60)
        for ev in events:
            # Claim first so the prompt is posted at most once, even on errors.
            await self.bot.db.mark_rsvp_sent(ev["message_id"])
            if ev["starts_at"] < now:
                continue  # already started: nothing to ask
            try:
                signups = await self.bot.db.get_signups(ev["message_id"])
                party, _ = assign(ev["compo"], ev["size"], signups)
                if not party:
                    continue  # nobody signed up
                prompt = await self._send_rsvp(ev, party)
                await self.bot.db.set_rsvp_prompt_id(ev["message_id"], prompt.id)
            except discord.HTTPException:
                pass  # channel deleted or permissions revoked: skip

    @rsvp_prompts.before_loop
    async def _wait_ready_rsvp(self):
        await self.bot.wait_until_ready()

    async def _channel(self, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            channel = await self.bot.fetch_channel(channel_id)
        return channel

    async def _rsvp_channel(self, ev):
        """The configured RSVP channel if set, else the event's own channel."""
        settings = await self.bot.db.get_settings(ev["guild_id"])
        channel_id = settings["rsvp_channel_id"] if settings else None
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except discord.HTTPException:
                    channel = None
            if channel is not None and hasattr(channel, "send"):
                return channel
        return await self._channel(ev["channel_id"])

    async def _send_rsvp(self, ev, party):
        lang = await i18n.resolve_lang(
            self.bot.db, self.bot.get_guild(ev["guild_id"])
        )
        channel = await self._rsvp_channel(ev)
        rsvps = await self.bot.db.get_rsvps(ev["message_id"])
        embed = build_rsvp_embed(ev, party, rsvps, lang=lang)
        mentions = " ".join(f"<@{s['user_id']}>" for s in party)
        return await channel.send(
            content=mentions or None,
            embed=embed,
            view=RSVPView(),
            allowed_mentions=discord.AllowedMentions(users=True),
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
            # Unicode only: the presence is plain text to Discord, so a
            # custom emoji would read as "<:rift:154256...> Rift — 18:00".
            emoji = PRESENCE_ACTIVITY_EMOJI.get(
                ev["activity"], config.DEFAULT_EMOJI_ACTIVITY["Other"]
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
