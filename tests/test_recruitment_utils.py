from bot.utils.recruitment import channel_slug, overwrite_spec, recruitment_enabled


def test_recruitment_enabled_needs_a_configured_channel():
    assert recruitment_enabled({"recruit_channel_id": 123}) is True
    assert recruitment_enabled({"recruit_channel_id": None}) is False
    assert recruitment_enabled(None) is False


def test_channel_slug_is_discord_safe():
    assert channel_slug("Sorcerer", "Kro Nos!!") == "cand-sorcerer-kro-nos"
    assert channel_slug("Cleric", "") == "cand-cleric"
    long = channel_slug("Ranger", "x" * 200)
    assert len(long) <= 90 and long.startswith("cand-ranger-")


def test_overwrite_spec_lists_who_may_see_the_channel():
    spec = overwrite_spec(candidate_id=42, admin_role_id=7, bot_id=99)
    assert spec["everyone"] is False
    assert set(spec["allow_view"]) == {42, 7, 99}
    spec2 = overwrite_spec(candidate_id=42, admin_role_id=None, bot_id=99)
    assert set(spec2["allow_view"]) == {42, 99}
