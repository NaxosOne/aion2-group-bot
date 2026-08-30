"""Persistent view button labels resolve from the catalog in both languages.

The button labels of the persistent views (sign-up, RSVP, poll, availability,
panel) are baked into the message at send time, translated via i18n.t(). These
tests guard the catalog side: every button-label key and every weekday_short
key must exist and format in both languages, so a renamed or half-translated
key fails here rather than shipping a raw key onto a button.
"""

import pytest

from bot import i18n

# Every translatable persistent-view button label, plus the short weekday
# labels used on the availability board buttons.
BUTTON_KEYS = [
    "signup.btn_leave",
    "signup.btn_done",
    "signup.btn_cancel",
    "signup.btn_manage",
    "signup.btn_up",
    "signup.btn_down",
    "signup.btn_edit",
    "signup.btn_calendar",
    "rsvp.btn_coming",
    "rsvp.btn_not_coming",
    "poll.btn_close",
    "availability.btn_clear",
    "panel.btn_create_event",
    "panel.btn_report_absence",
    *[f"weekday_short.{i}" for i in range(7)],
]


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key", BUTTON_KEYS)
def test_button_label_resolves(key, lang):
    out = i18n.t(key, lang)
    # A missing key degrades to the raw key; these labels carry no
    # placeholders, so no stray {marker} may survive either.
    assert out != key
    assert "{" not in out
    assert out.strip()
