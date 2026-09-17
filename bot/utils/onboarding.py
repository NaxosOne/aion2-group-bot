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


def role_grant_possible(
    bot_top_role_position: int, role_position: int, manage_roles: bool
) -> bool:
    """Whether the bot can actually add `role` to a member.

    Discord requires Manage Roles *and* the bot's top role strictly above the
    target role; otherwise `add_roles` raises Forbidden. Missing either one
    here is exactly what let recruitment silently "accept" candidates who
    never got the member role — surfaced now so admins fix it at config time
    instead of it failing invisibly per-guild at acceptance time.
    """
    return manage_roles and bot_top_role_position > role_position


def should_onboard(
    member_role_added: bool, has_main_profile: bool, is_bot: bool
) -> bool:
    """Whether to send the onboarding DM after a member update.

    A human who just became a validated member and has no main character yet.
    """
    return member_role_added and not has_main_profile and not is_bot


def welcome_on_join(access_gated: bool) -> bool:
    """Whether to post the public welcome board the moment a member joins.

    Only when access is *not* gated: if a validated-member role (or the
    recruitment flow) stands between joining and seeing the channels, a
    newcomer can't read the welcome channel yet and the how-to (member
    commands) is premature — they get the "apply" invite instead, and the
    public greeting waits until they're validated (see `welcome_on_validation`).
    """
    return not access_gated


def welcome_on_validation(member_role_added: bool, is_bot: bool) -> bool:
    """Whether to post the public welcome board after a member update.

    A human who just gained the validated-member role — the moment they gain
    access to the legion's channels — is greeted there and then.
    """
    return member_role_added and not is_bot
