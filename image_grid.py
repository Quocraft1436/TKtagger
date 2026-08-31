"""
image_grid.py - Widget hiển thị lưới ảnh
"""
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QGridLayout, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSizePolicy, QToolTip
)
from PySide6.QtCore import Qt, Signal, QSize, QRect, QPoint
from PySide6.QtGui import QPixmap, QImage, QIcon, QImageReader, QPainter, QColor, QFontMetrics, QFont
import os
import time

from i18n import tr

class ImageCard(QFrame):
    """Widget thẻ ảnh đơn: click để chọn (đổi nền/viền) và hiển thị tags."""
    selection_changed = Signal(int, bool)
    tag_added = Signal(int, str)

    tag_remove_requested = Signal(int, str)
    tag_insert_requested = Signal(str)
    preview_requested = Signal(int)
    render_finished = Signal(int, float)  # idx, elapsed_seconds

    def __init__(self, idx: int, img_data: dict, img_width: int = 200,
                 tag_filters: dict = None, parent=None):
        super().__init__(parent)
        self._t_start = time.perf_counter()
        self.idx = idx
        self.img_data = img_data
        self.img_width = img_width
        self.tag_filters = tag_filters or {}
        self._selected = False
        self.setObjectName("ImageCard")   # dùng cho CSS selector trong _set_border
        self.setFrameShape(QFrame.Box)
        self.setLineWidth(2)
        self._set_border(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setup_ui()

    def _set_border(self, selected: bool):
        # Thay cho checkbox: đổi cả viền lẫn nền card để thể hiện trạng
        # thái được chọn, dễ nhận biết hơn khi lưới ảnh nhỏ.
        if selected:
            self.setStyleSheet(
                "#ImageCard { border: 3px solid #4CAF50;"
                " background-color: rgba(76, 175, 80, 60);"
                " border-radius: 4px; }"
            )
        else:
            self.setStyleSheet(
                "#ImageCard { border: 2px solid #3c3c3c;"
                " background-color: transparent;"
                " border-radius: 4px; }"
            )

    def retranslate_ui(self):
        """Cập nhật các thành phần text trong card."""
        self.tag_entry.setPlaceholderText(tr("add_tag_placeholder"))
        self.preview_btn.setToolTip(tr("preview_image_tooltip")) # Giả định bạn có key này
        self.refresh_tags() 

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # Image
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setFixedSize(self.img_width, self.img_width)
        self._image_loaded = False
        layout.addWidget(self.img_label, alignment=Qt.AlignCenter)

        # Thay thế hiển thị Tags cũ bằng TagRenderWidget mới
        self.tag_display = TagRenderWidget(self)
        
        # Kết nối các tín hiệu chuột (mouse events)
        self.tag_display.tag_remove_requested.connect(
            lambda t: self.tag_remove_requested.emit(self.idx, t)
        )
        self.tag_display.tag_insert_requested.connect(self.tag_insert_requested.emit)
        
        layout.addWidget(self.tag_display)
        self.refresh_tags()

        # Tag entry row (Giữ nguyên như mã nguồn của bạn)
        entry_row = QWidget()
        entry_layout = QHBoxLayout(entry_row)
        entry_layout.setContentsMargins(0, 0, 0, 0)

        self.tag_entry = QLineEdit()
        self.tag_entry.setPlaceholderText(tr("add_tag_placeholder"))
        self.tag_entry.setFocusPolicy(Qt.ClickFocus)
        self.tag_entry.setFixedHeight(28)
        self.tag_entry.returnPressed.connect(self._add_tag)
        
        self.preview_btn = QPushButton()
        self.preview_btn.setFixedSize(28, 28)
        self.preview_btn.setIcon(QIcon.fromTheme("view-visible"))
        self.preview_btn.setStyleSheet("background:#2196F3; color:white; font-weight:bold; border-radius:2px;")
        self.preview_btn.clicked.connect(lambda: self.preview_requested.emit(self.idx))

        add_btn = QPushButton()
        add_btn.setFixedSize(28, 28)
        add_btn.setIcon(QIcon.fromTheme("list-add"))
        add_btn.setStyleSheet("background:#4CAF50; color:white; font-weight:bold; border-radius:2px;")
        add_btn.clicked.connect(self._add_tag)

        entry_layout.addWidget(self.tag_entry)
        entry_layout.addWidget(self.preview_btn)
        entry_layout.addWidget(add_btn)
        layout.addWidget(entry_row)

    def _load_image(self, label: QLabel):
        try:
            path = self.img_data.get('path', None)
            if not path:
                raise ValueError("No image path provided")

            reader = QImageReader(path)
            reader.setAutoTransform(True)  # tôn trọng EXIF orientation

            original_size = reader.size()
            if original_size.isValid() and original_size.width() > 0:
                target = QSize(self.img_width, self.img_width)
                scaled = original_size.scaled(
                    target, Qt.AspectRatioMode.KeepAspectRatio
                )
                reader.setScaledSize(scaled)

            image = reader.read()
            if image.isNull():
                raise ValueError(f"Cannot load image from {path}")

            pixmap = QPixmap.fromImage(image)
            label.setPixmap(pixmap)
        except Exception:
            label.setText("❌ Error")
            label.setStyleSheet("color: red; font-size: 10px;")

    def showEvent(self, event):
        super().showEvent(event)
        if not self._image_loaded:
            self._load_image(self.img_label)
            self._image_loaded = True
            elapsed = time.perf_counter() - self._t_start
            n_tags = len(self.img_data.get('tags', []) or [])
            print(f"[info] card #{self.idx} render: {elapsed*1000:.1f} ms | tags: {n_tags}")
            self.render_finished.emit(self.idx, elapsed)

    def mousePressEvent(self, event):
        if self.tag_entry.underMouse() or self.preview_btn.underMouse():
            super().mousePressEvent(event)
            return
            
        if event.button() == Qt.LeftButton:
            self.toggle_select()
        super().mousePressEvent(event)

    def refresh_tags(self):
        """Truyền trực tiếp danh sách tag xuống TagRenderWidget thay vì khởi tạo lại nhiều Widget/Layout."""
        tags = self.img_data.get('tags', [])
        self.tag_display.set_tags(tags, self.tag_filters)

    def toggle_select(self):
        self.set_selected(not self._selected, emit=True)

    def set_selected(self, value: bool, emit: bool = False):
        self._selected = value
        self._set_border(value)
        if emit:
            self.selection_changed.emit(self.idx, self._selected)

    def is_selected(self) -> bool:
        return self._selected

    def _add_tag(self):
        tag = self.tag_entry.text().strip()
        if tag:
            self.tag_entry.clear()
            self.tag_added.emit(self.idx, tag)

class TagRenderWidget(QWidget):
    """Widget sử dụng QPainter để vẽ danh sách tag thay vì dùng nhiều QLabel."""
    tag_remove_requested = Signal(str)
    tag_insert_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tags = []
        self.tag_filters = {}
        self.tag_rects = []
        
        # =========================================================================
        # CẤU HÌNH FONT & SIZE TẠI ĐÂY:
        # Bạn có thể đổi "Consolas" thành font monospace khác (VD: "Courier New", "Cascadia Code")
        # và điều chỉnh kích thước (VD: 9, 10, 11) cho vừa vặn với card ảnh 200px.
        # =========================================================================
        self.tag_font = QFont("Consolas", 11) 
        
        self.setMouseTracking(True) 
        self.setMinimumHeight(30)

    def set_tags(self, tags, tag_filters):
        self.tags = tags or []
        self.tag_filters = tag_filters or {}
        
        # Sắp xếp tag: các tag đang active lên đầu, còn lại phía sau
        active = [t for t in self.tags if self.tag_filters.get(t, False)]
        rest = [t for t in self.tags if not self.tag_filters.get(t, False)]
        self.ordered_tags = active + rest
        
        self.update_tag_layout()
        self.update()

    def update_tag_layout(self):
        """Tính toán vị trí từng tag và tự động ngắt dòng chuẩn xác, không bị dư khoảng trắng đầu dòng."""
        self.tag_rects = []
        if not self.ordered_tags:
            self.setMinimumHeight(25)
            return

        metrics = QFontMetrics(self.tag_font)
        x_offset = 2
        y_offset = 2
        line_height = metrics.height() + 4
        max_width = self.width() if self.width() > 0 else 200
        comma_width = metrics.horizontalAdvance(", ")

        for i, tag in enumerate(self.ordered_tags):
            text_width = metrics.horizontalAdvance(tag)
            has_next = (i < len(self.ordered_tags) - 1)
            
            # Tính tổng chiều rộng cần thiết cho tag và dấu phẩy của nó
            needed_width = text_width + (comma_width if has_next else 0)
            
            # Nếu không phải đang ở đầu dòng và tổng độ rộng vượt quá khung -> xuống dòng mới
            if x_offset > 2 and (x_offset + needed_width > max_width - 5):
                x_offset = 2
                y_offset += line_height

            rect = QRect(x_offset, y_offset, text_width, metrics.height())
            self.tag_rects.append((rect, tag))
            
            # Dịch chuyển x_offset cho phần tử tiếp theo trên cùng dòng
            x_offset += text_width
            if has_next:
                x_offset += comma_width

        # Cập nhật chiều cao tối thiểu cho widget
        self.setMinimumHeight(y_offset + line_height + 4)

    def resizeEvent(self, event):
        self.update_tag_layout()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Áp dụng font chữ đã cấu hình
        painter.setFont(self.tag_font)
        metrics = QFontMetrics(self.tag_font)

        # Xử lý trường hợp không có tag
        if not self.ordered_tags:
            painter.setPen(QColor("#888"))
            painter.drawText(self.rect(), Qt.AlignLeft | Qt.AlignTop, tr("no_tags_msg"))
            painter.end()
            return

        for i, (rect, tag) in enumerate(self.tag_rects):
            is_active = self.tag_filters.get(tag, False)
            color = QColor("#80ff80") if is_active else QColor("white")
            
            # Vẽ tag
            painter.setPen(color)
            painter.drawText(rect, Qt.AlignLeft | Qt.AlignTop, tag)

            # Vẽ dấu phẩy
            if i < len(self.tag_rects) - 1:
                comma_rect = QRect(
                    rect.right() + 2, rect.top(),
                    metrics.horizontalAdvance(", "), rect.height()
                )
                painter.setPen(QColor("white"))
                painter.drawText(comma_rect, Qt.AlignLeft | Qt.AlignTop, ", ")

        painter.end()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        hovered_tag = None

        for rect, tag in self.tag_rects:
            if rect.contains(pos):
                hovered_tag = tag
                break

        if hovered_tag:
            tooltip_pos = self.mapToGlobal(pos)
            QToolTip.showText(
                tooltip_pos + QPoint(10, 10), 
                f'"{hovered_tag}"\n{tr("tag_tooltip")}', 
                self
            )
            self.setCursor(Qt.PointingHandCursor)
        else:
            QToolTip.hideText()
            self.setCursor(Qt.ArrowCursor)

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        pos = event.pos()
        for rect, tag in self.tag_rects:
            if rect.contains(pos):
                if event.button() == Qt.MiddleButton:
                    self.tag_remove_requested.emit(tag)
                elif event.button() == Qt.RightButton:
                    self.tag_insert_requested.emit(tag)
                break
        super().mousePressEvent(event)

class ImageGrid(QWidget):
    """Widget lưới ảnh chính."""
    selection_changed = Signal(set)
    tag_add_requested = Signal(int, str)

    tag_insert_requested = Signal(str)
    tag_remove_requested = Signal(int, str)
    preview_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._images = []
        self._selected = set()
        self._tag_filters = {}
        self._cols = 3
        self._img_width = 200
        self._cards: dict = {}

        # --- Đo thời gian render toàn bộ lưới ---
        self._rebuild_start_time = None
        self._pending_render_count = 0
        self._card_render_times = {}  # idx -> elapsed seconds

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self.scroll_area)

        self._container = QWidget()
        self._grid_layout = QGridLayout(self._container)
        self._grid_layout.setContentsMargins(8, 8, 8, 8)
        self._grid_layout.setSpacing(10)
        self.scroll_area.setWidget(self._container)

    def retranslate_ui(self):
        self._rebuild()
        for card in self._cards.values():
            card.retranslate_ui()

    def set_data(self, images: list, tag_filters: dict = None):
        self._images = images
        self._tag_filters = tag_filters or {}
        self._selected.clear()
        self._rebuild()

    def set_columns(self, cols: int):
        self._cols = cols
        self._rebuild()

    def set_tag_filters(self, filters: dict):
        self._tag_filters = filters
        self._rebuild()

    def _rebuild(self):
        self._cards.clear()
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Reset bộ đếm thời gian cho lần rebuild này
        self._rebuild_start_time = time.perf_counter()
        self._pending_render_count = len(self._images)
        self._card_render_times = {}

        active_filters = [t for t, v in self._tag_filters.items() if v]

        with_tags = []
        without_tags = []
        for idx, img in enumerate(self._images):
            if active_filters:
                if any(t in img['tags'] for t in active_filters):
                    with_tags.append((idx, img))
                else:
                    without_tags.append((idx, img))
            else:
                with_tags.append((idx, img))

        row = 0
        if with_tags and active_filters:
            header = QLabel( tr("images_with_tags") + f": {', '.join(active_filters)}" )
            header.setStyleSheet("background:#4CAF50; color:white; font-weight:bold; padding:6px;")
            self._grid_layout.addWidget(header, row, 0, 1, self._cols)
            row += 1

        for grid_i, (idx, img) in enumerate(with_tags):
            card = self._make_card(idx, img)
            self._grid_layout.addWidget(card, row + grid_i // self._cols, grid_i % self._cols)
        if with_tags:
            row += ((len(with_tags) - 1) // self._cols) + 1

        if without_tags and active_filters:
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            self._grid_layout.addWidget(sep, row, 0, 1, self._cols)
            row += 1

            header2 = QLabel( tr("images_without_tags") + f": {', '.join(active_filters)}" )
            header2.setStyleSheet("background:#f44336; color:white; font-weight:bold; padding:6px;")
            self._grid_layout.addWidget(header2, row, 0, 1, self._cols)
            row += 1

            for grid_i, (idx, img) in enumerate(without_tags):
                card = self._make_card(idx, img)
                self._grid_layout.addWidget(card, row + grid_i // self._cols, grid_i % self._cols)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._grid_layout.addWidget(spacer, self._grid_layout.rowCount(), 0, 1, self._cols)

        # Nếu không có ảnh nào (không có card nào cần render), in thống kê ngay
        if self._pending_render_count == 0:
            self._print_grid_stats()

    def _make_card(self, idx: int, img: dict) -> ImageCard:
        card = ImageCard(idx, img, self._img_width, self._tag_filters)
        card.selection_changed.connect(self._on_card_selection)
        card.tag_added.connect(self.tag_add_requested)
        card.tag_remove_requested.connect(self._on_tag_remove)
        card.tag_insert_requested.connect(self.tag_insert_requested)
        card.preview_requested.connect(self._on_preview_requested)
        card.render_finished.connect(self._on_card_render_finished)
        if idx in self._selected:
            card.set_selected(True)
        self._cards[idx] = card
        return card

    def _on_card_render_finished(self, idx: int, elapsed: float):
        self._card_render_times[idx] = elapsed
        if len(self._card_render_times) >= self._pending_render_count:
            self._print_grid_stats()

    def _print_grid_stats(self):
        n = len(self._images)
        total_time = (
            time.perf_counter() - self._rebuild_start_time
            if self._rebuild_start_time is not None else 0.0
        )
        times = list(self._card_render_times.values())
        avg_per_card = (sum(times) / len(times)) if times else 0.0
        max_tags = max(
            (len(img.get('tags', []) or []) for img in self._images),
            default=0
        )
        print(
            f"[info] avg/card: {avg_per_card*1000:.1f} ms | "
            f"số ảnh: {n} | "
            f"số lượng tag tối đa mỗi card: {max_tags} | "
            f"tổng thời gian tất cả {n} ảnh: {total_time*1000:.1f} ms"
        )

    def _on_preview_requested(self, idx: int):
        if idx < len(self._images):
            self.preview_requested.emit(self._images[idx].get('path', ''))

    def _on_card_selection(self, idx: int, selected: bool):
        if selected:
            self._selected.add(idx)
        else:
            self._selected.discard(idx)
        self.selection_changed.emit(set(self._selected))

    def select_all(self):
        for idx in range(len(self._images)):
            self._selected.add(idx)
            if idx in self._cards:
                self._cards[idx].set_selected(True)
        self.selection_changed.emit(set(self._selected))

    def deselect_all(self):
        for idx in list(self._selected):
            if idx in self._cards:
                self._cards[idx].set_selected(False)
        self._selected.clear()
        self.selection_changed.emit(set())

    def invert_selection(self):
        for idx in range(len(self._images)):
            new_state = idx not in self._selected
            if new_state:
                self._selected.add(idx)
            else:
                self._selected.discard(idx)
            if idx in self._cards:
                self._cards[idx].set_selected(new_state)
        self.selection_changed.emit(set(self._selected))

    def refresh_card(self, idx: int):
        if idx in self._cards:
            self._cards[idx].refresh_tags()

    def get_selected(self) -> set:
        return set(self._selected)
    
    def _on_tag_remove(self, idx: int, tag: str):
        self.tag_remove_requested.emit(idx, tag)