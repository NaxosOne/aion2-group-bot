"""The branding helpers: asset URLs and per-activity banner URLs. Run: pytest"""

from bot import config
from bot.branding import ASSET_VERSION, activity_banner_url, asset_url


def test_asset_url_joins_base_name_and_cache_buster():
    assert asset_url("banner.png") == (
        f"{config.ASSET_BASE_URL}/banner.png?v={ASSET_VERSION}"
    )


def test_activity_banner_url_maps_the_type():
    assert "/banners/dungeon.png" in activity_banner_url("Dungeon")
    assert "/banners/pvp.png" in activity_banner_url("PvP")


def test_activity_banner_url_handles_legacy_french_labels():
    assert "/banners/dungeon.png" in activity_banner_url("Donjon")
    assert "/banners/abyss.png" in activity_banner_url("Abysses")


def test_activity_banner_url_falls_back_to_other_for_custom_types():
    assert "/banners/other.png" in activity_banner_url("Custom Raid Night")


def test_banner_urls_carry_the_cache_buster():
    assert activity_banner_url("Raid").endswith(f"?v={ASSET_VERSION}")
