"""
image_grid.py - Widget hiển thị lưới ảnh
"""
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QGridLayout, QVBoxLayout,
    QHBoxLayout, QLabel, QCheckBox, QLineEdit,
    QPushButton, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage
import os

from i18n import tr

class ImageCard(QFrame):
    """Widget thẻ ảnh đơn với checkbox và hiển thị tags."""
    selection_changed = Signal(int, bool)
    tag_added = Signal(int, str)

    tag_remove_requested = Signal(int, str)
    tag_insert_requested = Signal(str)

    def __init__(self, idx: int, img_data: dict, img_width: int = 200,
                 tag_filters: dict = None, parent=None):
        super().__init__(parent)
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
        # Dùng #ImageCard selector thay vì QFrame để stylesheet KHÔNG cascade xuống children
        if selected:
            self.setStyleSheet("#ImageCard { border: 3px solid #4CAF50; border-radius: 4px; }")
        else:
            self.setStyleSheet("#ImageCard { border: 2px solid #3c3c3c; border-radius: 4px; }")

    def retranslate_ui(self):
        """Cập nhật các thành phần text trong card."""
        self.tag_entry.setPlaceholderText(tr("add_tag_placeholder"))
        self.refresh_tags() # Để cập nhật tooltip và chữ "Không có tags"

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # Image
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignCenter)
        # img_label.setCursor(Qt.PointingHandCursor)
        img_label.setFixedSize(self.img_width, self.img_width)
        # img_label.mousePressEvent = lambda e: self.toggle_select()
        # self._load_image(img_label)
        self.img_label = img_label
        self._image_loaded = False
        layout.addWidget(self.img_label, alignment=Qt.AlignCenter)

        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self._on_check_changed)
        layout.addWidget(self.checkbox, alignment=Qt.AlignCenter)

        # Tags display
        self.tag_display = QWidget()
        self.tag_display_layout = QGridLayout(self.tag_display)
        self.tag_display_layout.setContentsMargins(2, 2, 2, 2)
        self.tag_display_layout.setSpacing(2)
        layout.addWidget(self.tag_display)
        self.refresh_tags()

        # Tag entry row
        entry_row = QWidget()
        entry_layout = QHBoxLayout(entry_row)
        entry_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_entry = QLineEdit()
        self.tag_entry.setPlaceholderText(tr("add_tag_placeholder"))
        self.tag_entry.setFocusPolicy(Qt.ClickFocus)
        self.tag_entry.returnPressed.connect(self._add_tag)
        add_btn = QPushButton("+")
        add_btn.setFixedWidth(28)
        add_btn.setStyleSheet("background:#4CAF50; color:white; font-weight:bold;")
        add_btn.clicked.connect(self._add_tag)
        entry_layout.addWidget(self.tag_entry)
        entry_layout.addWidget(add_btn)
        layout.addWidget(entry_row)

    def _load_image(self, label: QLabel):
        try:
            # Load ảnh trực tiếp bằng QPixmap (Không cần PIL)
            pixmap = QPixmap(self.img_data['path'])
            
            if pixmap.isNull():
                raise ValueError("Không thể tải ảnh")

            # Scale ảnh theo kích thước mong muốn
            pixmap = pixmap.scaled(
                self.img_width,
                self.img_width,
                Qt.AspectRatioMode.KeepAspectRatio, # Dùng enum đầy đủ để tránh lỗi bản PyQt6
                Qt.TransformationMode.SmoothTransformation
            )
            
            label.setPixmap(pixmap)
            
        except Exception as e:
            print(f"Error: {e}") # Debug lỗi nếu cần
            label.setText(f"❌ Error: {e}")
            label.setStyleSheet("color: red;")

    def showEvent(self, event):
        super().showEvent(event)
        if not self._image_loaded:
            self._load_image(self.img_label)
            self._image_loaded = True

    def mousePressEvent(self, event):
        if self.tag_entry.underMouse():
            super().mousePressEvent(event)
            return
            
        if event.button() == Qt.LeftButton:
            self.toggle_select()
        super().mousePressEvent(event)

    def refresh_tags(self):
        # Clear
        while self.tag_display_layout.count():
            item = self.tag_display_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tags = self.img_data['tags']
        max_per_row = 3
        if tags:
            for i, tag in enumerate(tags):
                is_active = self.tag_filters.get(tag, False)
                color = "#80ff80" if is_active else "white"
                lbl = QLabel(tag)
                lbl.setCursor(Qt.PointingHandCursor)
                lbl.setStyleSheet(
                    f"background:#3c3c3c; color:{color}; font-weight:bold;"
                    f" padding:2px 5px; border-radius:3px;"
                )
                lbl.setWordWrap(True)

                def make_mouse_event(t):
                    def handler(event):
                        if event.button() == Qt.MiddleButton:
                            self.tag_remove_requested.emit(self.idx, t)
                        elif event.button() == Qt.RightButton:
                            self.tag_insert_requested.emit(t)
                    return handler

                lbl.mousePressEvent = make_mouse_event(tag)

                lbl.setToolTip(f'"{tag}"\n' + tr("tag_tooltip"))

                self.tag_display_layout.addWidget(lbl, i // max_per_row, i % max_per_row)
        else:
            lbl = QLabel(tr("no_tags_msg"))
            lbl.setStyleSheet("color:#888; font-style:italic;")
            self.tag_display_layout.addWidget(lbl, 0, 0)

    def toggle_select(self):
        self.checkbox.setChecked(not self.checkbox.isChecked())

    def _on_check_changed(self, state):
        self._selected = (state == Qt.Checked.value or state == Qt.Checked)
        self._set_border(self._selected)
        self.selection_changed.emit(self.idx, self._selected)

    def set_selected(self, value: bool):
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(value)
        self.checkbox.blockSignals(False)
        self._selected = value
        self._set_border(value)

    def is_selected(self) -> bool:
        return self._selected

    def _add_tag(self):
        tag = self.tag_entry.text().strip()
        if tag:
            self.tag_entry.clear()
            self.tag_added.emit(self.idx, tag)


class ImageGrid(QWidget):
    """Widget lưới ảnh chính."""
    selection_changed = Signal(set)
    tag_add_requested = Signal(int, str)

    tag_insert_requested = Signal(str)
    tag_remove_requested = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._images = []
        self._selected = set()
        self._tag_filters = {}
        self._cols = 3
        self._img_width = 200
        self._cards: dict = {}

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
        """Cập nhật text cho ImageGrid."""
        self._rebuild() # Rebuild lại grid để cập nhật các Header "Ảnh có tags/Không có tags"
        
        # Cập nhật tất cả các card đang hiển thị
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
        # Clear
        self._cards.clear()
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

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

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._grid_layout.addWidget(spacer, self._grid_layout.rowCount(), 0, 1, self._cols)

    def _make_card(self, idx: int, img: dict) -> ImageCard:
        card = ImageCard(idx, img, self._img_width, self._tag_filters)
        card.selection_changed.connect(self._on_card_selection)
        card.tag_added.connect(self.tag_add_requested)
        card.tag_remove_requested.connect(self._on_tag_remove)
        card.tag_insert_requested.connect(self.tag_insert_requested)
        if idx in self._selected:
            card.set_selected(True)
        self._cards[idx] = card
        return card

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