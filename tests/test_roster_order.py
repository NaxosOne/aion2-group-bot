"""How /roster orders its lines: role, then class, then name. Run: pytest"""

from bot.cogs.profiles import _roster_order


def member(user_id, *characters):
    """(user_id, [rows]) as the roster groups them — main first."""
    return (
        user_id,
        [
            {"user_id": user_id, "role": role, "char_class": klass,
             "char_name": name, "is_main": int(i == 0)}
            for i, (role, klass, name) in enumerate(characters)
        ],
    )


def order(*entries):
    return [uid for uid, _ in sorted(entries, key=_roster_order)]


def test_roles_come_first_in_party_order():
    dps = member(1, ("dps", "Ranger", "Zed"))
    tank = member(2, ("tank", "Templar", "Kratos"))
    heal = member(3, ("heal", "Cleric", "Nami"))
    assert order(dps, tank, heal) == [2, 3, 1]


def test_classes_break_a_role_tie():
    templar = member(1, ("tank", "Templar", "Aaa"))
    gladiator = member(2, ("tank", "Gladiator", "Zzz"))
    assert order(templar, gladiator) == [2, 1]


def test_names_break_a_class_tie():
    zed = member(1, ("dps", "Ranger", "Zed"))
    ashe = member(2, ("dps", "Ranger", "Ashe"))
    assert order(zed, ashe) == [2, 1]


def test_ordering_ignores_case():
    lower = member(1, ("dps", "ranger", "aaa"))
    upper = member(2, ("dps", "Ranger", "AAB"))
    assert order(upper, lower) == [1, 2]


def test_only_the_main_decides_the_line_s_place():
    # The alt is a tank, but the line shows the main, so it sorts as a DPS.
    with_tank_alt = member(1, ("dps", "Ranger", "Zed"), ("tank", "Templar", "Kratos"))
    plain_tank = member(2, ("tank", "Templar", "Aaa"))
    assert order(with_tank_alt, plain_tank) == [2, 1]


def test_an_unknown_role_sorts_last_instead_of_raising():
    odd = member(1, ("bard", "Chanter", "Aaa"))
    dps = member(2, ("dps", "Ranger", "Zed"))
    assert order(odd, dps) == [2, 1]
