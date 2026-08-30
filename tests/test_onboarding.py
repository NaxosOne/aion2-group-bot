"""Tests for the pure onboarding helpers. Run: pytest"""

from bot.utils.onboarding import (
    onboard_custom_id,
    role_just_added,
    should_onboard,
)


def test_custom_id_round_trips_the_guild_id():
    cid = onboard_custom_id(123456789012345678)
    assert cid == "kisk:onboard:123456789012345678"
    assert int(cid.rsplit(":", 1)[1]) == 123456789012345678


def test_role_just_added_detects_the_transition():
    assert role_just_added(7, before_ids={1, 2}, after_ids={1, 2, 7}) is True
    # Already had it: not a transition.
    assert role_just_added(7, before_ids={7}, after_ids={7}) is False
    # Never got it.
    assert role_just_added(7, before_ids={1}, after_ids={1, 2}) is False


def test_should_onboard_only_new_humans_without_a_profile():
    assert (
        should_onboard(member_role_added=True, has_main_profile=False, is_bot=False)
        is True
    )
    # Already has a profile.
    assert (
        should_onboard(member_role_added=True, has_main_profile=True, is_bot=False)
        is False
    )
    # Role wasn't just added.
    assert (
        should_onboard(member_role_added=False, has_main_profile=False, is_bot=False)
        is False
    )
    # Bots never get onboarded.
    assert (
        should_onboard(member_role_added=True, has_main_profile=False, is_bot=True)
        is False
    )
