"""
i18n.py - Internationalization helper for TKtagger
Loads translations from separate language files in the i18n/ directory.
Supports individual language files (en.json, vi.json, etc.)
"""

import json
import os
import inspect
import re

_LANG = "en"             # default language
_STRINGS: dict = {}      # cache for loaded language strings
_LANG_CACHE: dict = {}   # cache for all loaded languages
_DEBUG_LANG = False      # flag to show actual keys instead of translations

# Show warnings for missing/unused translation keys.
_WARN_I18N = True


def _lang_dir() -> str:
    """Return the language directory."""
    return os.path.join(os.path.dirname(__file__), "lang")


def _load_language(lang: str) -> dict:
    """Load a specific language file and cache it."""
    if lang in _LANG_CACHE:
        return _LANG_CACHE[lang]

    lang_file = os.path.join(_lang_dir(), f"{lang}.json")

    if not os.path.exists(lang_file):
        if _WARN_I18N:
            print(
                f"[warning] missing language file: "
                f"{lang_file}"
            )
        _LANG_CACHE[lang] = {}
        return {}

    try:
        with open(lang_file, encoding="utf-8") as f:
            strings = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        if _WARN_I18N:
            print(
                f"[warning] failed to load language file "
                f"{lang_file}: {exc}"
            )
        _LANG_CACHE[lang] = {}
        return {}

    _LANG_CACHE[lang] = strings
    return strings


def _get_call_location() -> str:
    """
    Return the source location where tr() was called.

    Example:
        main.py:125
    """
    frame = inspect.currentframe()

    try:
        # Current frame -> _get_call_location
        # Caller       -> tr
        # Caller       -> actual source code
        frame = frame.f_back.f_back

        if frame is None:
            return "unknown location"

        filename = os.path.basename(frame.f_code.co_filename)
        line = frame.f_lineno

        return f"{filename}:{line}"
    finally:
        del frame


def _warn_missing_key(lang: str, key: str):
    """Warn when a translation key is missing."""
    location = _get_call_location()

    print(
        f"[warning] missing key at {location}: "
        f"language={lang}, key={key!r}"
    )


def _warn_unused_keys():
    """
    Check all language files against English.

    English is treated as the reference language.

    Warn when another language contains keys that do not
    exist in en.json.
    """
    en = _load_language("en")

    if not en:
        return

    for filename in sorted(os.listdir(_lang_dir())):
        if not filename.endswith(".json"):
            continue

        lang = os.path.splitext(filename)[0]

        if lang == "en":
            continue

        strings = _load_language(lang)

        extra_keys = sorted(set(strings) - set(en))

        for key in extra_keys:
            print(
                f"[warning] unused translation key: "
                f"{lang}.json -> {key!r} "
                f"(missing from en.json)"
            )


def check_languages():
    """
    Check all translation files against en.json.

    Reports:
      - missing keys in each language
      - extra/unused keys
    """
    en = _load_language("en")

    if not en:
        print("[warning] en.json is missing or empty")
        return

    i18n_dir = _lang_dir()

    if not os.path.isdir(i18n_dir):
        print(f"[warning] language directory missing: {i18n_dir}")
        return

    reference_keys = set(en)

    for filename in sorted(os.listdir(i18n_dir)):
        if not filename.endswith(".json"):
            continue

        lang = os.path.splitext(filename)[0]

        if lang == "en":
            continue

        strings = _load_language(lang)
        language_keys = set(strings)

        missing_keys = sorted(reference_keys - language_keys)
        extra_keys = sorted(language_keys - reference_keys)

        for key in missing_keys:
            print(
                f"[warning] some language missing key "
                f"Ref from EN: {lang.upper()}: {key}"
            )

        for key in extra_keys:
            print(
                f"[warning] unused tag: "
                f"{lang.upper()}: {key} "
                f"(not defined in EN)"
            )


def _load():
    """Load the current language into _STRINGS."""
    global _STRINGS
    _STRINGS = _load_language(_LANG)


def set_language(lang: str):
    """Switch active language."""
    global _LANG, _STRINGS

    _load_language(lang)

    _LANG = lang
    _STRINGS = _LANG_CACHE.get(lang, {})


def set_debug(enabled: bool):
    """Enable or disable debug mode to show raw keys."""
    global _DEBUG_LANG
    _DEBUG_LANG = enabled


def set_warning(enabled: bool):
    """Enable or disable i18n warnings."""
    global _WARN_I18N
    _WARN_I18N = enabled


def get_language() -> str:
    """Return the currently active language code."""
    return _LANG


def tr(key: str, **kwargs) -> str:
    """
    Return the translated string for *key*.

    Behavior:
      1. Debug mode -> return raw key.
      2. Try current language.
      3. Fall back to English.
      4. If English is also missing, return the key.
    """
    if _DEBUG_LANG:
        return key

    if not _STRINGS:
        _load()

    # Try current language first.
    text = _STRINGS.get(key)

    if text is None:
        if _LANG != "en":
            # Report missing key in active language.
            if _WARN_I18N:
                _warn_missing_key(_LANG, key)

            # Fallback to English.
            text = _load_language("en").get(key)

    # Final fallback: key itself.
    if text is None:
        if _WARN_I18N:
            location = _get_call_location()
            print(
                f"[warning] missing key at {location}: "
                f"key={key!r} is missing from EN"
            )

        text = key

    # Format with provided kwargs.
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            if _WARN_I18N:
                location = _get_call_location()
                print(
                    f"[warning] invalid format tags at "
                    f"{location}: key={key!r}"
                )

    return text


# Eagerly load default language on import.
_load()
