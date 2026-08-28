"""The bot's presence text. Run: pytest"""

from bot import config
from bot.embeds import ACTIVITY_EMOJI, PRESENCE_ACTIVITY_EMOJI
from bot.utils.emoji import CUSTOM_EMOJI_RE


def test_presence_emojis_are_never_custom():
    # Discord prints a bot's presence literally, so a custom emoji would show
    # as its raw <:rift:154256...> code instead of an icon.
    for activity, emoji in PRESENCE_ACTIVITY_EMOJI.items():
        assert not CUSTOM_EMOJI_RE.match(emoji), activity


def test_presence_uses_the_built_in_defaults():
    for activity, default in config.DEFAULT_EMOJI_ACTIVITY.items():
        assert PRESENCE_ACTIVITY_EMOJI[activity] == default


def test_both_mappings_cover_the_same_activities():
    # Including the French labels events created by earlier versions carry.
    assert set(PRESENCE_ACTIVITY_EMOJI) == set(ACTIVITY_EMOJI)
    assert "Donjon" in PRESENCE_ACTIVITY_EMOJI
