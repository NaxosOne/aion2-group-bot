"""The absences / welcome / announcement strings resolve from the catalog in
both languages. legion.py and register_absence are Discord-coupled, so this
guards the keys and their params — a renamed or half-translated key fails here
rather than degrading to a raw key in front of members."""

import pytest

from bot import i18n

VIEW_KEYS = {
    "announce.modal_title": {},
    "announce.field_title": {},
    "announce.field_message": {},
    "announce.footer": {"name": "Naxos"},
    "absences.title": {},
    "absences.none": {},
    "absences.ongoing": {},
    "absences.starting": {"date": "<t:1:D>"},
    "absences.line": {"user": 1, "state": "🔴", "date": "<t:1:D>"},
    "back.welcome_back": {"mention": "<@1>"},
    "back.none": {},
    "welcome_cmd.on": {},
    "welcome_cmd.off": {},
    "welcome_join.title": {},
    "welcome_join.body": {},
    "absence.end_before_start": {},
    "absence.period_single": {"date": "<t:1:D>"},
    "absence.period_range": {"start": "<t:1:D>", "end": "<t:2:D>"},
    "absence.announcement": {"mention": "<@1>", "period": "on <t:1:D>", "reason": ""},
    "absence.post_forbidden": {"channel": "<#1>"},
    "absence.registered": {"channel": "<#1>", "link": "https://x"},
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key,params", list(VIEW_KEYS.items()))
def test_legion_key_resolves_and_formats(key, params, lang):
    out = i18n.t(key, lang, **params)
    assert out != key
    assert "{" not in out
