"""The /language command: choose the server's language (FR / EN / Auto)."""

import discord
from discord import app_commands
from discord.app_commands import locale_str
from discord.ext import commands

from .. import i18n

LANG_LABEL = {"fr": "Français", "en": "English"}


def choice_to_lang(value: str) -> str | None:
    """The stored column value for a picker choice ('auto' -> None)."""
    return None if value == "auto" else value


@app_commands.guild_only()
class Settings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="language",
        description=locale_str(
            "Set the language Kisk uses on this server",
            key="commands.language.description",
        ),
    )
    @app_commands.describe(
        choice=locale_str(
            "The language for this server", key="commands.language.choice"
        )
    )
    @app_commands.choices(
        choice=[
            app_commands.Choice(name="Français", value="fr"),
            app_commands.Choice(name="English", value="en"),
            app_commands.Choice(name="Auto (Discord server language)", value="auto"),
        ]
    )
    @app_commands.default_permissions(manage_guild=True)
    async def language(
        self, interaction: discord.Interaction, choice: app_commands.Choice[str]
    ):
        lang_value = choice_to_lang(choice.value)
        await self.bot.db.set_language(interaction.guild_id, lang_value)
        effective = await i18n.resolve_lang(self.bot.db, interaction.guild)
        if lang_value is None:
            text = i18n.t("language.auto_confirm", effective)
        else:
            text = i18n.t(
                "language.set_confirm", effective, language=LANG_LABEL[lang_value]
            )
        await interaction.response.send_message(text, ephemeral=True)

    @app_commands.command(
        name="admin-role",
        description="Set a role Kisk treats as an admin (Manage Server only)",
    )
    @app_commands.describe(
        role="The role to grant Kisk-admin powers (leave empty to see the current one)",
        clear="Remove the configured admin role",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def admin_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role | None = None,
        clear: bool = False,
    ):
        db = self.bot.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        # Appointing the admin role stays gated on real Manage Server, so a Kisk
        # admin can never widen their own reach.
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                i18n.t("adminrole.forbidden", lang), ephemeral=True
            )
            return

        if clear:
            await db.set_setting(interaction.guild_id, "admin_role_id", None)
            await interaction.response.send_message(
                i18n.t("adminrole.cleared", lang), ephemeral=True
            )
            return

        if role is not None:
            await db.set_setting(interaction.guild_id, "admin_role_id", role.id)
            await interaction.response.send_message(
                i18n.t("adminrole.set_confirm", lang, role=role.mention),
                ephemeral=True,
            )
            return

        settings = await db.get_settings(interaction.guild_id)
        current = settings["admin_role_id"] if settings else None
        text = (
            i18n.t("adminrole.current", lang, role=f"<@&{current}>")
            if current
            else i18n.t("adminrole.none", lang)
        )
        await interaction.response.send_message(text, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))
