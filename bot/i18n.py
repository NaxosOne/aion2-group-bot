"""Server-language resolution and string catalog (FR/EN).

Pure helpers here take a language code ("fr"/"en"), never a DB row, so they
stay trivially testable. The catalog is loaded from bot/locales/*.json.
"""

SUPPORTED = ("en", "fr")
DEFAULT = "en"


def normalize_locale(locale: str | None) -> str:
    """A Discord locale ("fr", "fr-FR", "en-US"...) -> a supported language."""
    if locale:
        base = str(locale).lower().split("-", 1)[0]
        if base in SUPPORTED:
            return base
    return DEFAULT


def pick_lang(setting: str | None, guild_locale: str | None) -> str:
    """The language to use: explicit server override, else the guild's locale."""
    if setting in SUPPORTED:
        return setting
    return normalize_locale(guild_locale)
