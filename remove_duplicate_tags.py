"""
remove_duplicate_tags.py
Logic xóa tag trùng — tách ra khỏi main_window để dễ test/reuse.
"""
import os
from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QLabel, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from i18n import tr


class RemoveDuplicatesDialog(QDialog):
    """Dialog để chọn local hay global mode cho remove duplicates."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("remove_dup_confirm_title"))
        self.setModal(True)
        self._setup_ui()
        self.retranslate_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)
        
        # Header
        header = QLabel(tr("remove_dup_confirm_msg"))
        header_font = QFont()
        header_font.setPointSize(10)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        layout.addWidget(divider)
        
        # Global checkbox
        self._chk_global = QCheckBox()
        self._chk_global.setToolTip(tr("resort_global_tooltip"))
        layout.addWidget(self._chk_global)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        self._cancel_btn = QPushButton()
        self._cancel_btn.clicked.connect(self.reject)
        self._confirm_btn = QPushButton()
        self._confirm_btn.setStyleSheet("background:#4CAF50; color:white; font-weight:bold; padding:4px 12px;")
        self._confirm_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._confirm_btn)
        layout.addLayout(btn_layout)
        
        self.setMinimumWidth(380)
    
    def retranslate_ui(self):
        self._chk_global.setText(tr("resort_global_cb"))
        self._cancel_btn.setText(tr("ldl_cancel"))
        self._confirm_btn.setText(tr("ldl_confirm"))
    
    def is_global_mode(self) -> bool:
        return self._chk_global.isChecked()


def run_remove_duplicates(win, root_folder: str = None) -> bool:
    """
    Remove duplicate tags from all images.
    
    Args:
        win: MainWindow instance
        root_folder: Root folder for global mode (optional)
    
    Returns:
        True if processed, False if cancelled
    """
    if not win.current_folder:
        QMessageBox.information(win, tr("notify_no_folder"), tr("notify_no_folder_msg"))
        return False

    # Show dialog to ask local vs global mode
    dlg = RemoveDuplicatesDialog(win)
    if dlg.exec() != RemoveDuplicatesDialog.Accepted:
        return False
    
    global_mode = dlg.is_global_mode()
    
    if not root_folder:
        root_folder = win.root_folder or win.current_folder
    
    # Show confirmation with scope
    scope_txt = (tr("resort_scope_root", target=root_folder) if global_mode
                 else tr("resort_scope_current", target=win.current_folder))
    if QMessageBox.question(
        win, tr("remove_dup_confirm_title"),
        f"{tr('remove_dup_confirm_msg')}\n\n{scope_txt}",
        QMessageBox.Yes | QMessageBox.No
    ) != QMessageBox.Yes:
        return False

    before = win._snapshot()
    for idx, img in enumerate(win.images):
        img['tags'] = list(dict.fromkeys(img['tags']))
        img['modified'] = True
        win.image_grid.refresh_card(idx)

    win._push_history(tr("history_remove_dup"), before)
    win._reload_tags_panel()
    QMessageBox.information(win, tr("remove_dup_done"), tr("remove_dup_done_msg"))
    return True
