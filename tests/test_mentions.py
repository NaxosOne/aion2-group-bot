"""Tests for the role-ping permission gate. Run: pytest"""

from bot.utils.mentions import join_mentions, ping_permitted


def test_join_mentions_formats_ids():
    assert join_mentions([1, 2, 3]) == "<@1> <@2> <@3>"


def test_join_mentions_empty_is_blank():
    assert join_mentions([]) == ""


def test_join_mentions_trims_to_fit_the_budget():
    # 200 ids would blow Discord's 2000-char body; only whole mentions that fit
    # the budget are kept, so the send succeeds instead of failing outright.
    ids = list(range(1, 201))
    out = join_mentions(ids, budget=100)
    assert len(out) <= 100
    assert out.startswith("<@1> <@2>")
    # Never a dangling separator or a half-written mention.
    assert not out.endswith(" ")
    assert out.count("<@") == out.count(">")


def test_join_mentions_keeps_everything_when_it_fits():
    ids = list(range(1, 51))
    out = join_mentions(ids)  # default budget is well above this
    assert out.count("<@") == 50


def test_normal_role_allowed_for_anyone():
    # A regular role (e.g. @Aion2) can be pinged by any member.
    assert ping_permitted(is_default_role=False, is_moderator=False) is True
    assert ping_permitted(is_default_role=False, is_moderator=True) is True


def test_everyone_requires_moderator():
    # The default @everyone role is reserved to moderators.
    assert ping_permitted(is_default_role=True, is_moderator=False) is False
    assert ping_permitted(is_default_role=True, is_moderator=True) is True
