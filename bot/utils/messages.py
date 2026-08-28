"""Pure helpers for referencing Discord messages (no Discord dependency)."""


def parse_message_id(text: str) -> int | None:
    """The message id from a raw id or a Discord message link, else None.

    Accepts "123456789012345678" or
    "https://discord.com/channels/<guild>/<channel>/<message>".
    """
    text = text.strip()
    if text.isdigit():
        return int(text)
    last = text.rstrip("/").rsplit("/", 1)[-1]
    return int(last) if last.isdigit() else None
