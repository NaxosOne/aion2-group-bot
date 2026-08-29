"""The onboarding flow strings resolve from the catalog in both languages.

onboarding.py is Discord-coupled (buttons, modals, member events), so
behavioural verification lives in CI + manual smoke. What we *can* test purely
is that every key the cog feeds to i18n.t() exists in both catalogs and formats
with the exact params the handlers pass — so a renamed or half-translated key
fails here rather than degrading to a raw key in front of players.
"""

import pytest

from bot import i18n

# key -> the params onboarding.py passes at its call site
ONBOARD_KEYS = {
    "onboard.setup_title_main": {},
    "onboard.setup_title_alt": {},
    "onboard.modal_title_main": {},
    "onboard.modal_title_alt": {},
    "onboard.class_placeholder": {},
    "onboard.role_placeholder": {},
    "onboard.not_set": {},
    "onboard.summary_body": {"class_line": "🛡️ **Gladiator**", "role_line": "**Tank**"},
    "onboard.continue": {},
    "onboard.pick_first": {},
    "onboard.name_label": {},
    "onboard.name_placeholder": {},
    "onboard.cap_reached": {"max": 5},
    "onboard.added_more": {"detail": "**Kratos** — 🛡️ Gladiator, Tank"},
    "onboard.added_main": {"detail": "**Kratos** — 🛡️ Gladiator, Tank"},
    "onboard.add_char": {},
    "onboard.already_setup": {},
    "onboard.your_legion": {},
    "onboard.welcome_title": {"guild": "Naxos"},
    "onboard.welcome_body": {},
    "onboard.dm_fallback_prefix": {},
    "onboard.configure_button": {},
    "onboard.role_set_confirm": {"role": "Member"},
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key,params", list(ONBOARD_KEYS.items()))
def test_onboard_key_resolves_and_formats(key, params, lang):
    out = i18n.t(key, lang, **params)
    # A missing key degrades to the raw key; a formatting failure leaves the
    # {placeholder} markers in place. Neither may happen for a real handler.
    assert out != key
    assert "{" not in out
