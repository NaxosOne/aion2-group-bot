"""Tests for the role-ping permission gate. Run: pytest"""

from bot.utils.mentions import ping_permitted


def test_normal_role_allowed_for_anyone():
    # A regular role (e.g. @Aion2) can be pinged by any member.
    assert ping_permitted(is_default_role=False, is_moderator=False) is True
    assert ping_permitted(is_default_role=False, is_moderator=True) is True


def test_everyone_requires_moderator():
    # The default @everyone role is reserved to moderators.
    assert ping_permitted(is_default_role=True, is_moderator=False) is False
    assert ping_permitted(is_default_role=True, is_moderator=True) is True
