"""Pure Kisk permission predicates: a configured admin role plus Discord's
native Manage Server / Manage Messages. Run: pytest
"""

from bot.utils.permissions import is_admin, is_moderator


def test_manage_guild_is_always_admin():
    assert is_admin(None, set(), manage_guild=True) is True


def test_configured_role_grants_admin():
    assert is_admin(5, {5, 9}, manage_guild=False) is True


def test_without_role_or_permission_not_admin():
    assert is_admin(5, {9}, manage_guild=False) is False


def test_no_configured_role_falls_back_to_permission():
    # A member holding the (unrelated) role id is not admin when none is set.
    assert is_admin(None, {5}, manage_guild=False) is False


def test_manage_messages_is_moderator():
    assert is_moderator(
        None, set(), manage_guild=False, manage_messages=True
    ) is True


def test_admin_implies_moderator_via_role():
    assert is_moderator(
        5, {5}, manage_guild=False, manage_messages=False
    ) is True


def test_admin_implies_moderator_via_permission():
    assert is_moderator(
        None, set(), manage_guild=True, manage_messages=False
    ) is True


def test_plain_member_is_not_moderator():
    assert is_moderator(
        5, {9}, manage_guild=False, manage_messages=False
    ) is False
