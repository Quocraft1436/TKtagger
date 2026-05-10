"""
replace_tags.py
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QScrollArea, QWidget, QMessageBox
)
from i18n import tr


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
            entry.setClearButtonEnabled(True)
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
        self._cancel_btn.setText(tr("ldl_cancel"))
        self._confirm_btn.setText(tr("ldl_confirm"))

    def get_replace_map(self) -> dict:
        """Returns {old_tag: new_tag} for valid replacements."""
        result = {}
        for old_tag, entry in self._entries.items():
            new_tag = entry.text().strip()
            if new_tag and new_tag != old_tag:
                result[old_tag] = new_tag
        return result


def run_replace_tags(win) -> bool:
    selected = win.tag_panel.get_selected_filter_tags()
    if not selected:
        QMessageBox.warning(win, tr("warn_select_tag_replace"),
                            tr("warn_select_tag_replace_msg"))
        return False

    # Show dialog to get replacement mapping
    dlg = ReplaceTagsDialog(selected, win)
    if dlg.exec() != ReplaceTagsDialog.Accepted:
        return False

    replace_map = dlg.get_replace_map()
    if not replace_map:
        QMessageBox.information(win, tr("replace_nothing"), tr("replace_nothing_msg"))
        return False

    # Execute replacement
    before = win._snapshot()
    affected = 0
    for idx, img in enumerate(win.images):
        modified = False
        for old_tag, new_tag in replace_map.items():
            if old_tag in img['tags']:
                img['tags'].remove(old_tag)
                if new_tag not in img['tags']:
                    img['tags'].append(new_tag)
                modified = True
        if modified:
            img['modified'] = True
            win.image_grid.refresh_card(idx)
            affected += 1

    win._push_history(tr("history_replace_tags", map=replace_map), before)
    win._reload_tags_panel()
    QMessageBox.information(win, tr("replace_done"),
                            tr("replace_done_msg", count=affected))
    return True
