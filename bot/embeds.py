"""Construction de l'embed (le message riche) qui affiche une sortie."""

import discord

from .logic import COMPO_STANDARD, ROLES, assign, standard_slots

ACTIVITY_EMOJI = {
    "Donjon": "🏰",
    "Raid": "🐉",
    "Battleground": "🚩",
    "PvP": "⚔️",
    "Rift": "🌀",
    "Abysses": "🌌",
    "Autre": "🎲",
}
ROLE_EMOJI = {"tank": "🛡️", "heal": "💚", "dps": "🗡️"}
ROLE_LABEL = {"tank": "Tank", "heal": "Heal", "dps": "DPS"}

COULEUR_OUVERTE = discord.Colour.blurple()
COULEUR_COMPLETE = discord.Colour.green()
COULEUR_ANNULEE = discord.Colour.red()


def _classe(classes: dict, user_id: int) -> str:
    """Suffixe " — Classe" si le membre a rempli son /profil."""
    return f" — *{classes[user_id]}*" if user_id in classes else ""


def _noms(inscrits: list, classes: dict) -> str:
    if not inscrits:
        return "*—*"
    return "\n".join(
        f"• <@{s['user_id']}>{_classe(classes, s['user_id'])}" for s in inscrits
    )


def compo_standard_texte(slots: dict) -> str:
    """Ex. "1 tank / 1 heal / 3 DPS" ou "2 tanks / 2 heals / 6 DPS"."""
    t, h, d = slots["tank"], slots["heal"], slots["dps"]
    return (
        f"{t} tank{'s' if t > 1 else ''} / "
        f"{h} heal{'s' if h > 1 else ''} / {d} DPS"
    )


def build_event_embed(event, signups: list, classes: dict | None = None) -> discord.Embed:
    """Construit l'embed d'une sortie à partir de ses données en base.

    `classes` : {user_id: classe du main} pour afficher la classe des inscrits
    qui ont rempli leur /profil.
    """
    classes = classes or {}
    groupe, attente = assign(event["compo"], event["size"], signups)
    annulee = event["status"] == "cancelled"
    taille = event["size"]
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
        slots = standard_slots(event["size"])
        lignes.append(
            f"Composition : **standard** ({compo_standard_texte(slots)})"
        )
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
        slots = standard_slots(event["size"])
        par_role = {role: [s for s in groupe if s["role"] == role] for role in ROLES}
        for role in ROLES:
            embed.add_field(
                name=(
                    f"{ROLE_EMOJI[role]} {ROLE_LABEL[role]} "
                    f"({len(par_role[role])}/{slots[role]})"
                ),
                value=_noms(par_role[role], classes),
                inline=True,
            )
    else:
        embed.add_field(
            name=f"👥 Groupe ({len(groupe)}/{event['size']})",
            value="\n".join(
                f"• {ROLE_EMOJI[s['role']]} <@{s['user_id']}>"
                f"{_classe(classes, s['user_id'])}"
                for s in groupe
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
