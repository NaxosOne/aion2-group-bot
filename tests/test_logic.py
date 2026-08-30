"""Tests for the party/waitlist split. Run: pytest"""

from bot.logic import (
    MOVE_DOWN,
    MOVE_UP,
    COMPO_OPEN,
    COMPO_STANDARD,
    assign,
    missing_slots,
    reorder_priorities,
    split_groups,
    standard_slots,
)


def s(user_id, role):
    return {"user_id": user_id, "role": role}


def sp(user_id, role, priority):
    return {"user_id": user_id, "role": role, "priority": priority}


def ids(items):
    return [x["user_id"] for x in items]


def test_standard_comp():
    # 1 tank / 1 heal / 3 dps: the 2nd tank goes to the waitlist.
    signups = [s(1, "tank"), s(2, "tank"), s(3, "heal"), s(4, "dps")]
    party, waitlist = assign(COMPO_STANDARD, 5, signups)
    assert ids(party) == [1, 3, 4]
    assert ids(waitlist) == [2]

    # A 4th DPS goes to the waitlist.
    signups = [s(1, "dps"), s(2, "dps"), s(3, "dps"), s(4, "dps")]
    party, waitlist = assign(COMPO_STANDARD, 5, signups)
    assert ids(party) == [1, 2, 3]
    assert ids(waitlist) == [4]


def test_standard_promotion():
    # Tank 1 leaves: tank 2 is promoted automatically.
    signups = [s(2, "tank"), s(3, "heal")]  # user 1 was removed
    party, waitlist = assign(COMPO_STANDARD, 5, signups)
    assert ids(party) == [2, 3]
    assert waitlist == []


def test_standard_slots():
    assert standard_slots(5) == {"tank": 1, "heal": 1, "dps": 3}
    assert standard_slots(10) == {"tank": 2, "heal": 2, "dps": 6}


def test_standard_10():
    # Party of 10 (raid/battleground): 2 tanks / 2 heals / 6 DPS.
    signups = (
        [s(i, "tank") for i in (1, 2, 3)]        # 3rd tank waitlisted
        + [s(i, "heal") for i in (4, 5)]
        + [s(i, "dps") for i in range(6, 13)]    # 7th DPS waitlisted
    )
    party, waitlist = assign(COMPO_STANDARD, 10, signups)
    assert ids(party) == [1, 2, 4, 5, 6, 7, 8, 9, 10, 11]
    assert ids(waitlist) == [3, 12]


def test_open():
    # 5 slots, roles don't matter: the 6th goes to the waitlist.
    signups = [s(i, "dps") for i in range(1, 7)]
    party, waitlist = assign(COMPO_OPEN, 5, signups)
    assert ids(party) == [1, 2, 3, 4, 5]
    assert ids(waitlist) == [6]

    # Custom size (e.g. a raid of 10).
    party, waitlist = assign(COMPO_OPEN, 10, signups)
    assert len(party) == 6 and waitlist == []


def test_open_two_tanks_ok():
    # In open mode, 2 tanks and 1 heal are fine (abyss farming case).
    signups = [s(1, "tank"), s(2, "tank"), s(3, "heal"), s(4, "dps"), s(5, "dps")]
    party, waitlist = assign(COMPO_OPEN, 5, signups)
    assert len(party) == 5 and waitlist == []


def test_legacy_french_value():
    # Rows stored as "libre" by earlier versions still behave as open mode.
    signups = [s(i, "dps") for i in range(1, 7)]
    party, waitlist = assign("libre", 5, signups)
    assert len(party) == 5 and ids(waitlist) == [6]


def test_priority_bumps_within_role_standard():
    # 3 DPS slots. A later-joined DPS given a higher priority jumps the
    # queue for its own role, sending the lowest-priority DPS to the waitlist.
    signups = [sp(1, "dps", 0), sp(2, "dps", 0), sp(3, "dps", 0), sp(4, "dps", 5)]
    party, waitlist = assign(COMPO_STANDARD, 5, signups)
    assert ids(party) == [4, 1, 2]
    assert ids(waitlist) == [3]


