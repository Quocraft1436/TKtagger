"""
resort_tags_simple.py - Simple tag reordering (move to beginning/ending)
Dialog + logic in single module
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QCheckBox, QScrollArea, QWidget, QRadioButton, QButtonGroup, QFrame,
    QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from i18n import tr


class ResortTagsSimpleDialog(QDialog):
    def __init__(self, all_tags: list, parent=None):
        super().__init__(parent)
        self.all_tags = all_tags
        self.setModal(True)
        self._check_boxes = {}
        self._row_widgets = {}
        self._chk_global = None
        self.setup_ui()
        self.retranslate_ui()

    def setup_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 10, 14, 10)

        self._header_lbl = QLabel()
        self._header_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        self._layout.addWidget(self._header_lbl)

        self.search_edit = QLineEdit()
        self.search_edit.addAction(QIcon.fromTheme("edit-find"), QLineEdit.ActionPosition.LeadingPosition)
        self.search_edit.setClearButtonEnabled(True)
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

        # Global checkbox
        self._chk_global = QCheckBox()
        self._chk_global.setToolTip(tr("resort_global_tooltip"))
        self._layout.addWidget(self._chk_global)

        btn_layout = QHBoxLayout()
        self._deselect_btn = QPushButton()
        self._deselect_btn.clicked.connect(self._deselect_all)
        self._confirm_btn = QPushButton()
        self._confirm_btn.setStyleSheet("font-weight: bold; background: #4CAF50; color: white;")
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
        self._chk_global.setText(tr("resort_global_cb"))
        self._deselect_btn.setText(tr("ldl_deselect_all"))
        self._confirm_btn.setText(tr("ldl_confirm"))
        self._cancel_btn.setText(tr("ldl_cancel"))

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
    
    def is_global_mode(self) -> bool:
        return self._chk_global.isChecked() if self._chk_global else False


def run_resort_tags_simple(win, root_folder: str = None) -> bool:
    """
    Simple tag reordering: move selected tags to beginning or ending.
    Supports both local (current folder) and global (recursive from root) modes.
    
    Args:
        win: MainWindow instance
        root_folder: Root folder for global mode (optional)
        
    Returns:
        True if processed, False if cancelled
    """
    if not win.images:
        QMessageBox.information(win, tr("notify_no_image"), tr("notify_no_image_msg"))
        return False

    dlg = ResortTagsSimpleDialog(win.all_folder_tags, win)
    if dlg.exec() != ResortTagsSimpleDialog.Accepted:
        return False

    chosen = dlg.get_selected_tags()
    if not chosen:
        QMessageBox.information(win, tr("notify_no_tag_selected"),
                                tr("notify_no_tag_selected_msg"))
        return False

    position = dlg.get_position()
    global_mode = dlg.is_global_mode()
    
    if not root_folder:
        root_folder = win.root_folder or win.current_folder
    
    # Show confirmation with scope
    scope_txt = (tr("resort_scope_root", target=root_folder) if global_mode
                 else tr("resort_scope_current", target=win.current_folder))
    if QMessageBox.question(
        win, tr("sort_dialog_title"),
        scope_txt,
        QMessageBox.Yes | QMessageBox.No
    ) != QMessageBox.Yes:
        return False
    
    chosen_set = set(chosen)
    before = win._snapshot()
    affected = 0

    for idx, img in enumerate(win.images):
        present   = [t for t in img['tags'] if t in chosen_set]
        if not present:
            continue
        remaining = [t for t in img['tags'] if t not in chosen_set]
        img['tags'] = (present + remaining) if position == "beginning" else (remaining + present)
        img['modified'] = True
        win.image_grid.refresh_card(idx)
        affected += 1

    win._push_history(tr("history_sort_tags", tags=chosen, position=position), before)
    win._reload_tags_panel()
    QMessageBox.information(win, tr("sort_done"), tr("sort_done_msg", count=affected))
    return True
