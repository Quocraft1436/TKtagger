"""
main_window.py - Cửa sổ chính của ứng dụng TKtagger (PySide6)
"""
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QLabel, QLineEdit, QPushButton,
    QTreeWidget, QTreeWidgetItem, QMessageBox,
    QFileDialog, QFrame, QStatusBar, QToolBar,
)
from PySide6.QtCore import Qt, QSize, QSettings, Signal
from PySide6.QtGui import QAction, QKeySequence, QShortcut

from history_manager import HistoryManager
from history_window import HistoryWindow
from file_ops import load_folder_images, save_all_images
from image_grid import ImageGrid
from tag_panel import TagPanel
from dialogs import SortTagsDialog, ReplaceTagsDialog, AboutDialog
from waifu_tagger_window import WaifuTaggerWindow
from i18n import tr, set_language, get_language


class MainWindow(QMainWindow):

    tagging_completed = Signal(list)

    def __init__(self, initial_path=None):
        super().__init__()
        self.lang = "en"
        set_language(self.lang)

        self.root_folder = None
        self.current_folder = None
        self.images: list = []
        self.all_folder_tags: list = []
        self.folder_tag_counts: dict = {}

        self.history = HistoryManager(max_history=100)
        self.history_win: HistoryWindow = None

        self.setup_menu()
        self.setup_ui()
        self.setup_shortcuts()
        self.retranslate_ui()           # first paint with correct language

        if initial_path and os.path.exists(initial_path):
            self._auto_load_path(initial_path)

        self.tagging_completed.connect(self._on_tagging_finished)

    # ──────────────────────────────────────────────
    #  Language switcher
    # ──────────────────────────────────────────────
    def switch_language(self, lang: str):
        set_language(lang)
        self.lang = lang
        self.retranslate_ui()
        # Also retranslate history window if already open
        if self.history_win and self.history_win.isVisible():
            self.history_win.retranslate_ui()

    # ──────────────────────────────────────────────
    #  Retranslate – update every stored widget ref
    # ──────────────────────────────────────────────
    def retranslate_ui(self):
        self.setWindowTitle(tr("app_title"))

        # Menu bar
        self._lang_menu.setTitle(tr("language"))
        self._file_menu.setTitle(tr("menu_file"))
        self._act_open.setText(tr("menu_open_folder"))
        self.recent_menu.setTitle(tr("menu_open_recent"))
        self._act_save.setText(tr("menu_save"))
        self._act_quit.setText(tr("menu_quit"))
        self._edit_menu.setTitle(tr("menu_edit"))
        self.act_undo.setText(tr("menu_undo"))
        self.act_redo.setText(tr("menu_redo"))
        self._act_history_action.setText(tr("menu_history"))
        self.tool_menu.setTitle(tr("menu_tool"))
        self._act_rm_dup.setText(tr("menu_remove_dup"))
        self._act_sort.setText(tr("menu_sort_tags"))
        self._act_waifu.setText(tr("menu_waifu_tagger"))
        self._help_menu.setTitle(tr("menu_help"))
        self._act_about.setText(tr("menu_about"))

        # Left panel
        self._dir_lbl.setText(tr("folder_label"))

        # Top toolbar
        self._sel_all_btn.setText(tr("select_all_btn"))
        self._inv_sel_btn.setText(tr("invert_sel_btn"))
        self._desel_btn.setText(tr("deselect_btn"))
        self._save_btn.setText(tr("save_btn"))
        self._hist_btn.setText(tr("history_btn"))

        # Column label
        self._col_lbl.setText(tr("col_display"))

        # Bottom tag bar
        self._global_tag_entry.setPlaceholderText(tr("tag_placeholder"))
        self._add_tag_btn.setText(tr("add_tag_btn"))
        self._rem_tag_btn.setText(tr("remove_tag_btn"))

        # Update Tag Panel
        if hasattr(self, 'tag_panel'):
            self.tag_panel.retranslate_ui()
        
        if hasattr(self, 'image_grid'):
            self.image_grid.retranslate_ui()

        # Status bar
        self.statusBar().showMessage(tr("ready"))

        # Keep undo/redo action text in sync
        self._update_undo_redo_actions()

    # ──────────────────────────────────────────────
    #  UI Setup
    # ──────────────────────────────────────────────
    def setup_menu(self):
        menubar = self.menuBar()
        self.settings = QSettings("settings.ini", QSettings.IniFormat)

        # File – use empty strings; retranslate_ui fills them
        self._file_menu = menubar.addMenu("")
        self._act_open = QAction("", self)
        self._act_open.setShortcut(QKeySequence.Open)
        self._act_open.triggered.connect(self.select_root_folder)

        self.recent_menu = self._file_menu.addMenu("")
        self.update_recent_menu()

        self._act_save = QAction("", self)
        self._act_save.setShortcut(QKeySequence.Save)
        self._act_save.triggered.connect(self.save_all)

        self._act_quit = QAction("", self)
        self._act_quit.setShortcut(QKeySequence.Quit)
        self._act_quit.triggered.connect(self.close)

        self._file_menu.addAction(self._act_open)
        self._file_menu.addAction(self._act_save)
        self._file_menu.addSeparator()
        self._file_menu.addAction(self._act_quit)

        # Edit
        self._edit_menu = menubar.addMenu("")
        self.act_undo = QAction("", self)
        self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_undo.setEnabled(False)
        self.act_undo.triggered.connect(self.do_undo)

        self.act_redo = QAction("", self)
        self.act_redo.setShortcut(QKeySequence.Redo)
        self.act_redo.setEnabled(False)
        self.act_redo.triggered.connect(self.do_redo)

        self._act_history_action = QAction("", self)
        self._act_history_action.triggered.connect(self.show_history_window)

        self._edit_menu.addAction(self.act_undo)
        self._edit_menu.addAction(self.act_redo)
        self._edit_menu.addSeparator()
        self._edit_menu.addAction(self._act_history_action)

        # Tool
        self.tool_menu = menubar.addMenu("")
        self.tool_menu.setEnabled(False)

        self._act_rm_dup = QAction("", self)
        self._act_rm_dup.triggered.connect(self.remove_duplicate_tags)

        self._act_sort = QAction("", self)
        self._act_sort.triggered.connect(self.sort_tags)

        self._act_waifu = QAction("", self)
        self._act_waifu.setShortcut("Ctrl+T")
        self._act_waifu.triggered.connect(self.open_waifu_tagger)

        self.tool_menu.addAction(self._act_rm_dup)
        self.tool_menu.addAction(self._act_sort)
        self.tool_menu.addSeparator()
        self.tool_menu.addAction(self._act_waifu)

        # Language menu
        self._lang_menu = menubar.addMenu("Language")
        languages = [
            ("en", "English"),
            ("vi", "Tiếng Việt"),
        ]

        for code, label in languages:
            act = QAction(label, self)
            act.triggered.connect(lambda checked=False, c=code: self.switch_language(c))
            self._lang_menu.addAction(act)

        # Help
        self._help_menu = menubar.addMenu("")
        self._act_about = QAction("", self)
        self._act_about.triggered.connect(lambda: AboutDialog(self).exec())
        self._help_menu.addAction(self._act_about)

        self.history.add_callback(self._update_undo_redo_actions)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # ── Left: Folder tree ──
        left_frame = QWidget()
        left_frame.setMinimumWidth(200)
        left_frame.setMaximumWidth(300)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self._dir_lbl = QLabel()
        self._dir_lbl.setStyleSheet("font-size: 13px; font-weight: bold;")
        left_layout.addWidget(self._dir_lbl)

        self.dir_tree = QTreeWidget()
        self.dir_tree.setHeaderHidden(True)
        self.dir_tree.itemClicked.connect(self._on_tree_item_clicked)
        left_layout.addWidget(self.dir_tree)

        splitter.addWidget(left_frame)

        # ── Left 2nd: Tag panel ──
        self.tag_panel = TagPanel()
        self.tag_panel.setMinimumWidth(250)
        self.tag_panel.setMaximumWidth(350)
        self.tag_panel.filter_changed.connect(self._on_tag_filter_changed)
        self.tag_panel.tag_insert_requested.connect(self._insert_tag_to_global)
        self.tag_panel.delete_tags_requested.connect(self.open_delete_tag_window)
        self.tag_panel.replace_tags_requested.connect(self.open_replace_tag_window)
        splitter.addWidget(self.tag_panel)

        # ── Center: Image grid + toolbar ──
        center_frame = QWidget()
        center_layout = QVBoxLayout(center_frame)
        center_layout.setContentsMargins(4, 4, 4, 4)
        center_layout.setSpacing(4)

        # Top toolbar
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(4, 2, 4, 2)

        self._sel_all_btn = QPushButton()
        self._sel_all_btn.setStyleSheet("background:#4CAF50; color:white; font-weight:bold; padding:4px 8px;")
        self._sel_all_btn.clicked.connect(self.select_all_images)

        self._inv_sel_btn = QPushButton()
        self._inv_sel_btn.setStyleSheet("background:#FF9800; color:white; font-weight:bold; padding:4px 8px;")
        self._inv_sel_btn.clicked.connect(self.invert_selection)

        self._desel_btn = QPushButton()
        self._desel_btn.setStyleSheet("background:#f44336; color:white; font-weight:bold; padding:4px 8px;")
        self._desel_btn.clicked.connect(self.deselect_all_images)

        self._save_btn = QPushButton()
        self._save_btn.setStyleSheet("background:#2196F3; color:white; font-weight:bold; padding:4px 8px;")
        self._save_btn.clicked.connect(self.save_all)

        self._hist_btn = QPushButton()
        self._hist_btn.setStyleSheet("background:#607D8B; color:white; padding:4px 8px;")
        self._hist_btn.clicked.connect(self.show_history_window)

        top_layout.addWidget(self._sel_all_btn)
        top_layout.addWidget(self._inv_sel_btn)
        top_layout.addWidget(self._desel_btn)
        top_layout.addWidget(self._save_btn)
        top_layout.addStretch()
        top_layout.addWidget(self._hist_btn)
        center_layout.addWidget(top_bar)

        # Column controls
        col_bar = QWidget()
        col_layout = QHBoxLayout(col_bar)
        col_layout.setContentsMargins(4, 0, 4, 0)
        self._col_lbl = QLabel()
        col_layout.addWidget(self._col_lbl)
        for n in [1, 2, 3, 4, 5, 6, 8]:
            btn = QPushButton(str(n))
            btn.setFixedWidth(32)
            btn.clicked.connect(lambda _, num=n: self._set_columns(num))
            col_layout.addWidget(btn)
        col_layout.addStretch()
        center_layout.addWidget(col_bar)

        # Image grid
        self.image_grid = ImageGrid()
        self.image_grid.selection_changed.connect(self._on_selection_changed)
        self.image_grid.tag_add_requested.connect(self._on_individual_tag_add)
        self.image_grid.tag_insert_requested.connect(self._insert_tag_to_global)
        self.image_grid.tag_remove_requested.connect(self._on_individual_tag_remove)
        center_layout.addWidget(self.image_grid, stretch=1)

        # Bottom global tag bar
        bottom_bar = QWidget()
        bottom_bar.setStyleSheet("background:#3c3c3c;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(8, 6, 8, 6)

        bottom_layout.addWidget(QLabel("Tag:"))
        self.global_tag_entry = self._global_tag_entry = QLineEdit()
        self._global_tag_entry.setClearButtonEnabled(True)
        self._global_tag_entry.setFixedHeight(30)
        bottom_layout.addWidget(self._global_tag_entry, stretch=1)

        self._add_tag_btn = QPushButton()
        self._add_tag_btn.setStyleSheet("background:#4CAF50; color:white; font-weight:bold; padding:4px 10px;")
        self._add_tag_btn.clicked.connect(self.add_tag_to_selected)

        self._rem_tag_btn = QPushButton()
        self._rem_tag_btn.setStyleSheet("background:#f44336; color:white; font-weight:bold; padding:4px 10px;")
        self._rem_tag_btn.clicked.connect(self.remove_tag_from_selected)

        bottom_layout.addWidget(self._add_tag_btn)
        bottom_layout.addWidget(self._rem_tag_btn)
        center_layout.addWidget(bottom_bar)

        splitter.addWidget(center_frame)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        self._selected_images: set = set()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+A"), self).activated.connect(self.select_all_images)
        QShortcut(QKeySequence("Ctrl+I"), self).activated.connect(self.invert_selection)
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(self.deselect_all_images)

    # ──────────────────────────────────────────────
    #  Open Recent operations
    # ──────────────────────────────────────────────
    def update_recent_menu(self):
        self.recent_menu.clear()
        recent_folders = self.settings.value("recent_list", [], type=list)

        if isinstance(recent_folders, str):
            recent_folders = [recent_folders] if recent_folders else []

        if not recent_folders:
            no_recent_act = QAction(tr("recent_none"), self)
            no_recent_act.setEnabled(False)
            self.recent_menu.addAction(no_recent_act)
            return

        for folder in recent_folders:
            if os.path.exists(folder):
                action = QAction(folder, self)
                action.triggered.connect(lambda checked=False, f=folder: self._load_recent_folder(f))
                self.recent_menu.addAction(action)

        self.recent_menu.addSeparator()
        clear_act = QAction(tr("recent_clear"), self)
        clear_act.triggered.connect(self.clear_recent_history)
        self.recent_menu.addAction(clear_act)

    def _load_recent_folder(self, folder):
        self.root_folder = folder
        self._populate_tree(folder)
        self._load_folder(folder)
        self.save_to_recent(folder)

    def save_to_recent(self, folder):
        recent_folders = self.settings.value("recent_list", [])
        if isinstance(recent_folders, str):
            recent_folders = [recent_folders]
        elif recent_folders is None:
            recent_folders = []
        else:
            recent_folders = list(recent_folders)

        if folder in recent_folders:
            recent_folders.remove(folder)
        recent_folders.insert(0, folder)
        recent_folders = recent_folders[:10]

        self.settings.setValue("recent_list", recent_folders)
        self.update_recent_menu()

    def clear_recent_history(self):
        self.settings.setValue("recent_list", [])
        self.update_recent_menu()

    # ──────────────────────────────────────────────
    #  Folder / File operations
    # ──────────────────────────────────────────────
    def _auto_load_path(self, path):
        self.root_folder = path
        self.current_folder = path
        self._populate_tree(path)
        self._load_folder(path)
        self.save_to_recent(path)
        self.update_ui_state()

    def select_root_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr("dlg_open_folder"))
        if folder:
            self.root_folder = folder
            self.current_folder = folder
            self._populate_tree(folder)
            self._load_folder(folder)
            self.save_to_recent(folder)

    def _populate_tree(self, root_path: str):
        self.dir_tree.clear()

        def add_node(path: str, parent_item):
            name = os.path.basename(path) or path
            item = QTreeWidgetItem(parent_item, [name])
            item.setData(0, Qt.UserRole, path)
            try:
                for sub in sorted(os.listdir(path)):
                    sub_path = os.path.join(path, sub)
                    if os.path.isdir(sub_path):
                        add_node(sub_path, item)
            except PermissionError:
                pass
            return item

        root_item = add_node(root_path, self.dir_tree)
        root_item.setExpanded(True)

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        path = item.data(0, Qt.UserRole)
        if path and os.path.isdir(path):
            self._load_folder(path)

    def _load_folder(self, folder: str):
        if self.images and self._has_unsaved():
            resp = QMessageBox.question(
                self, tr("dlg_save_before_switch"),
                tr("dlg_save_before_switch_msg"),
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if resp == QMessageBox.Yes:
                self.save_all()
            elif resp == QMessageBox.Cancel:
                return

        try:
            self.images = load_folder_images(folder)
        except PermissionError:
            QMessageBox.critical(self, tr("dlg_no_permission"),
                                 tr("dlg_no_permission_msg", folder=folder))
            return

        self.current_folder = folder
        self.history.clear()
        self._selected_images.clear()
        self._load_all_folder_tags()
        self.statusBar().showMessage(tr("status_loaded", count=len(self.images), folder=folder))
        self.update_ui_state()

    def _load_all_folder_tags(self):
        counts = {}
        for img in self.images:
            for tag in img['tags']:
                counts[tag] = counts.get(tag, 0) + 1
        self.folder_tag_counts = counts
        self.all_folder_tags = sorted(counts.keys())
        self.tag_panel.load_tags(self.all_folder_tags, self.folder_tag_counts)
        self.image_grid.set_data(self.images, {})

    def _has_unsaved(self) -> bool:
        return any(img.get('modified') for img in self.images)

    # ──────────────────────────────────────────────
    #  Handle Update Function
    # ──────────────────────────────────────────────
    def update_ui_state(self):
        has_data = self.current_folder is not None
        if hasattr(self, 'tool_menu'):
            self.tool_menu.setEnabled(has_data)

    # ──────────────────────────────────────────────
    #  Save
    # ──────────────────────────────────────────────
    def save_all(self):
        count = save_all_images(self.images)
        if count:
            QMessageBox.information(self, tr("save_success"),
                                    tr("save_success_msg", count=count))
        else:
            QMessageBox.information(self, tr("save_nothing"), tr("save_nothing_msg"))
        self.statusBar().showMessage(tr("status_saved", count=count))

    # ──────────────────────────────────────────────
    #  Undo / Redo
    # ──────────────────────────────────────────────
    def _snapshot(self) -> list:
        return self.history.snapshot_tags(self.images)

    def _push_history(self, action: str, before: list):
        self.history.push(action, before, self.images)

    def do_undo(self):
        action = self.history.undo(self.images)
        if action:
            self._refresh_after_tag_change()
            self.statusBar().showMessage(tr("undo_done", action=action))
        else:
            self.statusBar().showMessage(tr("undo_nothing"))

    def do_redo(self):
        action = self.history.redo(self.images)
        if action:
            self._refresh_after_tag_change()
            self.statusBar().showMessage(tr("redo_done", action=action))
        else:
            self.statusBar().showMessage(tr("redo_nothing"))

    def _update_undo_redo_actions(self):
        self.act_undo.setEnabled(self.history.can_undo())
        self.act_redo.setEnabled(self.history.can_redo())
        if self.history.can_undo():
            top = self.history.get_undo_list()
            self.act_undo.setText(tr("undo_text_with_action", action=top[0]) if top else tr("menu_undo"))
        else:
            self.act_undo.setText(tr("menu_undo"))
        if self.history.can_redo():
            top = self.history.get_redo_list()
            self.act_redo.setText(tr("redo_text_with_action", action=top[0]) if top else tr("menu_redo"))
        else:
            self.act_redo.setText(tr("menu_redo"))

    def _refresh_after_tag_change(self):
        self._load_all_folder_tags()
        for idx in range(len(self.images)):
            self.image_grid.refresh_card(idx)

    # ──────────────────────────────────────────────
    #  History window
    # ──────────────────────────────────────────────
    def show_history_window(self):
        if self.history_win is None or not self.history_win.isVisible():
            self.history_win = HistoryWindow(self.history, parent=self)
        self.history_win.show()
        self.history_win.raise_()
        self.history_win.activateWindow()

    # ──────────────────────────────────────────────
    #  Selection
    # ──────────────────────────────────────────────
    def _on_selection_changed(self, selected: set):
        self._selected_images = selected
        self.statusBar().showMessage(tr("status_selected", count=len(selected)))

    def select_all_images(self):
        self.image_grid.select_all()

    def deselect_all_images(self):
        self.image_grid.deselect_all()

    def invert_selection(self):
        self.image_grid.invert_selection()

    # ──────────────────────────────────────────────
    #  Tag operations
    # ──────────────────────────────────────────────
    def _on_tag_filter_changed(self, filters: dict):
        self.image_grid.set_tag_filters(filters)

    def _insert_tag_to_global(self, tag: str):
        cur = self.global_tag_entry.text()
        self.global_tag_entry.setText((cur + ", " + tag) if cur else tag)
        self.global_tag_entry.setFocus()

    def _on_individual_tag_add(self, idx: int, tag: str):
        if tag and tag not in self.images[idx]['tags']:
            before = self._snapshot()
            self.images[idx]['tags'].append(tag)
            self.images[idx]['modified'] = True
            self._push_history(
                tr("history_add_tag", tag=tag, filename=self.images[idx]['filename']),
                before
            )
            self.image_grid.refresh_card(idx)
            self._reload_tags_panel()

    def add_tag_to_selected(self):
        tag = self.global_tag_entry.text().strip()
        if not tag:
            QMessageBox.warning(self, tr("warn_no_tag"), tr("warn_no_tag_msg"))
            return
        if not self._selected_images:
            QMessageBox.warning(self, tr("warn_no_image"), tr("warn_no_image_msg"))
            return

        before = self._snapshot()
        count = 0
        for idx in list(self._selected_images):
            if tag not in self.images[idx]['tags']:
                self.images[idx]['tags'].append(tag)
                self.images[idx]['modified'] = True
                self.image_grid.refresh_card(idx)
                count += 1

        self._push_history(tr("history_add_tag_bulk", tag=tag, count=count), before)
        self.global_tag_entry.clear()
        self._reload_tags_panel()
        QMessageBox.information(self, tr("add_tag_success"),
                                tr("add_tag_success_msg", tag=tag, count=count))
        self.deselect_all_images()

    def remove_tag_from_selected(self):
        raw = self.global_tag_entry.text()
        tags_to_remove = list(set(t.strip() for t in raw.split(',') if t.strip()))
        if not tags_to_remove:
            QMessageBox.warning(self, tr("warn_no_tag"), tr("warn_no_tag_msg"))
            return
        if not self._selected_images:
            QMessageBox.warning(self, tr("warn_no_image"), tr("warn_no_image_msg"))
            return

        before = self._snapshot()
        affected = 0
        for idx in list(self._selected_images):
            modified = False
            for tag in tags_to_remove:
                if tag in self.images[idx]['tags']:
                    self.images[idx]['tags'].remove(tag)
                    modified = True
            if modified:
                self.images[idx]['modified'] = True
                self.image_grid.refresh_card(idx)
                affected += 1

        self._push_history(
            tr("history_remove_tag_bulk", tags=tags_to_remove, count=affected), before
        )
        self.global_tag_entry.clear()
        self._reload_tags_panel()
        QMessageBox.information(self, tr("remove_tag_success"),
                                tr("remove_tag_success_msg",
                                   tag_count=len(tags_to_remove), img_count=affected))
        self.deselect_all_images()

    def _on_individual_tag_remove(self, idx: int, tag: str):
        if tag in self.images[idx]['tags']:
            before = self._snapshot()
            self.images[idx]['tags'].remove(tag)
            self.images[idx]['modified'] = True
            self._push_history(
                tr("history_remove_tag", tag=tag, filename=self.images[idx]['filename']),
                before
            )
            self.image_grid.refresh_card(idx)
            self._reload_tags_panel()

    def _set_columns(self, n: int):
        self.image_grid.set_columns(n)

    def _reload_tags_panel(self):
        current_filters = self.tag_panel._tag_filters.copy()
        counts = {}
        for img in self.images:
            for tag in img['tags']:
                counts[tag] = counts.get(tag, 0) + 1

        self.folder_tag_counts = counts
        self.all_folder_tags = sorted(counts.keys())
        self.tag_panel.load_tags(self.all_folder_tags, self.folder_tag_counts)

        for tag, is_active in current_filters.items():
            if tag in self.tag_panel._check_boxes:
                self.tag_panel._check_boxes[tag].setChecked(is_active)

        self.image_grid.set_tag_filters(current_filters)

    # ──────────────────────────────────────────────
    #  Tool operations
    # ──────────────────────────────────────────────
    def remove_duplicate_tags(self):
        if not self.current_folder:
            QMessageBox.information(self, tr("notify_no_folder"), tr("notify_no_folder_msg"))
            return
        if QMessageBox.question(
            self, tr("remove_dup_confirm_title"), tr("remove_dup_confirm_msg"),
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return

        before = self._snapshot()
        for idx, img in enumerate(self.images):
            img['tags'] = list(dict.fromkeys(img['tags']))
            img['modified'] = True
            self.image_grid.refresh_card(idx)

        self._push_history(tr("history_remove_dup"), before)
        self._reload_tags_panel()
        QMessageBox.information(self, tr("remove_dup_done"), tr("remove_dup_done_msg"))

    def sort_tags(self):
        if not self.images:
            QMessageBox.information(self, tr("notify_no_image"), tr("notify_no_image_msg"))
            return

        dlg = SortTagsDialog(self.all_folder_tags, self)
        if dlg.exec() != SortTagsDialog.Accepted:
            return

        chosen = dlg.get_selected_tags()
        if not chosen:
            QMessageBox.information(self, tr("notify_no_tag_selected"),
                                    tr("notify_no_tag_selected_msg"))
            return

        position = dlg.get_position()
        chosen_set = set(chosen)
        before = self._snapshot()
        affected = 0

        for idx, img in enumerate(self.images):
            present = [t for t in img['tags'] if t in chosen_set]
            if not present:
                continue
            remaining = [t for t in img['tags'] if t not in chosen_set]
            img['tags'] = (present + remaining) if position == "beginning" else (remaining + present)
            img['modified'] = True
            self.image_grid.refresh_card(idx)
            affected += 1

        self._push_history(
            tr("history_sort_tags", tags=chosen, position=position), before
        )
        self._reload_tags_panel()
        QMessageBox.information(self, tr("sort_done"), tr("sort_done_msg", count=affected))

    def open_delete_tag_window(self):
        selected = self.tag_panel.get_selected_filter_tags()
        if not selected:
            QMessageBox.warning(self, tr("warn_select_tag_delete"),
                                tr("warn_select_tag_delete_msg"))
            return

        tags_str = "\n- " + "\n- ".join(selected)
        if QMessageBox.question(
            self, tr("delete_tags_title"),
            tr("delete_tags_msg", tags=tags_str),
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return

        before = self._snapshot()
        count = 0
        for idx, img in enumerate(self.images):
            modified = False
            for tag in selected:
                if tag in img['tags']:
                    img['tags'].remove(tag)
                    modified = True
            if modified:
                img['modified'] = True
                self.image_grid.refresh_card(idx)
                count += 1

        self._push_history(tr("history_delete_tags", tags=selected, count=count), before)
        self._reload_tags_panel()
        QMessageBox.information(self, tr("delete_done"),
                                tr("delete_done_msg", tag_count=len(selected), img_count=count))

    def open_replace_tag_window(self):
        selected = self.tag_panel.get_selected_filter_tags()
        if not selected:
            QMessageBox.warning(self, tr("warn_select_tag_replace"),
                                tr("warn_select_tag_replace_msg"))
            return

        dlg = ReplaceTagsDialog(selected, self)
        if dlg.exec() != ReplaceTagsDialog.Accepted:
            return

        replace_map = dlg.get_replace_map()
        if not replace_map:
            QMessageBox.information(self, tr("replace_nothing"), tr("replace_nothing_msg"))
            return

        before = self._snapshot()
        affected = 0
        for idx, img in enumerate(self.images):
            modified = False
            for old_tag, new_tag in replace_map.items():
                if old_tag in img['tags']:
                    img['tags'].remove(old_tag)
                    if new_tag not in img['tags']:
                        img['tags'].append(new_tag)
                    modified = True
            if modified:
                img['modified'] = True
                self.image_grid.refresh_card(idx)
                affected += 1

        self._push_history(tr("history_replace_tags", map=replace_map), before)
        self._reload_tags_panel()
        QMessageBox.information(self, tr("replace_done"),
                                tr("replace_done_msg", count=affected))

    # ──────────────────────────────────────────────
    #  Waifu Tagger
    # ──────────────────────────────────────────────
    def open_waifu_tagger(self):
        dlg = WaifuTaggerWindow(
            parent=self,
            current_folder=self.current_folder,
            root_folder=self.root_folder,
        )
        dlg.tagging_started.connect(self._on_tagging_started)
        dlg.exec()

    def _on_tagging_started(self, config: dict):
        self.statusBar().showMessage(tr("waifu_running", mode=config['mode']))

        from threading import Thread
        from tagger_logic import run_tagger, run_tagger_api

        def thread_wrapper():
            try:
                target_func = run_tagger if config["mode"] == "local" else run_tagger_api
                results = target_func(config, lambda c, t, m: self.statusBar().showMessage(f"[{c}/{t}] {m}"))

                if config["mode"] == "api":
                    self.statusBar().showMessage(tr("waifu_api_done"))
                    self.tagging_completed.emit([])
                elif results and isinstance(results, list):
                    self.tagging_completed.emit(results)
            except Exception as exc:
                self.statusBar().showMessage(tr("waifu_error", error=exc))

        Thread(target=thread_wrapper, daemon=True).start()

    def _on_tagging_finished(self, results: list):
        if not results:
            self._load_folder(self.current_folder)
            self.statusBar().showMessage(tr("waifu_reload_done"))
            QMessageBox.information(self, tr("remove_dup_done"), tr("waifu_reload_msg"))
            return

        before = self._snapshot()
        path_to_idx = {img['path']: i for i, img in enumerate(self.images)}
        updated_count = 0

        for item in results:
            img_path = item.get("path")
            new_tags = item.get("tags")
            if img_path in path_to_idx:
                idx = path_to_idx[img_path]
                self.images[idx]['tags'] = new_tags
                self.images[idx]['modified'] = True
                updated_count += 1

        self._push_history(tr("history_waifu_tag", count=updated_count), before)
        self._refresh_after_tag_change()
        self.statusBar().showMessage(tr("waifu_done_status", count=updated_count))
        QMessageBox.information(self, tr("remove_dup_done"),
                                tr("waifu_done_msg", count=updated_count))

    # ──────────────────────────────────────────────
    #  Closing
    # ──────────────────────────────────────────────
    def closeEvent(self, event):
        if self._has_unsaved():
            resp = QMessageBox.question(
                self, tr("close_save_title"), tr("close_save_msg"),
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if resp == QMessageBox.Yes:
                self.save_all()
                event.accept()
            elif resp == QMessageBox.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
