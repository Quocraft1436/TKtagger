"""
i18n.py - Internationalization helper for TKtagger
Loads translations from separate language files in the i18n/ directory.
Supports individual language files (en.json, vi.json, etc.)
"""
import json
import os

_LANG = "en"          # default language
_STRINGS: dict = {}   # cache for loaded language strings
_LANG_CACHE: dict = {} # cache for all loaded languages


def _load_language(lang: str) -> dict:
    """Load a specific language file and cache it."""
    if lang in _LANG_CACHE:
        return _LANG_CACHE[lang]
    
    i18n_dir = os.path.join(os.path.dirname(__file__), "lang")
    lang_file = os.path.join(i18n_dir, f"{lang}.json")
    
    if not os.path.exists(lang_file):
        raise ValueError(f"Language file not found: {lang_file}")
    
    with open(lang_file, encoding="utf-8") as f:
        strings = json.load(f)
    
    _LANG_CACHE[lang] = strings
    return strings


def _load():
    """Load the current language into _STRINGS."""
    global _STRINGS
    _STRINGS = _load_language(_LANG)


def set_language(lang: str):
    """Switch active language. Must have a corresponding file in i18n/ directory (e.g. 'en', 'vi')."""
    global _LANG, _STRINGS
    # Validate the language exists by attempting to load it
    _load_language(lang)
    _LANG = lang
    _STRINGS = _LANG_CACHE[lang]


def get_language() -> str:
    """Return the currently active language code."""
    return _LANG


def tr(key: str, **kwargs) -> str:
    """Return the translated string for *key*, formatting any {placeholder} values.
    Falls back to English if the key is not found in the current language."""
    if not _STRINGS:
        _load()
    
    # Try current language first, then fall back to English
    text = _STRINGS.get(key)
    if text is None and _LANG != "en":
        text = _load_language("en").get(key)
    if text is None:
        text = key
    
    # Format with any provided kwargs
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text


# Eagerly load English on import
_load()
