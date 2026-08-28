"""Server-language resolution and string catalog (FR/EN).

Pure helpers here take a language code ("fr"/"en"), never a DB row, so they
stay trivially testable. The catalog is loaded from bot/locales/*.json.
"""

import json
import logging
from pathlib import Path

log = logging.getLogger("kisk")

SUPPORTED = ("en", "fr")
DEFAULT = "en"

_LOCALES_DIR = Path(__file__).parent / "locales"


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


def _load() -> dict[str, dict[str, str]]:
    catalogs: dict[str, dict[str, str]] = {}
    for lang in SUPPORTED:
        path = _LOCALES_DIR / f"{lang}.json"
        catalogs[lang] = json.loads(path.read_text(encoding="utf-8"))
    return catalogs


# Loaded once at import: a malformed locale file should fail fast at startup
# rather than let every t() silently return raw keys at runtime.
_CATALOGS = _load()


def t(key: str, lang: str, /, **params: object) -> str:
    """Translated, formatted string. Never raises inside a handler.

    Missing key/lang -> fall back to the default language, then the raw key.
    """
    lang = lang if lang in SUPPORTED else DEFAULT
    template = _CATALOGS.get(lang, {}).get(key)
    if template is None:
        template = _CATALOGS.get(DEFAULT, {}).get(key)
    if template is None:
        log.warning("i18n: missing key %r", key)
        return key
    try:
        return template.format(**params) if params else template
    except Exception:
        # This helper runs inside command/button handlers: a bad or missing
        # placeholder must degrade to the raw template, never raise.
        log.warning("i18n: bad placeholders for key %r", key)
        return template
