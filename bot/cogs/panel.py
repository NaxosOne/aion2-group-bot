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

from .. import config, i18n
from ..actions import publish_event, register_absence
from ..branding import BANNER_URL, brand
from ..embeds import build_event_embed
from ..errors import ModalErrorMixin, ViewErrorMixin
from ..logic import COMPO_OPEN, COMPO_STANDARD
from ..utils.permissions import member_is_admin
from ..utils.time_parse import ParseError, parse_when
from ..views import SignupView

# The event types offered by the dropdown, in the order they appear.
ACTIVITIES = ("Dungeon", "Raid", "Battleground", "PvP", "Rift", "Abyss", "Other")

# Party setups: value -> (composition mode, size). The human-readable label and
# description live in the locale catalogs as panel.setup_label_<value> /
# panel.setup_desc_<value>.
SETUPS = {
    "standard5": (COMPO_STANDARD, 5),
    "standard10": (COMPO_STANDARD, 10),
    "open5": (COMPO_OPEN, 5),
    "open10": (COMPO_OPEN, 10),
    "open25": (COMPO_OPEN, 25),
}
DEFAULT_SETUP = "standard5"


class ActivitySelect(discord.ui.Select):
    """Dropdown of event types: no typing, no typos, no invented types."""

    def __init__(self, chosen: str | None, lang: str):
        super().__init__(
            placeholder=i18n.t("panel.activity_placeholder", lang),
            row=0,
            options=self._options(chosen),
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

    def __init__(self, chosen: str, lang: str):
        super().__init__(
            placeholder=i18n.t("panel.setup_placeholder", lang),
            row=1,
            options=self._options(chosen, lang),
        )

    @staticmethod
    def _options(chosen: str, lang: str) -> list[discord.SelectOption]:
        return [
            discord.SelectOption(
                label=i18n.t(f"panel.setup_label_{value}", lang),
                description=i18n.t(f"panel.setup_desc_{value}", lang),
                value=value,
                default=(value == chosen),
            )
            for value in SETUPS
        ]

    async def callback(self, interaction: discord.Interaction):
        self.view.setup = self.values[0]
        self.options = self._options(self.values[0], self.view.lang)
        await interaction.response.edit_message(
            embed=self.view.summary(), view=self.view
        )


class EventSetupView(ViewErrorMixin, discord.ui.View):
    """The private step-one message: pick the type and the setup.

    Short-lived and only visible to the member who clicked, so its state
    lives on the instance — nothing to persist across restarts.
    """

    def __init__(self, lang: str):
        super().__init__(timeout=600)
        self.lang = lang
        self.activity: str | None = None
        self.setup: str = DEFAULT_SETUP
        self.add_item(ActivitySelect(None, lang))
        self.add_item(SetupSelect(DEFAULT_SETUP, lang))
        # Localize the decorator-defined Continue button per server language.
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label is not None:
                child.label = i18n.t("panel.continue", lang)

    def summary(self) -> discord.Embed:
        label = i18n.t(f"panel.setup_label_{self.setup}", self.lang)
        description = i18n.t(f"panel.setup_desc_{self.setup}", self.lang)
        if self.activity:
            type_line = f"{config.EMOJI_ACTIVITY[self.activity]} **{self.activity}**"
        else:
            type_line = i18n.t("onboard.not_set", self.lang)
        return discord.Embed(
            title=i18n.t("panel.event_step1_title", self.lang),
            description=i18n.t(
                "panel.event_step1_body",
                self.lang,
                type_line=type_line,
                label=label,
                description=description,
            ),
            colour=discord.Colour.blurple(),
        )

    @discord.ui.button(
        label="Continue", emoji="➡️", style=discord.ButtonStyle.success, row=2
    )
    async def proceed(self, interaction: discord.Interaction, _):
        if self.activity is None:
            await interaction.response.send_message(
                i18n.t("panel.pick_type_first", self.lang),
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(
            EventDetailsModal(self.activity, self.setup, self.lang)
        )


class EventDetailsModal(ModalErrorMixin, discord.ui.Modal):
    """Step two: only what genuinely needs typing."""

    def __init__(self, activity: str, setup: str, lang: str):
        super().__init__(
            title=i18n.t("panel.modal_new_event", lang, activity=activity)[:45]
        )
        self.activity = activity
        self.setup = setup
        self.lang = lang

        self.event_title = discord.ui.TextInput(
            label=i18n.t("panel.field_title", lang), max_length=100
        )
        self.add_item(self.event_title)

        # "Other" is the one type members can name themselves.
        self.custom_type = None
        if activity == "Other":
            self.custom_type = discord.ui.TextInput(
                label=i18n.t("panel.field_type_name", lang),
                placeholder=i18n.t("panel.field_type_name_ph", lang),
                required=False,
                max_length=30,
            )
            self.add_item(self.custom_type)

        self.when = discord.ui.TextInput(
            label=i18n.t("panel.field_when", lang),
            placeholder=i18n.t("panel.field_when_ph", lang),
            required=False,
            max_length=30,
        )
        self.add_item(self.when)

        self.description = discord.ui.TextInput(
            label=i18n.t("panel.field_description", lang),
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500,
        )
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        starts_at = None
        if self.when.value:
            try:
                starts_at = int(
                    parse_when(
                        self.when.value, config.TIMEZONE, lang=self.lang
                    ).timestamp()
                )
            except ParseError as err:
                await interaction.response.send_message(str(err), ephemeral=True)
                return

        activity = self.activity
        if self.custom_type is not None and self.custom_type.value.strip():
            activity = self.custom_type.value.strip()

        comp_mode, size = SETUPS[self.setup]
        await publish_event(
            interaction,
            title=self.event_title.value.strip(),
            activity=activity,
            comp_mode=comp_mode,
            size=size,
            starts_at=starts_at,
            description=self.description.value.strip() or None,
        )


class AwayModal(ModalErrorMixin, discord.ui.Modal):
    def __init__(self, lang: str):
        super().__init__(title=i18n.t("panel.modal_away_title", lang))

        self.start = discord.ui.TextInput(
            label=i18n.t("panel.field_from", lang),
            placeholder=i18n.t("panel.field_from_ph", lang),
            max_length=30,
        )
        self.add_item(self.start)

        self.until = discord.ui.TextInput(
            label=i18n.t("panel.field_until", lang),
            placeholder=i18n.t("panel.field_until_ph", lang),
            required=False,
            max_length=30,
        )
        self.add_item(self.until)

        self.reason = discord.ui.TextInput(
            label=i18n.t("panel.field_reason", lang),
            placeholder=i18n.t("panel.field_reason_ph", lang),
            required=False,
            max_length=100,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await register_absence(
            interaction,
            self.start.value,
            self.until.value or None,
            self.reason.value.strip() or None,
        )


class PanelView(ViewErrorMixin, discord.ui.View):
    _LABELS = {
        "panel:event": "panel.btn_create_event",
        "panel:away": "panel.btn_report_absence",
    }

    def __init__(self, lang: str = "en"):
        super().__init__(timeout=None)
        for child in self.children:
            key = self._LABELS.get(getattr(child, "custom_id", None))
            if key is not None:
                child.label = i18n.t(key, lang)

    @discord.ui.button(
        label="Create an event",
        emoji="📅",
        style=discord.ButtonStyle.primary,
        custom_id="panel:event",
    )
    async def create_event(self, interaction: discord.Interaction, _):
        lang = await i18n.resolve_lang(interaction.client.db, interaction.guild)
        view = EventSetupView(lang)
        await interaction.response.send_message(
            embed=view.summary(), view=view, ephemeral=True
        )

    @discord.ui.button(
        label="Report an absence",
        emoji="🏖️",
        style=discord.ButtonStyle.secondary,
        custom_id="panel:away",
    )
    async def report_absence(self, interaction: discord.Interaction, _):
        lang = await i18n.resolve_lang(interaction.client.db, interaction.guild)
        await interaction.response.send_modal(AwayModal(lang))


@app_commands.guild_only()
def _panel_embed(settings, lang: str) -> discord.Embed:
    """The quick-actions panel embed, with a note of the configured channels."""
    event_channel = settings["event_channel_id"] if settings else None
    absence_channel = settings["absence_channel_id"] if settings else None
    where = ""
    if event_channel or absence_channel:
        targets = []
        if event_channel:
            targets.append(
                i18n.t("panel.target_events", lang, channel=f"<#{event_channel}>")
            )
        if absence_channel:
            targets.append(
                i18n.t("panel.target_absences", lang, channel=f"<#{absence_channel}>")
            )
        where = "\n\n*" + ", ".join(targets) + ".*"
    embed = discord.Embed(
        title=i18n.t("panel.title", lang),
        description=i18n.t(
            "panel.body",
            lang,
            tank=config.EMOJI_TANK,
            heal=config.EMOJI_HEAL,
            dps=config.EMOJI_DPS,
            where=where,
        ),
        colour=discord.Colour.blurple(),
    )
    brand(embed)
    embed.set_image(url=BANNER_URL)
    return embed


class Panel(commands.Cog):
    """The /panel command that posts the quick-actions message."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="channels",
        description="Choose where events, absences and RSVPs are posted (moderators)",
    )
    @app_commands.describe(
        events="Channel for event calls (leave empty to keep the current setting)",
        absences="Channel for absence notices",
        rsvp="Channel for the 'are you coming?' RSVP prompts",
        voice="Category for temporary event voice channels (enables them)",
        reset="Post everything back in the channel the command is used in",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def channels(
        self,
        interaction: discord.Interaction,
        events: discord.TextChannel | None = None,
        absences: discord.TextChannel | None = None,
        rsvp: discord.TextChannel | None = None,
        voice: discord.CategoryChannel | None = None,
        reset: bool = False,
    ):
        db = self.bot.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        if reset:
            await db.set_setting(interaction.guild_id, "event_channel_id", None)
            await db.set_setting(interaction.guild_id, "absence_channel_id", None)
            await db.set_setting(interaction.guild_id, "rsvp_channel_id", None)
            await db.set_setting(interaction.guild_id, "voice_category_id", None)
            await interaction.response.send_message(
                i18n.t("channels.reset_done", lang),
                ephemeral=True,
            )
            return

        if events is not None:
            await db.set_setting(interaction.guild_id, "event_channel_id", events.id)
        if absences is not None:
            await db.set_setting(
                interaction.guild_id, "absence_channel_id", absences.id
            )
        if rsvp is not None:
            await db.set_setting(interaction.guild_id, "rsvp_channel_id", rsvp.id)
        if voice is not None:
            await db.set_setting(interaction.guild_id, "voice_category_id", voice.id)

        settings = await db.get_settings(interaction.guild_id)

        def describe(setting: str) -> str:
            channel_id = settings[setting] if settings else None
            return (
                f"<#{channel_id}>"
                if channel_id
                else i18n.t("channels.where_used", lang)
            )

        message = i18n.t(
            "channels.destinations",
            lang,
            events=describe("event_channel_id"),
            absences=describe("absence_channel_id"),
            rsvp=describe("rsvp_channel_id"),
        )
        voice_category = settings["voice_category_id"] if settings else None
        if voice_category:
            message += "\n" + i18n.t(
                "channels.voice_on", lang, category=f"<#{voice_category}>"
            )
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(
        name="panel",
        description=(
            "Post the quick-actions panel here, or refresh the existing "
            "one (moderators)"
        ),
    )
    @app_commands.default_permissions(manage_messages=True)
    async def panel(self, interaction: discord.Interaction):
        db = self.bot.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        settings = await db.get_settings(interaction.guild_id)
        embed = _panel_embed(settings, lang)

        # Refresh the remembered panel in place so re-running /panel after an
        # update never leaves a stale duplicate behind.
        stored = await db.get_panel(interaction.guild_id)
        if stored is not None:
            channel_id, message_id = stored
            channel = self.bot.get_channel(channel_id)
            if channel is not None:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed, view=PanelView(lang))
                    await interaction.response.send_message(
                        i18n.t("panel.refreshed", lang, link=message.jump_url),
                        ephemeral=True,
                    )
                    return
                except discord.NotFound:
                    pass  # deleted: fall through and post a fresh one
                except discord.Forbidden:
                    await interaction.response.send_message(
                        i18n.t("panel.refresh_forbidden", lang), ephemeral=True
                    )
                    return

        # Post a new panel in the current channel and remember where it lives.
        message = await interaction.channel.send(embed=embed, view=PanelView(lang))
        await db.set_panel(interaction.guild_id, interaction.channel_id, message.id)
        configured = (
            settings and settings["event_channel_id"] and settings["absence_channel_id"]
        )
        note = "" if configured else "\n" + i18n.t("panel.pin_tip", lang)
        await interaction.response.send_message(
            i18n.t("panel.posted", lang, link=message.jump_url) + note,
            ephemeral=True,
        )

    @app_commands.command(
        name="redeploy",
        description=(
            "Refresh the panel and re-render open events with the latest "
            "buttons (admins)"
        ),
    )
    @app_commands.default_permissions(manage_guild=True)
    async def redeploy(self, interaction: discord.Interaction):
        db = self.bot.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        if not await member_is_admin(db, interaction.user):
            await interaction.response.send_message(
                i18n.t("redeploy.admin_only", lang), ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        # Re-render every open event so already-posted messages gain the
        # current buttons and embed.
        events_done = 0
        for event in await db.get_open_events(interaction.guild_id):
            channel = self.bot.get_channel(event["channel_id"])
            if channel is None:
                continue
            try:
                signups = await db.get_signups(event["message_id"])
                classes = await db.get_main_classes(
                    event["guild_id"], [s["user_id"] for s in signups]
                )
                embed = build_event_embed(event, signups, classes, lang)
                await channel.get_partial_message(event["message_id"]).edit(
                    embed=embed, view=SignupView(lang)
                )
                events_done += 1
            except discord.HTTPException:
                continue

        # Refresh the panel in place when we know where it is.
        panel_done = False
        stored = await db.get_panel(interaction.guild_id)
        if stored is not None:
            channel_id, message_id = stored
            channel = self.bot.get_channel(channel_id)
            if channel is not None:
                settings = await db.get_settings(interaction.guild_id)
                try:
                    await channel.get_partial_message(message_id).edit(
                        embed=_panel_embed(settings, lang), view=PanelView(lang)
                    )
                    panel_done = True
                except discord.HTTPException:
                    pass

        panel_state = i18n.t(
            "redeploy.panel_yes" if panel_done else "redeploy.panel_no", lang
        )
        await interaction.followup.send(
            i18n.t("redeploy.done", lang, events=events_done, panel=panel_state),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Panel(bot))
