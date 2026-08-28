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
