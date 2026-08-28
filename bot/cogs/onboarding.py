"""Profile onboarding: when a member is validated (gains the configured
"member" role), Kisk DMs them a button that opens a guided form to register
their main character — class, role and name — without typing any command.

The DM button is a persistent DynamicItem: it lives in a direct message (no
guild context), so the guild it onboards for travels in its custom_id and is
parsed back when the member clicks, even after a bot restart.
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from .. import config, i18n
from ..errors import ModalErrorMixin, ViewErrorMixin
from ..logic import MAX_CHARACTERS
from ..utils.onboarding import onboard_custom_id, role_just_added, should_onboard
from .profiles import AION_CLASSES

log = logging.getLogger(__name__)

# Role options offered in the onboarding form: (stored value, label, emoji).
ROLE_OPTIONS = (
    ("tank", "Tank", config.EMOJI_TANK),
    ("heal", "Heal", config.EMOJI_HEAL),
    ("dps", "DPS", config.EMOJI_DPS),
)
ROLE_LABELS = {value: label for value, label, _ in ROLE_OPTIONS}


class ClassSelect(discord.ui.Select):
    """Dropdown of Aion 2 classes: no typing, no typos, no invented classes."""

    def __init__(self, chosen: str | None, lang: str):
        super().__init__(
            placeholder=i18n.t("onboard.class_placeholder", lang),
            row=0, options=self._options(chosen),
        )

    @staticmethod
    def _options(chosen: str | None) -> list[discord.SelectOption]:
        return [
            discord.SelectOption(
                label=name, emoji=config.CLASS_EMOJI[name], default=(name == chosen)
            )
            for name in AION_CLASSES
        ]

    async def callback(self, interaction: discord.Interaction):
        self.view.char_class = self.values[0]
        self.options = self._options(self.values[0])
        await interaction.response.edit_message(embed=self.view.summary(), view=self.view)


class RoleSelect(discord.ui.Select):
    """Dropdown of the three party roles."""

    def __init__(self, chosen: str | None, lang: str):
        super().__init__(
            placeholder=i18n.t("onboard.role_placeholder", lang),
            row=1, options=self._options(chosen),
        )

    @staticmethod
    def _options(chosen: str | None) -> list[discord.SelectOption]:
        return [
            discord.SelectOption(
                label=label, value=value, emoji=emoji, default=(value == chosen)
            )
            for value, label, emoji in ROLE_OPTIONS
        ]

    async def callback(self, interaction: discord.Interaction):
        self.view.role = self.values[0]
        self.options = self._options(self.values[0])
        await interaction.response.edit_message(embed=self.view.summary(), view=self.view)


class ProfileSetupView(ViewErrorMixin, discord.ui.View):
    """The DM step-one message: pick class and role, then Continue to name it.

    Short-lived (only the member sees their own DM), so its state lives on the
    instance — nothing to persist across restarts.
    """

    def __init__(
        self, guild_id: int, guild_name: str, ephemeral: bool,
        lang: str, slot: str = "main",
    ):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.guild_name = guild_name
        # Ephemeral in a guild channel (the DM fallback), plain in a real DM.
        self.ephemeral = ephemeral
        self.lang = lang
        self.slot = slot  # 'main' or 'alt'
        self.char_class: str | None = None
        self.role: str | None = None
        self.add_item(ClassSelect(None, lang))
        self.add_item(RoleSelect(None, lang))
        # Localize the decorator-defined Continue button per server language.
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.label = i18n.t("onboard.continue", lang)

    def summary(self) -> discord.Embed:
        not_set = i18n.t("onboard.not_set", self.lang)
        if self.char_class:
            class_line = f"{config.CLASS_EMOJI[self.char_class]} **{self.char_class}**"
        else:
            class_line = not_set
        role_line = f"**{ROLE_LABELS[self.role]}**" if self.role else not_set
        title = f"{i18n.t(f'onboard.setup_title_{self.slot}', self.lang)} — {self.guild_name}"
        return discord.Embed(
            title=title,
            description=i18n.t(
                "onboard.summary_body", self.lang,
                class_line=class_line, role_line=role_line,
            ),
            colour=discord.Colour.blurple(),
        )

    @discord.ui.button(
        label="Continue", emoji="➡️",
        style=discord.ButtonStyle.success, row=2,
    )
    async def proceed(self, interaction: discord.Interaction, _):
        if self.char_class is None or self.role is None:
            await interaction.response.send_message(
                i18n.t("onboard.pick_first", self.lang),
                ephemeral=self.ephemeral,
            )
            return
        await interaction.response.send_modal(
            ProfileNameModal(
                self.guild_id, self.guild_name, self.char_class,
                self.role, self.ephemeral, self.lang, self.slot,
            )
        )


class ProfileNameModal(ModalErrorMixin, discord.ui.Modal):
    """Step two: the one thing that genuinely needs typing — the name."""

    def __init__(
        self, guild_id: int, guild_name: str, char_class: str,
        role: str, ephemeral: bool, lang: str, slot: str,
    ):
        super().__init__(title=i18n.t(f"onboard.modal_title_{slot}", lang))
        self.guild_id = guild_id
        self.guild_name = guild_name
        self.char_class = char_class
        self.role = role
        self.ephemeral = ephemeral
        self.lang = lang
        self.slot = slot
        self.char_name = discord.ui.TextInput(
            label=i18n.t("onboard.name_label", lang),
            max_length=32, placeholder=i18n.t("onboard.name_placeholder", lang),
        )
        self.add_item(self.char_name)

    async def on_submit(self, interaction: discord.Interaction):
        name = self.char_name.value.strip()
        db = interaction.client.db
        characters = await db.get_profiles(self.guild_id, interaction.user.id)
        known = {row["char_name"].lower() for row in characters}
        if name.lower() not in known and len(characters) >= MAX_CHARACTERS:
            await interaction.response.send_message(
                i18n.t("onboard.cap_reached", self.lang, max=MAX_CHARACTERS),
                ephemeral=self.ephemeral,
            )
            return

        await db.add_character(
            self.guild_id, interaction.user.id, name, self.char_class, self.role
        )
        emoji = config.CLASS_EMOJI.get(self.char_class, "")
        detail = f"**{name}** — {emoji} {self.char_class}, {ROLE_LABELS[self.role]}"
        if characters:
            text = i18n.t("onboard.added_more", self.lang, detail=detail)
        else:
            text = i18n.t("onboard.added_main", self.lang, detail=detail)
        # Keep offering the button until they hit the cap; /profile set adds
        # more later just as well.
        view = (
            AddAltView(self.guild_id, self.guild_name, self.ephemeral, self.lang)
            if len(characters) + 1 < MAX_CHARACTERS
            else discord.utils.MISSING
        )
        await interaction.response.send_message(
            text, view=view, ephemeral=self.ephemeral
        )


class AddAltView(ViewErrorMixin, discord.ui.View):
    """A single button, shown after each character, to register one more."""

    def __init__(self, guild_id: int, guild_name: str, ephemeral: bool, lang: str):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.guild_name = guild_name
        self.ephemeral = ephemeral
        self.lang = lang
        # Localize the decorator-defined "add a character" button.
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.label = i18n.t("onboard.add_char", lang)

    @discord.ui.button(
        label="Add a character", emoji="➕",
        style=discord.ButtonStyle.secondary,
    )
    async def add_alt(self, interaction: discord.Interaction, _):
        view = ProfileSetupView(
            self.guild_id, self.guild_name, self.ephemeral, self.lang, slot="alt"
        )
        await interaction.response.send_message(
            embed=view.summary(), view=view, ephemeral=self.ephemeral
        )


class OnboardButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"kisk:onboard:(?P<guild_id>\d+)",
):
    """Persistent DM button that opens the onboarding form for a given guild."""

    def __init__(self, guild_id: int, lang: str = i18n.DEFAULT):
        self.guild_id = guild_id
        super().__init__(
            discord.ui.Button(
                label=i18n.t("onboard.configure_button", lang),
                emoji="📝",
                style=discord.ButtonStyle.primary,
                custom_id=onboard_custom_id(guild_id),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match, /):
        # Reconstructed on click; the label shown is the one baked into the
        # already-sent message, so the default language here is irrelevant.
        return cls(int(match["guild_id"]))

    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.db
        guild = interaction.client.get_guild(self.guild_id)
        lang = await i18n.resolve_lang(db, guild)
        # In a real DM the message is already private; in the channel fallback
        # keep the form ephemeral so it stays private to the member who clicks.
        ephemeral = interaction.guild is not None
        if await db.has_main_profile(self.guild_id, interaction.user.id):
            await interaction.response.send_message(
                i18n.t("onboard.already_setup", lang),
                ephemeral=ephemeral,
            )
            return
        guild_name = guild.name if guild else i18n.t("onboard.your_legion", lang)
        view = ProfileSetupView(self.guild_id, guild_name, ephemeral, lang)
        await interaction.response.send_message(
            embed=view.summary(), view=view, ephemeral=ephemeral
        )


@app_commands.guild_only()
class Onboarding(commands.GroupCog, name="onboard"):
    """Configure and drive the profile-onboarding flow."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="role",
        description="Set the role that means 'validated member' (triggers onboarding)",
    )
    @app_commands.describe(role="The role newly-validated members receive")
    @app_commands.default_permissions(manage_guild=True)
    async def set_role(self, interaction: discord.Interaction, role: discord.Role):
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        await self.bot.db.set_setting(
            interaction.guild_id, "member_role_id", role.id
        )
        await interaction.response.send_message(
            i18n.t("onboard.role_set_confirm", lang, role=role.name),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Fires on every member change (nickname, status...); skip the DB hit
        # unless the roles actually changed.
        if before.roles == after.roles:
            return
        settings = await self.bot.db.get_settings(after.guild.id)
        role_id = settings["member_role_id"] if settings else None
        if not role_id:
            return
        before_ids = {r.id for r in before.roles}
        after_ids = {r.id for r in after.roles}
        if not role_just_added(role_id, before_ids, after_ids):
            return
        has_profile = await self.bot.db.has_main_profile(after.guild.id, after.id)
        if not should_onboard(
            member_role_added=True, has_main_profile=has_profile, is_bot=after.bot
        ):
            return
        await self._onboard(after, settings)

    def _onboard_view(self, guild_id: int, lang: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(OnboardButton(guild_id, lang))
        return view

    @staticmethod
    def _welcome_embed(guild: discord.Guild, lang: str) -> discord.Embed:
        return discord.Embed(
            title=i18n.t("onboard.welcome_title", lang, guild=guild.name),
            description=i18n.t("onboard.welcome_body", lang),
            colour=discord.Colour.blurple(),
        )

    async def _onboard(self, member: discord.Member, settings):
        """DM the member; if their DMs are closed, fall back to a channel."""
        lang = await i18n.resolve_lang(self.bot.db, member.guild)
        try:
            await member.send(
                embed=self._welcome_embed(member.guild, lang),
                view=self._onboard_view(member.guild.id, lang),
            )
            return
        except discord.Forbidden:
            log.info("DMs closed for %s; trying a channel fallback", member.id)
        await self._onboard_in_channel(member, settings, lang)

    async def _onboard_in_channel(self, member: discord.Member, settings, lang: str):
        channel = self._fallback_channel(member.guild, settings)
        if channel is None:
            log.info("No fallback channel available to onboard %s", member.id)
            return
        embed = self._welcome_embed(member.guild, lang)
        embed.description = (
            i18n.t("onboard.dm_fallback_prefix", lang)
            + "\n\n"
            + (embed.description or "")
        )
        try:
            await channel.send(
                content=member.mention,
                embed=embed,
                view=self._onboard_view(member.guild.id, lang),
                allowed_mentions=discord.AllowedMentions(users=[member]),
            )
        except discord.HTTPException:
            log.warning("Could not post onboarding fallback for %s", member.id)

    @staticmethod
    def _fallback_channel(guild: discord.Guild, settings):
        """The welcome channel if configured, else the guild's system channel."""
        channel_id = settings["welcome_channel_id"] if settings else None
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel is not None:
                return channel
        return guild.system_channel


async def setup(bot: commands.Bot):
    await bot.add_cog(Onboarding(bot))
