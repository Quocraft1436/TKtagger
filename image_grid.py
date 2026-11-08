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
from bisect import bisect_right

from libs.i18n import tr
from libs.thumbnail_loader import ThumbnailLoader

def _tag_layout(tags, metrics, width):
    """Measure and wrap tags identically for painted cards and virtual rows."""
    entries = []
    x, y = 2, 2
    line_height = metrics.height() + 4
    available = max(1, width - 7)
    comma_width = metrics.horizontalAdvance(", ")
    for index, tag in enumerate(tags):
        remaining = tag
        while remaining:
            has_next = index < len(tags) - 1
            needed = metrics.horizontalAdvance(remaining) + (comma_width if has_next else 0)
            if x > 2 and x + needed > width - 5:
                x = 2
                y += line_height
            length = len(remaining)
            if metrics.horizontalAdvance(remaining) > available:
                low, high = 1, length
                while low < high:
                    middle = (low + high + 1) // 2
                    if metrics.horizontalAdvance(remaining[:middle]) <= available:
                        low = middle
                    else:
                        high = middle - 1
                length = low
            text, remaining = remaining[:length], remaining[length:]
            text_width = metrics.horizontalAdvance(text)
            comma = has_next and not remaining
            entries.append((QRect(x, y, text_width, metrics.height()), tag, text, comma))
            x += text_width + (comma_width if comma else 0)
            if remaining:
                x = 2
                y += line_height
    return entries, (y + line_height + 4 if tags else 25)


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
        
        # The grid sets the caption height for each virtual row. Bounded modes
        # scroll captions; full-content mode expands the row to fit them.
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
        self.tag_entry.setMinimumWidth(0)
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
        self.tag_rects, height = _tag_layout(
            self.ordered_tags, QFontMetrics(self.tag_font), self.width())
        self.setMinimumHeight(height)

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

        for rect, tag, text, comma in self.tag_rects:
            is_active = self.tag_filters.get(tag, False)

            # Tag active vẫn màu xanh.
            # Tag bình thường lấy màu text của theme.
            color = QColor("#80ff80") if is_active else text_color

            painter.setPen(color)
            painter.drawText(
                rect,
                Qt.AlignLeft | Qt.AlignTop,
                text
            )

            # Vẽ dấu phẩy
            if comma:
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

        for rect, tag, _, _ in self.tag_rects:
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
        for rect, tag, _, _ in self.tag_rects:
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
    columns_changed = Signal(int)
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
        self._manual_cols = 3
        self.layout_mode = "classic"
        self.card_height_mode = "medium"
        self._row_offsets = []
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
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(80)
        self._resize_timer.timeout.connect(self._adapt_layout)
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
        self._manual_cols = cols
        if self.layout_mode == "classic" and cols != self._cols:
            self._change_layout(cols, 200)

    def set_layout_mode(self, mode):
        mode = mode if mode in ("classic", "adaptive") else "classic"
        if mode == self.layout_mode:
            return
        self.layout_mode = mode
        self._resize_timer.stop()
        if mode == "adaptive":
            self._adapt_layout()
        else:
            self._change_layout(self._manual_cols, 200)

    def set_card_height_mode(self, mode):
        mode = mode if mode in ("medium", "tall", "full") else "medium"
        if mode != self.card_height_mode:
            self.card_height_mode = mode
            self._change_layout(self._cols, self._img_width)

    def _row_at(self, section, offset):
        offsets = self._row_offsets[section]
        return min(len(offsets) - 2, max(0, bisect_right(offsets, offset) - 1))

    def _adapt_layout(self):
        if self.layout_mode != "adaptive":
            return
        available = max(1, self.scroll_area.viewport().width() - 16)
        cols = max(1, available // 224)
        image_width = max(1, available // cols - 24)
        if (cols, image_width) != (self._cols, self._img_width):
            self._change_layout(cols, image_width)

    def _logical_top(self):
        view_height = self.scroll_area.viewport().height()
        return round(self.scroll_area.verticalScrollBar().value()
                     * max(0, self._virtual_height - view_height)
                     / max(1, self._container.height() - view_height))

    def _change_layout(self, cols, image_width):
        # Keep the first visible image at the same relative row position.
        top = self._logical_top()
        anchor = None
        for section_index, (start, indices) in enumerate(self._sections):
            offsets = self._row_offsets[section_index]
            if start + offsets[-1] > top:
                row = self._row_at(section_index, top - start)
                position = row * self._cols
                fraction = max(0, top - start - offsets[row]) / (offsets[row + 1] - offsets[row])
                if position < len(indices):
                    anchor = (indices, position, fraction)
                break
        self._cols = cols
        self._img_width = image_width
        self._row_height = image_width + (294 if self.card_height_mode == "tall" else 174)
        self._rebuild(reuse_sections=not self._reorder_timer.isActive())
        if anchor:
            indices, position, fraction = anchor
            for section_index, (start, section) in enumerate(self._sections):
                if section is indices:
                    row = position // cols
                    offsets = self._row_offsets[section_index]
                    target = start + offsets[row] + fraction * (offsets[row + 1] - offsets[row])
                    height = self.scroll_area.viewport().height()
                    logical_range = max(1, self._virtual_height - height)
                    physical_range = max(0, self._container.height() - height)
                    self.scroll_area.verticalScrollBar().setValue(round(target * physical_range / logical_range))
                    break
        self._update_visible()
        self.columns_changed.emit(cols)

    def set_tag_filters(self, filters: dict):
        active = {key: True for key, value in filters.items() if value}
        if active == self._tag_filters:
            return
        self._tag_filters = active
        self._rebuild()

    def _rebuild(self, reuse_sections=False):
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
            if not reuse_sections:
                for header in self._headers:
                    header.deleteLater()
                self._headers.clear()
                active = {tag for tag, enabled in self._tag_filters.items() if enabled}
                matched, rest = [], []
                for idx, image in enumerate(self._images):
                    (matched if not active or active.intersection(image['tags']) else rest).append(idx)
                self._sections = []
                for indices, title in ((matched, 'images_with_tags'), (rest, 'images_without_tags')):
                    if not indices:
                        continue
                    if active:
                        self._headers.append(QLabel(tr(title) + ': ' + ', '.join(sorted(active)), self._container))
                    self._sections.append((0, indices))
            y = 8
            self._row_offsets = []
            metrics = QFontMetrics(QFont("Consolas", 11))
            measured = {}
            for section_index, (_, indices) in enumerate(self._sections):
                if self._headers:
                    self._headers[section_index]._virtual_y = y
                    y += 32
                self._sections[section_index] = (y, indices)
                rows = (len(indices) + self._cols - 1) // self._cols
                if self.card_height_mode == "full":
                    offsets = [0]
                    for row in range(rows):
                        tag_height = 25
                        for idx in indices[row * self._cols:(row + 1) * self._cols]:
                            tags = tuple(self._images[idx].get('tags', []))
                            # Reordering active tags can change line wrapping.
                            tags = tuple(t for t in tags if self._tag_filters.get(t, False)) + tuple(t for t in tags if not self._tag_filters.get(t, False))
                            if tags not in measured:
                                if len(measured) >= 4096:
                                    measured.clear()
                                measured[tags] = _tag_layout(tags, metrics, max(1, self._img_width - 8))[1]
                            tag_height = max(tag_height, measured[tags])
                        offsets.append(offsets[-1] + self._img_width + tag_height + 62)
                else:
                    offsets = range(0, (rows + 1) * self._row_height, self._row_height)
                self._row_offsets.append(offsets)
                y += offsets[-1]
            self._virtual_height = max(1, y)
            # QWidget coordinates are limited (~16 million pixels). Map the
            # scrollbar to logical rows instead of allocating a taller canvas.
            minimum_width = (self._cols * (self._img_width + 24) + 16
                             if self.layout_mode == "classic" else 0)
            self._container.setMinimumSize(minimum_width, min(self._virtual_height, 8_000_000))
        finally:
            self._rebuilding = False
        self._update_visible()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Resize, QEvent.Show):
            if self.layout_mode == "adaptive":
                self._resize_timer.start()
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
        for section_index, (start, indices) in enumerate(self._sections):
            offsets = self._row_offsets[section_index]
            rows = len(offsets) - 1
            if bottom < start or top > start + offsets[-1]:
                continue
            first = max(0, self._row_at(section_index, top - start) - 1)
            last = min(rows, self._row_at(section_index, bottom - start) + 2)
            for position in range(first * self._cols, min(len(indices), last * self._cols)):
                idx = indices[position]
                wanted[idx] = (8 + position % self._cols * width,
                               start + offsets[position // self._cols],
                               offsets[position // self._cols + 1] - offsets[position // self._cols])
        for idx in list(self._cards):
            if idx not in wanted:
                card = self._cards.pop(idx)
                card.hide()
                card.deleteLater()
        keys = []
        for idx, (x, y, row_height) in wanted.items():
            card = self._cards.get(idx)
            if card is None:
                card = self._make_card(idx, self._images[idx])
                card.setParent(self._container)
            card.tag_scroll.setFixedHeight(row_height - self._img_width - 54)
            card.tag_scroll.setVerticalScrollBarPolicy(
                Qt.ScrollBarAlwaysOff if self.card_height_mode == "full" else Qt.ScrollBarAsNeeded)
            card.setGeometry(x, physical_top + y - top, width - 10, row_height - 10)
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
        if self.card_height_mode == "full" or any(self._tag_filters.values()):
            self._reorder_timer.start(0)

    def refresh_tags(self):
        for card in self._cards.values():
            card.refresh_tags()
        if self.card_height_mode == "full" or any(self._tag_filters.values()):
            self._reorder_timer.start(0)


    def get_selected(self) -> set:
        return set(self._selected)
    
    def _on_tag_remove(self, idx: int, tag: str):
        self.tag_remove_requested.emit(idx, tag)
