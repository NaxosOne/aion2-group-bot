"""Commandes slash (/sortie, /sorties) et boucle des rappels automatiques."""

import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import config
from ..embeds import build_event_embed
from ..logic import COMPO_LIBRE, COMPO_STANDARD, STANDARD_SIZE, assign
from ..utils.time_parse import FORMAT_AIDE, ParseError, parse_when
from ..views import SignupView


@app_commands.guild_only()
class Groups(commands.Cog):
    """Création et listing des sorties, plus l'envoi des rappels."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.rappels.start()

    async def cog_unload(self):
        self.rappels.cancel()

    # ----- /sortie -----

    @app_commands.command(name="sortie", description="Créer un appel de groupe (donjon, PvP...)")
    @app_commands.rename(activite="type")
    @app_commands.describe(
        titre="Nom de la sortie (ex. « Donjon du Feu HM »)",
        activite="Type de sortie",
        compo="Standard = 1 tank / 1 heal / 3 DPS. Libre = premier arrivé, premier servi.",
        quand="Ex. « 21h », « demain 20h30 », « 30/08 21h ». Vide = dès maintenant.",
        taille="Nombre de places en compo libre (défaut : 5). Ignoré en compo standard.",
        description="Infos en plus : niveau requis, salon vocal, etc.",
    )
    @app_commands.choices(
        activite=[
            app_commands.Choice(name="🏰 Donjon", value="Donjon"),
            app_commands.Choice(name="⚔️ PvP", value="PvP"),
            app_commands.Choice(name="🎲 Autre", value="Autre"),
        ],
        compo=[
            app_commands.Choice(name="Standard (1 tank / 1 heal / 3 DPS)", value=COMPO_STANDARD),
            app_commands.Choice(name="Libre (rôles sans limite)", value=COMPO_LIBRE),
        ],
    )
    async def sortie(
        self,
        interaction: discord.Interaction,
        titre: app_commands.Range[str, 1, 100],
        activite: app_commands.Choice[str],
        compo: app_commands.Choice[str],
        quand: str | None = None,
        taille: app_commands.Range[int, 2, 25] | None = None,
        description: app_commands.Range[str, 1, 500] | None = None,
    ):
        starts_at = None
        if quand:
            try:
                starts_at = int(parse_when(quand, config.TIMEZONE).timestamp())
            except ParseError as err:
                await interaction.response.send_message(str(err), ephemeral=True)
                return

        size = STANDARD_SIZE if compo.value == COMPO_STANDARD else (taille or 5)

        event = {
            "channel_id": interaction.channel_id,
            "guild_id": interaction.guild_id,
            "creator_id": interaction.user.id,
            "creator_name": interaction.user.display_name,
            "title": titre,
            "activity": activite.value,
            "description": description,
            "compo": compo.value,
            "size": size,
            "starts_at": starts_at,
            "status": "open",
        }

        # On envoie d'abord le message pour connaître son ID, qui sert de clé.
        embed = build_event_embed(event, [])
        await interaction.response.send_message(embed=embed, view=SignupView())
        message = await interaction.original_response()
        await self.bot.db.create_event(message_id=message.id, **event)

    # ----- /sorties -----

    @app_commands.command(name="sorties", description="Voir les sorties à venir sur ce serveur")
    async def sorties(self, interaction: discord.Interaction):
        events = await self.bot.db.upcoming_events(interaction.guild_id, int(time.time()))
        if not events:
            await interaction.response.send_message(
                "Aucune sortie prévue pour l'instant. Lance la tienne avec `/sortie` !",
                ephemeral=True,
            )
            return

        lignes = []
        for ev in events:
            signups = await self.bot.db.get_signups(ev["message_id"])
            groupe, attente = assign(ev["compo"], ev["size"], signups)
            taille = STANDARD_SIZE if ev["compo"] == COMPO_STANDARD else ev["size"]
            horaire = f"<t:{ev['starts_at']}:R>" if ev["starts_at"] else "pas d'horaire"
            lien = (
                f"https://discord.com/channels/{ev['guild_id']}"
                f"/{ev['channel_id']}/{ev['message_id']}"
            )
            lignes.append(
                f"• [**{ev['title']}**]({lien}) — {ev['activity']}, {horaire} — "
                f"{len(groupe)}/{taille} inscrits"
                + (f" (+{len(attente)} en attente)" if attente else "")
            )

        embed = discord.Embed(
            title="📅 Sorties à venir",
            description="\n".join(lignes),
            colour=discord.Colour.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ----- Rappels automatiques -----

    @tasks.loop(seconds=60)
    async def rappels(self):
        maintenant = int(time.time())
        events = await self.bot.db.events_to_remind(
            maintenant, config.REMINDER_MINUTES * 60
        )
        for ev in events:
            await self.bot.db.mark_reminded(ev["message_id"])
            if ev["starts_at"] < maintenant - 600:
                # Le bot était éteint et la sortie est passée depuis longtemps :
                # inutile d'envoyer un rappel en retard.
                continue
            try:
                await self._envoyer_rappel(ev)
            except discord.HTTPException:
                pass  # salon supprimé ou permissions retirées : on ignore

    @rappels.before_loop
    async def _attendre_pret(self):
        await self.bot.wait_until_ready()

    async def _envoyer_rappel(self, ev):
        channel = self.bot.get_channel(ev["channel_id"])
        if channel is None:
            channel = await self.bot.fetch_channel(ev["channel_id"])
        signups = await self.bot.db.get_signups(ev["message_id"])
        groupe, _ = assign(ev["compo"], ev["size"], signups)
        mentions = " ".join(f"<@{s['user_id']}>" for s in groupe)
        lien = (
            f"https://discord.com/channels/{ev['guild_id']}"
            f"/{ev['channel_id']}/{ev['message_id']}"
        )
        await channel.send(
            f"⏰ Rappel : [**{ev['title']}**](<{lien}>) commence "
            f"<t:{ev['starts_at']}:R> !"
            + (f"\n{mentions}" if mentions else " (personne d'inscrit 😢)")
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Groups(bot))