def test_priority_bumps_in_open():
    # Open party of 2: the third sign-up, boosted, takes a party seat.
    signups = [sp(1, "dps", 0), sp(2, "dps", 0), sp(3, "heal", 1)]
    party, waitlist = assign(COMPO_OPEN, 2, signups)
    assert ids(party) == [3, 1]
    assert ids(waitlist) == [2]


def test_priority_stable_within_same_value():
    # Equal priority preserves join order (first come, first served).
    signups = [sp(1, "dps", 2), sp(2, "dps", 2), sp(3, "dps", 2)]
    party, waitlist = assign(COMPO_OPEN, 2, signups)
    assert ids(party) == [1, 2]
    assert ids(waitlist) == [3]


def test_priority_missing_key_defaults_to_zero():
    # A sign-up with no priority key ranks below an explicitly boosted one,
    # so old rows created before the column existed still behave as FCFS.
    signups = [s(1, "dps"), s(2, "dps"), sp(3, "dps", 4)]
    party, waitlist = assign(COMPO_OPEN, 2, signups)
    assert ids(party) == [3, 1]
    assert ids(waitlist) == [2]


def test_missing_slots_partial_standard():
    # 1 tank / 1 heal / 3 dps, only the tank filled: heal and all DPS open.
    signups = [s(1, "tank")]
    assert missing_slots(COMPO_STANDARD, 5, signups) == {"heal": 1, "dps": 3}


def test_missing_slots_omits_filled_roles():
    # A filled role drops out; only the two open DPS remain.
    signups = [s(1, "tank"), s(2, "heal"), s(3, "dps")]
    assert missing_slots(COMPO_STANDARD, 5, signups) == {"dps": 2}


def test_missing_slots_empty_when_full():
    signups = [s(1, "tank"), s(2, "heal"), s(3, "dps"), s(4, "dps"), s(5, "dps")]
    assert missing_slots(COMPO_STANDARD, 5, signups) == {}


def test_missing_slots_ignores_waitlisted_overflow():
    # A second tank is waitlisted, not filling heal/dps: they stay open.
    signups = [s(1, "tank"), s(2, "tank")]
    assert missing_slots(COMPO_STANDARD, 5, signups) == {"heal": 1, "dps": 3}


def test_missing_slots_open_mode_is_empty():
    # Open mode has no per-role slots, so nothing to report.
    signups = [s(1, "dps")]
    assert missing_slots(COMPO_OPEN, 5, signups) == {}


def test_split_groups_chunks_members_in_order():
    assert split_groups([1, 2, 3, 4, 5, 6], groups=2, group_size=3) == [
        [1, 2, 3], [4, 5, 6],
    ]


def test_split_groups_last_group_can_be_partial():
    assert split_groups([1, 2, 3, 4, 5], groups=2, group_size=3) == [
        [1, 2, 3], [4, 5],
    ]


def test_split_groups_always_returns_the_requested_number():
    # Fewer members than one group still shows every (empty) group.
    assert split_groups([1, 2], groups=3, group_size=3) == [[1, 2], [], []]


def order_of(priorities):
    """The ranking implied by a {user_id: priority} map (highest first)."""
    return sorted(priorities, key=lambda uid: priorities[uid], reverse=True)


def test_move_up_swaps_with_predecessor():
    # 3 climbs one rank, over 2.
    result = reorder_priorities([1, 2, 3, 4], 3, MOVE_UP)
    assert order_of(result) == [1, 3, 2, 4]


def test_move_down_swaps_with_successor():
    # 2 drops one rank, under 3 (mirror of moving 3 up).
    result = reorder_priorities([1, 2, 3, 4], 2, MOVE_DOWN)
    assert order_of(result) == [1, 3, 2, 4]


def test_move_up_at_top_is_noop():
    result = reorder_priorities([1, 2, 3], 1, MOVE_UP)
    assert order_of(result) == [1, 2, 3]


def test_move_down_at_bottom_is_noop():
    result = reorder_priorities([1, 2, 3], 3, MOVE_DOWN)
    assert order_of(result) == [1, 2, 3]


def test_reorder_priorities_are_strictly_descending():
    # Dense, distinct ranks let a later swap stay unambiguous.
    result = reorder_priorities([1, 2, 3], 3, MOVE_UP)
    assert result == {1: 3, 3: 2, 2: 1}
