"""Logique de composition des groupes, sans dépendance à Discord.

Le principe : on ne stocke jamais qui est "titulaire" ou "en attente".
On stocke seulement la liste des inscrits (rôle + ordre d'arrivée), et on
recalcule la répartition à chaque affichage avec `assign()`. Premier arrivé,
premier servi ; changer de rôle remet en fin de file.
"""

ROLES = ("tank", "heal", "dps")

# Composition "standard" d'un groupe de 5 : 1 tank / 1 heal / 3 DPS.
STANDARD_SLOTS = {"tank": 1, "heal": 1, "dps": 3}
STANDARD_SIZE = sum(STANDARD_SLOTS.values())

COMPO_STANDARD = "standard"
COMPO_LIBRE = "libre"


def assign(compo: str, size: int, signups: list) -> tuple[list, list]:
    """Répartit les inscrits entre le groupe et la liste d'attente.

    `signups` : liste de dicts (ou rows SQLite) avec au moins la clé "role",
    triée par ordre d'inscription. Retourne (groupe, attente).
    """
    groupe: list = []
    attente: list = []

    if compo == COMPO_STANDARD:
        pris = {role: 0 for role in ROLES}
        for s in signups:
            role = s["role"]
            if pris[role] < STANDARD_SLOTS[role]:
                pris[role] += 1
                groupe.append(s)
            else:
                attente.append(s)
    else:  # compo libre : seule la taille totale compte
        for s in signups:
            if len(groupe) < size:
                groupe.append(s)
            else:
                attente.append(s)

    return groupe, attente


def role_capacity(compo: str, size: int, role: str) -> int:
    """Nombre de places pour un rôle donné (utile pour l'affichage)."""
    if compo == COMPO_STANDARD:
        return STANDARD_SLOTS[role]
    return size
