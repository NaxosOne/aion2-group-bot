"""Recruitment: newcomers are DM'd a "Postuler" button on join; they fill a
form; officers review each application in a dedicated per-candidate channel and
Accept (grants the member role -> onboarding fires) or Reject (optional reason,
DM'd to the candidate). See docs/plans/2026-09-01-recruitment-design.md."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from .. import config, i18n
from ..branding import brand
from ..errors import ModalErrorMixin, ViewErrorMixin
from ..utils.permissions import member_is_admin
from ..utils.recruitment import channel_slug, overwrite_spec, recruitment_enabled
from .onboarding import ROLE_LABELS, ClassSelect, RoleSelect

log = logging.getLogger(__name__)


# ----- Candidate side: apply button + form -----


class ApplyButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"kisk:apply:(?P<guild_id>\d+)",
):
    """Persistent DM button that opens the application form for a guild."""

    def __init__(self, guild_id: int, lang: str = i18n.DEFAULT):
        self.guild_id = guild_id
        super().__init__(
            discord.ui.Button(
                label=i18n.t("recruit.apply_button", lang),
                emoji="📝",
                style=discord.ButtonStyle.primary,
                custom_id=f"kisk:apply:{guild_id}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match, /):
        return cls(int(match["guild_id"]))

    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.db
        guild = interaction.client.get_guild(self.guild_id)
        lang = await i18n.resolve_lang(db, guild)
        ephemeral = interaction.guild is not None
        settings = await db.get_settings(self.guild_id)
        if not recruitment_enabled(settings):
            await interaction.response.send_message(
                i18n.t("recruit.no_channel", lang), ephemeral=ephemeral
            )
            return
        if await db.get_pending_application(self.guild_id, interaction.user.id):
            await interaction.response.send_message(
                i18n.t("recruit.already_pending", lang), ephemeral=ephemeral
            )
            return
        guild_name = guild.name if guild else i18n.t("onboard.your_legion", lang)
        view = ApplicationSetupView(self.guild_id, guild_name, ephemeral, lang)
        await interaction.response.send_message(
            embed=view.summary(), view=view, ephemeral=ephemeral
        )


class ApplicationSetupView(ViewErrorMixin, discord.ui.View):
    """Pick class + role (reused selects), then Continue -> the text modal."""

    def __init__(self, guild_id, guild_name, ephemeral, lang):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.guild_name = guild_name
        self.ephemeral = ephemeral
        self.lang = lang
        self.char_class = None
        self.role = None
        self.add_item(ClassSelect(None, lang))
        self.add_item(RoleSelect(None, lang))
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.label = i18n.t("recruit.continue", lang)

    def summary(self) -> discord.Embed:
        not_set = i18n.t("onboard.not_set", self.lang)
        if self.char_class:
            cls = f"{config.CLASS_EMOJI[self.char_class]} **{self.char_class}**"
        else:
            cls = not_set
        role = f"**{ROLE_LABELS[self.role]}**" if self.role else not_set
        return brand(
            discord.Embed(
                title=i18n.t("recruit.setup_title", self.lang, guild=self.guild_name),
                description=i18n.t(
                    "recruit.summary_body", self.lang, class_line=cls, role_line=role
                ),
                colour=discord.Colour.blurple(),
            )
        )

    @discord.ui.button(label="Continue", emoji="➡️", style=discord.ButtonStyle.success)
    async def proceed(self, interaction: discord.Interaction, _):
        if self.char_class is None or self.role is None:
            await interaction.response.send_message(
                i18n.t("recruit.pick_first", self.lang), ephemeral=self.ephemeral
            )
            return
        await interaction.response.send_modal(
            ApplicationModal(
                self.guild_id, self.char_class, self.role, self.ephemeral, self.lang
            )
        )


class ApplicationModal(ModalErrorMixin, discord.ui.Modal):
    """The five free-text fields, then create the channel + fiche."""

    def __init__(self, guild_id, char_class, role, ephemeral, lang):
        super().__init__(title=i18n.t("recruit.modal_title", lang))
        self.guild_id = guild_id
        self.char_class = char_class
        self.role = role
        self.ephemeral = ephemeral
        self.lang = lang
        self.f_name = discord.ui.TextInput(
            label=i18n.t("recruit.name_label", lang), max_length=32
        )
        self.f_level = discord.ui.TextInput(
            label=i18n.t("recruit.level_label", lang), max_length=100, required=False
        )
        self.f_exp = discord.ui.TextInput(
            label=i18n.t("recruit.exp_label", lang),
            style=discord.TextStyle.paragraph,
            max_length=400,
            required=False,
        )
        self.f_avail = discord.ui.TextInput(
            label=i18n.t("recruit.avail_label", lang), max_length=100, required=False
        )
        self.f_motivation = discord.ui.TextInput(
            label=i18n.t("recruit.motivation_label", lang),
            style=discord.TextStyle.paragraph,
            max_length=400,
            required=False,
        )
        for item in (
            self.f_name,
            self.f_level,
            self.f_exp,
            self.f_avail,
            self.f_motivation,
        ):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Recruitment")
        await cog.submit_application(interaction, self)


# ----- Officer side: fiche + accept / reject -----


class ReviewView(ViewErrorMixin, discord.ui.View):
    """Accept / Reject on a fiche. Persistent: each button carries the app id."""

    def __init__(self, app_id: int, lang: str = i18n.DEFAULT):
        super().__init__(timeout=None)
        self.add_item(DecisionButton(app_id, "accept", lang))
        self.add_item(DecisionButton(app_id, "reject", lang))


class DecisionButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"kisk:recruit:(?P<app_id>\d+):(?P<action>accept|reject)",
):
    def __init__(self, app_id: int, action: str, lang: str = i18n.DEFAULT):
        self.app_id = app_id
        self.action = action
        accept = action == "accept"
        super().__init__(
            discord.ui.Button(
                label=i18n.t(f"recruit.btn_{action}", lang),
                emoji="✅" if accept else "❌",
                style=(
                    discord.ButtonStyle.success
                    if accept
                    else discord.ButtonStyle.danger
                ),
                custom_id=f"kisk:recruit:{app_id}:{action}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match, /):
        return cls(int(match["app_id"]), match["action"])

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Recruitment")
        await cog.decide(interaction, self.app_id, self.action)


class RejectReasonModal(ModalErrorMixin, discord.ui.Modal):
    def __init__(self, app_id: int, lang: str):
        super().__init__(title=i18n.t("recruit.reject_modal_title", lang))
        self.app_id = app_id
        self.lang = lang
        self.reason = discord.ui.TextInput(
            label=i18n.t("recruit.reject_reason_label", lang),
            style=discord.TextStyle.paragraph,
            max_length=400,
            required=False,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Recruitment")
        await cog.finalize_reject(
            interaction, self.app_id, self.reason.value.strip() or None
        )


# ----- The cog -----


@app_commands.guild_only()
class Recruitment(commands.Cog):
    """Applications: on-join DM, per-candidate channel, officer review."""

    recruit = app_commands.Group(
        name="recruit", description="Recruitment settings", guild_only=True
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----- Config -----

    @recruit.command(name="channel", description="Review applications in this channel")
    @app_commands.describe(action="Enable in this channel, or disable")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Enable in this channel", value="on"),
            app_commands.Choice(name="Disable", value="off"),
        ]
    )
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction, action: app_commands.Choice[str]):
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        value = interaction.channel_id if action.value == "on" else None
        await self.bot.db.set_setting(interaction.guild_id, "recruit_channel_id", value)
        key = "recruit.cmd_on" if action.value == "on" else "recruit.cmd_off"
        await interaction.response.send_message(i18n.t(key, lang), ephemeral=True)

    # ----- Join / leave -----

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        settings = await self.bot.db.get_settings(member.guild.id)
        if not recruitment_enabled(settings):
            return  # feature off on this server -> no DM at all
        lang = await i18n.resolve_lang(self.bot.db, member.guild)
        try:
            await member.send(
                embed=self._invite_embed(member.guild, lang),
                view=self._apply_view(member.guild.id, lang),
            )
        except discord.Forbidden:
            log.info("DMs closed for %s; trying a channel fallback", member.id)
            await self._invite_in_channel(member, settings, lang)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        app = await self.bot.db.get_pending_application(member.guild.id, member.id)
        if app is None:
            return
        await self._teardown_channel(member.guild, app)
        await self._delete_fiche(member.guild, app)
        await self.bot.db.delete_application(app["id"])

    # ----- Application intake (called by ApplicationModal) -----

    async def submit_application(self, interaction, modal):
        db = self.bot.db
        lang = modal.lang
        guild = interaction.client.get_guild(modal.guild_id)
        settings = await db.get_settings(modal.guild_id)
        channel_id = settings["recruit_channel_id"] if settings else None
        officers = guild.get_channel(channel_id) if guild and channel_id else None
        await interaction.response.defer(ephemeral=modal.ephemeral)
        if officers is None:
            # Recruitment was turned off (or the channel vanished) between the
            # apply click and this submit — nowhere to post the fiche.
            await interaction.followup.send(
                i18n.t("recruit.no_channel", lang), ephemeral=modal.ephemeral
            )
            return
        # Re-check here too: the persistent apply button stays clickable, so a
        # candidate could open a second form before finishing the first — this
        # stops a duplicate pending application (and its orphan channel/fiche).
        if await db.get_pending_application(modal.guild_id, interaction.user.id):
            await interaction.followup.send(
                i18n.t("recruit.already_pending", lang), ephemeral=modal.ephemeral
            )
            return
        app_id = await db.create_application(
            guild_id=modal.guild_id,
            user_id=interaction.user.id,
            char_name=modal.f_name.value.strip(),
            char_class=modal.char_class,
            role=modal.role,
            level_cp=modal.f_level.value.strip() or None,
            experience=modal.f_exp.value.strip() or None,
            availability=modal.f_avail.value.strip() or None,
            motivation=modal.f_motivation.value.strip() or None,
        )
        channel = None
        try:
            channel = await self._create_candidate_channel(
                guild, officers, interaction.user, modal, settings
            )
            await channel.send(
                i18n.t(
                    "recruit.channel_welcome", lang, mention=interaction.user.mention
                ),
                allowed_mentions=discord.AllowedMentions(users=[interaction.user]),
            )
            app = await db.get_application(app_id)
            fiche = await officers.send(
                embed=self._fiche_embed(app, interaction.user, channel, lang),
                view=ReviewView(app_id, lang),
            )
        except discord.Forbidden:
            await self._rollback_application(guild, app_id, channel)
            key = "recruit.missing_perm" if channel is None else "recruit.save_failed"
            await interaction.followup.send(
                i18n.t(key, lang), ephemeral=modal.ephemeral
            )
            return
        except discord.HTTPException:
            await self._rollback_application(guild, app_id, channel)
            await interaction.followup.send(
                i18n.t("recruit.save_failed", lang), ephemeral=modal.ephemeral
            )
            return
        await db.set_application_card(app_id, channel.id, fiche.id)
        await interaction.followup.send(
            i18n.t("recruit.submitted", lang), ephemeral=modal.ephemeral
        )

    # ----- Decision (called by DecisionButton / RejectReasonModal) -----

    async def decide(self, interaction, app_id, action):
        db = self.bot.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        if not await member_is_admin(db, interaction.user):
            await interaction.response.send_message(
                i18n.t("recruit.not_officer", lang), ephemeral=True
            )
            return
        app = await db.get_application(app_id)
        if app is None or app["status"] != "pending":
            await interaction.response.send_message(
                i18n.t("recruit.already_decided", lang), ephemeral=True
            )
            return
        if action == "reject":
            await interaction.response.send_modal(RejectReasonModal(app_id, lang))
            return
        await self._accept(interaction, app, lang)

    async def _accept(self, interaction, app, lang):
        db = self.bot.db
        guild = interaction.guild
        settings = await db.get_settings(guild.id)
        role_id = settings["member_role_id"] if settings else None
        role = guild.get_role(role_id) if role_id else None
        if role is None:
            # Not configured, or the configured role was since deleted: either
            # way we can't validate — bail before claiming the decision.
            await interaction.response.send_message(
                i18n.t("recruit.no_member_role", lang), ephemeral=True
            )
            return
        member = guild.get_member(app["user_id"])
        if member is None:
            await interaction.response.send_message(
                i18n.t("recruit.applicant_gone", lang), ephemeral=True
            )
            return
        if not await db.set_application_status(
            app["id"], "accepted", reviewer_id=interaction.user.id, reason=None
        ):
            await interaction.response.send_message(
                i18n.t("recruit.already_decided", lang), ephemeral=True
            )
            return
        await interaction.response.defer()
        # Grant the role -> Onboarding.on_member_update DMs the profile setup.
        try:
            await member.add_roles(role, reason="Recruitment: application accepted")
        except discord.HTTPException:
            log.warning("Could not grant the member role to %s on accept", member.id)
        try:
            await member.send(i18n.t("recruit.dm_accepted", lang, guild=guild.name))
        except discord.HTTPException:
            pass
        await self._teardown_channel(guild, app)
        await self._stamp_fiche(
            interaction.message, "recruit.accepted_fiche", interaction.user, lang
        )

    async def finalize_reject(self, interaction, app_id, reason):
        db = self.bot.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        app = await db.get_application(app_id)
        decided = app is not None and await db.set_application_status(
            app_id, "rejected", reviewer_id=interaction.user.id, reason=reason
        )
        if not decided:
            await interaction.response.send_message(
                i18n.t("recruit.already_decided", lang), ephemeral=True
            )
            return
        await interaction.response.defer()
        member = interaction.guild.get_member(app["user_id"])
        if member is not None:
            key = "recruit.dm_rejected_reason" if reason else "recruit.dm_rejected"
            try:
                await member.send(
                    i18n.t(key, lang, guild=interaction.guild.name, reason=reason or "")
                )
            except discord.HTTPException:
                pass
        await self._teardown_channel(interaction.guild, app)
        fiche = await self._fetch_fiche(interaction.guild, app)
        if fiche is not None:
            await self._stamp_fiche(
                fiche, "recruit.rejected_fiche", interaction.user, lang
            )

    # ----- Helpers -----

    def _apply_view(self, guild_id, lang):
        view = discord.ui.View(timeout=None)
        view.add_item(ApplyButton(guild_id, lang))
        return view

    def _invite_embed(self, guild, lang):
        return brand(
            discord.Embed(
                title=i18n.t("recruit.dm_title", lang, guild=guild.name),
                description=i18n.t("recruit.dm_body", lang),
                colour=discord.Colour.blurple(),
            )
        )

    async def _invite_in_channel(self, member, settings, lang):
        channel_id = settings["welcome_channel_id"] if settings else None
        channel = member.guild.get_channel(channel_id) if channel_id else None
        channel = channel or member.guild.system_channel
        if channel is None:
            log.info("No fallback channel to invite %s to apply", member.id)
            return
        embed = self._invite_embed(member.guild, lang)
        embed.description = (
            i18n.t("recruit.dm_fallback_prefix", lang)
            + "\n\n"
            + (embed.description or "")
        )
        try:
            await channel.send(
                content=member.mention,
                embed=embed,
                view=self._apply_view(member.guild.id, lang),
                allowed_mentions=discord.AllowedMentions(users=[member]),
            )
        except discord.HTTPException:
            log.warning("Could not post the apply invite for %s", member.id)

    async def _create_candidate_channel(self, guild, officers, user, modal, settings):
        spec = overwrite_spec(
            candidate_id=user.id,
            admin_role_id=settings["admin_role_id"] if settings else None,
            bot_id=guild.me.id,
        )
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False)
        }
        for object_id in spec["allow_view"]:
            target = guild.get_role(object_id) or guild.get_member(object_id)
            if target is None:
                if object_id != guild.me.id:
                    log.warning("Overwrite target %s no longer resolves", object_id)
                target = guild.me
            overwrites[target] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True
            )
        return await guild.create_text_channel(
            name=channel_slug(modal.char_class, modal.f_name.value),
            category=officers.category if officers else None,
            overwrites=overwrites,
            reason=f"Recruitment: application from {user}",
        )

    async def _rollback_application(self, guild, app_id, channel):
        """Undo a half-created application: drop the channel (if one was made)
        and the DB row, so a mid-flow failure leaves nothing dangling."""
        if channel is not None:
            try:
                await channel.delete(reason="Recruitment: application aborted")
            except discord.HTTPException:
                pass
        await self.bot.db.delete_application(app_id)

    async def _teardown_channel(self, guild, app):
        if not app["channel_id"]:
            return
        channel = guild.get_channel(app["channel_id"])
        if channel is not None:
            try:
                await channel.delete(reason="Recruitment: application closed")
            except discord.HTTPException:
                pass

    def _fiche_embed(self, app, user, channel, lang):
        emoji = config.CLASS_EMOJI.get(app["char_class"], "")
        embed = brand(
            discord.Embed(
                title=i18n.t("recruit.fiche_title", lang, name=app["char_name"]),
                description=i18n.t(
                    "recruit.fiche_class_role",
                    lang,
                    emoji=emoji,
                    cls=app["char_class"],
                    role=ROLE_LABELS.get(app["role"], app["role"]),
                ),
                colour=discord.Colour.blurple(),
            )
        )
        for key, field in (
            ("recruit.fiche_level", app["level_cp"]),
            ("recruit.fiche_exp", app["experience"]),
            ("recruit.fiche_avail", app["availability"]),
            ("recruit.fiche_motivation", app["motivation"]),
        ):
            if field:
                embed.add_field(name=i18n.t(key, lang), value=field, inline=False)
        embed.add_field(
            name=i18n.t("recruit.btn_discuss", lang),
            value=channel.mention,
            inline=False,
        )
        # The status field stays LAST so _stamp_fiche can replace it on decision.
        embed.add_field(
            name="​",
            value=i18n.t("recruit.fiche_pending", lang, mention=user.mention),
            inline=False,
        )
        return embed

    async def _fetch_fiche(self, guild, app):
        settings = await self.bot.db.get_settings(guild.id)
        channel_id = settings["recruit_channel_id"] if settings else None
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel is None or not app["card_message_id"]:
            return None
        try:
            return await channel.fetch_message(app["card_message_id"])
        except discord.HTTPException:
            return None

    async def _delete_fiche(self, guild, app):
        settings = await self.bot.db.get_settings(guild.id)
        channel_id = settings["recruit_channel_id"] if settings else None
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel is None or not app["card_message_id"]:
            return
        try:
            await channel.get_partial_message(app["card_message_id"]).delete()
        except discord.HTTPException:
            pass

    async def _stamp_fiche(self, message, outcome_key, reviewer, lang):
        """Edit the fiche in place: replace the status line with the outcome and
        drop the buttons (the fiche is kept as a trace)."""
        if not message.embeds:
            return
        embed = message.embeds[0]
        text = i18n.t(outcome_key, lang, who=reviewer.mention)
        last = len(embed.fields) - 1
        if last >= 0:
            embed.set_field_at(last, name="​", value=text, inline=False)
        else:
            embed.add_field(name="​", value=text, inline=False)
        try:
            await message.edit(embed=embed, view=None)
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Recruitment(bot))
