"""Bot configuration, read from environment variables (or .env)."""

import os
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

TOKEN = os.getenv("DISCORD_TOKEN", "")

# If set, slash commands are synced to this guild only (visible immediately).
# Otherwise the sync is global (can take up to 1 hour to propagate).
GUILD_ID = int(os.getenv("GUILD_ID") or 0)

# Timezone in which players type their schedules.
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Europe/Paris"))

# How many minutes before an event's start the reminder is sent.
REMINDER_MINUTES = int(os.getenv("REMINDER_MINUTES") or 15)

# Automatic weekly availability board (enabled with /availability weekly):
# day (0 = Monday ... 6 = Sunday) and hour of posting.
AVAILABILITY_DAY = int(os.getenv("AVAILABILITY_DAY") or 0)
AVAILABILITY_HOUR = int(os.getenv("AVAILABILITY_HOUR") or 9)

DB_PATH = os.getenv("DB_PATH", "data/bot.db")
