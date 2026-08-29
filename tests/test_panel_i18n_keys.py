"""The /panel, event-setup and /channels strings resolve in both languages.

panel.py is Discord-coupled (buttons, modals, selects), so behavioural
verification lives in CI + manual smoke. What we *can* test purely is that every
key panel.py feeds to i18n.t() exists in both catalogs and formats with the
exact params the handlers pass, so a renamed or half-translated key fails here
rather than degrading to a raw key in front of players.
"""

import pytest

from bot import i18n

# key -> the params panel.py passes at its call site
PANEL_KEYS = {
    "panel.setup_label_standard5": {},
    "panel.setup_desc_standard5": {},
    "panel.setup_label_standard10": {},
    "panel.setup_desc_standard10": {},
    "panel.setup_label_open5": {},
    "panel.setup_desc_open5": {},
    "panel.setup_label_open10": {},
    "panel.setup_desc_open10": {},
    "panel.setup_label_open25": {},
    "panel.setup_desc_open25": {},
    "panel.activity_placeholder": {},
    "panel.setup_placeholder": {},
    "panel.event_step1_title": {},
    "panel.event_step1_body": {
        "type_line": "🗡️ **PvP**",
        "label": "Party of 5",
        "description": "1 tank / 1 heal / 3 DPS",
    },
    "panel.continue": {},
    "panel.pick_type_first": {},
    "panel.modal_new_event": {"activity": "Raid"},
    "panel.field_title": {},
    "panel.field_type_name": {},
    "panel.field_type_name_ph": {},
    "panel.field_when": {},
    "panel.field_when_ph": {},
    "panel.field_description": {},
    "panel.modal_away_title": {},
    "panel.field_from": {},
    "panel.field_from_ph": {},
    "panel.field_until": {},
    "panel.field_until_ph": {},
    "panel.field_reason": {},
    "panel.field_reason_ph": {},
    "channels.reset_done": {},
    "channels.destinations": {
        "events": "<#1>", "absences": "<#2>", "rsvp": "<#3>",
    },
    "channels.where_used": {},
    "panel.target_events": {"channel": "<#1>"},
    "panel.target_absences": {"channel": "<#2>"},
    "panel.title": {},
    "panel.body": {"tank": "🛡️", "heal": "💚", "dps": "🗡️", "where": ""},
    "panel.pin_tip": {},
    "panel.posted": {"link": "https://x/1"},
    "panel.refreshed": {"link": "https://x/1"},
    "panel.refresh_forbidden": {},
    "redeploy.admin_only": {},
    "redeploy.done": {"events": 3, "panel": "refreshed"},
    "redeploy.panel_yes": {},
    "redeploy.panel_no": {},
}

# Discord hard limits the event-setup surfaces must respect in every language.
MODAL_TITLE_KEYS = ("panel.modal_away_title",)
FIELD_LABEL_KEYS = (
    "panel.field_title", "panel.field_type_name", "panel.field_when",
    "panel.field_description", "panel.field_from", "panel.field_until",
    "panel.field_reason",
)
PLACEHOLDER_KEYS = (
    "panel.field_type_name_ph", "panel.field_when_ph", "panel.field_from_ph",
    "panel.field_until_ph", "panel.field_reason_ph", "panel.activity_placeholder",
    "panel.setup_placeholder",
)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key,params", list(PANEL_KEYS.items()))
def test_panel_key_resolves_and_formats(key, params, lang):
    out = i18n.t(key, lang, **params)
    # A missing key degrades to the raw key; a formatting failure leaves the
    # {placeholder} markers in place. Neither may happen for a real handler.
    assert out != key
    assert "{" not in out


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key", MODAL_TITLE_KEYS + FIELD_LABEL_KEYS)
def test_labels_within_discord_limit(key, lang):
    # Modal titles and TextInput labels are capped at 45 characters by Discord.
    assert len(i18n.t(key, lang)) <= 45


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key", PLACEHOLDER_KEYS)
def test_placeholders_within_discord_limit(key, lang):
    # TextInput/Select placeholders are capped at 100 characters by Discord.
    assert len(i18n.t(key, lang)) <= 100
