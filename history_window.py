"""
history_window.py - Cửa sổ xem lịch sử thao tác
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QSplitter, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from i18n import tr


class HistoryWindow(QDialog):
    def __init__(self, history_manager, parent=None):
        super().__init__(parent)
        self.history = history_manager
        self.setMinimumSize(420, 500)
        self.setup_ui()
        self.retranslate_ui()
        self.history.add_callback(self.refresh)
        self.refresh()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self._title_lbl)

        splitter = QSplitter(Qt.Vertical)

        # Undo list
        undo_frame = QFrame()
        undo_layout = QVBoxLayout(undo_frame)
        undo_layout.setContentsMargins(0, 0, 0, 0)
        self._undo_lbl = QLabel()
        self._undo_lbl.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self.undo_list = QListWidget()
        self.undo_list.setAlternatingRowColors(True)
        undo_layout.addWidget(self._undo_lbl)
        undo_layout.addWidget(self.undo_list)
        splitter.addWidget(undo_frame)

        # Redo list
        redo_frame = QFrame()
        redo_layout = QVBoxLayout(redo_frame)
        redo_layout.setContentsMargins(0, 0, 0, 0)
        self._redo_lbl = QLabel()
        self._redo_lbl.setStyleSheet("color: #FF9800; font-weight: bold;")
        self.redo_list = QListWidget()
        self.redo_list.setAlternatingRowColors(True)
        redo_layout.addWidget(self._redo_lbl)
        redo_layout.addWidget(self.redo_list)
        splitter.addWidget(redo_frame)

        layout.addWidget(splitter, stretch=1)

        # Buttons
        btn_layout = QHBoxLayout()
        self.undo_btn = QPushButton()
        self.undo_btn.setStyleSheet("background:#4CAF50; color:white; font-weight:bold; padding:6px 14px;")
        self.undo_btn.clicked.connect(self._request_undo)

        self.redo_btn = QPushButton()
        self.redo_btn.setStyleSheet("background:#FF9800; color:white; font-weight:bold; padding:6px 14px;")
        self.redo_btn.clicked.connect(self._request_redo)

        self._clear_btn = QPushButton()
        self._clear_btn.setStyleSheet("background:#f44336; color:white; padding:6px 14px;")
        self._clear_btn.clicked.connect(self._clear)

        self._close_btn = QPushButton()
        self._close_btn.setStyleSheet("padding:6px 14px;")
        self._close_btn.clicked.connect(self.close)

        btn_layout.addWidget(self.undo_btn)
        btn_layout.addWidget(self.redo_btn)
        btn_layout.addWidget(self._clear_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self._close_btn)
        layout.addLayout(btn_layout)

    def retranslate_ui(self):
        self.setWindowTitle(tr("history_win_title"))
        self._title_lbl.setText(tr("history_win_header"))
        self._undo_lbl.setText(tr("history_undo_label"))
        self._redo_lbl.setText(tr("history_redo_label"))
        self.undo_btn.setText(tr("history_undo_btn"))
        self.redo_btn.setText(tr("history_redo_btn"))
        self._clear_btn.setText(tr("history_clear_btn"))
        self._close_btn.setText(tr("history_close_btn"))

    def refresh(self):
        self.undo_list.clear()
        for i, action in enumerate(self.history.get_undo_list()):
            item = QListWidgetItem(f"  {i+1}. {action}")
            item.setForeground(QColor("#ccffcc"))
            self.undo_list.addItem(item)

        self.redo_list.clear()
        for i, action in enumerate(self.history.get_redo_list()):
            item = QListWidgetItem(f"  {i+1}. {action}")
            item.setForeground(QColor("#ffdead"))
            self.redo_list.addItem(item)

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
