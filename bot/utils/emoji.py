"""Validating the emojis configured through the environment.

Discord rejects an entire message when one select option carries an emoji it
cannot parse: a single bad value in `.env` answers every click with
`400 Invalid Form Body — Invalid emoji` and takes the whole panel down. So
values are checked here instead, and anything unusable falls back to the
built-in default with a warning in the logs.
"""

import logging
import re

log = logging.getLogger(__name__)

# <:name:id> or <a:name:id>, the form the developer portal gives you.
CUSTOM_EMOJI_RE = re.compile(r"^<a?:[A-Za-z0-9_]{2,32}:\d{15,25}>$")

# Characters that decorate an emoji without being one: variation selector,
# zero-width joiner, keycap mark and the skin-tone modifiers.
_DECORATIONS = {0xFE0F, 0x200D, 0x20E3} | set(range(0x1F3FB, 0x1F400))

# Below this codepoint nothing is an emoji; it also catches the mojibake a
# `.env` saved in the wrong encoding produces (© is the lowest real one).
_LOWEST_EMOJI_CODEPOINT = 0x00A9


def is_valid(value: str) -> bool:
    """Whether Discord will accept this string as a button or option emoji."""
    if not value:
        return False
    if CUSTOM_EMOJI_RE.match(value):
        return True
    if value.endswith("⃣"):  # keycap, e.g. 1️⃣ — starts with a digit
        return True
    core = [c for c in value if ord(c) not in _DECORATIONS]
    return bool(core) and all(ord(c) >= _LOWEST_EMOJI_CODEPOINT for c in core)


def resolve(value: str | None, default: str, variable: str) -> str:
    """The configured emoji, or the default when it is missing or unusable."""
    if not value:
        return default
    if is_valid(value):
        return value
    log.warning(
        "%s=%r is not a valid emoji, using %s instead. Use a plain emoji "
        "(🏰) or the portal's custom code (<:name:123456789012345678>).",
        variable, value, default,
    )
    return default
