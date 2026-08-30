"""Shared visual identity for Kisk's embeds: the logo, the banners, and a
`brand()` helper that stamps every embed with a consistent author line.

Artwork is referenced by URL (see config.ASSET_BASE_URL) so frequently-edited
embeds never have to re-upload a file. Images only appear once the assets are
generated and publicly reachable; until then the embeds simply render without
them.
"""

import discord

from . import config

LOGO_URL = f"{config.ASSET_BASE_URL}/avatar.png"
BANNER_URL = f"{config.ASSET_BASE_URL}/banner.png"

# Event type -> banner slug. Legacy French labels (kept on old events) map to
# the same art; anything else falls back to the neutral "other" banner.
_ACTIVITY_SLUG = {
    "Dungeon": "dungeon",
    "Raid": "raid",
    "Battleground": "battleground",
    "PvP": "pvp",
    "Rift": "rift",
    "Abyss": "abyss",
    "Other": "other",
    "Donjon": "dungeon",
    "Abysses": "abyss",
    "Autre": "other",
}


def asset_url(name: str) -> str:
    """The public URL of an asset by its path under the assets directory."""
    return f"{config.ASSET_BASE_URL}/{name}"


def activity_banner_url(activity: str) -> str:
    """The wide banner URL for an event type, falling back to 'other'."""
    return asset_url(f"banners/{_ACTIVITY_SLUG.get(activity, 'other')}.png")


def activity_icon_url(activity: str) -> str:
    """The square icon URL for an event type (the shipped class/type art)."""
    return asset_url(f"emoji/{_ACTIVITY_SLUG.get(activity, 'other')}.png")


def brand(embed: discord.Embed) -> discord.Embed:
    """Stamps an embed with Kisk's author line and logo. Returns it for chaining."""
    embed.set_author(name="Kisk", icon_url=LOGO_URL)
    return embed
