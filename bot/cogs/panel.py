"""The quick-actions panel: buttons that open pop-up forms (modals), so
members can create an event or report an absence without typing a single
slash command.

A moderator posts the panel once with /panel (and pins it); its buttons are
persistent, like every other button of the bot.
"""

import discord
from discord import app_commands
from discord.ext import commands

from .. import config
from ..actions import publish_event, register_absence
from ..errors import ModalErrorMixin, ViewErrorMixin
from ..logic import COMPO_OPEN, COMPO_STANDARD
from ..utils.time_parse import ParseError, parse_when

# Lenient input for the "Type" field of the form (French synonyms included).
ACTIVITY_ALIASES = {
    "dungeon": "Dungeon", "donjon": "Dungeon",
    "raid": "Raid",
    "battleground": "Battleground", "bg": "Battleground",
    "pvp": "PvP",
    "rift": "Rift", "faille": "Rift",
    "abyss": "Abyss", "abysses": "Abyss", "aby": "Abyss",
    "other": "Other", "autre": "Other",
}

ACTIVITY_HELP = "Dungeon, Raid, Battleground (BG), PvP, Rift, Abyss or Other"


def parse_activity(text: str) -> str | None:
    return ACTIVITY_ALIASES.get(" ".join(text.strip().lower().split()))


def parse_comp(text: str) -> tuple[str, int] | None:
    """ "5" -> standard party of 5, "10" -> standard party of 10,
    "open"/"libre" -> open with 5 slots, another number -> open that size."""
    s = text.strip().lower()
    if s in ("", "5"):
        return (COMPO_STANDARD, 5)
    if s == "10":
        return (COMPO_STANDARD, 10)
    if s in ("open", "libre"):
        return (COMPO_OPEN, 5)
    if s.isdigit() and 2 <= int(s) <= 25:
        return (COMPO_OPEN, int(s))
    return None


