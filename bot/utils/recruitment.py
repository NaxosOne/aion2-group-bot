"""Pure helpers for the recruitment flow — no Discord dependency, so the
logic is unit-testable without a live guild."""

import re

_CHANNEL_MAX = 90  # Discord caps channel names at 100; leave margin.


def recruitment_enabled(settings) -> bool:
    """True when this guild has an officers' recruitment channel configured."""
    return bool(settings and settings["recruit_channel_id"])


def channel_slug(char_class: str, char_name: str) -> str:
    """A Discord-safe channel name for a candidate's dedicated channel."""
    raw = f"cand-{char_class}-{char_name}".lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return slug[:_CHANNEL_MAX].rstrip("-")


def overwrite_spec(*, candidate_id: int, admin_role_id: int | None, bot_id: int):
    """Who may see the dedicated channel, as plain data the cog turns into
    discord.PermissionOverwrite objects: @everyone denied, candidate + admin
    role (if any) + the bot allowed."""
    allow_view = [candidate_id, bot_id]
    if admin_role_id:
        allow_view.insert(1, admin_role_id)
    return {"everyone": False, "allow_view": allow_view}
