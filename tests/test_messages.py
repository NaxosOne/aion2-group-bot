"""Tests for the message-id parser. Run: pytest"""

from bot.utils.messages import parse_message_id


def test_parse_raw_id():
    assert parse_message_id("123456789012345678") == 123456789012345678
    assert parse_message_id("  42 ") == 42


def test_parse_message_link():
    link = "https://discord.com/channels/111/222/333444555"
    assert parse_message_id(link) == 333444555
    assert parse_message_id(link + "/") == 333444555


def test_parse_rejects_garbage():
    assert parse_message_id("") is None
    assert parse_message_id("not a link") is None
    assert parse_message_id("https://discord.com/channels/111/222/abc") is None
