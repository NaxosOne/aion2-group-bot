"""The schedule-parser error messages resolve from the catalog in both
languages. ParseError now carries a translated message built from these keys,
so a renamed key or a missing {value} would surface here."""

import pytest

from bot import i18n

TIME_KEYS = {
    "time.bad_time": {},
    "time.empty": {},
    "time.invalid_time": {"value": "25:00"},
    "time.invalid_date": {"value": "31/02"},
    "time.date_past": {},
    "time.time_past": {},
    "time.bad_date": {},
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key,params", list(TIME_KEYS.items()))
def test_time_key_resolves_and_formats(key, params, lang):
    out = i18n.t(key, lang, **params)
    assert out != key
    assert "{" not in out
