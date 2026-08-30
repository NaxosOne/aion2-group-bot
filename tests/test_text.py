"""Truncating long text to fit Discord's field/description limits. Run: pytest"""

from bot.utils.text import truncate_field


def test_short_value_is_unchanged():
    assert truncate_field("hello") == "hello"


def test_value_at_the_limit_is_unchanged():
    value = "x" * 1024
    assert truncate_field(value, limit=1024) == value


def test_long_value_is_cut_line_aware_and_within_limit():
    value = "\n".join("m" * 40 for _ in range(50))  # ~2049 chars
    out = truncate_field(value, limit=1024)
    assert len(out) <= 1024
    assert out.endswith("…")
    # Kept content stops on a whole line (no partial line before the ellipsis).
    assert out[: -len("\n…")] in value


def test_a_single_over_long_line_is_hard_cut():
    out = truncate_field("y" * 2000, limit=1024)
    assert len(out) == 1024
    assert out.endswith("…")


def test_respects_a_custom_limit():
    assert len(truncate_field("a" * 100, limit=10)) == 10
