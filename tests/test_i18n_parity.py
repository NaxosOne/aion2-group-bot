"""Guards the FR/EN catalogs: both must define the same keys, and each key
must use the same set of {placeholders} in both languages. A forgotten or
mistyped translation fails the build here rather than at runtime."""

import json
import re
from pathlib import Path

_DIR = Path(__file__).resolve().parent.parent / "bot" / "locales"
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _load(lang):
    return json.loads((_DIR / f"{lang}.json").read_text(encoding="utf-8"))


def test_both_catalogs_have_identical_keys():
    en, fr = _load("en"), _load("fr")
    assert set(en) == set(fr), (
        f"only in en: {set(en) - set(fr)}; only in fr: {set(fr) - set(en)}"
    )


def test_placeholders_match_per_key():
    en, fr = _load("en"), _load("fr")
    for key in en:
        assert set(_PLACEHOLDER.findall(en[key])) == set(_PLACEHOLDER.findall(fr[key])), \
            f"placeholder mismatch on {key!r}"
