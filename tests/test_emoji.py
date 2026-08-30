"""Tests for the configured-emoji validation. Run: pytest"""

import logging

from bot.utils.emoji import is_valid, resolve


def test_accepts_real_emoji():
    for value in ("🏰", "🐉", "⚔️", "🛡️", "🌌", "👻", "1️⃣", "👍🏽"):
        assert is_valid(value), value


def test_accepts_custom_emoji_codes():
    assert is_valid("<:dungeon:123456789012345678>")
    assert is_valid("<a:spinning:123456789012345678>")


def test_rejects_what_discord_would_refuse():
    # A shortcode, a bare name, a truncated id, quotes or stray whitespace:
    # each of these answered every panel click with 400 Invalid Form Body.
    for value in (
        "",
        ":dungeon:",
        "dungeon",
        "<:dungeon:12>",
        "<dungeon>",
        '"🏰"',
        "🏰 ",
        " 🏰",
        "🏰🏰x",
        "ð\x9f\x8f°",  # UTF-8 read as latin-1: a .env saved in the wrong encoding
    ):
        assert not is_valid(value), value


def test_resolve_falls_back_and_warns(caplog):
    with caplog.at_level(logging.WARNING):
        assert resolve(":dungeon:", "🏰", "EMOJI_DUNGEON") == "🏰"
    assert "EMOJI_DUNGEON" in caplog.text

    # Valid values and empty settings pass through silently.
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        assert resolve("🐉", "🏰", "EMOJI_DUNGEON") == "🐉"
        assert resolve(None, "🏰", "EMOJI_DUNGEON") == "🏰"
        assert resolve("", "🏰", "EMOJI_DUNGEON") == "🏰"
    assert caplog.text == ""
