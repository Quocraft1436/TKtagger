"""
settings_manager.py
Quản lý cài đặt toàn cục của TKtagger qua INI file.
Dùng singleton: from settings_manager import settings
"""
from __future__ import annotations
import json
import locale
from pathlib import Path
from configparser import ConfigParser

from PySide6.QtCore import QObject, Signal

# ── Settings file path ───────────────────────────────────────────────────────
SETTINGS_FILE = Path(__file__).parent / "settings.ini"
SETTINGS_SECTION = "General"

# ── keys ─────────────────────────────────────────────────────────────────────
KEY_BOOKDICT_PATH = "bookdict_path"
KEY_LANGUAGE      = "language"
KEY_RECENT_FILES  = "recent_list"


class SettingsManager(QObject):
    """
    Singleton wrapper quanh ConfigParser (INI file).
    Phát signal bookdict_changed(dict) khi path bookdict thay đổi / reload.
    Phát signal language_changed(str) khi ngôn ngữ thay đổi.
    """
    bookdict_changed = Signal(dict)   # payload: raw json_data (không có 'order')
    bookdict_order_changed = Signal(list)  # payload: order list
    language_changed = Signal(str)    # payload: language code (e.g., "en", "vi")

    _instance: "SettingsManager | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_init_done"):
            return
        super().__init__()
        self._init_done = True
        self._config = ConfigParser()
        self._load_config()
        self._bookdict_data: dict = {}
        self._bookdict_order: list = []

    def _load_config(self):
        """Load INI file. Create if not exists."""
        if SETTINGS_FILE.exists():
            self._config.read(SETTINGS_FILE, encoding="utf-8")
        if not self._config.has_section(SETTINGS_SECTION):
            self._config.add_section(SETTINGS_SECTION)

    def _save_config(self):
        """Save config to INI file."""
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            self._config.write(f)

    # ── Config passthrough ────────────────────────────────────────────────────
    def value(self, key: str, default=None):
        try:
            return self._config.get(SETTINGS_SECTION, key)
        except:
            return default

    def set_value(self, key: str, val):
        self._config.set(SETTINGS_SECTION, key, str(val))
        self._save_config()

    # ── Language ──────────────────────────────────────────────────────────────
    def get_language(self) -> str:
        """
        Get the current language setting.
        Falls back to system locale, or "en" if system locale not supported.
        """
        saved = self.value(KEY_LANGUAGE, None)
        if saved:
            return saved
        
        # Try to detect system locale
        system_lang = self._detect_system_language()
        return system_lang
    
    def _detect_system_language(self) -> str:
        """Detect system language, return supported language code or 'en'."""
        try:
            lang_code = locale.getdefaultlocale()[0]
            if lang_code:
                # Extract 2-letter language code (e.g., "vi" from "vi_VN")
                lang = lang_code.split('_')[0].lower()
                # Only return if we have that language file
                lang_dir = Path(__file__).parent / "lang"
                if (lang_dir / f"{lang}.json").exists():
                    return lang
        except Exception:
            pass
        return "en"
    
    @property
    def language(self) -> str:
        """Get the current language setting (property accessor)."""
        return self.get_language()

    @language.setter
    def language(self, lang: str):
        """Set language and emit signal."""
        old_lang = self.get_language()
        self.set_value(KEY_LANGUAGE, lang)
        if lang != old_lang:
            self.language_changed.emit(lang)

    # ── Bookdict ──────────────────────────────────────────────────────────────
    @property
    def bookdict_path(self) -> str:
        return self.value(KEY_BOOKDICT_PATH, "")

    @bookdict_path.setter
    def bookdict_path(self, path: str):
        self.set_value(KEY_BOOKDICT_PATH, path)

    @property
    def bookdict_data(self) -> dict:
        return self._bookdict_data

    @property
    def bookdict_order(self) -> list:
        return self._bookdict_order

    def load_bookdict(self, path: str = "") -> bool:
        """
        Load bookdict.json từ path (hoặc dùng saved path).
        Trả về True nếu thành công, False nếu thất bại.
        Phát signal bookdict_changed.
        """
        target = path or self.bookdict_path
        if not target:
            return False
        p = Path(target)
        if not p.exists():
            return False
        try:
            with open(p, "r", encoding="utf-8") as f:
                raw: dict = json.load(f)
        except Exception as e:
            print(f"[SettingsManager] Failed to load bookdict: {e}")
            return False

        order = raw.pop("order", None) or list(raw.keys())
        self._bookdict_data  = raw
        self._bookdict_order = order
        if path:
            self.bookdict_path = path

        self.bookdict_changed.emit(dict(raw))
        self.bookdict_order_changed.emit(list(order))
        return True

    def reload_bookdict(self) -> bool:
        return self.load_bookdict(self.bookdict_path)

    # ── Supported languages (auto-detect) ─────────────────────────────────────
    @staticmethod
    def get_supported_languages() -> list[tuple[str, str]]:
        """
        Auto-detect supported languages from lang/ folder.
        Returns list of (code, name) tuples.
        e.g., [("en", "English"), ("vi", "Tiếng Việt")]
        """
        lang_dir = Path(__file__).parent / "lang"
        supported = []
        
        # Build a name map for language codes
        lang_names = {
            "en": "English",
            "vi": "Tiếng Việt",
            "es": "Español",
            "fr": "Français",
            "de": "Deutsch",
            "ja": "日本語",
            "zh": "中文",
            "ko": "한국어",
        }
        
        if lang_dir.exists():
            for lang_file in sorted(lang_dir.glob("*.json")):
                code = lang_file.stem
                name = lang_names.get(code, code.upper())
                supported.append((code, name))
        
        # Fallback: at least return English
        if not supported:
            supported = [("en", "English")]
        
        return supported

    # ── Recent files ──────────────────────────────────────────────────────────
    def get_recent_files(self) -> list[str]:
        raw = self.value(KEY_RECENT_FILES, "")
        if not raw:
            return []
        # Parse comma-separated list
        return [r.strip() for r in raw.split(",") if Path(r.strip()).exists()]

    def add_recent_file(self, path: str, max_items: int = 10):
        recents = self.get_recent_files()
        if path in recents:
            recents.remove(path)
        recents.insert(0, path)
        # Save as comma-separated list
        self.set_value(KEY_RECENT_FILES, ", ".join(recents[:max_items]))


# ── Singleton instance (import này để dùng) ─────────────────────────────────
settings = SettingsManager()
