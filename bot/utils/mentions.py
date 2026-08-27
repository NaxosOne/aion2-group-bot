"""Pure helpers for role mentions (no Discord dependency, so easy to test)."""


def ping_permitted(is_default_role: bool, is_moderator: bool) -> bool:
    """Whether a member may make Kisk ping the given role on their behalf.

    Mentioning through the bot bypasses the member's own mention permissions,
    so the default @everyone role is reserved to moderators. Any other role is
    fair game — pinging @Aion2 to rally the legion is the whole point.
    """
    return is_moderator or not is_default_role
