"""Interprétation des horaires tapés en français dans /sortie.

Formats acceptés (l'heure est obligatoire, la date est optionnelle) :
    "21h"  "21h30"  "21:30"          -> aujourd'hui, ou demain si déjà passé
    "demain 21h"  "aujourd'hui 20h30"
    "30/08 21h"  "30/08/2026 21:00"  -> l'année est déduite si absente
"""

import re
from datetime import date, datetime, timedelta

FORMAT_AIDE = (
    "Formats acceptés : `21h`, `21h30`, `demain 21h`, `30/08 21h`, "
    "`30/08/2026 21:00` (l'heure est obligatoire)."
)

FORMAT_AIDE_DATE = "Formats acceptés : `30/08`, `30/08/2026`, `aujourd'hui`, `demain`."


class ParseError(ValueError):
    """Erreur d'interprétation, avec un message affichable à l'utilisateur."""


_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?:\s+|$)")
_TIME_RE = re.compile(r"^(\d{1,2})\s*[h:]\s*(\d{2})?$")


def parse_when(text: str, tz, now: datetime | None = None) -> datetime:
    """Convertit un texte comme "demain 21h" en datetime avec fuseau horaire."""
    now = (now or datetime.now(tz)).astimezone(tz)
    s = " ".join(text.strip().lower().split())
    if not s:
        raise ParseError(f"Horaire vide. {FORMAT_AIDE}")

    # 1) La partie date : mot-clé, date chiffrée, ou rien (= aujourd'hui).
    offset = None  # décalage en jours pour "aujourd'hui"/"demain"
    date_part = None  # (jour, mois, année ou None)
    for mot, decalage in (
        ("aujourd'hui", 0),
        ("aujourdhui", 0),
        ("auj", 0),
        ("demain", 1),
    ):
        if s == mot or s.startswith(mot + " "):
            offset = decalage
            s = s[len(mot):].strip()
            break
    if offset is None:
        m = _DATE_RE.match(s)
        if m:
            jour, mois = int(m.group(1)), int(m.group(2))
            annee = m.group(3)
            if annee is not None:
                annee = int(annee)
                if annee < 100:
                    annee += 2000
            date_part = (jour, mois, annee)
            s = s[m.end():].strip()

    # 2) La partie heure, obligatoire.
    m = _TIME_RE.match(s)
    if not m:
        raise ParseError(f"Je n'ai pas compris cet horaire. {FORMAT_AIDE}")
    heure, minute = int(m.group(1)), int(m.group(2) or 0)
    if heure > 23 or minute > 59:
        raise ParseError(f"Heure invalide : `{heure:02d}:{minute:02d}`.")

    # 3) Assemblage.
    if date_part is not None:
        jour, mois, annee = date_part
        try:
            dt = datetime(annee or now.year, mois, jour, heure, minute, tzinfo=tz)
        except ValueError:
            raise ParseError(f"Date invalide : `{jour:02d}/{mois:02d}`.") from None
        if dt <= now:
            if annee is None:
                # "30/08 21h" alors qu'on est en septembre -> année suivante.
                dt = dt.replace(year=now.year + 1)
            else:
                raise ParseError("Cette date est déjà passée.")
        return dt

    base = now.date() + timedelta(days=offset or 0)
    dt = datetime(base.year, base.month, base.day, heure, minute, tzinfo=tz)
    if dt <= now:
        if offset is None:
            # "21h" alors qu'il est 22h -> demain 21h.
            dt += timedelta(days=1)
        else:
            raise ParseError("Cet horaire est déjà passé.")
    return dt


_DATE_SEULE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$")


def parse_date(text: str, tz, now: datetime | None = None) -> date:
    """Convertit "30/08", "30/08/2026", "aujourd'hui" ou "demain" en date."""
    now = (now or datetime.now(tz)).astimezone(tz)
    s = " ".join(text.strip().lower().split())
    if s in ("aujourd'hui", "aujourdhui", "auj"):
        return now.date()
    if s == "demain":
        return now.date() + timedelta(days=1)

    m = _DATE_SEULE_RE.match(s)
    if not m:
        raise ParseError(f"Je n'ai pas compris cette date. {FORMAT_AIDE_DATE}")
    jour, mois = int(m.group(1)), int(m.group(2))
    annee = m.group(3)
    if annee is not None:
        annee = int(annee)
        if annee < 100:
            annee += 2000
    try:
        d = date(annee or now.year, mois, jour)
        if d < now.date() and annee is None:
            # "01/01" alors qu'on est en août -> l'année prochaine.
            d = date(now.year + 1, mois, jour)
    except ValueError:
        raise ParseError(f"Date invalide : `{jour:02d}/{mois:02d}`.") from None
    if d < now.date():
        raise ParseError("Cette date est déjà passée.")
    return d
