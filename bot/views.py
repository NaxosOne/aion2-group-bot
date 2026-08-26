"""Les boutons sous le message de sortie (Tank / Heal / DPS / Quitter / Annuler).

La vue est "persistante" : grâce aux custom_id fixes, les boutons continuent
de fonctionner même après un redémarrage du bot (elle est ré-enregistrée au
démarrage dans main.py).
"""

import time

import discord

from .embeds import ROLE_EMOJI, ROLE_LABEL, build_event_embed
from .logic import assign


class SignupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # ----- Boutons d'inscription -----

    @discord.ui.button(
        label="Tank", emoji="🛡️", style=discord.ButtonStyle.primary, custom_id="aion2:tank"
    )
    async def bouton_tank(self, interaction: discord.Interaction, _):
        await self._rejoindre(interaction, "tank")

    @discord.ui.button(
        label="Heal", emoji="💚", style=discord.ButtonStyle.success, custom_id="aion2:heal"
    )
    async def bouton_heal(self, interaction: discord.Interaction, _):
        await self._rejoindre(interaction, "heal")

    @discord.ui.button(
        label="DPS", emoji="🗡️", style=discord.ButtonStyle.danger, custom_id="aion2:dps"
    )
    async def bouton_dps(self, interaction: discord.Interaction, _):
        await self._rejoindre(interaction, "dps")

    @discord.ui.button(
        label="Quitter", emoji="🚪", style=discord.ButtonStyle.secondary,
        custom_id="aion2:leave", row=1,
    )
    async def bouton_quitter(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        event = await self._event_ouvert(interaction)
        if event is None:
            return

        groupe_avant, _ = assign(
            event["compo"], event["size"], await db.get_signups(event["message_id"])
        )
        retire = await db.remove_signup(event["message_id"], interaction.user.id)
        if not retire:
            await interaction.response.send_message(
                "Tu n'es pas inscrit à cette sortie.", ephemeral=True
            )
            return

        await self._rafraichir(interaction, event)
        await interaction.followup.send("Tu es désinscrit. 👋", ephemeral=True)
        await self._annoncer_promus(interaction, event, groupe_avant)

    @discord.ui.button(
        label="Annuler la sortie", emoji="🗑️", style=discord.ButtonStyle.secondary,
        custom_id="aion2:cancel", row=1,
    )
    async def bouton_annuler(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        event = await self._event_ouvert(interaction)
        if event is None:
            return

        est_createur = interaction.user.id == event["creator_id"]
        est_modo = interaction.user.guild_permissions.manage_messages
        if not (est_createur or est_modo):
            await interaction.response.send_message(
                "Seul le créateur de la sortie (ou un modérateur) peut l'annuler.",
                ephemeral=True,
            )
            return

        await db.set_status(event["message_id"], "cancelled")
        event = await db.get_event(event["message_id"])
        signups = await db.get_signups(event["message_id"])
        classes = await db.get_main_classes(
            event["guild_id"], [s["user_id"] for s in signups]
        )
        embed = build_event_embed(event, signups, classes)
        await interaction.response.edit_message(embed=embed, view=None)

        groupe, attente = assign(event["compo"], event["size"], signups)
        mentions = " ".join(f"<@{s['user_id']}>" for s in groupe + attente)
        await interaction.followup.send(
            f"❌ **{event['title']}** a été annulée par {interaction.user.mention}."
            + (f"\n{mentions}" if mentions else "")
        )

    # ----- Mécanique commune -----

    async def _rejoindre(self, interaction: discord.Interaction, role: str):
        db = interaction.client.db
        event = await self._event_ouvert(interaction)
        if event is None:
            return

        existant = await db.get_signup(event["message_id"], interaction.user.id)
        if existant and existant["role"] == role:
            await interaction.response.send_message(
                f"Tu es déjà inscrit en {ROLE_EMOJI[role]} **{ROLE_LABEL[role]}**.",
                ephemeral=True,
            )
            return

        groupe_avant, _ = assign(
            event["compo"], event["size"], await db.get_signups(event["message_id"])
        )
        await db.upsert_signup(
            event["message_id"],
            interaction.user.id,
            interaction.user.display_name,
            role,
            time.time(),
        )

        signups = await self._rafraichir(interaction, event)
        groupe, attente = assign(event["compo"], event["size"], signups)
        if any(s["user_id"] == interaction.user.id for s in groupe):
            message = f"Tu es inscrit en {ROLE_EMOJI[role]} **{ROLE_LABEL[role]}** ! ✅"
        else:
            position = next(
                i for i, s in enumerate(attente, start=1)
                if s["user_id"] == interaction.user.id
            )
            message = (
                f"C'est complet pour l'instant : tu es en **liste d'attente** "
                f"(position {position}) en {ROLE_EMOJI[role]} {ROLE_LABEL[role]}. "
                f"Tu seras promu automatiquement si une place se libère. ⏳"
            )
        await interaction.followup.send(message, ephemeral=True)
        await self._annoncer_promus(interaction, event, groupe_avant)

    async def _event_ouvert(self, interaction: discord.Interaction):
        """Retrouve la sortie liée au message cliqué, si elle est encore ouverte."""
        event = await interaction.client.db.get_event(interaction.message.id)
        if event is None:
            await interaction.response.send_message(
                "Je ne retrouve plus cette sortie (base de données réinitialisée ?).",
                ephemeral=True,
            )
            return None
        if event["status"] != "open":
            await interaction.response.send_message(
                "Cette sortie a été annulée.", ephemeral=True
            )
            return None
        return event

    async def _rafraichir(self, interaction: discord.Interaction, event) -> list:
        """Met à jour l'embed du message et retourne les inscriptions à jour."""
        db = interaction.client.db
        signups = await db.get_signups(event["message_id"])
        classes = await db.get_main_classes(
            event["guild_id"], [s["user_id"] for s in signups]
        )
        embed = build_event_embed(event, signups, classes)
        await interaction.response.edit_message(embed=embed, view=self)
        return signups

    async def _annoncer_promus(self, interaction, event, groupe_avant: list):
        """Prévient publiquement les joueurs promus de l'attente vers le groupe."""
        signups = await interaction.client.db.get_signups(event["message_id"])
        groupe, _ = assign(event["compo"], event["size"], signups)
        ids_avant = {s["user_id"] for s in groupe_avant}
        promus = [
            s for s in groupe
            if s["user_id"] not in ids_avant and s["user_id"] != interaction.user.id
        ]
        if promus:
            mentions = " ".join(f"<@{s['user_id']}>" for s in promus)
            await interaction.followup.send(
                f"📣 {mentions} : une place s'est libérée, tu rejoins le groupe "
                f"**{event['title']}** !"
            )
