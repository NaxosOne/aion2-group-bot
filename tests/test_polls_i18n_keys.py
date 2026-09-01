"""The polls / availability strings resolve from the catalog in both languages.

polls.py is Discord-coupled (buttons, interactions, background loop), so
behavioural verification lives in CI + manual smoke. What we *can* test purely
is that every key polls.py feeds to i18n.t() exists in both catalogs and formats
with the exact params the handlers pass, so a renamed or half-translated key
fails here rather than degrading to a raw key in front of players.
"""

import pytest

from bot import i18n

# key -> the params polls.py passes at its call site
POLL_KEYS = {
    "weekday.0": {},
    "weekday.1": {},
    "weekday.2": {},
    "weekday.3": {},
    "weekday.4": {},
    "weekday.5": {},
    "weekday.6": {},
    "poll.closed_prefix": {},
    "poll.votes": {"total": 3},
    "poll.not_found_or_closed": {},
    "poll.only_author_close": {},
    "poll.not_found": {},
    "poll.closed": {},
    "poll.save_failed": {},
    "availability.week_of": {"date": "01/09"},
    "availability.title": {"week": "week of 01/09"},
    "availability.hint": {},
    "availability.most_available": {"days": "Saturday (8)"},
    "availability.board_gone": {},
    "availability.weekly_on": {"day": "Monday", "hour": 20},
    "availability.weekly_off": {},
    "availability.save_failed": {},
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key,params", list(POLL_KEYS.items()))
def test_poll_key_resolves_and_formats(key, params, lang):
    out = i18n.t(key, lang, **params)
    # A missing key degrades to the raw key; a formatting failure leaves the
    # {placeholder} markers in place. Neither may happen for a real handler.
    assert out != key
    assert "{" not in out
