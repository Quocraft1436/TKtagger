"""
tag_panel.py - Panel bên phải hiển thị danh sách tags của thư mục
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QFrame,
    QCheckBox, QSizePolicy, QComboBox,
)
from PySide6.QtCore import Qt, Signal
from i18n import tr

class TagPanel(QWidget):
    filter_changed         = Signal(dict)
    tag_insert_requested   = Signal(str)
    delete_tags_requested  = Signal()
    replace_tags_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_tags:    list = []
        self._tag_counts:  dict = {}
        self._tag_filters: dict = {}
        self._check_boxes: dict = {}
        self._dict_groups: dict = {}   # {group_name: [tag, …]}
        self._dict_loaded: bool = False
        self.setup_ui()
        self.retranslate_ui()

    # ─── UI ─────────────────────────────────────────────────────────────────
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Search row
        search_row = QHBoxLayout()
        self._search_lbl = QLabel()
        self._search_lbl.setFixedWidth(40)
        self.search_edit = QLineEdit()
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter_display)
        search_row.addWidget(self._search_lbl)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        # Group filter row (ẩn khi chưa load dict)
        self._group_filter_row = QWidget()
        gfr = QHBoxLayout(self._group_filter_row)
        gfr.setContentsMargins(0, 0, 0, 0)
        gfr.setSpacing(4)
        self._group_filter_lbl = QLabel()
        self._group_filter_lbl.setFixedWidth(40)
        self._group_combo = QComboBox()
        self._group_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._group_combo.currentIndexChanged.connect(lambda _: self._rebuild_tag_list(self.search_edit.text()))
        gfr.addWidget(self._group_filter_lbl)
        gfr.addWidget(self._group_combo)
        layout.addWidget(self._group_filter_row)
        self._group_filter_row.setVisible(False)

        # Action buttons
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

        # Scroll area
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

    # ─── i18n ────────────────────────────────────────────────────────────────
    def retranslate_ui(self):
        self._search_lbl.setText(tr("search_label") + ":")
        self.search_edit.setPlaceholderText(tr("search_placeholder"))

        self._group_filter_lbl.setText(tr("group_label") + ":")
        if self._group_combo.count() > 0:
            self._group_combo.setItemText(0, tr("group_all"))
        self._deselect_btn.setText(tr("deselect_filters_btn"))
        self._delete_btn.setText(tr("delete_tags_btn"))
        self._replace_btn.setText(tr("replace_tags_btn"))
        if self._all_tags:
            self._rebuild_tag_list(self.search_edit.text())

    # ─── Dict integration ───────────────────────────────────────────────────
    def set_dict_groups(self, groups: dict):
        """
        groups = {group_name: [expanded_tag, …]}
        Truyền {} hoặc None để reset (ẩn combo).
        """
        self._dict_groups = groups or {}
        self._dict_loaded = bool(self._dict_groups)
        self._group_combo.blockSignals(True)
        self._group_combo.clear()
        if self._dict_loaded:
            all_text = tr("group_all")
            self._group_combo.addItem(all_text)
            for gname in self._dict_groups:
                self._group_combo.addItem(gname)
        self._group_combo.blockSignals(False)
        self._group_filter_row.setVisible(self._dict_loaded)
        self._rebuild_tag_list(self.search_edit.text())

    # ─── Tag row ─────────────────────────────────────────────────────────────
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
        insert_btn = QPushButton(tr("insert_btn_short"))
        insert_btn.setFixedWidth(55)
        insert_btn.setStyleSheet("background:#2196F3; color:white; font-size:9px; padding:2px;")
        insert_btn.clicked.connect(lambda _, t=tag: self.tag_insert_requested.emit(t))
        row_layout.addWidget(cb)
        row_layout.addWidget(lbl)
        row_layout.addWidget(insert_btn)
        return row

    # ─── Load / rebuild ──────────────────────────────────────────────────────
    def load_tags(self, all_tags: list, tag_counts: dict):
        self._all_tags    = all_tags
        self._tag_counts  = tag_counts
        self._tag_filters = {}
        self._check_boxes = {}
        self._rebuild_tag_list(self.search_edit.text())

    def _get_group_whitelist(self):
        """Trả về set tags thuộc nhóm đang chọn, hoặc None nếu All."""
        if not self._dict_loaded or self._group_combo.currentIndex() <= 0:
            return None
        gname = self._group_combo.currentText()
        return set(self._dict_groups.get(gname, []))

    @staticmethod
    def _matches_jei(tag: str, tokens: list) -> bool:
        """JEI: khớp nếu tag chứa ÍT NHẤT MỘT token (OR logic)."""
        if not tokens:
            return True
        tl = tag.lower()
        return any(tok in tl for tok in tokens)

    def _rebuild_tag_list(self, filter_text: str = ""):
        # Clear
        while self.tags_layout.count() > 1:
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._check_boxes.clear()

        # JEI tokens
        tokens = [t.strip().lower() for t in filter_text.split(",") if t.strip()]
        whitelist = self._get_group_whitelist()

        for tag in self._all_tags:
            if whitelist is not None and tag not in whitelist:
                continue
            if not self._matches_jei(tag, tokens):
                continue
            row = self._make_tag_row(tag)
            self.tags_layout.insertWidget(self.tags_layout.count() - 1, row)

    # ─── Signals ─────────────────────────────────────────────────────────────
    def _filter_display(self, text: str):
        self._rebuild_tag_list(text)

    def _on_filter_toggle(self, tag: str, state: int):
        self._tag_filters[tag] = (state == Qt.Checked or state == 2)
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