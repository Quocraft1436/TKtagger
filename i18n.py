"""
i18n.py - Internationalization helper for TKtagger
Loads translations from i18n.json and provides a simple tr() function.
"""
import json
import os

_LANG = "en"          # default language
_STRINGS: dict = {}


def _load():
    global _STRINGS
    path = os.path.join(os.path.dirname(__file__), "i18n.json")
    with open(path, encoding="utf-8") as f:
        _STRINGS = json.load(f)


def set_language(lang: str):
    """Switch active language.  lang must be a top-level key in i18n.json (e.g. 'en', 'vi')."""
    global _LANG
    if not _STRINGS:
        _load()
    if lang not in _STRINGS:
        raise ValueError(f"Language '{lang}' not found in i18n.json")
    _LANG = lang


def get_language() -> str:
    return _LANG


def tr(key: str, **kwargs) -> str:
    """Return the translated string for *key*, formatting any {placeholder} values."""
    if not _STRINGS:
        _load()
    text = _STRINGS.get(_LANG, {}).get(key) or _STRINGS.get("en", {}).get(key) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text


# Eagerly load on import
_load()
