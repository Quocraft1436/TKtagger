"""
table_icon.py - Mapping icon names to QIcon objects
"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QPalette
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from settings_manager import settings


ICON_DIR = Path(__file__).resolve().parent / "icons"


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


def get_icon_color() -> QColor:
    """
    Lấy màu chữ/icon từ QPalette hiện tại.

    Light mode -> màu foreground tối
    Dark mode  -> màu foreground sáng
    """

    app = QApplication.instance()

    if app is None:
        # Fallback khi QApplication chưa được tạo
        return QColor("#E3E3E3")

    return app.palette().color(QPalette.ColorRole.WindowText)


def load_tinted_icon(path: Path, color: QColor) -> QIcon:
    """
    Render SVG thành alpha mask rồi phủ màu mới lên icon.
    Chỉ cần một file SVG duy nhất.
    """

    renderer = QSvgRenderer(str(path))

    if not renderer.isValid():
        raise ValueError(f"SVG không hợp lệ: {path}")

    size = renderer.defaultSize()

    if not size.isValid() or size.isEmpty():
        size = QSize(24, 24)

    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.transparent)

    # Render SVG
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    # Tạo pixmap màu
    color_pixmap = QPixmap(size)
    color_pixmap.fill(color)

    # Dùng alpha của SVG để tạo icon đơn màu
    painter = QPainter(pixmap)
    painter.setCompositionMode(
        QPainter.CompositionMode.CompositionMode_SourceIn
    )
    painter.drawPixmap(0, 0, color_pixmap)
    painter.end()

    return QIcon(pixmap)


def get_icon(name: str) -> QIcon:
    """Lấy QIcon theo tên và tự đổi màu theo palette hiện tại."""

    filename = ICON_MAP.get(name)

    if filename is None:
        raise KeyError(f"Icon chưa được khai báo: {name}")

    path = ICON_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy icon: {path}")

    return load_tinted_icon(path, get_icon_color())


def get_icon_size() -> QSize:
    """Lấy kích thước icon từ SettingsManager."""
    size = settings.icon_size
    return QSize(size, size)
