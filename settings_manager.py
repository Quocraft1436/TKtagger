"""
settings_manager.py
Quản lý cài đặt toàn cục của TKtagger qua QSettings.
Dùng singleton: from settings_manager import settings
"""
from __future__ import annotations
import json
from pathlib import Path

from PySide6.QtCore import QSettings, QObject, Signal


APP_ORG  = "TKtagger"
APP_NAME = "TKtagger"

# ── keys ─────────────────────────────────────────────────────────────────────
KEY_BOOKDICT_PATH = "global/bookdict_path"
KEY_LANGUAGE      = "global/language"
KEY_RECENT_FILES  = "recent/files"
KEY_WINDOW_GEO    = "window/geometry"
KEY_WINDOW_STATE  = "window/state"


class SettingsManager(QObject):
    """
    Singleton wrapper quanh QSettings.
    Phát signal bookdict_changed(dict) khi path bookdict thay đổi / reload.
    """
    bookdict_changed = Signal(dict)   # payload: raw json_data (không có 'order')
    bookdict_order_changed = Signal(list)  # payload: order list

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
        self._qs = QSettings(APP_ORG, APP_NAME)
        self._bookdict_data: dict = {}
        self._bookdict_order: list = []

    # ── QSettings passthrough ─────────────────────────────────────────────────
    def value(self, key: str, default=None):
        return self._qs.value(key, default)

    def set_value(self, key: str, val):
        self._qs.setValue(key, val)
        self._qs.sync()

    # ── Language ──────────────────────────────────────────────────────────────
    @property
    def language(self) -> str:
        return self._qs.value(KEY_LANGUAGE, "en")

    @language.setter
    def language(self, lang: str):
        self._qs.setValue(KEY_LANGUAGE, lang)

    # ── Bookdict ──────────────────────────────────────────────────────────────
    @property
    def bookdict_path(self) -> str:
        return self._qs.value(KEY_BOOKDICT_PATH, "")

    @bookdict_path.setter
    def bookdict_path(self, path: str):
        self._qs.setValue(KEY_BOOKDICT_PATH, path)
        self._qs.sync()

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

    # ── Recent files ──────────────────────────────────────────────────────────
    def get_recent_files(self) -> list[str]:
        raw = self._qs.value(KEY_RECENT_FILES, [])
        if isinstance(raw, str):
            raw = [raw]
        return [r for r in (raw or []) if Path(r).exists()]

    def add_recent_file(self, path: str, max_items: int = 10):
        recents = self.get_recent_files()
        if path in recents:
            recents.remove(path)
        recents.insert(0, path)
        self._qs.setValue(KEY_RECENT_FILES, recents[:max_items])


# ── Singleton instance (import này để dùng) ─────────────────────────────────
settings = SettingsManager()
