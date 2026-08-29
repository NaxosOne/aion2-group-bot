"""The /language and /admin-role strings resolve and format in both languages.

settings.py is Discord-coupled, so behavioural verification lives in CI. What we
*can* test purely is that every key it feeds to i18n.t() exists in both catalogs
and formats with the exact params the handler passes.
"""

import pytest

from bot import i18n

SETTINGS_KEYS = {
    "language.set_confirm": {"language": "English"},
    "language.auto_confirm": {},
    "adminrole.set_confirm": {"role": "<@&1>"},
    "adminrole.cleared": {},
    "adminrole.current": {"role": "<@&1>"},
    "adminrole.none": {},
    "adminrole.forbidden": {},
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key,params", list(SETTINGS_KEYS.items()))
def test_settings_key_resolves_and_formats(key, params, lang):
    out = i18n.t(key, lang, **params)
    assert out != key
    assert "{" not in out
