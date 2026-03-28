"""
history_window.py - Simple timeline history window
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from i18n import tr


class HistoryWindow(QDialog):
    def __init__(self, history_manager, parent=None):
        super().__init__(parent)
        self.history = history_manager

        self.setMinimumSize(360, 500)

        self.setup_ui()
        self.retranslate_ui()

        self.history.add_callback(self.refresh)
        self.refresh()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Timeline list
        self.timeline = QListWidget()
        layout.addWidget(self.timeline)

        # Buttons
        btn_layout = QHBoxLayout()

        self.undo_btn = QPushButton()
        self.undo_btn.setIcon(QIcon.fromTheme("edit-undo"))
        self.undo_btn.clicked.connect(self._request_undo)

        self.redo_btn = QPushButton()
        self.redo_btn.setIcon(QIcon.fromTheme("edit-redo"))
        self.redo_btn.clicked.connect(self._request_redo)
        
        # Clear button will be replace to Discard for session history
        self.clear_btn = QPushButton()
        self.clear_btn.setIcon(QIcon.fromTheme("dialog-cancel"))
        self.clear_btn.clicked.connect(self._clear)

        btn_layout.addWidget(self.undo_btn)
        btn_layout.addWidget(self.redo_btn)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)

    def retranslate_ui(self):
        self.setWindowTitle(tr("history_win_title"))
        self.undo_btn.setText(tr("ldl_undo"))
        self.redo_btn.setText(tr("ldl_redo"))
        self.clear_btn.setText(tr("history_clear_btn"))

    def refresh(self):
        self.timeline.clear()

        undo_list = self.history.get_undo_list()
        redo_list = self.history.get_redo_list()

        # Build full timeline
        full = undo_list + ["^ ---"] + redo_list

        # Current index in original list
        current_index = len(undo_list) - 1

        for i, action in enumerate(full):
            item = QListWidgetItem(str(action))

            # Convert reversed index back to original index
            original_index = len(full) - 1 - i

            if original_index == current_index:
                item.setSelected(True)

            if action == "---":
                item.setFlags(Qt.NoItemFlags)

            self.timeline.addItem(item)

        self.undo_btn.setEnabled(self.history.can_undo())
        self.redo_btn.setEnabled(self.history.can_redo())

    def _request_undo(self):
        if self.parent():
            self.parent().do_undo()

    def _request_redo(self):
        if self.parent():
            self.parent().do_redo()

    def _clear(self):
        self.history.clear()
        self.refresh()