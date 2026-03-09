"""
dialogs.py - Các cửa sổ hộp thoại phụ
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QCheckBox, QScrollArea,
    QWidget, QRadioButton, QButtonGroup, QFrame,
    QMessageBox
)
from PySide6.QtCore import Qt, QCoreApplication
from i18n import tr


class SortTagsDialog(QDialog):
    def __init__(self, all_tags: list, parent=None):
        super().__init__(parent)
        self.all_tags = all_tags
        self.setModal(True)
        self._check_boxes = {}
        self._row_widgets = {}
        self.setup_ui()
        self.retranslate_ui()

    def setup_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 10, 14, 10)

        self._header_lbl = QLabel()
        self._header_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        self._layout.addWidget(self._header_lbl)

        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self._filter)
        self._layout.addWidget(self.search_edit)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(1)
        self.content_layout.addStretch()
        scroll.setWidget(self.content_widget)
        self._layout.addWidget(scroll, stretch=1)

        for tag in self.all_tags:
            cb = QCheckBox(tag)
            self._check_boxes[tag] = cb
            self.content_layout.insertWidget(self.content_layout.count() - 1, cb)
            self._row_widgets[tag] = cb

        # Position radios
        pos_frame = QFrame()
        pos_layout = QHBoxLayout(pos_frame)
        self._pos_lbl = QLabel()
        pos_layout.addWidget(self._pos_lbl)
        self._pos_group = QButtonGroup(self)
        self._rb_begin = QRadioButton()
        self._rb_end = QRadioButton()
        self._rb_begin.setChecked(True)
        self._pos_group.addButton(self._rb_begin)
        self._pos_group.addButton(self._rb_end)
        pos_layout.addWidget(self._rb_begin)
        pos_layout.addWidget(self._rb_end)
        pos_layout.addStretch()
        self._layout.addWidget(pos_frame)

        btn_layout = QHBoxLayout()
        self._deselect_btn = QPushButton()
        self._deselect_btn.clicked.connect(self._deselect_all)
        self._confirm_btn = QPushButton()
        self._confirm_btn.setStyleSheet("font-weight: bold; background: #4CAF50; color: white; padding: 6px 16px;")
        self._confirm_btn.clicked.connect(self.accept)
        self._cancel_btn = QPushButton()
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._deselect_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._confirm_btn)
        self._layout.addLayout(btn_layout)

    def retranslate_ui(self):
        self.setWindowTitle(tr("sort_dialog_title"))
        self.setMinimumSize(380, 580)
        self._header_lbl.setText(tr("sort_dialog_header"))
        self.search_edit.setPlaceholderText(tr("sort_search_placeholder"))
        self._pos_lbl.setText(tr("sort_position_label"))
        self._rb_begin.setText(tr("sort_pos_begin"))
        self._rb_end.setText(tr("sort_pos_end"))
        self._deselect_btn.setText(tr("sort_deselect_all"))
        self._confirm_btn.setText(tr("sort_confirm"))
        self._cancel_btn.setText(tr("sort_cancel"))

    def _filter(self, text: str):
        text = text.lower().strip()
        for tag, widget in self._row_widgets.items():
            widget.setVisible(not text or text in tag.lower())

    def _deselect_all(self):
        for cb in self._check_boxes.values():
            cb.setChecked(False)

    def get_selected_tags(self) -> list:
        return [tag for tag, cb in self._check_boxes.items() if cb.isChecked()]

    def get_position(self) -> str:
        return "beginning" if self._rb_begin.isChecked() else "ending"


class ReplaceTagsDialog(QDialog):
    def __init__(self, selected_tags: list, parent=None):
        super().__init__(parent)
        self.selected_tags = selected_tags
        self.setMinimumWidth(500)
        self.setModal(True)
        self._entries = {}
        self.setup_ui()
        self.retranslate_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)

        self._desc_lbl = QLabel()
        self._desc_lbl.setWordWrap(True)
        layout.addWidget(self._desc_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        for tag in self.selected_tags:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(tag)
            lbl.setFixedWidth(150)
            lbl.setStyleSheet("font-weight: bold;")
            entry = QLineEdit()
            self._entries[tag] = entry
            row_layout.addWidget(lbl)
            row_layout.addWidget(entry)
            content_layout.addWidget(row)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        btn_layout = QHBoxLayout()
        self._cancel_btn = QPushButton()
        self._cancel_btn.clicked.connect(self.reject)
        self._confirm_btn = QPushButton()
        self._confirm_btn.setStyleSheet("font-weight: bold; background: #FF9800; color: white; padding: 6px 16px;")
        self._confirm_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._confirm_btn)
        layout.addLayout(btn_layout)

    def retranslate_ui(self):
        self.setWindowTitle(tr("replace_dialog_title"))
        self._desc_lbl.setText(tr("replace_dialog_desc"))
        for entry in self._entries.values():
            entry.setPlaceholderText(tr("replace_placeholder"))
        self._cancel_btn.setText(tr("replace_cancel"))
        self._confirm_btn.setText(tr("replace_confirm"))

    def get_replace_map(self) -> dict:
        result = {}
        for old_tag, entry in self._entries.items():
            new_tag = entry.text().strip()
            if new_tag and new_tag != old_tag:
                result[old_tag] = new_tag
        return result


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(360, 220)
        self.setModal(True)
        self.setup_ui()
        self.retranslate_ui()

class AboutDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(420, 240)
        self.setModal(True)

        self.setup_ui()
        self.retranslate_ui()

    def setup_ui(self):

        main_layout = QVBoxLayout(self)
        top_layout = QHBoxLayout()

        # icon_label = QLabel()
        # pix = QPixmap("icon.png")   # path icon
        # icon_label.setPixmap(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        # icon_label.setAlignment(Qt.AlignTop)

        # top_layout.addWidget(icon_label)

        # ----- info -----
        info_layout = QVBoxLayout()

        lbl_title = QLabel("TK-Tagger")
        lbl_title.setStyleSheet("font-size:20px; font-weight:bold;")
        info_layout.addWidget(lbl_title)

        self._lbl_author = QLabel()
        info_layout.addWidget(self._lbl_author)

        url = "https://github.com/Quocraft1436/TKtagger"
        lbl_link = QLabel(f'<a href="{url}">{url}</a>')
        lbl_link.setOpenExternalLinks(True)
        info_layout.addWidget(lbl_link)

        self._lbl_version = QLabel()
        info_layout.addWidget(self._lbl_version)

        self._lbl_license = QLabel()
        self._lbl_license.setStyleSheet("font-style: italic;")
        info_layout.addWidget(self._lbl_license)

        self._lbl_copy = QLabel()
        self._lbl_copy.setWordWrap(True)
        info_layout.addWidget(self._lbl_copy)

        info_layout.addStretch()

        top_layout.addLayout(info_layout)

        main_layout.addLayout(top_layout)

        # ===== button =====
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._close_btn = QPushButton()
        self._close_btn.setFixedWidth(80)
        self._close_btn.clicked.connect(self.close)

        btn_layout.addWidget(self._close_btn)

        main_layout.addLayout(btn_layout)

    def retranslate_ui(self):
        self.setWindowTitle(tr("about_title"))
        self._lbl_author.setText(tr("about_author"))
        version = QCoreApplication.applicationVersion()
        self._lbl_version.setText(tr("about_version", version=version))
        self._lbl_license.setText(tr("about_license"))
        self._lbl_copy.setText(tr("about_copy"))
        self._close_btn.setText(tr("about_close"))
