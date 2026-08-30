"""Pure helper behind the weekly availability board: ranking the days by how
many players are free. Run: pytest
"""

from bot.utils.availability import availability_ranking


def mark(user_id, day):
    return {"user_id": user_id, "day": day}


def test_empty_when_nobody_marked():
    assert availability_ranking([]) == []


def test_counts_players_per_day():
    marks = [mark(1, 5), mark(2, 5), mark(3, 4)]
    assert availability_ranking(marks) == [(5, 2), (4, 1)]


def test_most_available_day_comes_first():
    marks = [mark(1, 0), mark(2, 6), mark(3, 6), mark(4, 6)]
    assert availability_ranking(marks)[0] == (6, 3)


def test_ties_break_by_earlier_weekday():
    marks = [mark(1, 5), mark(2, 2)]  # both have one, Tuesday(2) before Saturday(5)
    assert availability_ranking(marks) == [(2, 1), (5, 1)]
