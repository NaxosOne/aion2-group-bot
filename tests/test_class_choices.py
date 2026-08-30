"""/profile set must not accept a class outside the list. Run: pytest"""

from bot import config
from bot.cogs.profiles import AION_CLASSES, Profile


def option(display_name):
    """One option of /profile set, by the name Discord shows."""
    command = next(c for c in Profile.__cog_app_commands__ if c.name == "set")
    return next(
        param
        for param in command._params.values()
        if param.display_name == display_name
    )


def test_the_class_option_is_a_closed_list():
    choices = option("class").choices
    assert choices, "free text would let a typo through"
    assert [c.value for c in choices] == AION_CLASSES


def test_the_list_follows_the_configured_classes():
    # Adding Fist Fighter to config.CLASS_EMOJI is meant to be enough.
    assert AION_CLASSES == list(config.CLASS_EMOJI)


def test_the_list_fits_discord_s_choice_cap():
    assert len(option("class").choices) <= 25


def test_the_role_option_stays_a_closed_list_too():
    assert [c.value for c in option("role").choices] == ["tank", "heal", "dps"]


def test_the_character_name_stays_free_text():
    # Names are the one thing that genuinely has to be typed.
    assert not option("name").choices
