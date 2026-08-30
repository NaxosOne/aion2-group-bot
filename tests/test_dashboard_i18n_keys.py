"""The dashboard strings resolve from the catalog in both languages.

dashboard.py is Discord-coupled (command, background loop), so behavioural
verification lives in CI + manual smoke. What we *can* test purely is that every
key it feeds to i18n.t() exists in both catalogs and formats with the exact
params the handlers pass, so a renamed or half-translated key fails here rather
than degrading to a raw key in front of players.
"""

import pytest

from bot import i18n

DASHBOARD_KEYS = {
    "dashboard.title": {},
    "dashboard.subtitle": {},
    "dashboard.events": {},
    "dashboard.no_events": {},
    "dashboard.no_time": {},
    "dashboard.lfg": {},
    "dashboard.lfg_line": {"looking": 3, "available": 2},
    "dashboard.recurring": {},
    "dashboard.absences": {},
    "dashboard.no_absences": {},
    "dashboard.roster": {},
    "dashboard.roster_members": {"members": 12},
    "dashboard.footer": {"updated": "<t:1:R>"},
    "dashboard.posted": {"link": "https://discord.com/x"},
    "dashboard.refreshed": {"link": "https://discord.com/x"},
    "dashboard.forbidden": {},
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key,params", list(DASHBOARD_KEYS.items()))
def test_dashboard_key_resolves_and_formats(key, params, lang):
    out = i18n.t(key, lang, **params)
    assert out != key
    assert "{" not in out
