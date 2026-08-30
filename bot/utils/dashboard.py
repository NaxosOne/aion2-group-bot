"""Pure aggregation for the legion dashboard: roster size and role split.

No Discord or database dependency, so these helpers are unit-tested directly.
Implements ROADMAP Phase 4 — Legion dashboard.
"""

from ..logic import ROLES


def roster_stats(profiles: list) -> tuple[int, dict]:
    """``(members with a profile, {role: number of mains in that role})``.

    Counts one main per member (``is_main = 1``); a member whose rows carry no
    flagged main still counts toward the member total. ``profiles``: rows with
    ``user_id``, ``role`` and ``is_main``.
    """
    members = {profile["user_id"] for profile in profiles}
    distribution = {role: 0 for role in ROLES}
    for profile in profiles:
        if profile["is_main"] and profile["role"] in distribution:
            distribution[profile["role"]] += 1
    return len(members), distribution
