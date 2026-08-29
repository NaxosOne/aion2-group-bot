from bot.cogs.settings import LANG_LABEL, choice_to_lang


def test_choice_to_lang():
    assert choice_to_lang("fr") == "fr"
    assert choice_to_lang("en") == "en"
    assert choice_to_lang("auto") is None


def test_labels_exist():
    assert LANG_LABEL["fr"] == "Français"
    assert LANG_LABEL["en"] == "English"
