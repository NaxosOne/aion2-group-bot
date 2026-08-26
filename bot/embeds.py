"""Construction de l'embed (le message riche) qui affiche une sortie."""

import discord

from .logic import COMPO_STANDARD, ROLES, STANDARD_SLOTS, assign

ACTIVITY_EMOJI = {"Donjon": "🏰", "PvP": "⚔️", "Autre": "🎲"}
ROLE_EMOJI = {"tank": "🛡️", "heal": "💚", "dps": "🗡️"}
ROLE_LABEL = {"tank": "Tank", "heal": "Heal", "dps": "DPS"}

COULEUR_OUVERTE = discord.Colour.blurple()
COULEUR_COMPLETE = discord.Colour.green()
COULEUR_ANNULEE = discord.Colour.red()


def _noms(inscrits: list) -> str:
    return "\n".join(f"• <@{s['user_id']}>" for s in inscrits) if inscrits else "*—*"


def build_event_embed(event, signups: list) -> discord.Embed:
    """Construit l'embed d'une sortie à partir de ses données en base."""
    groupe, attente = assign(event["compo"], event["size"], signups)
    annulee = event["status"] == "cancelled"
    taille = 5 if event["compo"] == COMPO_STANDARD else event["size"]
    complete = len(groupe) >= taille

    emoji = ACTIVITY_EMOJI.get(event["activity"], "📣")
    titre = f"{emoji} {event['title']}"
    if annulee:
        titre = f"❌ [ANNULÉE] {event['title']}"

    lignes = []
    if event["description"]:
        lignes.append(event["description"])
    if event["starts_at"]:
        lignes.append(f"🕘 <t:{event['starts_at']}:F> (<t:{event['starts_at']}:R>)")
    if event["compo"] == COMPO_STANDARD:
        lignes.append("Composition : **standard** (1 tank / 1 heal / 3 DPS)")
    else:
        lignes.append(f"Composition : **libre** ({event['size']} places)")

    if annulee:
        couleur = COULEUR_ANNULEE
    elif complete:
        couleur = COULEUR_COMPLETE
    else:
        couleur = COULEUR_OUVERTE

    embed = discord.Embed(title=titre, description="\n".join(lignes), colour=couleur)

    if event["compo"] == COMPO_STANDARD:
        par_role = {role: [s for s in groupe if s["role"] == role] for role in ROLES}
        for role in ROLES:
            embed.add_field(
                name=(
                    f"{ROLE_EMOJI[role]} {ROLE_LABEL[role]} "
                    f"({len(par_role[role])}/{STANDARD_SLOTS[role]})"
                ),
                value=_noms(par_role[role]),
                inline=True,
            )
    else:
        embed.add_field(
            name=f"👥 Groupe ({len(groupe)}/{event['size']})",
            value="\n".join(
                f"• {ROLE_EMOJI[s['role']]} <@{s['user_id']}>" for s in groupe
            )
            or "*—*",
            inline=False,
        )

    if attente:
        embed.add_field(
            name=f"⏳ Liste d'attente ({len(attente)})",
            value="\n".join(
                f"{i}. {ROLE_EMOJI[s['role']]} <@{s['user_id']}>"
                for i, s in enumerate(attente, start=1)
            ),
            inline=False,
        )

    embed.set_footer(
        text=f"{event['activity']} • Créée par {event['creator_name']}"
        + (" • COMPLET" if complete and not annulee else "")
    )
    return embed
