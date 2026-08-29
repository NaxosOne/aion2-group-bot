"""Pure helpers behind temporary event voice channels: when to create one,
what to name it, and when it has gone stale. Run: pytest
"""

from bot.utils.voice import voice_channel_name, voice_due, voice_is_stale

LEAD = 15 * 60      # create 15 min before the start
GRACE = 3 * 60 * 60  # a channel is stale 3 h after the start


def test_voice_not_due_before_the_window():
    # 20 min before start, with a 15 min lead: too early.
    assert voice_due(1_000_000, now=1_000_000 - 20 * 60, lead_s=LEAD) is False


def test_voice_due_inside_the_window():
    assert voice_due(1_000_000, now=1_000_000 - 10 * 60, lead_s=LEAD) is True


def test_voice_due_at_and_after_start():
    assert voice_due(1_000_000, now=1_000_000, lead_s=LEAD) is True


def test_voice_never_due_without_a_schedule():
    assert voice_due(None, now=1_000_000, lead_s=LEAD) is False


def test_voice_channel_name_prefixes_the_speaker():
    assert voice_channel_name("Fire Temple HM") == "🔊 Fire Temple HM"


def test_voice_channel_name_is_capped_at_100_chars():
    name = voice_channel_name("x" * 200)
    assert len(name) == 100


def test_voice_stale_when_done_or_cancelled():
    assert voice_is_stale("done", 1_000_000, now=1_000_000, grace_s=GRACE) is True
    assert voice_is_stale("cancelled", None, now=0, grace_s=GRACE) is True


def test_voice_stale_when_long_past_its_start():
    assert voice_is_stale(
        "open", 1_000_000, now=1_000_000 + GRACE + 1, grace_s=GRACE
    ) is True


def test_voice_not_stale_while_the_event_is_live():
    assert voice_is_stale(
        "open", 1_000_000, now=1_000_000 + 10 * 60, grace_s=GRACE
    ) is False
