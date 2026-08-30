"""Pure helper for the weekly availability board — no Discord dependency."""


def availability_ranking(marks):
    """Days with at least one available player, most-available first.

    `marks`: rows with a "day" key (0 = Monday … 6 = Sunday). Returns
    `[(day, count), ...]` sorted by count descending, ties broken by the
    earlier weekday.
    """
    counts: dict[int, int] = {}
    for m in marks:
        counts[m["day"]] = counts.get(m["day"], 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
