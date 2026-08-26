"""Tests du parseur d'horaires. Lancer : python -m tests.test_time_parse"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from bot.utils.time_parse import ParseError, parse_date, parse_when

TZ = ZoneInfo("Europe/Paris")
# On fige "maintenant" pour des tests reproductibles : mercredi 26/08/2026, 18h00.
NOW = datetime(2026, 8, 26, 18, 0, tzinfo=TZ)


def p(texte):
    return parse_when(texte, TZ, now=NOW)


def test_heure_seule():
    assert p("21h") == datetime(2026, 8, 26, 21, 0, tzinfo=TZ)
    assert p("21h30") == datetime(2026, 8, 26, 21, 30, tzinfo=TZ)
    assert p("21:30") == datetime(2026, 8, 26, 21, 30, tzinfo=TZ)
    # 9h est déjà passé aujourd'hui -> demain 9h.
    assert p("9h") == datetime(2026, 8, 27, 9, 0, tzinfo=TZ)


def test_mots_cles():
    assert p("demain 21h") == datetime(2026, 8, 27, 21, 0, tzinfo=TZ)
    assert p("aujourd'hui 20h30") == datetime(2026, 8, 26, 20, 30, tzinfo=TZ)
    assert p("Demain 9H00") == datetime(2026, 8, 27, 9, 0, tzinfo=TZ)


def test_dates():
    assert p("30/08 21h") == datetime(2026, 8, 30, 21, 0, tzinfo=TZ)
    assert p("30/08/2026 21:00") == datetime(2026, 8, 30, 21, 0, tzinfo=TZ)
    # 01/01 est passé cette année -> année suivante.
    assert p("01/01 20h") == datetime(2027, 1, 1, 20, 0, tzinfo=TZ)


def test_parse_date():
    pd = lambda t: parse_date(t, TZ, now=NOW)
    assert pd("30/08") == date(2026, 8, 30)
    assert pd("30/08/2026") == date(2026, 8, 30)
    assert pd("aujourd'hui") == date(2026, 8, 26)
    assert pd("demain") == date(2026, 8, 27)
    # Date sans année déjà passée cette année -> l'année prochaine.
    assert pd("01/01") == date(2027, 1, 1)
    for mauvais in ("", "hier", "32/01", "31/02", "01/01/2020"):
        try:
            pd(mauvais)
        except ParseError:
            pass
        else:
            raise AssertionError(f"{mauvais!r} aurait dû être rejeté")


def test_erreurs():
    for mauvais in ("", "n'importe quoi", "25h", "12h75", "31/02 20h",
                    "aujourd'hui 9h", "demain", "30/08/2020 21h"):
        try:
            p(mauvais)
        except ParseError:
            pass
        else:
            raise AssertionError(f"{mauvais!r} aurait dû être rejeté")


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
    print("Tous les tests d'horaires passent.")
