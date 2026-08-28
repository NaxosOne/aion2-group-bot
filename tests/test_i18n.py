import asyncio

from bot import i18n


def test_normalize_locale_maps_french_variants_to_fr():
    assert i18n.normalize_locale("fr") == "fr"
    assert i18n.normalize_locale("fr-FR") == "fr"


def test_normalize_locale_defaults_unknown_to_en():
    assert i18n.normalize_locale("en-US") == "en"
    assert i18n.normalize_locale("de") == "en"
    assert i18n.normalize_locale(None) == "en"


def test_pick_lang_prefers_explicit_setting():
    assert i18n.pick_lang("fr", "en-US") == "fr"
    assert i18n.pick_lang("en", "fr") == "en"


def test_pick_lang_falls_back_to_guild_locale_when_unset():
    assert i18n.pick_lang(None, "fr") == "fr"
    assert i18n.pick_lang(None, "en-GB") == "en"
    assert i18n.pick_lang(None, None) == "en"


def test_pick_lang_ignores_unsupported_setting():
    assert i18n.pick_lang("de", "fr") == "fr"


def test_t_returns_string_for_language():
    english = i18n.t("common.error", "en")
    french = i18n.t("common.error", "fr")
    assert english.startswith("Something went wrong")
    assert french != english
    assert "problème" in french.lower()


def test_t_formats_placeholders():
    out = i18n.t("language.set_confirm", "en", language="English")
    assert "English" in out


def test_t_missing_key_falls_back_to_key():
    assert i18n.t("does.not.exist", "en") == "does.not.exist"


def test_t_unknown_lang_uses_default():
    assert i18n.t("common.error", "de") == i18n.t("common.error", "en")


def test_t_bad_params_never_raise_and_return_template():
    # A required placeholder was not supplied: t() must not raise; it degrades
    # to the raw template (so the {language} marker survives unformatted).
    out = i18n.t("language.set_confirm", "en", unrelated="x")
    assert "{language}" in out


class _FakeDB:
    def __init__(self, lang):
        self._lang = lang

    async def get_language(self, guild_id):
        return self._lang


class _FakeGuild:
    def __init__(self, locale):
        self.id = 1
        self.preferred_locale = locale


def test_resolve_lang_uses_setting_over_guild_locale():
    assert asyncio.run(i18n.resolve_lang(_FakeDB("fr"), _FakeGuild("en-US"))) == "fr"


def test_resolve_lang_auto_from_guild_locale_when_unset():
    assert asyncio.run(i18n.resolve_lang(_FakeDB(None), _FakeGuild("fr-FR"))) == "fr"
    assert asyncio.run(i18n.resolve_lang(_FakeDB(None), _FakeGuild("en-GB"))) == "en"


def test_resolve_lang_none_guild_defaults_en():
    assert asyncio.run(i18n.resolve_lang(_FakeDB(None), None)) == "en"


def test_resolve_lang_handles_missing_preferred_locale():
    assert asyncio.run(i18n.resolve_lang(_FakeDB(None), _FakeGuild(None))) == "en"
