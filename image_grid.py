"""
image_grid.py - Widget hiển thị lưới ảnh
"""
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QToolTip
)
from PySide6.QtCore import Qt, Signal, QRect, QPoint, QTimer, Slot, QEvent
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor, QFontMetrics, QFont, QPalette
import time

from i18n import tr
from thumbnail_loader import ThumbnailLoader

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
        
        # A bounded tag area gives virtual rows a stable height. Long captions
        # remain accessible by scrolling within the card.
        self.tag_scroll = QScrollArea()
        self.tag_scroll.setWidgetResizable(True)
        self.tag_scroll.setFixedHeight(120)
        self.tag_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tag_scroll.setWidget(self.tag_display)
        layout.addWidget(self.tag_scroll)
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

    def set_thumbnail(self, image):
        if self._image_loaded:
            return
        self._image_loaded = True
        if image.isNull():
            self.img_label.setText("❌ Error")
        else:
            self.img_label.setPixmap(QPixmap.fromImage(image))
        self.render_finished.emit(self.idx, time.perf_counter() - self._t_start)

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

        painter.setFont(self.tag_font)
        metrics = QFontMetrics(self.tag_font)

        # Lấy màu text theo Light/Dark theme của Qt
        text_color = self.palette().color(QPalette.ColorRole.WindowText)

        # Xử lý trường hợp không có tag
        if not self.ordered_tags:
            painter.setPen(QColor("#888888"))
            painter.drawText(
                self.rect(),
                Qt.AlignLeft | Qt.AlignTop,
                tr("no_tags_msg")
            )
            painter.end()
            return

        for i, (rect, tag) in enumerate(self.tag_rects):
            is_active = self.tag_filters.get(tag, False)

            # Tag active vẫn màu xanh.
            # Tag bình thường lấy màu text của theme.
            color = QColor("#80ff80") if is_active else text_color

            painter.setPen(color)
            painter.drawText(
                rect,
                Qt.AlignLeft | Qt.AlignTop,
                tag
            )

            # Vẽ dấu phẩy
            if i < len(self.tag_rects) - 1:
                comma_rect = QRect(
                    rect.right() + 2,
                    rect.top(),
                    metrics.horizontalAdvance(", "),
                    rect.height()
                )

                # Không hard-code white nữa
                painter.setPen(text_color)
                painter.drawText(
                    comma_rect,
                    Qt.AlignLeft | Qt.AlignTop,
                    ", "
                )

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

        self._sections = []
        self._virtual_height = 1
        self._headers = []
        self._row_height = self._img_width + 174
        self._rebuilding = False
        self.rebuild_count = 0
        self._reorder_timer = QTimer(self)
        self._reorder_timer.setSingleShot(True)
        self._reorder_timer.timeout.connect(self._rebuild)
        self.thumbnails = ThumbnailLoader(self)
        self.thumbnails.ready.connect(self._thumbnail_ready)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)
        self._container = QWidget()
        self.scroll_area.setWidget(self._container)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._update_visible)
        self.scroll_area.viewport().installEventFilter(self)

    def retranslate_ui(self):
        self._rebuild()
        for card in self._cards.values():
            card.retranslate_ui()

    def set_data(self, images: list, tag_filters: dict = None):
        self._images = images
        self._tag_filters = tag_filters or {}
        self._selected.clear()
        self._rebuild()
        # Replacing data clears selection; keep action targets in sync with cards.
        self.selection_changed.emit(set())

    def set_columns(self, cols: int):
        cols = max(1, int(cols))
        if cols != self._cols:
            self._cols = cols
            self._rebuild()

    def set_tag_filters(self, filters: dict):
        active = {key: True for key, value in filters.items() if value}
        if active == self._tag_filters:
            return
        self._tag_filters = active
        self._rebuild()

    def _rebuild(self):
        if self._rebuilding:
            return
        self._reorder_timer.stop()
        self._rebuilding = True
        self.rebuild_count += 1
        try:
            for card in self._cards.values():
                card.hide()
                card.deleteLater()
            self._cards.clear()
            for header in self._headers:
                header.deleteLater()
            self._headers.clear()
            active = {tag for tag, enabled in self._tag_filters.items() if enabled}
            matched, rest = [], []
            for idx, image in enumerate(self._images):
                (matched if not active or active.intersection(image['tags']) else rest).append(idx)
            self._sections = []
            y = 8
            for indices, title in ((matched, 'images_with_tags'), (rest, 'images_without_tags')):
                if not indices:
                    continue
                if active:
                    header = QLabel(tr(title) + ': ' + ', '.join(sorted(active)), self._container)
                    header._virtual_y = y
                    self._headers.append(header)
                    y += 32
                self._sections.append((y, indices))
                y += ((len(indices) + self._cols - 1) // self._cols) * self._row_height
            self._virtual_height = max(1, y)
            # QWidget coordinates are limited (~16 million pixels). Map the
            # scrollbar to logical rows instead of allocating a taller canvas.
            self._container.setMinimumSize(self._cols * (self._img_width + 24) + 16,
                                           min(self._virtual_height, 8_000_000))
        finally:
            self._rebuilding = False
        self._update_visible()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Resize, QEvent.Show):
            self._update_visible()
        return super().eventFilter(watched, event)

    def _update_visible(self, *_):
        if self._rebuilding:
            return
        bar = self.scroll_area.verticalScrollBar()
        physical_top = bar.value()
        view_height = self.scroll_area.viewport().height()
        logical_range = max(0, self._virtual_height - view_height)
        physical_range = max(1, self._container.height() - view_height)
        top = round(physical_top * logical_range / physical_range)
        bottom = top + view_height
        scale = max(1, logical_range / physical_range)
        bar.setSingleStep(max(1, round(40 / scale)))
        bar.setPageStep(max(1, round(view_height / scale)))
        for header in self._headers:
            header.setVisible(top - 32 <= header._virtual_y <= bottom)
            if header.isVisible():
                header.setGeometry(8, physical_top + header._virtual_y - top,
                                   max(300, self.scroll_area.viewport().width() - 16), 28)
        width = max(self._img_width + 16, (self._container.width() - 16) // self._cols)
        wanted = {}
        for start, indices in self._sections:
            rows = (len(indices) + self._cols - 1) // self._cols
            first = max(0, (top - start) // self._row_height - 1)
            last = min(rows, (bottom - start) // self._row_height + 2)
            for position in range(first * self._cols, min(len(indices), last * self._cols)):
                idx = indices[position]
                wanted[idx] = (8 + position % self._cols * width,
                               start + position // self._cols * self._row_height)
        for idx in list(self._cards):
            if idx not in wanted:
                card = self._cards.pop(idx)
                card.hide()
                card.deleteLater()
        keys = []
        for idx, (x, y) in wanted.items():
            card = self._cards.get(idx)
            if card is None:
                card = self._make_card(idx, self._images[idx])
                card.setParent(self._container)
            card.setGeometry(x, physical_top + y - top, width - 10, self._row_height - 10)
            card.show()
            keys.append((self._images[idx].get('path', ''), self._img_width))
        self.thumbnails.set_visible(keys)

    @Slot(object, object)
    def _thumbnail_ready(self, key, image):
        for card in self._cards.values():
            if (card.img_data.get('path', ''), card.img_width) == key:
                card.set_thumbnail(image)

    def _make_card(self, idx: int, img: dict) -> ImageCard:
        card = ImageCard(idx, img, self._img_width, self._tag_filters)
        card.selection_changed.connect(self._on_card_selection)
        card.tag_added.connect(self.tag_add_requested)
        card.tag_remove_requested.connect(self._on_tag_remove)
        card.tag_insert_requested.connect(self.tag_insert_requested)
        card.preview_requested.connect(self._on_preview_requested)
        if idx in self._selected:
            card.set_selected(True)
        self._cards[idx] = card
        return card

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
        if any(self._tag_filters.values()):
            self._reorder_timer.start(0)

    def refresh_tags(self):
        for card in self._cards.values():
            card.refresh_tags()
        if any(self._tag_filters.values()):
            self._reorder_timer.start(0)


    def get_selected(self) -> set:
        return set(self._selected)
    
    def _on_tag_remove(self, idx: int, tag: str):
        self.tag_remove_requested.emit(idx, tag)
