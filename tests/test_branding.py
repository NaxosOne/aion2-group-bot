"""The branding helpers: asset URLs and per-activity banner URLs. Run: pytest"""

from bot import config
from bot.branding import activity_banner_url, asset_url


def test_asset_url_joins_base_and_name():
    assert asset_url("banner.png") == f"{config.ASSET_BASE_URL}/banner.png"


def test_activity_banner_url_maps_the_type():
    assert activity_banner_url("Dungeon").endswith("/banners/dungeon.png")
    assert activity_banner_url("PvP").endswith("/banners/pvp.png")


def test_activity_banner_url_handles_legacy_french_labels():
    assert activity_banner_url("Donjon").endswith("/banners/dungeon.png")
    assert activity_banner_url("Abysses").endswith("/banners/abyss.png")


def test_activity_banner_url_falls_back_to_other_for_custom_types():
    assert activity_banner_url("Custom Raid Night").endswith("/banners/other.png")
