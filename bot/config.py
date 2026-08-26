"""Configuration du bot, lue depuis les variables d'environnement (ou .env)."""

import os
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

TOKEN = os.getenv("DISCORD_TOKEN", "")

# Si renseigné, les commandes slash sont synchronisées uniquement sur ce
# serveur (visible immédiatement). Sinon, sync global (jusqu'à 1 h de délai).
GUILD_ID = int(os.getenv("GUILD_ID") or 0)

# Fuseau horaire dans lequel les joueurs tapent leurs horaires.
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Europe/Paris"))

# Minutes avant le début de la sortie où le rappel est envoyé.
REMINDER_MINUTES = int(os.getenv("REMINDER_MINUTES") or 15)

# Publication automatique des dispos de la semaine (si activée avec
# /dispo hebdo) : jour (0 = lundi ... 6 = dimanche) et heure.
DISPO_JOUR = int(os.getenv("DISPO_JOUR") or 0)
DISPO_HEURE = int(os.getenv("DISPO_HEURE") or 9)

DB_PATH = os.getenv("DB_PATH", "data/bot.db")
