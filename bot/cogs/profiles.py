"""Commandes /profil : l'annuaire des persos de la légion (main + reroll)."""

import discord
from discord import app_commands
from discord.ext import commands

from ..embeds import ROLE_EMOJI, ROLE_LABEL

# Suggestions de classes (héritées d'Aion — champ libre : tape ce que tu veux
# si les classes d'Aion 2 diffèrent, la liste est facile à mettre à jour ici).
CLASSES_AION = [
    "Gladiateur",
    "Templier",
    "Assassin",
    "Rôdeur",
    "Sorcier",
    "Spiritualiste",
    "Clerc",
    "Aède",
]

SLOT_LABEL = {"main": "Main", "alt": "Alt (reroll)"}


async def classe_autocomplete(_: discord.Interaction, current: str):
    cur = current.lower()
    return [
        app_commands.Choice(name=c, value=c) for c in CLASSES_AION if cur in c.lower()
    ][:25]


def _ligne_perso(p) -> str:
    """Ex. "🛡️ **Kratos** (Templier)"."""
    return f"{ROLE_EMOJI[p['role']]} **{p['char_name']}** ({p['char_class']})"


@app_commands.guild_only()
class Profil(commands.GroupCog, name="profil"):
    """Enregistrer et consulter les persos des membres."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="definir", description="Enregistrer ton perso principal ou ton reroll")
    @app_commands.describe(
        perso="Main ou alt (reroll) ?",
        nom="Le nom du personnage en jeu",
        classe="Sa classe (suggestions proposées, texte libre accepté)",
        role="Son rôle en groupe",
    )
    @app_commands.choices(
        perso=[
            app_commands.Choice(name="Main", value="main"),
            app_commands.Choice(name="Alt (reroll)", value="alt"),
        ],
        role=[
            app_commands.Choice(name="🛡️ Tank", value="tank"),
            app_commands.Choice(name="💚 Heal", value="heal"),
            app_commands.Choice(name="🗡️ DPS", value="dps"),
        ],
    )
    @app_commands.autocomplete(classe=classe_autocomplete)
    async def definir(
        self,
        interaction: discord.Interaction,
        perso: app_commands.Choice[str],
        nom: app_commands.Range[str, 1, 32],
        classe: app_commands.Range[str, 1, 32],
        role: app_commands.Choice[str],
    ):
        await self.bot.db.set_profile(
            interaction.guild_id,
            interaction.user.id,
            perso.value,
            nom.strip(),
            classe.strip(),
            role.value,
        )
        await interaction.response.send_message(
            f"{SLOT_LABEL[perso.value]} enregistré : {ROLE_EMOJI[role.value]} "
            f"**{nom.strip()}** ({classe.strip()}, {ROLE_LABEL[role.value]}). "
            f"Ta classe s'affichera dans les groupes ! ✅",
            ephemeral=True,
        )

    @app_commands.command(name="voir", description="Voir le profil d'un membre")
    @app_commands.describe(membre="Le membre à consulter (vide = toi)")
    async def voir(
        self, interaction: discord.Interaction, membre: discord.Member | None = None
    ):
        cible = membre or interaction.user
        persos = await self.bot.db.get_profiles(interaction.guild_id, cible.id)
        if not persos:
            qui = "Tu n'as" if cible == interaction.user else f"{cible.display_name} n'a"
            await interaction.response.send_message(
                f"{qui} pas encore de profil. Ça se crée avec `/profil definir` !",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"👤 Profil de {cible.display_name}",
            colour=discord.Colour.blurple(),
        )
        for p in persos:  # main d'abord, puis alt
            embed.add_field(name=SLOT_LABEL[p["slot"]], value=_ligne_perso(p), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="annuaire", description="L'annuaire des persos de la légion")
    async def annuaire(self, interaction: discord.Interaction):
        persos = await self.bot.db.all_profiles(interaction.guild_id)
        if not persos:
            await interaction.response.send_message(
                "L'annuaire est vide : chacun peut s'ajouter avec `/profil definir`.",
                ephemeral=True,
            )
            return

        # Regroupe main + alt par membre (les rows arrivent triées main d'abord).
        par_membre: dict[int, list] = {}
        for p in persos:
            par_membre.setdefault(p["user_id"], []).append(p)

        lignes = []
        for user_id, liste in par_membre.items():
            ligne = f"• <@{user_id}> : {_ligne_perso(liste[0])}"
            if len(liste) > 1:
                ligne += f" — alt : {_ligne_perso(liste[1])}"
            lignes.append(ligne)

        # Marge de sécurité sous la limite Discord de 4096 caractères.
        texte = "\n".join(lignes)
        if len(texte) > 3900:
            texte = texte[:3900] + "\n…"

        embed = discord.Embed(
            title=f"📖 Annuaire de la légion ({len(par_membre)} membres)",
            description=texte,
            colour=discord.Colour.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Profil(bot))
