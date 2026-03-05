"""
tag_panel.py - Panel bên phải hiển thị danh sách tags của thư mục
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QFrame,
    QCheckBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from i18n import tr

class TagPanel(QWidget):
    filter_changed = Signal(dict)
    tag_insert_requested = Signal(str)
    delete_tags_requested = Signal()
    replace_tags_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_tags: list = []
        self._tag_counts: dict = {}
        self._tag_filters: dict = {}
        self._check_boxes: dict = {}
        self.setup_ui()
        # 2. Gọi retranslate lần đầu
        self.retranslate_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Lưu lại các label/button cần đổi text vào self
        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(self._title_lbl)

        search_row = QHBoxLayout()
        self._search_lbl = QLabel()
        self._search_lbl.setFixedWidth(40) # Tăng nhẹ độ rộng cho Tiếng Anh (Search:)
        
        self.search_edit = QLineEdit()
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter_display)
        
        search_row.addWidget(self._search_lbl)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        self._deselect_btn = QPushButton()
        self._deselect_btn.setStyleSheet("background:#9C27B0; color:white; font-weight:bold; padding:4px;")
        self._deselect_btn.clicked.connect(self.deselect_all_filters)

        self._delete_btn = QPushButton()
        self._delete_btn.setStyleSheet("background:#f44336; color:white; font-weight:bold; padding:4px;")
        self._delete_btn.clicked.connect(self.delete_tags_requested)

        self._replace_btn = QPushButton()
        self._replace_btn.setStyleSheet("background:#FF9800; color:white; font-weight:bold; padding:4px;")
        self._replace_btn.clicked.connect(self.replace_tags_requested)

        btn_row.addWidget(self._deselect_btn)
        btn_row.addWidget(self._delete_btn)
        btn_row.addWidget(self._replace_btn)
        layout.addLayout(btn_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.tags_container = QWidget()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(2, 2, 2, 2)
        self.tags_layout.setSpacing(1)
        self.tags_layout.addStretch()

        self.scroll_area.setWidget(self.tags_container)
        layout.addWidget(self.scroll_area, stretch=1)

    # 3. Phương thức cập nhật ngôn ngữ
    def retranslate_ui(self):
        self._title_lbl.setText("🔍 " + tr("tag_panel_title"))
        self._search_lbl.setText(tr("search_label") + ":")
        self.search_edit.setPlaceholderText(tr("search_placeholder"))
        self._deselect_btn.setText(tr("deselect_filters_btn"))
        self._delete_btn.setText(tr("delete_tags_btn"))
        self._replace_btn.setText(tr("replace_tags_btn"))
        
        # Rebuild lại danh sách để cập nhật chữ "Chèn/Insert" trên từng dòng tag
        if self._all_tags:
            self._rebuild_tag_list(self.search_edit.text())

    def _make_tag_row(self, tag: str) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(4, 1, 4, 1)
        row_layout.setSpacing(4)

        cb = QCheckBox()
        cb.setChecked(self._tag_filters.get(tag, False))
        cb.stateChanged.connect(lambda state, t=tag: self._on_filter_toggle(t, state))
        self._check_boxes[tag] = cb

        count = self._tag_counts.get(tag, 0)
        lbl = QLabel(f"{tag} ({count})")
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lbl.setCursor(Qt.PointingHandCursor)
        lbl.mousePressEvent = lambda e, t=tag: self.tag_insert_requested.emit(t)

        # Sử dụng tr() cho nút chèn
        insert_btn = QPushButton(tr("insert_btn_short"))
        insert_btn.setFixedWidth(55) # Tăng nhẹ để vừa chữ "Insert"
        insert_btn.setStyleSheet("background:#2196F3; color:white; font-size:9px; padding:2px;")
        insert_btn.clicked.connect(lambda _, t=tag: self.tag_insert_requested.emit(t))

        row_layout.addWidget(cb)
        row_layout.addWidget(lbl)
        row_layout.addWidget(insert_btn)
        return row

    def load_tags(self, all_tags: list, tag_counts: dict):
        self._all_tags = all_tags
        self._tag_counts = tag_counts
        self._tag_filters = {}
        self._check_boxes = {}
        self._rebuild_tag_list(self.search_edit.text())

    def _rebuild_tag_list(self, filter_text: str = ""):
        # Clear old
        while self.tags_layout.count() > 1:
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._check_boxes.clear()
        ft = filter_text.lower().strip()

        for tag in self._all_tags:
            if ft and ft not in tag.lower():
                continue
            row = self._make_tag_row(tag)
            self.tags_layout.insertWidget(self.tags_layout.count() - 1, row)

    def _filter_display(self, text: str):
        self._rebuild_tag_list(text)

    def _on_filter_toggle(self, tag: str, state: int):
        # self._tag_filters[tag] = (state == Qt.Checked)
        is_checked = (state == Qt.Checked or state == 2) 
        self._tag_filters[tag] = is_checked
        self.filter_changed.emit(dict(self._tag_filters))

    def deselect_all_filters(self):
        self._tag_filters.clear()
        for cb in self._check_boxes.values():
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
        self.filter_changed.emit({})

    def get_selected_filter_tags(self) -> list:
        return [t for t, v in self._tag_filters.items() if v]
