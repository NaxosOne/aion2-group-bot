"""Vie de la légion : absences (/absent, /absents, /retour) et annonces (/annonce)."""

import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from .. import config
from ..utils.time_parse import FORMAT_AIDE_DATE, ParseError, parse_date


class AnnonceModal(discord.ui.Modal, title="Annonce de la légion"):
    """Fenêtre de saisie : permet un message sur plusieurs lignes."""

    titre = discord.ui.TextInput(label="Titre", max_length=100)
    contenu = discord.ui.TextInput(
        label="Message",
        style=discord.TextStyle.paragraph,
        max_length=2000,
    )

    def __init__(self, ping: discord.Role | None):
        super().__init__()
        self.ping = ping

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"📯 {self.titre.value}",
            description=self.contenu.value,
            colour=discord.Colour.gold(),
        )
        embed.set_footer(text=f"Annonce de la légion • par {interaction.user.display_name}")

        content = None
        if self.ping is not None:
            # Le rôle @everyone se mentionne "@everyone", pas via <@&id>.
            content = "@everyone" if self.ping.is_default() else self.ping.mention

        await interaction.response.send_message(
            content=content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=True, roles=True),
        )


@app_commands.guild_only()
class Legion(commands.Cog):
    """Absences des membres et annonces officielles."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----- Absences -----

    @app_commands.command(name="absent", description="Signaler une absence à la légion")
    @app_commands.describe(
        du="Premier jour d'absence (ex. « 30/08 », « demain »)",
        au="Dernier jour d'absence (vide = même jour que « du »)",
        raison="Optionnel : vacances, examens, IRL...",
    )
    async def absent(
        self,
        interaction: discord.Interaction,
        du: str,
        au: str | None = None,
        raison: app_commands.Range[str, 1, 100] | None = None,
    ):
        tz = config.TIMEZONE
        try:
            debut = parse_date(du, tz)
            fin = parse_date(au, tz) if au else debut
        except ParseError as err:
            await interaction.response.send_message(
                f"{err} {FORMAT_AIDE_DATE}", ephemeral=True
            )
            return
        if fin < debut:
            await interaction.response.send_message(
                "Le jour de retour est avant le jour de départ. 🤔", ephemeral=True
            )
            return

        debut_ts = int(datetime(debut.year, debut.month, debut.day, 0, 0, tzinfo=tz).timestamp())
        fin_ts = int(datetime(fin.year, fin.month, fin.day, 23, 59, tzinfo=tz).timestamp())
        await self.bot.db.add_absence(
            interaction.guild_id, interaction.user.id, debut_ts, fin_ts, raison
        )

        if debut == fin:
            periode = f"le <t:{debut_ts}:D>"
        else:
            periode = f"du <t:{debut_ts}:D> au <t:{fin_ts}:D>"
        await interaction.response.send_message(
            f"🏖️ {interaction.user.mention} sera absent {periode}"
            + (f" ({raison})" if raison else "")
            + ". Bon repos !",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="absents", description="Voir qui est absent ou bientôt absent")
    async def absents(self, interaction: discord.Interaction):
        maintenant = int(time.time())
        absences = await self.bot.db.list_absences(interaction.guild_id, maintenant)
        if not absences:
            await interaction.response.send_message(
                "Personne d'absent à l'horizon, la légion est au complet ! 💪",
                ephemeral=True,
            )
            return

        lignes = []
        for a in absences:
            en_cours = a["starts_on"] <= maintenant
            statut = "🔴 en cours" if en_cours else f"à partir du <t:{a['starts_on']}:D>"
            lignes.append(
                f"• <@{a['user_id']}> — {statut}, retour après le <t:{a['ends_on']}:D>"
                + (f" *({a['reason']})*" if a["reason"] else "")
            )

        embed = discord.Embed(
            title="🏖️ Absences",
            description="\n".join(lignes),
            colour=discord.Colour.orange(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="retour", description="Annuler tes absences (retour anticipé)")
    async def retour(self, interaction: discord.Interaction):
        annulees = await self.bot.db.clear_absences(
            interaction.guild_id, interaction.user.id, int(time.time())
        )
        if annulees:
            await interaction.response.send_message(
                f"🎉 {interaction.user.mention} est de retour !",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        else:
            await interaction.response.send_message(
                "Tu n'avais pas d'absence en cours ou à venir.", ephemeral=True
            )

    # ----- Annonces -----

    @app_commands.command(name="annonce", description="Publier une annonce de la légion (modérateurs)")
    @app_commands.describe(ping="Optionnel : rôle à mentionner (ex. @Aion2, @everyone)")
    @app_commands.default_permissions(manage_messages=True)
    async def annonce(
        self, interaction: discord.Interaction, ping: discord.Role | None = None
    ):
        await interaction.response.send_modal(AnnonceModal(ping))


async def setup(bot: commands.Bot):
    await bot.add_cog(Legion(bot))
