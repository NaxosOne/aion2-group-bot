"""Pure helpers for RSVP tallies (no Discord dependency)."""


def rsvp_summary(
    party_ids: list[int], responses: dict[int, str]
) -> tuple[list[int], list[int], list[int]]:
    """Splits the party into (confirmed, declined, awaiting).

    `party_ids` is the signed-up party (join order). `responses` maps a user id
    to 'yes' or 'no'. Anyone in the party without a response is still awaiting.
    """
    confirmed = [u for u in party_ids if responses.get(u) == "yes"]
    declined = [u for u in party_ids if responses.get(u) == "no"]
    awaiting = [u for u in party_ids if u not in responses]
    return confirmed, declined, awaiting
