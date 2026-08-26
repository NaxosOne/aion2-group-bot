"""Sondages : /vote (questions rapides) et /dispo (dispos de la semaine).

Les deux reposent sur des vues persistantes (custom_id fixes), comme les
sorties : les boutons survivent aux redémarrages du bot.
"""

import json
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import config

EMOJIS_CHOIX = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
JOURS_COURTS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


# ----- /vote -----


def build_poll_embed(poll, votes: list) -> discord.Embed:
    options = json.loads(poll["options"])
    par_choix: dict[int, list] = {i: [] for i in range(len(options))}
    for v in votes:
        if v["choice"] in par_choix:
            par_choix[v["choice"]].append(v["user_id"])

    clos = poll["status"] != "open"
    embed = discord.Embed(
        title=f"🗳️ {poll['question']}",
        colour=discord.Colour.dark_grey() if clos else discord.Colour.blurple(),
    )
    for i, option in enumerate(options):
        votants = par_choix[i]
        valeur = " ".join(f"<@{uid}>" for uid in votants) or "*—*"
        if len(valeur) > 1000:
            valeur = valeur[:1000] + "…"
        embed.add_field(
            name=f"{EMOJIS_CHOIX[i]} {option} — {len(votants)}",
            value=valeur,
            inline=False,
        )
    total = len(votes)
    embed.set_footer(
        text=("Sondage clos • " if clos else "")
        + f"{total} vote{'s' if total > 1 else ''}"
    )
    return embed


