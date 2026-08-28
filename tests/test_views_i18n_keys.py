"""The sign-up / RSVP view strings resolve from the catalog in both languages.

views.py itself is Discord-coupled (buttons, interactions), so behavioural
verification lives in CI + manual smoke. What we *can* test purely is that every
key views.py now feeds to i18n.t() exists in both catalogs and formats with the
exact params the handlers pass, so a renamed or half-translated key fails here
rather than degrading to a raw key in front of players.
"""

import pytest

from bot import i18n

# key -> the params views.py passes at its call site
VIEW_KEYS = {
    "signup.char_gone": {},
    "signup.bringing": {"name": "Aria", "title": "Raid"},
    "signup.already_role": {"emoji": "🛡️", "label": "Tank"},
    "signup.pick_switch": {"emoji": "🛡️", "label": "Tank"},
    "signup.pick_join": {"emoji": "🛡️", "label": "Tank"},
    "signup.pick_placeholder": {},
    "signup.with_character": {"name": "Aria"},
    "signup.joined": {"emoji": "🛡️", "label": "Tank", "who": " with **Aria**"},
    "signup.waitlisted": {
        "position": 2, "emoji": "🛡️", "label": "Tank", "who": ""
    },
    "signup.left": {},
    "signup.not_signed_up": {},
    "signup.only_creator_close": {},
    "signup.only_creator_cancel": {},
    "signup.completed": {"title": "Raid"},
    "signup.cancelled": {"title": "Raid", "who": "<@1>"},
    "signup.promoted": {"mentions": "<@1>", "title": "Raid"},
    "signup.event_gone": {},
    "signup.event_done": {},
    "signup.event_cancelled": {},
    "rsvp.inactive": {},
    "rsvp.sign_up_first": {},
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key,params", list(VIEW_KEYS.items()))
def test_view_key_resolves_and_formats(key, params, lang):
    out = i18n.t(key, lang, **params)
    # A missing key degrades to the raw key; a formatting failure leaves the
    # {placeholder} markers in place. Neither may happen for a real handler.
    assert out != key
    assert "{" not in out


def test_who_composition_joined_reads_naturally():
    who = i18n.t("signup.with_character", "en", name="Aria")
    msg = i18n.t("signup.joined", "en", emoji="🛡️", label="Tank", who=who)
    assert "with **Aria**" in msg
    assert "Tank" in msg


def test_who_empty_when_no_character():
    msg = i18n.t("signup.joined", "fr", emoji="🛡️", label="Tank", who="")
    assert "Tank" in msg
    assert "None" not in msg
