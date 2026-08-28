"""Pure helpers for event discussion threads (no Discord dependency)."""

# Discord caps thread names at 100 characters.
THREAD_NAME_LIMIT = 100


def event_thread_name(title: str) -> str:
    """The discussion thread's name for an event: its title, length-capped."""
    return title.strip()[:THREAD_NAME_LIMIT]