class VoteView(discord.ui.View):
    def __init__(self, nb_options: int = 5):
        super().__init__(timeout=None)
        # Retire les boutons en trop pour un sondage à moins de 5 choix.
        for item in list(self.children):
            if (
                item.custom_id.startswith("vote:choix:")
                and int(item.custom_id.rsplit(":", 1)[1]) >= nb_options
            ):
                self.remove_item(item)

    @discord.ui.button(emoji="1️⃣", style=discord.ButtonStyle.primary, custom_id="vote:choix:0")
    async def choix_0(self, interaction: discord.Interaction, _):
        await self._voter(interaction, 0)

    @discord.ui.button(emoji="2️⃣", style=discord.ButtonStyle.primary, custom_id="vote:choix:1")
    async def choix_1(self, interaction: discord.Interaction, _):
        await self._voter(interaction, 1)

    @discord.ui.button(emoji="3️⃣", style=discord.ButtonStyle.primary, custom_id="vote:choix:2")
    async def choix_2(self, interaction: discord.Interaction, _):
        await self._voter(interaction, 2)

    @discord.ui.button(emoji="4️⃣", style=discord.ButtonStyle.primary, custom_id="vote:choix:3")
    async def choix_3(self, interaction: discord.Interaction, _):
        await self._voter(interaction, 3)

    @discord.ui.button(emoji="5️⃣", style=discord.ButtonStyle.primary, custom_id="vote:choix:4")
    async def choix_4(self, interaction: discord.Interaction, _):
        await self._voter(interaction, 4)

    @discord.ui.button(
        label="Clore", emoji="🔒", style=discord.ButtonStyle.secondary,
        custom_id="vote:clore", row=1,
    )
    async def clore(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        poll = await db.get_poll(interaction.message.id)
        if poll is None or poll["status"] != "open":
            await interaction.response.send_message(
                "Ce sondage est introuvable ou déjà clos.", ephemeral=True
            )
            return
        est_createur = interaction.user.id == poll["creator_id"]
        est_modo = interaction.user.guild_permissions.manage_messages
        if not (est_createur or est_modo):
            await interaction.response.send_message(
                "Seul l'auteur du sondage (ou un modérateur) peut le clore.",
                ephemeral=True,
            )
            return
        await db.set_poll_status(poll["message_id"], "closed")
        poll = await db.get_poll(poll["message_id"])
        embed = build_poll_embed(poll, await db.get_votes(poll["message_id"]))
        await interaction.response.edit_message(embed=embed, view=None)

    async def _voter(self, interaction: discord.Interaction, choix: int):
        db = interaction.client.db
        poll = await db.get_poll(interaction.message.id)
        if poll is None:
            await interaction.response.send_message(
                "Je ne retrouve plus ce sondage.", ephemeral=True
            )
            return
        if poll["status"] != "open":
            await interaction.response.send_message(
                "Ce sondage est clos.", ephemeral=True
            )
            return
        if choix >= len(json.loads(poll["options"])):
            return  # bouton d'un choix qui n'existe pas (ne devrait pas arriver)
        await db.set_vote(poll["message_id"], interaction.user.id, choix)
        embed = build_poll_embed(poll, await db.get_votes(poll["message_id"]))
        await interaction.response.edit_message(embed=embed)


# ----- /dispo -----


def label_semaine(now: datetime) -> str:
    lundi = now.date() - timedelta(days=now.weekday())
    return f"semaine du {lundi.strftime('%d/%m')}"


def build_dispo_embed(dispo, marks: list) -> discord.Embed:
    par_jour: dict[int, list] = {i: [] for i in range(7)}
    for m in marks:
        par_jour[m["day"]].append(m["user_id"])

    embed = discord.Embed(
        title=f"📅 Dispos — {dispo['week_label']}",
        description="Clique sur les jours où tu peux jouer (re-clique pour retirer).",
        colour=discord.Colour.green(),
    )
    for i, jour in enumerate(JOURS):
        joueurs = par_jour[i]
        embed.add_field(
            name=f"{jour} ({len(joueurs)})",
            value="\n".join(f"<@{uid}>" for uid in joueurs) or "*—*",
            inline=True,
        )
    return embed


class DispoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for i, jour in enumerate(JOURS_COURTS):
            bouton = discord.ui.Button(
                label=jour,
                style=discord.ButtonStyle.primary,
                custom_id=f"dispo:{i}",
                row=0 if i < 5 else 1,
            )
            bouton.callback = self._callback_jour(bouton, i)
            self.add_item(bouton)

    def _callback_jour(self, bouton: discord.ui.Button, jour: int):
        async def callback(interaction: discord.Interaction):
            db = interaction.client.db
            dispo = await db.get_dispo(interaction.message.id)
            if dispo is None:
                await interaction.response.send_message(
                    "Je ne retrouve plus ce tableau de dispos.", ephemeral=True
                )
                return
            await db.toggle_dispo_mark(dispo["message_id"], interaction.user.id, jour)
            embed = build_dispo_embed(dispo, await db.get_dispo_marks(dispo["message_id"]))
            await interaction.response.edit_message(embed=embed)

        return callback


# ----- Le cog -----


@app_commands.guild_only()
class Polls(commands.Cog):
    """Sondages rapides et dispos de la semaine (avec publication hebdo auto)."""

    dispo = app_commands.Group(
        name="dispo", description="Les disponibilités de la semaine", guild_only=True
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.boucle_dispo.start()

    async def cog_unload(self):
        self.boucle_dispo.cancel()

    @app_commands.command(name="vote", description="Lancer un sondage rapide avec boutons")
    @app_commands.describe(
        question="La question posée",
        choix1="Premier choix",
        choix2="Deuxième choix",
        choix3="Troisième choix (optionnel)",
        choix4="Quatrième choix (optionnel)",
        choix5="Cinquième choix (optionnel)",
    )
    async def vote(
        self,
        interaction: discord.Interaction,
        question: app_commands.Range[str, 1, 200],
        choix1: app_commands.Range[str, 1, 80],
        choix2: app_commands.Range[str, 1, 80],
        choix3: app_commands.Range[str, 1, 80] | None = None,
        choix4: app_commands.Range[str, 1, 80] | None = None,
        choix5: app_commands.Range[str, 1, 80] | None = None,
    ):
        options = [c.strip() for c in (choix1, choix2, choix3, choix4, choix5) if c]
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

    @dispo.command(name="poster", description="Publier le tableau des dispos de la semaine")
    async def dispo_poster(self, interaction: discord.Interaction):
        label = label_semaine(datetime.now(config.TIMEZONE))
        embed = build_dispo_embed({"week_label": label}, [])
        await interaction.response.send_message(embed=embed, view=DispoView())
        message = await interaction.original_response()
        await self.bot.db.create_dispo(
            message.id, interaction.guild_id, interaction.channel_id, label
        )

    @dispo.command(
        name="hebdo",
        description="Publier automatiquement les dispos chaque semaine dans ce salon",
    )
    @app_commands.describe(action="Activer dans ce salon, ou désactiver")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Activer dans ce salon", value="on"),
            app_commands.Choice(name="Désactiver", value="off"),
        ]
    )
    @app_commands.default_permissions(manage_messages=True)
    async def dispo_hebdo(
        self, interaction: discord.Interaction, action: app_commands.Choice[str]
    ):
        if action.value == "on":
            await self.bot.db.set_setting(
                interaction.guild_id, "dispo_channel_id", interaction.channel_id
            )
            await interaction.response.send_message(
                f"📅 C'est noté : je publierai le tableau des dispos ici chaque "
                f"{JOURS[config.DISPO_JOUR].lower()} vers {config.DISPO_HEURE}h.",
                ephemeral=True,
            )
        else:
            await self.bot.db.set_setting(interaction.guild_id, "dispo_channel_id", None)
            await interaction.response.send_message(
                "Publication automatique des dispos désactivée.", ephemeral=True
            )

    @tasks.loop(minutes=10)
    async def boucle_dispo(self):
        """Publie le tableau hebdo dans les serveurs qui l'ont activé."""
        tz = config.TIMEZONE
        now = datetime.now(tz)
        lundi = now.date() - timedelta(days=now.weekday())
        jour_pub = lundi + timedelta(days=config.DISPO_JOUR)
        moment_pub = datetime(
            jour_pub.year, jour_pub.month, jour_pub.day, config.DISPO_HEURE, tzinfo=tz
        )
        if now < moment_pub:
            return

        for reglages in await self.bot.db.guilds_with_dispo():
            if reglages["dispo_last_posted"] >= int(moment_pub.timestamp()):
                continue  # déjà publié cette semaine
            # Marqué avant l'envoi pour ne jamais spammer en cas d'erreur répétée.
            await self.bot.db.set_setting(
                reglages["guild_id"], "dispo_last_posted", int(now.timestamp())
            )
            try:
                channel = self.bot.get_channel(
                    reglages["dispo_channel_id"]
                ) or await self.bot.fetch_channel(reglages["dispo_channel_id"])
                label = label_semaine(now)
                embed = build_dispo_embed({"week_label": label}, [])
                message = await channel.send(embed=embed, view=DispoView())
                await self.bot.db.create_dispo(
                    message.id, reglages["guild_id"], channel.id, label
                )
            except discord.HTTPException:
                pass  # salon supprimé ou permissions retirées

    @boucle_dispo.before_loop
    async def _attendre_pret(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Polls(bot))
