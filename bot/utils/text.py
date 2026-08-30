"""Fit text to Discord's length limits (embed field 1024, description 4096,
message 2000) without breaking a line in the middle where it can be helped.
"""

_ELLIPSIS = "…"


def truncate_field(value: str, limit: int = 1024) -> str:
    """Trim `value` to at most `limit` characters, keeping whole lines.

    Drops trailing lines and appends an ellipsis; a single line longer than the
    limit is hard-cut. A value already within the limit is returned unchanged.
    """
    if len(value) <= limit:
        return value
    tail = "\n" + _ELLIPSIS
    kept: list[str] = []
    total = 0
    for line in value.split("\n"):
        add = len(line) + (1 if kept else 0)  # +1 for the joining newline
        if total + add + len(tail) > limit:
            break
        kept.append(line)
        total += add
    if not kept:
        return value[: limit - len(_ELLIPSIS)] + _ELLIPSIS
    return "\n".join(kept) + tail
