"""
table_icon.py - Mapping icon names to QIcon objects
"""

from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize

from settings_manager import settings

ICON_MAP = {
    # Selection
    "select_none": "select_24dp_E3E3E3_FILL0_wght200_GRAD0_opsz24.svg",
    "select_all": "select_all_24dp_E3E3E3_FILL0_wght200_GRAD0_opsz24.svg",
    "select_invert": "flip_24dp_E3E3E3_FILL0_wght200_GRAD0_opsz24.svg",
    "delete": "delete_24dp_E3E3E3_FILL0_wght200_GRAD0_opsz24.svg",
    "replace": "edit_24dp_E3E3E3_FILL0_wght200_GRAD0_opsz24.svg",
    "add": "add_2_24dp_E3E3E3_FILL0_wght200_GRAD0_opsz24.svg",
    # File operations
    "save": "save_24dp_E3E3E3_FILL0_wght200_GRAD0_opsz24.svg",
    # View
    "view-history": "history_24dp_E3E3E3_FILL0_wght200_GRAD0_opsz24.svg",
    "view-preview": "frame_inspect_24dp_E3E3E3_FILL0_wght200_GRAD0_opsz24.svg",
}


def get_icon(name: str) -> QIcon:
    """Lấy QIcon theo tên mapping."""
    filename = ICON_MAP.get(name)

    if filename is None:
        raise KeyError(f"Icon chưa được khai báo: {name}")

    path = ICON_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy icon: {path}")

    return QIcon(str(path))

def get_icon_size() -> QSize:
    """Lấy kích thước icon từ SettingsManager."""
    size = settings.icon_size
    return QSize(size, size)

ICON_DIR = Path("./icons")