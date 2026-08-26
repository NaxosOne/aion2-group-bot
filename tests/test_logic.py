"""Tests de la répartition groupe / liste d'attente. Lancer : python -m tests.test_logic"""

from bot.logic import COMPO_LIBRE, COMPO_STANDARD, assign


def s(user_id, role):
    return {"user_id": user_id, "role": role}


def ids(liste):
    return [x["user_id"] for x in liste]


def test_standard_compo():
    # 1 tank / 1 heal / 3 dps : le 2e tank part en attente.
    signups = [s(1, "tank"), s(2, "tank"), s(3, "heal"), s(4, "dps")]
    groupe, attente = assign(COMPO_STANDARD, 5, signups)
    assert ids(groupe) == [1, 3, 4]
    assert ids(attente) == [2]

    # Un 4e DPS part en attente.
    signups = [s(1, "dps"), s(2, "dps"), s(3, "dps"), s(4, "dps")]
    groupe, attente = assign(COMPO_STANDARD, 5, signups)
    assert ids(groupe) == [1, 2, 3]
    assert ids(attente) == [4]


def test_standard_promotion():
    # Le tank 1 se désinscrit : le tank 2 est promu automatiquement.
    signups = [s(2, "tank"), s(3, "heal")]  # le user 1 a été retiré
    groupe, attente = assign(COMPO_STANDARD, 5, signups)
    assert ids(groupe) == [2, 3]
    assert attente == []


def test_libre():
    # 5 places, peu importe les rôles : le 6e part en attente.
    signups = [s(i, "dps") for i in range(1, 7)]
    groupe, attente = assign(COMPO_LIBRE, 5, signups)
    assert ids(groupe) == [1, 2, 3, 4, 5]
    assert ids(attente) == [6]

    # Taille personnalisée (ex. raid de 10).
    groupe, attente = assign(COMPO_LIBRE, 10, signups)
    assert len(groupe) == 6 and attente == []


def test_libre_deux_tanks_ok():
    # En libre, 2 tanks et 1 heal passent sans souci (cas farm abysses).
    signups = [s(1, "tank"), s(2, "tank"), s(3, "heal"), s(4, "dps"), s(5, "dps")]
    groupe, attente = assign(COMPO_LIBRE, 5, signups)
    assert len(groupe) == 5 and attente == []


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
    print("Tous les tests de logique passent.")
