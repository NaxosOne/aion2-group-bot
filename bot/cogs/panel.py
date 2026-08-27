"""The quick-actions panel: buttons that open menus and pop-up forms, so
members can create an event or report an absence without typing a single
slash command.

A moderator posts the panel once with /panel (and pins it); its buttons are
persistent, like every other button of the bot.

Creating an event takes two steps, because Discord forms (modals) only
accept text fields — dropdowns have to live in a message:
  1. the button opens a private message with two dropdowns (type, party
     setup) and a Continue button;
  2. Continue opens the form for what genuinely needs typing (title, time,
     description — plus a free-text name when the type is "Other").
"""

import discord
from discord import app_commands
from discord.ext import commands

from .. import config
from ..actions import publish_event, register_absence
from ..errors import ModalErrorMixin, ViewErrorMixin
from ..logic import COMPO_OPEN, COMPO_STANDARD
from ..utils.time_parse import ParseError, parse_when

# The event types offered by the dropdown, in the order they appear.
ACTIVITIES = ("Dungeon", "Raid", "Battleground", "PvP", "Rift", "Abyss", "Other")

# Party setups: value -> (label, description, composition mode, size).
SETUPS = {
    "standard5": ("Party of 5", "1 tank / 1 heal / 3 DPS", COMPO_STANDARD, 5),
    "standard10": ("Party of 10", "2 tanks / 2 heals / 6 DPS", COMPO_STANDARD, 10),
    "open5": ("Open — 5 slots", "No role limits", COMPO_OPEN, 5),
    "open10": ("Open — 10 slots", "No role limits", COMPO_OPEN, 10),
    "open25": ("Open — 25 slots", "No role limits, for sieges", COMPO_OPEN, 25),
}
DEFAULT_SETUP = "standard5"


class ActivitySelect(discord.ui.Select):
    """Dropdown of event types: no typing, no typos, no invented types."""

    def __init__(self, chosen: str | None):
        super().__init__(
            placeholder="Event type…", row=0, options=self._options(chosen)
        )

    @staticmethod
    def _options(chosen: str | None) -> list[discord.SelectOption]:
        return [
            discord.SelectOption(
                label=name,
                emoji=config.EMOJI_ACTIVITY[name],
                default=(name == chosen),
            )
            for name in ACTIVITIES
        ]

    async def callback(self, interaction: discord.Interaction):
        self.view.activity = self.values[0]
        self.options = self._options(self.values[0])
        await interaction.response.edit_message(
            embed=self.view.summary(), view=self.view
        )


class SetupSelect(discord.ui.Select):
    """Dropdown of party setups, so sizes stay ones the bot can fill."""

    def __init__(self, chosen: str):
        super().__init__(
            placeholder="Party setup…", row=1, options=self._options(chosen)
        )

    @staticmethod
    def _options(chosen: str) -> list[discord.SelectOption]:
        return [
            discord.SelectOption(
                label=label, description=description, value=value,
                default=(value == chosen),
            )
            for value, (label, description, _, _) in SETUPS.items()
        ]

    async def callback(self, interaction: discord.Interaction):
        self.view.setup = self.values[0]
        self.options = self._options(self.values[0])
        await interaction.response.edit_message(
            embed=self.view.summary(), view=self.view
        )


class EventSetupView(ViewErrorMixin, discord.ui.View):
    """The private step-one message: pick the type and the setup.

    Short-lived and only visible to the member who clicked, so its state
    lives on the instance — nothing to persist across restarts.
    """

    def __init__(self):
        super().__init__(timeout=600)
        self.activity: str | None = None
        self.setup: str = DEFAULT_SETUP
        self.add_item(ActivitySelect(None))
        self.add_item(SetupSelect(DEFAULT_SETUP))

    def summary(self) -> discord.Embed:
        label, description, _, _ = SETUPS[self.setup]
        if self.activity:
            type_line = f"{config.EMOJI_ACTIVITY[self.activity]} **{self.activity}**"
        else:
            type_line = "*not chosen yet*"
        return discord.Embed(
            title="📅 New event — step 1 of 2",
            description=(
                f"**Type:** {type_line}\n"
                f"**Setup:** {label} *({description})*\n\n"
                "Pick from the menus, then hit **Continue** to name it."
            ),
            colour=discord.Colour.blurple(),
        )

    @discord.ui.button(
        label="Continue", emoji="➡️", style=discord.ButtonStyle.success, row=2
    )
    async def proceed(self, interaction: discord.Interaction, _):
        if self.activity is None:
            await interaction.response.send_message(
                "Pick an event type in the first menu, then hit Continue.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(
            EventDetailsModal(self.activity, self.setup)
        )


class EventDetailsModal(ModalErrorMixin, discord.ui.Modal):
    """Step two: only what genuinely needs typing."""

    def __init__(self, activity: str, setup: str):
        super().__init__(title=f"New {activity} event"[:45])
        self.activity = activity
        self.setup = setup

        self.event_title = discord.ui.TextInput(label="Title", max_length=100)
        self.add_item(self.event_title)

        # "Other" is the one type members can name themselves.
        self.custom_type = None
        if activity == "Other":
            self.custom_type = discord.ui.TextInput(
                label="Type name (optional)",
                placeholder="Guild meeting, screenshot night...",
                required=False, max_length=30,
            )
            self.add_item(self.custom_type)

        self.when = discord.ui.TextInput(
            label="When (optional)",
            placeholder="21:00 · 9pm · tomorrow 20:30 · 30/08 21:00",
            required=False, max_length=30,
        )
        self.add_item(self.when)

        self.description = discord.ui.TextInput(
            label="Description (optional)",
            style=discord.TextStyle.paragraph,
            required=False, max_length=500,
        )
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        starts_at = None
        if self.when.value:
            try:
                starts_at = int(parse_when(self.when.value, config.TIMEZONE).timestamp())
            except ParseError as err:
                await interaction.response.send_message(str(err), ephemeral=True)
                return

        activity = self.activity
        if self.custom_type is not None and self.custom_type.value.strip():
            activity = self.custom_type.value.strip()

        _, _, comp_mode, size = SETUPS[self.setup]
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
        view = EventSetupView()
        await interaction.response.send_message(
            embed=view.summary(), view=view, ephemeral=True
        )

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
                "No commands to remember — click a button, pick from the "
                "menus, fill in the blanks:\n\n"
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
