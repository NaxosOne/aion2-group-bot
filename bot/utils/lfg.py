"""Pure LFG-pool logic: dropping expired entries, grouping the live pool by
activity, and matching the pool against an event's still-open roles.

No Discord or database dependency, so these helpers are unit-tested directly.
Implements the "Looking for group" board rules (ROADMAP Phase 3 — LFG system).
"""

# How long a "looking" entry stays live, offered as /lfg durations.
LFG_DURATIONS = {"1h": 3600, "3h": 3 * 3600, "6h": 6 * 3600}
DEFAULT_DURATION = "3h"


def active_entries(entries: list, now: int) -> list:
    """The pool with expired entries dropped (expires_at strictly after now)."""
    return [entry for entry in entries if entry["expires_at"] > now]


def group_by_activity(entries: list, activities) -> list:
    """Live pool grouped as ``[(activity, [entries])]`` in ``activities`` order.

    Only activities with at least one entry are returned; within an activity,
    entries keep their incoming order (the DB sorts them by soonest expiry).
    """
    grouped = []
    for activity in activities:
        members = [entry for entry in entries if entry["activity"] == activity]
        if members:
            grouped.append((activity, members))
    return grouped


def matching_pool(entries: list, activity: str, roles, now: int) -> list:
    """Live entries looking for ``activity`` whose role is in ``roles``.

    ``roles``: an iterable of the still-open roles to match; when ``None`` every
    role matches (an open-composition event needs any role). Used to invite pool
    members to an event that still has room.
    """
    wanted = None if roles is None else set(roles)
    return [
        entry
        for entry in active_entries(entries, now)
        if entry["activity"] == activity
        and (wanted is None or entry["role"] in wanted)
    ]
