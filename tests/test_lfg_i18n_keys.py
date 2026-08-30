"""The LFG strings resolve from the catalog in both languages.

lfg.py and the event "Invite LFG" button are Discord-coupled, so behavioural
verification lives in CI + manual smoke. What we *can* test purely is that every
key they feed to i18n.t() exists in both catalogs and formats with the exact
params the handlers pass, so a renamed or half-translated key fails here rather
than degrading to a raw key in front of players.
"""

import pytest

from bot import i18n

# key -> the params the LFG cog / view / event integration pass at each call site
LFG_KEYS = {
    "lfg.title": {},
    "lfg.hint": {},
    "lfg.empty": {},
    "lfg.footer": {"total": 3},
    "lfg.pick_activity": {},
    "lfg.pick_role": {},
    "lfg.pick_both": {},
    "lfg.btn_confirm": {},
    "lfg.btn_looking": {},
    "lfg.btn_stop": {},
    "lfg.looking_prompt": {},
    "lfg.looking_added": {"emoji": "🏰", "activity": "Dungeon", "role": "Tank"},
    "lfg.stopped": {},
    "lfg.not_looking": {},
    "lfg.board_refreshed": {"link": "https://discord.com/x"},
    "lfg.board_forbidden": {},
    "lfg.board_posted": {"link": "https://discord.com/x"},
    "lfg.invite_ping": {
        "mentions": "<@1>",
        "emoji": "🏰",
        "activity": "Dungeon",
        "link": "https://discord.com/x",
    },
    "lfg.invite_none": {},
    "lfg.invite_full": {},
    "lfg.invite_forbidden": {},
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key,params", list(LFG_KEYS.items()))
def test_lfg_key_resolves_and_formats(key, params, lang):
    out = i18n.t(key, lang, **params)
    # A missing key degrades to the raw key; a formatting failure leaves the
    # {placeholder} markers in place. Neither may happen for a real handler.
    assert out != key
    assert "{" not in out
