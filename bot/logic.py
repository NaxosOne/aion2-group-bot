"""Logique de composition des groupes, sans dépendance à Discord.

Le principe : on ne stocke jamais qui est "titulaire" ou "en attente".
On stocke seulement la liste des inscrits (rôle + ordre d'arrivée), et on
recalcule la répartition à chaque affichage avec `assign()`. Premier arrivé,
premier servi ; changer de rôle remet en fin de file.
"""

ROLES = ("tank", "heal", "dps")

# Composition "standard" par tranche de 5 joueurs : 1 tank / 1 heal / 3 DPS.
STANDARD_RATIO = {"tank": 1, "heal": 1, "dps": 3}
STANDARD_SIZE = sum(STANDARD_RATIO.values())  # 5

COMPO_STANDARD = "standard"
COMPO_LIBRE = "libre"


def standard_slots(size: int) -> dict:
    """Places par rôle en compo standard : 5 -> 1/1/3, 10 (raid/BG) -> 2/2/6."""
    groupes = max(1, size // STANDARD_SIZE)
    return {role: n * groupes for role, n in STANDARD_RATIO.items()}


def assign(compo: str, size: int, signups: list) -> tuple[list, list]:
    """Répartit les inscrits entre le groupe et la liste d'attente.

    `signups` : liste de dicts (ou rows SQLite) avec au moins la clé "role",
    triée par ordre d'inscription. Retourne (groupe, attente).
    """
    groupe: list = []
    attente: list = []

    if compo == COMPO_STANDARD:
        slots = standard_slots(size)
        pris = {role: 0 for role in ROLES}
        for s in signups:
            role = s["role"]
            if pris[role] < slots[role]:
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
        return standard_slots(size)[role]
    return size
