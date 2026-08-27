"""Polls: /vote (quick questions) and /availability (weekly play-time board).

Both rely on persistent views (fixed custom_ids), like events do: the
buttons survive bot restarts. The custom_ids keep their original names
("vote:choix:N", "dispo:N") for compatibility with already published
messages.
"""

import json
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import config
from ..errors import ViewErrorMixin

CHOICE_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAYS_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ----- /vote -----


def build_poll_embed(poll, votes: list) -> discord.Embed:
    options = json.loads(poll["options"])
    by_choice: dict[int, list] = {i: [] for i in range(len(options))}
    for v in votes:
        if v["choice"] in by_choice:
            by_choice[v["choice"]].append(v["user_id"])

    closed = poll["status"] != "open"
    embed = discord.Embed(
        title=f"🗳️ {poll['question']}",
        colour=discord.Colour.dark_grey() if closed else discord.Colour.blurple(),
    )
    for i, option in enumerate(options):
        voters = by_choice[i]
        value = " ".join(f"<@{uid}>" for uid in voters) or "*—*"
        if len(value) > 1000:
            value = value[:1000] + "…"
        embed.add_field(
            name=f"{CHOICE_EMOJIS[i]} {option} — {len(voters)}",
            value=value,
            inline=False,
        )
    total = len(votes)
    embed.set_footer(
        text=("Poll closed • " if closed else "")
        + f"{total} vote{'s' if total > 1 else ''}"
    )
    return embed


