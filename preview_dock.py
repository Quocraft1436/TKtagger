import os
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QPushButton, QSizePolicy,
)
from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtGui import QPixmap, QCursor, QWheelEvent, QMouseEvent, QIcon

from i18n import tr

# ──────────────────────────────────────────────────────────
#  Zoom canvas
# ──────────────────────────────────────────────────────────
_ZOOM_MIN   = 10    # 10 %
_ZOOM_MAX   = 800   # 800 %
_ZOOM_STEP  = 10    
_ZOOM_DEF   = 100   


class _ZoomCanvas(QWidget):
    """Widget nội bộ vẽ ảnh với pan + zoom."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._zoom   = 1.0          
        self._offset = QPoint(0, 0) 
        self._pan_active = False
        self._pan_start  = QPoint()

        self.setMinimumSize(100, 100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

    def set_pixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.reset_view()

    def set_zoom_ratio(self, ratio: float):
        ratio = max(_ZOOM_MIN / 100, min(_ZOOM_MAX / 100, ratio))
        self._zoom = ratio
        self._clamp_offset()
        self.update()

    def zoom_ratio(self) -> float:
        return self._zoom

    def reset_view(self):
        self._offset = QPoint(0, 0)
        if self._pixmap and not self._pixmap.isNull():
            w_ratio = self.width()  / self._pixmap.width()
            h_ratio = self.height() / self._pixmap.height()
            self._zoom = min(w_ratio, h_ratio, 1.0)
        else:
            self._zoom = 1.0
        self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1e1e1e"))

        if not self._pixmap or self._pixmap.isNull():
            painter.setPen(QColor("#555"))
            painter.drawText(self.rect(), Qt.AlignCenter, tr("preview.no_image"))
            return

        img_w = int(self._pixmap.width()  * self._zoom)
        img_h = int(self._pixmap.height() * self._zoom)

        cx = (self.width()  - img_w) // 2 + self._offset.x()
        cy = (self.height() - img_h) // 2 + self._offset.y()

        scaled = self._pixmap.scaled(
            QSize(img_w, img_h),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        painter.drawPixmap(cx, cy, scaled)

    def _zoom_around(self, factor: float, pivot: QPoint):
        new_zoom = max(_ZOOM_MIN / 100, min(_ZOOM_MAX / 100, self._zoom * factor))
        if new_zoom == self._zoom:
            return

        old_zoom = self._zoom
        img_w_old = self._pixmap.width()  * old_zoom if self._pixmap else 0
        img_h_old = self._pixmap.height() * old_zoom if self._pixmap else 0
        cx_old = (self.width()  - img_w_old) / 2 + self._offset.x()
        cy_old = (self.height() - img_h_old) / 2 + self._offset.y()

        self._zoom = new_zoom
        scale = new_zoom / old_zoom
        dx = pivot.x() - cx_old
        dy = pivot.y() - cy_old
        self._offset += QPoint(int(dx * (1 - scale)), int(dy * (1 - scale)))

        self._clamp_offset()
        self.update()

    def _clamp_offset(self):
        if not self._pixmap:
            return
        img_w = self._pixmap.width()  * self._zoom
        img_h = self._pixmap.height() * self._zoom
        # Cho phép kéo ảnh ra ngoài biên một chút để linh hoạt
        max_dx = max(0, int((img_w - self.width())  / 2 + img_w * 0.2))
        max_dy = max(0, int((img_h - self.height()) / 2 + img_h * 0.2))
        x = max(-max_dx, min(max_dx, self._offset.x()))
        y = max(-max_dy, min(max_dy, self._offset.y()))
        self._offset = QPoint(x, y)

    def wheelEvent(self, event: QWheelEvent):
        # Zoom bằng scroll (không cần Ctrl)
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1 / 1.15
        self._zoom_around(factor, event.position().toPoint())
        event.accept()
        
        p = self.parent()
        while p:
            if hasattr(p, '_on_canvas_zoom_changed'):
                p._on_canvas_zoom_changed()
                break
            p = p.parent()

    def mousePressEvent(self, event: QMouseEvent):
        # Nhấn giữ chuột trái là PAN
        if event.button() == Qt.LeftButton:
            self._pan_active = True
            self._pan_start  = event.pos()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._pan_active:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self._offset += delta
            self._clamp_offset()
            self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._pan_active = False
            self.unsetCursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._clamp_offset()


# ──────────────────────────────────────────────────────────
#  Dock container
# ──────────────────────────────────────────────────────────
class PreviewDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PreviewDock")
        self.setMinimumWidth(260)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(4)

        self._name_label = QLabel("—")
        self._name_label.setAlignment(Qt.AlignCenter)
        self._name_label.setWordWrap(True)
        root_layout.addWidget(self._name_label)

        self._canvas = _ZoomCanvas()
        root_layout.addWidget(self._canvas, stretch=1)

        ctrl_row = QWidget()
        ctrl_layout = QHBoxLayout(ctrl_row)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(6)

        self._zoom_ico_label = QLabel()
        # Thay emoji bằng QIcon hệ thống (hoặc đường dẫn file .svg/.png của bạn)
        self._zoom_ico_label.setPixmap(QIcon.fromTheme("zoom-in").pixmap(16, 16))
        self._zoom_ico_label.setFixedWidth(20)
        ctrl_layout.addWidget(self._zoom_ico_label)

        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setRange(_ZOOM_MIN, _ZOOM_MAX)
        self._zoom_slider.setSingleStep(_ZOOM_STEP)
        self._zoom_slider.setPageStep(50)
        self._zoom_slider.setValue(_ZOOM_DEF)
        self._zoom_slider.setTickPosition(QSlider.TicksBelow)
        self._zoom_slider.setTickInterval(100)
        self._zoom_slider.valueChanged.connect(self._on_slider_changed)
        ctrl_layout.addWidget(self._zoom_slider, stretch=1)

        self._zoom_pct_label = QLabel("100%")
        self._zoom_pct_label.setFixedWidth(44)
        self._zoom_pct_label.setAlignment(Qt.AlignCenter)
        ctrl_layout.addWidget(self._zoom_pct_label)

        self._reset_btn = QPushButton()
        self._reset_btn.setIcon(QIcon.fromTheme("view-refresh")) 
        self._reset_btn.setFixedWidth(80)
        self._reset_btn.clicked.connect(self._on_reset)
        ctrl_layout.addWidget(self._reset_btn)

        root_layout.addWidget(ctrl_row)

        self._tip_label = QLabel()
        self._tip_label.setAlignment(Qt.AlignCenter)
        self._tip_label.setStyleSheet("font-size: 10px; color: #888;")
        root_layout.addWidget(self._tip_label)

        self.setWidget(root)
        self.retranslate_ui()
        self._sync_slider_to_canvas()

    def retranslate_ui(self):
        """Cập nhật các chuỗi văn bản bằng hàm tr()."""
        self._reset_btn.setText(tr("preview_zoom_reset_btn"))
        self._tip_label.setText(tr("preview_tips")) # Cập nhật key hướng dẫn mới
        self.setWindowTitle(tr("preview_dock")) 
        if self._name_label.text() == "—":
             self._name_label.setText("—")

    def show_image(self, path: str):
        self._name_label.setText(os.path.basename(path) if path else "—")
        if path:
            px = QPixmap(path)
            if not px.isNull():
                self._canvas.set_pixmap(px)
                self._sync_slider_to_canvas()
                return
        self._canvas.set_pixmap(QPixmap())

    def _on_slider_changed(self, value: int):
        ratio = value / 100.0
        self._canvas.set_zoom_ratio(ratio)
        self._zoom_pct_label.setText(f"{value}%")

    def _on_reset(self):
        self._canvas.reset_view()
        self._sync_slider_to_canvas()

    def _on_canvas_zoom_changed(self):
        self._sync_slider_to_canvas()

    def _sync_slider_to_canvas(self):
        pct = int(self._canvas.zoom_ratio() * 100)
        pct = max(_ZOOM_MIN, min(_ZOOM_MAX, pct))
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(pct)
        self._zoom_slider.blockSignals(False)
        self._zoom_pct_label.setText(f"{pct}%")