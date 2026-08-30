"""Pure helpers for role mentions (no Discord dependency, so easy to test)."""

# Discord rejects a message body over 2000 characters. Ping strings are built
# from a whole party or pool, which for a maxed siege (up to 200 members) far
# exceeds that, so an unbounded ping would fail to send at all. Kept a little
# under the hard limit to leave room for the message text the mentions follow.
MENTIONS_BUDGET = 1900


def join_mentions(user_ids, budget: int = MENTIONS_BUDGET) -> str:
    """Space-joined ``<@id>`` mentions, trimmed to fit a message body.

    Returns as many whole mentions as fit within ``budget`` characters. Discord
    only pings the first 100 mentions in a message regardless, so trimming an
    oversized list keeps the ping working (some pings) instead of failing the
    send outright (no ping at all).
    """
    parts: list[str] = []
    length = 0
    for user_id in user_ids:
        token = f"<@{user_id}>"
        add = len(token) + (1 if parts else 0)  # +1 for the joining space
        if length + add > budget:
            break
        parts.append(token)
        length += add
    return " ".join(parts)


def ping_permitted(is_default_role: bool, is_moderator: bool) -> bool:
    """Whether a member may make Kisk ping the given role on their behalf.

    Mentioning through the bot bypasses the member's own mention permissions,
    so the default @everyone role is reserved to moderators. Any other role is
    fair game — pinging @Aion2 to rally the legion is the whole point.
    """
    return is_moderator or not is_default_role