class EventModal(ModalErrorMixin, discord.ui.Modal, title="New event"):
    event_title = discord.ui.TextInput(label="Title", max_length=100)
    activity = discord.ui.TextInput(
        label="Type", placeholder=ACTIVITY_HELP, max_length=20
    )
    comp = discord.ui.TextInput(
        label="Party size",
        placeholder="5 = 1 tank/1 heal/3 DPS · 10 = 2/2/6 · other number = open",
        required=False, max_length=10,
    )
    when = discord.ui.TextInput(
        label="When (optional)",
        placeholder="21:00 · 9pm · tomorrow 20:30 · 30/08 21:00",
        required=False, max_length=30,
    )
    description = discord.ui.TextInput(
        label="Description (optional)",
        style=discord.TextStyle.paragraph,
        required=False, max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        activity = parse_activity(self.activity.value)
        if activity is None:
            await interaction.response.send_message(
                f"Unknown event type `{self.activity.value}`. "
                f"Valid types: {ACTIVITY_HELP}.",
                ephemeral=True,
            )
            return

        parsed = parse_comp(self.comp.value)
        if parsed is None:
            await interaction.response.send_message(
                f"I didn't understand the party size `{self.comp.value}`. "
                "Use `5` (1 tank / 1 heal / 3 DPS), `10` (2/2/6), "
                "or another number between 2 and 25 for an open party.",
                ephemeral=True,
            )
            return
        comp_mode, size = parsed

        starts_at = None
        if self.when.value:
            try:
                starts_at = int(parse_when(self.when.value, config.TIMEZONE).timestamp())
            except ParseError as err:
                await interaction.response.send_message(str(err), ephemeral=True)
                return

        await publish_event(
            interaction,
            title=self.event_title.value.strip(),
            activity=activity,
            comp_mode=comp_mode,
            size=size,
            starts_at=starts_at,
            description=self.description.value.strip() or None,
        )


class AwayModal(ModalErrorMixin, discord.ui.Modal, title="Report an absence"):
    start = discord.ui.TextInput(
        label="From",
        placeholder="30/08 · tomorrow · 30/08 14:00",
        max_length=30,
    )
    until = discord.ui.TextInput(
        label="Until (optional, empty = same day)",
        placeholder="05/09 · 05/09 18:00",
        required=False, max_length=30,
    )
    reason = discord.ui.TextInput(
        label="Reason (optional)",
        placeholder="Holidays, exams, IRL...",
        required=False, max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await register_absence(
            interaction,
            self.start.value,
            self.until.value or None,
            self.reason.value.strip() or None,
        )


class PanelView(ViewErrorMixin, discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create an event", emoji="📅", style=discord.ButtonStyle.primary,
        custom_id="panel:event",
    )
    async def create_event(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(EventModal())

    @discord.ui.button(
        label="Report an absence", emoji="🏖️", style=discord.ButtonStyle.secondary,
        custom_id="panel:away",
    )
    async def report_absence(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(AwayModal())


@app_commands.guild_only()
class Panel(commands.Cog):
    """The /panel command that posts the quick-actions message."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="channels",
        description="Choose where events and absences are posted (moderators)",
    )
    @app_commands.describe(
        events="Channel for event calls (leave empty to keep the current setting)",
        absences="Channel for absence notices",
        reset="Post everything back in the channel the command is used in",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def channels(
        self,
        interaction: discord.Interaction,
        events: discord.TextChannel | None = None,
        absences: discord.TextChannel | None = None,
        reset: bool = False,
    ):
        db = self.bot.db
        if reset:
            await db.set_setting(interaction.guild_id, "event_channel_id", None)
            await db.set_setting(interaction.guild_id, "absence_channel_id", None)
            await interaction.response.send_message(
                "Reset: events and absences are now posted wherever the "
                "command or the button is used.",
                ephemeral=True,
            )
            return

        if events is not None:
            await db.set_setting(interaction.guild_id, "event_channel_id", events.id)
        if absences is not None:
            await db.set_setting(
                interaction.guild_id, "absence_channel_id", absences.id
            )

        settings = await db.get_settings(interaction.guild_id)

        def describe(setting: str) -> str:
            channel_id = settings[setting] if settings else None
            return f"<#{channel_id}>" if channel_id else "*where the command is used*"

        await interaction.response.send_message(
            "📍 Current destinations:\n"
            f"• Events → {describe('event_channel_id')}\n"
            f"• Absences → {describe('absence_channel_id')}\n\n"
            "Set them with `/channels events: #… absences: #…`, or clear them "
            "with `/channels reset: True`.",
            ephemeral=True,
        )

    @app_commands.command(
        name="panel",
        description="Post the quick-actions panel in this channel (moderators)",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def panel(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        event_channel = settings["event_channel_id"] if settings else None
        absence_channel = settings["absence_channel_id"] if settings else None

        where = ""
        if event_channel or absence_channel:
            targets = []
            if event_channel:
                targets.append(f"events go to <#{event_channel}>")
            if absence_channel:
                targets.append(f"absences go to <#{absence_channel}>")
            where = "\n\n*" + ", ".join(targets) + ".*"

        embed = discord.Embed(
            title="⚡ Kisk — quick actions",
            description=(
                "No commands to remember — just click a button and fill in "
                "the form:\n\n"
                "📅 **Create an event** — dungeon, raid, battleground, PvP...\n"
                "🏖️ **Report an absence** — let the legion know when you're away\n\n"
                "Joining an event stays one click on its "
                f"{config.EMOJI_TANK} Tank / {config.EMOJI_HEAL} Heal / "
                f"{config.EMOJI_DPS} DPS buttons." + where
            ),
            colour=discord.Colour.blurple(),
        )
        await interaction.response.send_message(embed=embed, view=PanelView())
        if not (event_channel and absence_channel):
            await interaction.followup.send(
                "💡 Pin this message, then use `/channels events: #… "
                "absences: #…` so the results are posted in their own "
                "channels instead of pushing the panel out of sight.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Panel(bot))
