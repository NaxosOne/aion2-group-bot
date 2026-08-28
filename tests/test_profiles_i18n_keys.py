"""The /profile and /roster strings resolve from the catalog in both languages.

profiles.py is Discord-coupled (interactions, embeds, autocomplete), so
behavioural verification lives in CI + manual smoke. What we *can* test purely
is that every key those handlers feed to i18n.t() exists in both catalogs and
formats with the exact params the call sites pass, so a renamed or
half-translated key fails here rather than degrading to a raw key in front of
players.
"""

import pytest

from bot import i18n

# key -> the params profiles.py passes at its call site
PROFILE_KEYS = {
    "profile.every_character": {},
    "profile.cap_reached": {"max": 6},
    "profile.note_main": {},
    "profile.note_alt": {},
    "profile.saved": {"detail": "🛡️ **Nami** (Cleric, Tank)", "note": "note text"},
    "profile.main_not_found": {"character": "Nami"},
    "profile.main_set": {"name": "Nami"},
    "profile.show_none_self": {},
    "profile.show_none_other": {"name": "Aria"},
    "profile.show_title_self": {},
    "profile.show_title_other": {"name": "Aria"},
    "profile.show_footer": {"n": 3},
    "profile.delete_mod_only": {},
    "profile.delete_not_found_self": {"character": "Nami"},
    "profile.delete_not_found_other": {"name": "Aria", "character": "Nami"},
    "profile.delete_none_self": {},
    "profile.delete_none_other": {"name": "Aria"},
    "profile.deleted_self_profile": {"count": 2},
    "profile.deleted_other_profile": {"name": "Aria", "count": 2},
    "profile.deleted_self_char": {"char": "Nami"},
    "profile.deleted_other_char": {"name": "Aria", "char": "Nami"},
    "roster.empty": {},
    "roster.alts": {"alts": "Nami, Kratos"},
    "roster.title": {"members": 3, "chars": 7},
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key,params", list(PROFILE_KEYS.items()))
def test_profile_key_resolves_and_formats(key, params, lang):
    out = i18n.t(key, lang, **params)
    # A missing key degrades to the raw key; a formatting failure leaves the
    # {placeholder} markers in place. Neither may happen for a real handler.
    assert out != key
    assert "{" not in out


def test_self_and_other_keys_differ_where_grammar_demands():
    # French possessives can't be built by concatenation, so self/other are
    # separate keys — they must actually resolve to distinct strings.
    self_msg = i18n.t("profile.deleted_self_char", "fr", char="Nami")
    other_msg = i18n.t("profile.deleted_other_char", "fr", name="Aria", char="Nami")
    assert self_msg != other_msg
    assert "Aria" in other_msg
    assert "Aria" not in self_msg
