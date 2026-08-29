"""Pure iCalendar (.ics) export of events — no Discord dependency.

Produces an RFC 5545 VCALENDAR with one VEVENT per scheduled event, so a member
can drop the server's upcoming events into their own calendar.
"""

import time
from datetime import datetime, timezone

_PRODID = "-//Kisk//Aion 2//EN"


def _ics_time(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    # RFC 5545 text escaping; the backslash must be replaced first.
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def build_calendar(
    events, *, default_duration_s: int = 3600, dtstamp_ts=None
) -> str:
    """A VCALENDAR string for the scheduled events (unscheduled ones skipped).

    No end time is stored, so each event lasts `default_duration_s`. `dtstamp_ts`
    overrides the generation time, which keeps the output deterministic in tests.
    """
    stamp = _ics_time(dtstamp_ts if dtstamp_ts is not None else int(time.time()))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{_PRODID}",
        "CALSCALE:GREGORIAN",
    ]
    for event in events:
        start = event["starts_at"]
        if start is None:
            continue
        lines += [
            "BEGIN:VEVENT",
            f"UID:{event['message_id']}@kisk",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{_ics_time(start)}",
            f"DTEND:{_ics_time(start + default_duration_s)}",
            f"SUMMARY:{_escape(event['title'])}",
        ]
        description = event["description"]
        if description:
            lines.append(f"DESCRIPTION:{_escape(description)}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
