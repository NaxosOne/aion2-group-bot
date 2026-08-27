"""Bot configuration, read from environment variables (or .env)."""

import os
from zoneinfo import ZoneInfo

from .utils.emoji import resolve as _emoji

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

# Role emojis. Defaults are Unicode; to use custom emojis, upload PNGs in the
# developer portal (your application -> Emojis tab), then paste the emoji
# codes here, e.g. EMOJI_TANK=<:tank:123456789012345678>. Ready-made icons
# matching Kisk's style live in assets/emoji/.
EMOJI_TANK = _emoji(os.getenv("EMOJI_TANK"), "🛡️", "EMOJI_TANK")
EMOJI_HEAL = _emoji(os.getenv("EMOJI_HEAL"), "💚", "EMOJI_HEAL")
EMOJI_DPS = _emoji(os.getenv("EMOJI_DPS"), "🗡️", "EMOJI_DPS")

# Event-type emojis, overridable the same way (EMOJI_DUNGEON, EMOJI_RAID...).
# Note: custom emojis show up in embeds and messages, but Discord renders the
# slash-command choice lists as plain text, where only Unicode emojis work.
EMOJI_ACTIVITY = {
    name: _emoji(
        os.getenv(f"EMOJI_{name.upper()}"), default, f"EMOJI_{name.upper()}"
    )
    for name, default in {
        "Dungeon": "🏰",
        "Raid": "🐉",
        "Battleground": "🚩",
        "PvP": "⚔️",
        "Rift": "🌀",
        "Abyss": "🌌",
        "Other": "🎲",
    }.items()
}

# Aion 2 class emojis, overridable the same way (EMOJI_GLADIATOR, EMOJI_TEMPLAR
# ...). Defaults are Unicode; to use the real in-game icons, upload them as
# custom emojis on your Discord (developer portal -> Emojis) and paste the codes
# here, e.g. EMOJI_GLADIATOR=<:gladiator:123456789012345678>.
CLASS_EMOJI = {
    name: _emoji(
        os.getenv(f"EMOJI_{name.upper()}"), default, f"EMOJI_{name.upper()}"
    )
    for name, default in {
        "Gladiator": "⚔️",
        "Templar": "🛡️",
        "Assassin": "🗡️",
        "Ranger": "🏹",
        "Sorcerer": "🔥",
        "Spiritmaster": "👻",
        "Cleric": "✨",
        "Chanter": "🎵",
    }.items()
}

DB_PATH = os.getenv("DB_PATH", "data/bot.db")
