"""Pure helpers for the profile-onboarding flow (no Discord dependency)."""

CUSTOM_ID_PREFIX = "kisk:onboard"


def onboard_custom_id(guild_id: int) -> str:
    """The persistent button custom_id carrying the guild it onboards for.

    The button lives in a DM (no guild context), so the guild id travels in the
    custom_id and is parsed back when the member clicks.
    """
    return f"{CUSTOM_ID_PREFIX}:{guild_id}"


def role_just_added(role_id: int, before_ids: set[int], after_ids: set[int]) -> bool:
    """Whether `role_id` was present after an update but not before."""
    return role_id in after_ids and role_id not in before_ids


def should_onboard(
    member_role_added: bool, has_main_profile: bool, is_bot: bool
) -> bool:
    """Whether to send the onboarding DM after a member update.

    A human who just became a validated member and has no main character yet.
    """
    return member_role_added and not has_main_profile and not is_bot
