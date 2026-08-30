"""The event-creation, /events, /rsvp and reminder strings resolve in both langs.

actions.publish_event and cogs/groups.py are Discord-coupled (interactions,
loops), so behavioural verification lives in CI + manual smoke. What we *can*
test purely is that every key those handlers feed to i18n.t() exists in both
catalogs and formats with the exact params passed at each call site, so a
renamed or half-translated key fails here rather than degrading to a raw key
in front of players.
"""

import pytest

from bot import i18n

# key -> the params the handler passes at its call site
EVENT_KEYS = {
    # actions.publish_event / _open_event_thread
    "event.mod_only_everyone": {},
    "event.post_forbidden": {"channel": "#general"},
    "event.post_failed": {"channel": "#general", "error": "500 Internal"},
    "event.save_failed": {},
    "event.created": {"channel": "#general", "link": "https://x/1"},
    "event.thread_intro": {"title": "Fire Temple HM"},
    # cogs/groups.py /events
    "events.none": {},
    "events.title": {},
    "events.no_time": {},
    "events.line": {
        "title": "Fire Temple HM",
        "link": "https://x/1",
        "activity": "Dungeon",
        "when": "<t:1:R>",
        "signed": 3,
        "size": 5,
    },
    "events.waitlist_suffix": {"n": 2},
    # cogs/groups.py recurring events
    "recurring.mod_only": {},
    "recurring.needs_time": {},
    "recurring.created": {"title": "Raid", "when": "<t:1:F>"},
    "recurring.list_empty": {},
    "recurring.list_header": {},
    "recurring.list_line": {"id": 3, "title": "Raid", "when": "<t:1:F>"},
    "recurring.stopped": {"id": 3},
    "recurring.not_found": {"id": 3},
    # embeds.py "still needed" summary
    "event.needs": {"roles": "1 🛡️ Tank"},
    "event.needs_role": {"n": 1, "emoji": "🛡️", "label": "Tank"},
    "event.open_slot": {},
    "event.group": {"n": 2},
    "siege.open_only": {},
    # cogs/groups.py /rsvp
    "rsvp.need_id": {},
    "rsvp.not_found_here": {},
    "rsvp.nobody_signed_up": {},
    "rsvp.post_failed": {},
    "rsvp.posted": {"link": "https://x/1"},
    # cogs/groups.py _send_reminder
    "reminder.text": {
        "title": "Fire Temple HM",
        "link": "https://x/1",
        "when": "<t:1:R>",
    },
    "reminder.nobody": {},
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key,params", list(EVENT_KEYS.items()))
def test_event_key_resolves_and_formats(key, params, lang):
    out = i18n.t(key, lang, **params)
    # A missing key degrades to the raw key; a formatting failure leaves the
    # {placeholder} markers in place. Neither may happen for a real handler.
    assert out != key
    assert "{" not in out


def test_events_line_composes_with_waitlist_suffix():
    line = i18n.t(
        "events.line",
        "en",
        title="Raid",
        link="https://x/1",
        activity="Raid",
        when="<t:1:R>",
        signed=5,
        size=5,
    )
    line += i18n.t("events.waitlist_suffix", "en", n=2)
    assert "Raid" in line
    assert "waitlisted" in line


def test_reminder_nobody_composition_reads_naturally():
    text = i18n.t(
        "reminder.text", "fr", title="Raid", link="https://x/1", when="bientôt"
    )
    full = text + i18n.t("reminder.nobody", "fr")
    assert "Raid" in full
    assert "{" not in full