class VoteView(ViewErrorMixin, discord.ui.View):
    def __init__(self, option_count: int = 5):
        super().__init__(timeout=None)
        # Drop the extra buttons for a poll with fewer than 5 options.
        for item in list(self.children):
            if (
                item.custom_id.startswith("vote:choix:")
                and int(item.custom_id.rsplit(":", 1)[1]) >= option_count
            ):
                self.remove_item(item)

    @discord.ui.button(emoji="1️⃣", style=discord.ButtonStyle.primary, custom_id="vote:choix:0")
    async def option_0(self, interaction: discord.Interaction, _):
        await self._vote(interaction, 0)

    @discord.ui.button(emoji="2️⃣", style=discord.ButtonStyle.primary, custom_id="vote:choix:1")
    async def option_1(self, interaction: discord.Interaction, _):
        await self._vote(interaction, 1)

    @discord.ui.button(emoji="3️⃣", style=discord.ButtonStyle.primary, custom_id="vote:choix:2")
    async def option_2(self, interaction: discord.Interaction, _):
        await self._vote(interaction, 2)

    @discord.ui.button(emoji="4️⃣", style=discord.ButtonStyle.primary, custom_id="vote:choix:3")
    async def option_3(self, interaction: discord.Interaction, _):
        await self._vote(interaction, 3)

    @discord.ui.button(emoji="5️⃣", style=discord.ButtonStyle.primary, custom_id="vote:choix:4")
    async def option_4(self, interaction: discord.Interaction, _):
        await self._vote(interaction, 4)

    @discord.ui.button(
        label="Close", emoji="🔒", style=discord.ButtonStyle.secondary,
        custom_id="vote:clore", row=1,
    )
    async def close(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        poll = await db.get_poll(interaction.message.id)
        if poll is None or poll["status"] != "open":
            await interaction.response.send_message(
                "This poll can't be found or is already closed.", ephemeral=True
            )
            return
        is_creator = interaction.user.id == poll["creator_id"]
        is_mod = interaction.user.guild_permissions.manage_messages
        if not (is_creator or is_mod):
            await interaction.response.send_message(
                "Only the poll author (or a moderator) can close it.",
                ephemeral=True,
            )
            return
        await db.set_poll_status(poll["message_id"], "closed")
        poll = await db.get_poll(poll["message_id"])
        embed = build_poll_embed(poll, await db.get_votes(poll["message_id"]))
        await interaction.response.edit_message(embed=embed, view=None)

    async def _vote(self, interaction: discord.Interaction, choice: int):
        db = interaction.client.db
        poll = await db.get_poll(interaction.message.id)
        if poll is None:
            await interaction.response.send_message(
                "I can't find this poll any more.", ephemeral=True
            )
            return
        if poll["status"] != "open":
            await interaction.response.send_message(
                "This poll is closed.", ephemeral=True
            )
            return
        if choice >= len(json.loads(poll["options"])):
            return  # button for an option that doesn't exist (shouldn't happen)
        await db.set_vote(poll["message_id"], interaction.user.id, choice)
        embed = build_poll_embed(poll, await db.get_votes(poll["message_id"]))
        await interaction.response.edit_message(embed=embed)


# ----- /availability -----


def week_label(now: datetime) -> str:
    monday = now.date() - timedelta(days=now.weekday())
    return f"week of {monday.strftime('%d/%m')}"


def build_availability_embed(board, marks: list) -> discord.Embed:
    by_day: dict[int, list] = {i: [] for i in range(7)}
    for m in marks:
        by_day[m["day"]].append(m["user_id"])

    embed = discord.Embed(
        title=f"📅 Availability — {board['week_label']}",
        description="Click the days you can play (click again to remove).",
        colour=discord.Colour.green(),
    )
    for i, day in enumerate(DAYS):
        players = by_day[i]
        embed.add_field(
            name=f"{day} ({len(players)})",
            value="\n".join(f"<@{uid}>" for uid in players) or "*—*",
            inline=True,
        )
    return embed


class AvailabilityView(ViewErrorMixin, discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for i, day in enumerate(DAYS_SHORT):
            button = discord.ui.Button(
                label=day,
                style=discord.ButtonStyle.primary,
                custom_id=f"dispo:{i}",
                row=0 if i < 5 else 1,
            )
            button.callback = self._day_callback(i)
            self.add_item(button)

    def _day_callback(self, day: int):
        async def callback(interaction: discord.Interaction):
            db = interaction.client.db
            board = await db.get_availability(interaction.message.id)
            if board is None:
                await interaction.response.send_message(
                    "I can't find this availability board any more.", ephemeral=True
                )
                return
            await db.toggle_availability(board["message_id"], interaction.user.id, day)
            embed = build_availability_embed(
                board, await db.get_availability_marks(board["message_id"])
            )
            await interaction.response.edit_message(embed=embed)

        return callback


# ----- The cog -----


@app_commands.guild_only()
class Polls(commands.Cog):
    """Quick polls and the weekly availability board (with auto-posting)."""

    availability = app_commands.Group(
        name="availability", description="The weekly availability board", guild_only=True
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.weekly_loop.start()

    async def cog_unload(self):
        self.weekly_loop.cancel()

    @app_commands.command(name="vote", description="Start a quick poll with buttons")
    @app_commands.describe(
        question="The question to ask",
        option1="First option",
        option2="Second option",
        option3="Third option (optional)",
        option4="Fourth option (optional)",
        option5="Fifth option (optional)",
    )
    async def vote(
        self,
        interaction: discord.Interaction,
        question: app_commands.Range[str, 1, 200],
        option1: app_commands.Range[str, 1, 80],
        option2: app_commands.Range[str, 1, 80],
        option3: app_commands.Range[str, 1, 80] | None = None,
        option4: app_commands.Range[str, 1, 80] | None = None,
        option5: app_commands.Range[str, 1, 80] | None = None,
    ):
        options = [o.strip() for o in (option1, option2, option3, option4, option5) if o]
        poll = {
            "question": question,
            "options": json.dumps(options),
            "status": "open",
        }
        embed = build_poll_embed(poll, [])
        await interaction.response.send_message(embed=embed, view=VoteView(len(options)))
        message = await interaction.original_response()
        await self.bot.db.create_poll(
            message.id,
            interaction.guild_id,
            interaction.channel_id,
            interaction.user.id,
            question,
            json.dumps(options),
        )

    @availability.command(name="post", description="Post this week's availability board")
    async def availability_post(self, interaction: discord.Interaction):
        label = week_label(datetime.now(config.TIMEZONE))
        embed = build_availability_embed({"week_label": label}, [])
        await interaction.response.send_message(embed=embed, view=AvailabilityView())
        message = await interaction.original_response()
        await self.bot.db.create_availability(
            message.id, interaction.guild_id, interaction.channel_id, label
        )

    @availability.command(
        name="weekly",
        description="Automatically post the availability board here every week",
    )
    @app_commands.describe(action="Enable in this channel, or disable")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Enable in this channel", value="on"),
            app_commands.Choice(name="Disable", value="off"),
        ]
    )
    @app_commands.default_permissions(manage_messages=True)
    async def availability_weekly(
        self, interaction: discord.Interaction, action: app_commands.Choice[str]
    ):
        if action.value == "on":
            await self.bot.db.set_setting(
                interaction.guild_id, "dispo_channel_id", interaction.channel_id
            )
            await interaction.response.send_message(
                f"📅 Got it: I'll post the availability board here every "
                f"{DAYS[config.AVAILABILITY_DAY]} around {config.AVAILABILITY_HOUR}:00.",
                ephemeral=True,
            )
        else:
            await self.bot.db.set_setting(interaction.guild_id, "dispo_channel_id", None)
            await interaction.response.send_message(
                "Weekly availability posting disabled.", ephemeral=True
            )

    @tasks.loop(minutes=10)
    async def weekly_loop(self):
        """Posts the weekly board in the guilds that enabled it."""
        tz = config.TIMEZONE
        now = datetime.now(tz)
        monday = now.date() - timedelta(days=now.weekday())
        post_day = monday + timedelta(days=config.AVAILABILITY_DAY)
        post_time = datetime(
            post_day.year, post_day.month, post_day.day,
            config.AVAILABILITY_HOUR, tzinfo=tz,
        )
        if now < post_time:
            return

        for settings in await self.bot.db.guilds_with_availability():
            if settings["dispo_last_posted"] >= int(post_time.timestamp()):
                continue  # already posted this week
            # Marked before sending so a repeated error can never spam.
            await self.bot.db.set_setting(
                settings["guild_id"], "dispo_last_posted", int(now.timestamp())
            )
            try:
                channel = self.bot.get_channel(
                    settings["dispo_channel_id"]
                ) or await self.bot.fetch_channel(settings["dispo_channel_id"])
                label = week_label(now)
                embed = build_availability_embed({"week_label": label}, [])
                message = await channel.send(embed=embed, view=AvailabilityView())
                await self.bot.db.create_availability(
                    message.id, settings["guild_id"], channel.id, label
                )
            except discord.HTTPException:
                pass  # channel deleted or permissions revoked

    @weekly_loop.before_loop
    async def _wait_ready(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Polls(bot))
