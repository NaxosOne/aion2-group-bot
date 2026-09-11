"""Legion life: absences (/away, /absences, /back), announcements (/announce)
and welcoming newcomers (/welcome)."""

import time

import discord
from discord import app_commands
from discord.ext import commands

from .. import i18n
from ..actions import fmt_absence_ts, register_absence
from ..branding import brand
from ..errors import ModalErrorMixin
from ..utils.onboarding import role_just_added, welcome_on_join, welcome_on_validation


class AnnounceModal(ModalErrorMixin, discord.ui.Modal):
    """Pop-up form: allows a multi-line message."""

    def __init__(self, ping: discord.Role | None, lang: str):
        super().__init__(title=i18n.t("announce.modal_title", lang))
        self.ping = ping
        self.lang = lang
        self.announce_title = discord.ui.TextInput(
            label=i18n.t("announce.field_title", lang), max_length=100
        )
        self.content = discord.ui.TextInput(
            label=i18n.t("announce.field_message", lang),
            style=discord.TextStyle.paragraph,
            max_length=2000,
        )
        self.add_item(self.announce_title)
        self.add_item(self.content)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"📯 {self.announce_title.value}",
            description=self.content.value,
            colour=discord.Colour.gold(),
        )
        brand(embed)
        embed.set_footer(
            text=i18n.t(
                "announce.footer", self.lang, name=interaction.user.display_name
            )
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
        start=(
            "First day away, time optional "
            "(e.g. “30/08”, “30/08 14:00”, “tomorrow 18h”)"
        ),
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
        await register_absence(interaction, start, until, reason)

    @app_commands.command(name="absences", description="See who's away or about to be")
    async def absences(self, interaction: discord.Interaction):
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        now = int(time.time())
        absences = await self.bot.db.list_absences(interaction.guild_id, now)
        if not absences:
            await interaction.response.send_message(
                i18n.t("absences.none", lang),
                ephemeral=True,
            )
            return

        lines = []
        for a in absences:
            ongoing = a["starts_on"] <= now
            state = (
                i18n.t("absences.ongoing", lang)
                if ongoing
                else i18n.t(
                    "absences.starting", lang, date=fmt_absence_ts(a["starts_on"])
                )
            )
            lines.append(
                i18n.t(
                    "absences.line",
                    lang,
                    user=a["user_id"],
                    state=state,
                    date=fmt_absence_ts(a["ends_on"], end=True),
                )
                + (f" *({a['reason']})*" if a["reason"] else "")
            )

        embed = discord.Embed(
            title=i18n.t("absences.title", lang),
            description="\n".join(lines),
            colour=discord.Colour.orange(),
        )
        brand(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="back", description="Cancel your absences (early return)"
    )
    async def back(self, interaction: discord.Interaction):
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        cancelled = await self.bot.db.clear_absences(
            interaction.guild_id, interaction.user.id, int(time.time())
        )
        if cancelled:
            await interaction.response.send_message(
                i18n.t("back.welcome_back", lang, mention=interaction.user.mention),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        else:
            await interaction.response.send_message(
                i18n.t("back.none", lang), ephemeral=True
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
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        if action.value == "on":
            await self.bot.db.set_setting(
                interaction.guild_id, "welcome_channel_id", interaction.channel_id
            )
            await interaction.response.send_message(
                i18n.t("welcome_cmd.on", lang),
                ephemeral=True,
            )
        else:
            await self.bot.db.set_setting(
                interaction.guild_id, "welcome_channel_id", None
            )
            await interaction.response.send_message(
                i18n.t("welcome_cmd.off", lang), ephemeral=True
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        settings = await self.bot.db.get_settings(member.guild.id)
        # When access is gated (a validated-member role and/or recruitment), a
        # newcomer can't see the welcome channel yet — greeting and tagging them
        # there is useless. They get the "Postuler" invite (recruitment cog)
        # instead; the public welcome waits until they're validated below.
        if not welcome_on_join(self._access_gated(settings)):
            return
        await self._post_welcome(member, settings)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Fires on every member change; only act when the validated-member role
        # was actually just added — that's when they gain channel access and the
        # public welcome (with its how-to) finally makes sense.
        if before.roles == after.roles:
            return
        settings = await self.bot.db.get_settings(after.guild.id)
        role_id = settings["member_role_id"] if settings else None
        if not role_id:
            return
        added = role_just_added(
            role_id, {r.id for r in before.roles}, {r.id for r in after.roles}
        )
        if not welcome_on_validation(member_role_added=added, is_bot=after.bot):
            return
        await self._post_welcome(after, settings)

    @staticmethod
    def _access_gated(settings) -> bool:
        """Whether joining alone doesn't grant access to the legion's channels:
        a validated-member role or the recruitment flow stands in between."""
        if settings is None:
            return False
        return bool(settings["member_role_id"] or settings["recruit_channel_id"])

    async def _post_welcome(self, member: discord.Member, settings) -> None:
        """Post the public welcome board, tagging the member, in the welcome
        channel. No-op if no welcome channel is configured or reachable."""
        if settings is None or not settings["welcome_channel_id"]:
            return
        channel = member.guild.get_channel(settings["welcome_channel_id"])
        if channel is None:
            return
        lang = await i18n.resolve_lang(self.bot.db, member.guild)
        embed = discord.Embed(
            title=i18n.t("welcome_join.title", lang),
            description=i18n.t("welcome_join.body", lang),
            colour=discord.Colour.blurple(),
        )
        brand(embed)
        try:
            await channel.send(
                content=member.mention,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(users=[member]),
            )
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
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        await interaction.response.send_modal(AnnounceModal(ping, lang))


async def setup(bot: commands.Bot):
    await bot.add_cog(Legion(bot))
