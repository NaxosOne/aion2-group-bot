"""Tests for the pure RSVP tally helper. Run: pytest"""

from bot.utils.rsvp import rsvp_summary


def test_rsvp_summary_partitions_the_party():
    party = [1, 2, 3, 4]
    responses = {1: "yes", 2: "no"}  # 3 and 4 haven't replied
    confirmed, declined, awaiting = rsvp_summary(party, responses)
    assert confirmed == [1]
    assert declined == [2]
    assert awaiting == [3, 4]


def test_rsvp_summary_ignores_responses_from_outside_the_party():
    party = [1, 2]
    responses = {1: "yes", 99: "yes"}  # 99 is not in the party
    confirmed, declined, awaiting = rsvp_summary(party, responses)
    assert confirmed == [1]
    assert declined == []
    assert awaiting == [2]
