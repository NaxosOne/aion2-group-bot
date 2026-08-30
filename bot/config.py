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

# How many minutes before start the "are you coming?" RSVP prompt is posted.
RSVP_MINUTES = int(os.getenv("RSVP_MINUTES") or 60)

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

# The built-in event-type emojis. Kept reachable because a few surfaces
# cannot render a custom emoji and have to fall back to Unicode: Discord
# shows slash-command choice lists as plain text, and prints the bot's
# presence literally, raw <:name:id> code and all.
DEFAULT_EMOJI_ACTIVITY = {
    "Dungeon": "🏰",
    "Raid": "🐉",
    "Battleground": "🚩",
    "PvP": "⚔️",
    "Rift": "🌀",
    "Abyss": "🌌",
    "Other": "🎲",
}

# The same list, with the .env overrides applied (EMOJI_DUNGEON, EMOJI_RAID
# ...). Use this everywhere a custom emoji renders: embeds, messages,
# buttons and menus.
EMOJI_ACTIVITY = {
    name: _emoji(os.getenv(f"EMOJI_{name.upper()}"), default, f"EMOJI_{name.upper()}")
    for name, default in DEFAULT_EMOJI_ACTIVITY.items()
}


# Aion 2 class emojis, overridable the same way (EMOJI_GLADIATOR, EMOJI_TEMPLAR
# ...). Defaults are Unicode; to use the real in-game icons, upload them as
# custom emojis on your Discord (developer portal -> Emojis) and paste the codes
# here, e.g. EMOJI_GLADIATOR=<:gladiator:123456789012345678>.
def _class_variable(name: str) -> str:
    """ "Fist Fighter" -> EMOJI_FIST_FIGHTER."""
    return f"EMOJI_{name.upper().replace(' ', '_')}"


CLASS_EMOJI = {
    name: _emoji(os.getenv(_class_variable(name)), default, _class_variable(name))
    for name, default in {
        "Gladiator": "⚔️",
        "Templar": "🛡️",
        "Assassin": "🗡️",
        "Ranger": "🏹",
        "Sorcerer": "🔥",
        "Spiritmaster": "👻",
        "Cleric": "✨",
        "Chanter": "🎵",
        # Aion 2's Fist Fighter hasn't launched yet. Uncomment this line the
        # day it does: the class then shows up in every menu, the roster and
        # the autocomplete on its own (icon ready in assets/emoji/).
        # "Fist Fighter": "👊",
    }.items()
}

DB_PATH = os.getenv("DB_PATH", "data/bot.db")

# Where the embed artwork (logo, banners) is served from. Defaults to this
# repository's raw assets on GitHub; override it to point at any public host.
# Images only render if the assets are publicly reachable at this base.
ASSET_BASE_URL = os.getenv(
    "ASSET_BASE_URL",
    "https://raw.githubusercontent.com/NaxosOne/aion2-group-bot"
    "/claude/discord-bot-aion-groups-3bnutq/assets",
).rstrip("/")
