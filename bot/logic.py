"""Party composition logic, with no Discord dependency.

The idea: we never store who is "in the party" vs "waitlisted". We only
store the sign-ups (role + join order) and recompute the split on every
render with `assign()`. First come, first served; switching roles sends
you to the back of the queue.
"""

ROLES = ("tank", "heal", "dps")

# Standard composition per 5 players: 1 tank / 1 heal / 3 DPS.
STANDARD_RATIO = {"tank": 1, "heal": 1, "dps": 3}
STANDARD_SIZE = sum(STANDARD_RATIO.values())  # 5

# How many characters one member may register. Discord caps a dropdown at 25
# options; well under that keeps the character menus short enough to be useful.
MAX_CHARACTERS = 10

COMPO_STANDARD = "standard"
# Stored value for the no-role-limits mode. Any value other than "standard"
# behaves as open, which keeps old rows created as "libre" working.
COMPO_OPEN = "open"


def standard_slots(size: int) -> dict:
    """Per-role slots in standard mode: 5 -> 1/1/3, 10 (raid/BG) -> 2/2/6."""
    groups = max(1, size // STANDARD_SIZE)
    return {role: n * groups for role, n in STANDARD_RATIO.items()}


def assign(compo: str, size: int, signups: list) -> tuple[list, list]:
    """Splits the sign-ups between the party and the waitlist.

    `signups`: list of dicts (or SQLite rows) with at least a "role" key,
    sorted by join order. Returns (party, waitlist).
    """
    party: list = []
    waitlist: list = []

    if compo == COMPO_STANDARD:
        slots = standard_slots(size)
        taken = {role: 0 for role in ROLES}
        for s in signups:
            role = s["role"]
            if taken[role] < slots[role]:
                taken[role] += 1
                party.append(s)
            else:
                waitlist.append(s)
    else:  # open composition: only the total size matters
        for s in signups:
            if len(party) < size:
                party.append(s)
            else:
                waitlist.append(s)

    return party, waitlist


def role_capacity(compo: str, size: int, role: str) -> int:
    """Number of slots for a given role (useful for display)."""
    if compo == COMPO_STANDARD:
        return standard_slots(size)[role]
    return size
