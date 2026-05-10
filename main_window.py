"""
main_window.py - Cửa sổ chính của ứng dụng TKtagger (PySide6)
"""
import os
import json
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QDockWidget, QLabel, QLineEdit, QPushButton,
    QTreeWidget, QTreeWidgetItem, QMessageBox,
    QFileDialog, QSpinBox, QStatusBar, QToolBar, QInputDialog,
)
from PySide6.QtCore import Qt, QSettings, Signal
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QIcon

from history_manager import HistoryManager
from history_window import HistoryWindow
from file_ops import load_folder_images, save_all_images
from image_grid import ImageGrid
from tag_panel import TagPanel
from dialogs import AboutDialog

from tools.replace_tags import run_replace_tags
from tools.waifu_tagger_window import WaifuTaggerWindow
from tools.calculator_dataset import CalcDatasetDialog
from tools.dict_tags import DictTagsWidget, VirtualTagEngine
from tools.remove_duplicate_tags import run_remove_duplicates

from tools.resort_tag_window_operation import run_operation_sort_tag

from settings_manager import settings
from i18n import tr, set_language, get_language

class MainWindow(QMainWindow):

    tagging_completed = Signal(list)

    def __init__(self, initial_path=None):
        super().__init__()
        
        self.root_folder = None
        self.current_folder = None
        self.images: list = []
        self.all_folder_tags: list = []
        self.folder_tag_counts: dict = {}
        self._folder_cache: dict[str, list] = {}

        self.history = HistoryManager(max_history=256)
        self.history_win: HistoryWindow = None

        # Dict Manager state
        self._dict_data:      dict = {}
        self._dict_order:     list = []
        self._dict_path:      str  = ""
        self._dict_tags_win:  DictTagsWidget = None
        self._resort_win                     = None   # ResortTagsWidget window

        self.setup_menu()
        self.setup_ui()
        self.retranslate_ui()           # first paint with correct language

        self.check_auto_load_dict()
        if initial_path and os.path.exists(initial_path):
            self.select_root_folder(initial_path)

        self.tagging_completed.connect(self._on_tagging_finished)

        self.resize(1024, 720)

    # ──────────────────────────────────────────────
    #  Language switcher
    # ──────────────────────────────────────────────
    def switch_language(self, lang: str):
        settings.language = lang  # Save to settings.ini
        set_language(lang)
        self.retranslate_ui()
        # Also retranslate history window if already open
        if self.history_win and self.history_win.isVisible():
            self.history_win.retranslate_ui()

    # ──────────────────────────────────────────────
    #  Retranslate – update every stored widget ref
    # ──────────────────────────────────────────────
    def retranslate_ui(self):

        # Menu bar
        self._lang_menu.setTitle(tr("language"))
        self._file_menu.setTitle(tr("menu_file"))
        self._act_open.setText(tr("menu_open_folder"))
        self.recent_menu.setTitle(tr("menu_open_recent"))
        self._act_save.setText(tr("ldl_save"))
        self._act_quit.setText(tr("menu_quit"))
        self._edit_menu.setTitle(tr("menu_edit"))
        self.act_undo.setText(tr("ldl_undo"))
        self.act_redo.setText(tr("ldl_redo"))
        self.act_select_all.setText(tr("ldl_select_all"))
        self.act_deselect_all.setText(tr("ldl_deselect_all"))
        self.act_invert_selection.setText(tr("ldl_invert_selection"))
        self._act_history_action.setText(tr("menu_history"))
        self.act_nuke_selection.setText(tr("menu_nuke_selection"))
        self.tool_menu.setTitle(tr("menu_tool"))
        self._act_rm_dup.setText(tr("menu_remove_dup"))
        self._act_sort.setText(tr("menu_sort_tags"))
        self._act_waifu.setText(tr("menu_waifu_tagger"))
        self._act_calc_dataset.setText(tr("menu_calc_dataset"))
        self._help_menu.setTitle(tr("menu_help"))
        self._act_about.setText(tr("menu_about"))
        # Dict menu
        self._dict_menu.setTitle(tr("menu_dict"))
        self._act_dict_new.setText(tr("menu_dict_new"))
        self._act_dict_load.setText(tr("menu_dict_load"))
        self._act_dict_auto_load.setText(tr("menu_dict_setpath"))
        self._act_dict_open_mgr.setText(tr("menu_dict_manager"))

        # Left panel
        self._folder_dock.setWindowTitle("📁 " +tr("folder_label"))

        # Right panel
        self._tag_dock.setWindowTitle("🔍 " + tr("tag_panel_title"))

        # Top toolbar
        self._sel_all_btn.setText(tr("ldl_select_all"))
        self._inv_sel_btn.setText(tr("ldl_invert_selection"))
        self._desel_btn.setText(tr("ldl_deselect_all"))
        self._save_btn.setText(tr("ldl_save"))
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

        self.act_select_all = QAction("", self)
        self.act_select_all.setShortcut(QKeySequence.SelectAll)
        self.act_select_all.triggered.connect(self.select_all_images)

        self.act_deselect_all = QAction("", self)
        self.act_deselect_all.setShortcut(QKeySequence("Ctrl+D"))
        self.act_deselect_all.triggered.connect(self.deselect_all_images)

        self.act_invert_selection = QAction("", self)
        self.act_invert_selection.setShortcut(QKeySequence("Ctrl+I"))
        self.act_invert_selection.triggered.connect(self.invert_image_selection)

        self.act_nuke_selection = QAction("", self)
        self.act_nuke_selection.triggered.connect(self.nuke_tags_from_selected)

        self._edit_menu.addAction(self.act_undo)
        self._edit_menu.addAction(self.act_redo)
        self._edit_menu.addSeparator()
        self._edit_menu.addAction(self._act_history_action)
        self._edit_menu.addAction(self.act_nuke_selection)
        self._edit_menu.addSeparator()
        self._edit_menu.addAction(self.act_select_all)
        self._edit_menu.addAction(self.act_deselect_all)
        self._edit_menu.addAction(self.act_invert_selection)

        # Tool
        self.tool_menu = menubar.addMenu("")
        # self.tool_menu.setEnabled(False)

        self._act_rm_dup = QAction("", self)
        self._act_rm_dup.triggered.connect(self.remove_duplicate_tags)

        self._act_sort = QAction("", self)
        self._act_sort.triggered.connect(self.sort_tags)

        self._act_waifu = QAction("", self)
        self._act_waifu.triggered.connect(self.open_waifu_tagger)

        self._act_calc_dataset = QAction("", self)
        self._act_calc_dataset.triggered.connect(self.open_calc_dataset)
        self._act_calc_dataset.setShortcuts(["Ctrl+Shift+D", "F9"])

        self._act_rm_dup.setShortcuts(["Ctrl+E", "F5"])
        self._act_sort.setShortcuts(["Ctrl+R", "F6"])
        self._act_waifu.setShortcuts(["Ctrl+T", "F8"])        
        self.tool_menu.addAction(self._act_rm_dup)
        self.tool_menu.addAction(self._act_sort)
        self.tool_menu.addSeparator()
        self.tool_menu.addAction(self._act_waifu)
        self.tool_menu.addAction(self._act_calc_dataset)

        # Dict Manager menu
        self._dict_menu = menubar.addMenu("")
        self._act_dict_new     = QAction("", self); self._act_dict_new.triggered.connect(self.dict_new)
        self._act_dict_load    = QAction("", self); self._act_dict_load.triggered.connect(self.dict_load)
        self._act_dict_auto_load = QAction("", self); self._act_dict_auto_load.triggered.connect(self.set_auto_load_dict)
        self._act_dict_open_mgr= QAction("", self); self._act_dict_open_mgr.triggered.connect(self.dict_open_manager)

        self._act_dict_open_mgr.setEnabled(False)

        self._dict_menu.addAction(self._act_dict_new)
        self._dict_menu.addAction(self._act_dict_load)
        self._dict_menu.addAction(self._act_dict_auto_load)
        self._dict_menu.addSeparator()
        self._dict_menu.addAction(self._act_dict_open_mgr)

        # Language menu
        self._lang_menu = menubar.addMenu("Language")
        languages = settings.get_supported_languages()

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
        center_layout = QVBoxLayout(central)
        center_layout.setContentsMargins(4, 4, 4, 4)
        center_layout.setSpacing(4)
        self.setDockOptions(
            QMainWindow.AnimatedDocks |
            QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks
        )

        # Top toolbar
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)

        self._sel_all_btn = QPushButton()
        self._sel_all_btn.setStyleSheet("background:#4CAF50; color:white; font-weight:bold; padding:4px 8px;")
        self._sel_all_btn.setIcon(QIcon.fromTheme("edit-select-all"))
        self._sel_all_btn.clicked.connect(self.select_all_images)

        self._inv_sel_btn = QPushButton()
        self._inv_sel_btn.setStyleSheet("background:#FF9800; color:white; font-weight:bold; padding:4px 8px;")
        self._inv_sel_btn.setIcon(QIcon.fromTheme("edit-select-invert"))
        self._inv_sel_btn.clicked.connect(self.invert_image_selection)

        self._desel_btn = QPushButton()
        self._desel_btn.setStyleSheet("background:#f44336; color:white; font-weight:bold; padding:4px 8px;")
        self._desel_btn.setIcon(QIcon.fromTheme("edit-select-none"))
        self._desel_btn.clicked.connect(self.deselect_all_images)

        self._save_btn = QPushButton()
        self._save_btn.setStyleSheet("background:#2196F3; color:white; font-weight:bold; padding:4px 8px;")
        self._save_btn.setIcon(QIcon.fromTheme("document-save"))
        self._save_btn.clicked.connect(self.save_all)

        self._hist_btn = QPushButton()
        self._hist_btn.setStyleSheet("background:#607D8B; color:white; padding:4px 8px;")
        self._hist_btn.setIcon(QIcon.fromTheme("view-history"))
        self._hist_btn.clicked.connect(self.show_history_window)

        # Column controls
        self.col_spin = QSpinBox()
        self.col_spin.setRange(1, 8)
        self.col_spin.setFixedWidth(50)
        self.col_spin.valueChanged.connect(self._set_columns)

        # Column label
        self._col_lbl = QLabel()

        top_layout.addWidget(self._sel_all_btn)
        top_layout.addWidget(self._inv_sel_btn)
        top_layout.addWidget(self._desel_btn)
        top_layout.addStretch()
        top_layout.addWidget(self._col_lbl)
        top_layout.addWidget(self.col_spin)
        top_layout.addWidget(self._save_btn)
        top_layout.addWidget(self._hist_btn)
        center_layout.addWidget(top_bar)

        # Image grid
        self.image_grid = ImageGrid()
        self.image_grid.selection_changed.connect(self._on_selection_changed)
        self.image_grid.tag_add_requested.connect(self._on_individual_tag_add)
        self.image_grid.tag_insert_requested.connect(self._insert_tag_to_global)
        self.image_grid.tag_remove_requested.connect(self._on_individual_tag_remove)
        center_layout.addWidget(self.image_grid, stretch=1)
        self.col_spin.setValue(self.image_grid._cols)

        # Bottom global tag bar
        bottom_bar = QWidget()
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(8, 6, 8, 6)

        self.global_tag_entry = self._global_tag_entry = QLineEdit()        

        self.global_tag_entry.addAction(QIcon.fromTheme("tag"), QLineEdit.ActionPosition.LeadingPosition)
        self._global_tag_entry.setClearButtonEnabled(True)
        self._global_tag_entry.setFixedHeight(30)
        bottom_layout.addWidget(self._global_tag_entry, stretch=1)

        self._add_tag_btn = QPushButton()
        self._add_tag_btn.setStyleSheet("background:#4CAF50; color:white; font-weight:bold; padding:4px 10px;")
        self._add_tag_btn.setIcon(QIcon.fromTheme("list-add"))
        self._add_tag_btn.clicked.connect(self.add_tag_to_selected)

        self._rem_tag_btn = QPushButton()
        self._rem_tag_btn.setStyleSheet("background:#f44336; color:white; font-weight:bold; padding:4px 10px;")
        self._rem_tag_btn.setIcon(QIcon.fromTheme("list-remove"))
        self._rem_tag_btn.clicked.connect(self.remove_tag_from_selected)

        bottom_layout.addWidget(self._add_tag_btn)
        bottom_layout.addWidget(self._rem_tag_btn)
        center_layout.addWidget(bottom_bar)

        # Folder Tree
        folder_dock = QDockWidget(self)
        folder_dock.setObjectName("FolderDock")
        folder_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        folder_dock.setFeatures(
            QDockWidget.DockWidgetMovable
        )

        folder_widget = QWidget()
        folder_widget.setMinimumWidth(180)
        folder_layout = QVBoxLayout(folder_widget)
        folder_layout.setContentsMargins(4, 4, 4, 4)

        self.dir_tree = QTreeWidget()
        self.dir_tree.setHeaderHidden(True)
        self.dir_tree.itemClicked.connect(self._on_tree_item_clicked)
        folder_layout.addWidget(self.dir_tree)

        folder_dock.setWidget(folder_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, folder_dock)

        # Tag Panel
        tag_dock = QDockWidget(self)
        tag_dock.setObjectName("TagDock")
        tag_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        tag_dock.setFeatures(
            QDockWidget.DockWidgetMovable
        )

        self.tag_panel = TagPanel()
        self.tag_panel.setMinimumWidth(220)
        self.tag_panel.filter_changed.connect(self._on_tag_filter_changed)
        self.tag_panel.tag_insert_requested.connect(self._insert_tag_to_global)
        self.tag_panel.delete_tags_requested.connect(self.open_delete_tag_window)
        self.tag_panel.replace_tags_requested.connect(self.open_replace_tag_window)

        tag_dock.setWidget(self.tag_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, folder_dock)

        self.addDockWidget(Qt.LeftDockWidgetArea, tag_dock)

        self.splitDockWidget(folder_dock, tag_dock, Qt.Horizontal)

        self._folder_dock = folder_dock
        self._tag_dock = tag_dock

        self._selected_images: set = set()

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
        self._set_active_directory(folder)

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

    def select_root_folder(self, path=None):
        if not path:
            path = QFileDialog.getExistingDirectory(self, tr("dlg_open_folder"))
        
        if path:
            self._set_active_directory(path)

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
        # Lưu state folder hiện tại trước
        self._save_current_folder_state()

        # Load folder mới
        if folder in self._folder_cache:
            self.images = self._folder_cache[folder]
        else:
            try:
                self.images = load_folder_images(folder)
            except PermissionError:
                QMessageBox.critical(self, tr("dlg_no_permission"), tr("dlg_no_permission_msg", folder=folder))
                return
            self._folder_cache[folder] = self.images

        self.current_folder = folder  # ← update SAU khi đã save state cũ
        self._selected_images.clear()
        self._load_all_folder_tags()
        self.statusBar().showMessage(tr("status_loaded", count=len(self.images), folder=folder))

    def _save_current_folder_state(self):
        """Lưu state folder hiện tại vào cache trước khi rời."""
        if self.current_folder and self.images:
            self._folder_cache[self.current_folder] = self.images

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
        # Check folder đang xem
        if any(img.get('modified') for img in self.images):
            return True
        # Check các folder đang cached
        for cached_images in self._folder_cache.values():
            if any(img.get('modified') for img in cached_images):
                return True
        return False

    def _set_active_directory(self, folder):
        """Hàm tập trung duy nhất để thay đổi thư mục làm việc"""

        if not os.path.isdir(folder):
            raise NotADirectoryError(f"The path does not exist or is not a directory: {folder}")

        if self.images and self._has_unsaved():
            resp = QMessageBox.question(
                self, tr("dlg_save_before_switch"), tr("dlg_save_before_switch_msg"),
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if resp == QMessageBox.Yes:
                self.save_all()
            elif resp == QMessageBox.Cancel:
                return
        
        self.history.clear()

        # Clear cache và reset state TRƯỚC
        self._folder_cache.clear()
        self.images = []          # ← reset images để _save_current_folder_state không cache rác
        self.current_folder = None  # ← reset để _load_folder không lưu state cũ

        self.root_folder = folder
        self._populate_tree(folder)
        self._load_folder(folder)
        self.save_to_recent(folder)

    # ──────────────────────────────────────────────
    #  Save
    # ──────────────────────────────────────────────
    def save_all(self):
        # Gom tất cả images từ cache + folder hiện tại
        all_images = list(self.images)
        for path, cached in self._folder_cache.items():
            if path != self.current_folder:
                all_images.extend(cached)

        count = save_all_images(all_images)
        # count = save_all_images(self.images)
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
            self.act_undo.setText(tr("undo_text_with_action", action=top[0]) if top else tr("ldl_undo"))
        else:
            self.act_undo.setText(tr("ldl_undo"))
        if self.history.can_redo():
            top = self.history.get_redo_list()
            self.act_redo.setText(tr("redo_text_with_action", action=top[0]) if top else tr("ldl_redo"))
        else:
            self.act_redo.setText(tr("ldl_redo"))

    def _refresh_after_tag_change(self):
        self._load_all_folder_tags()
        for idx in range(len(self.images)):
            self.image_grid.refresh_card(idx)

    # ──────────────────────────────────────────────
    #  History window
    # ──────────────────────────────────────────────
    def show_history_window(self):
        if not hasattr(self, 'history_dock') or self.history_dock is None:
            self.history_dock = HistoryWindow(self.history, parent=self)
            self.addDockWidget(Qt.RightDockWidgetArea, self.history_dock)
            self.history_dock.show()
            return

        if self.history_dock.isVisible():
            self.history_dock.hide()
        else:
            self.history_dock.show()
            self.history_dock.raise_()

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

    def invert_image_selection(self):
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
        # QMessageBox.information(self, tr("add_tag_success"), tr("add_tag_success_msg", tag=tag, count=count))
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

        self._push_history(tr("history_remove_tag_bulk", tags=tags_to_remove, count=affected, folder=Path(self.current_folder).name), before)
        self.global_tag_entry.clear()
        self._reload_tags_panel()
        # QMessageBox.information(self, tr("remove_tag_success"), tr("remove_tag_success_msg", tag_count=len(tags_to_remove), img_count=affected))
        self.deselect_all_images()

    def _on_individual_tag_remove(self, idx: int, tag: str):
        if tag in self.images[idx]['tags']:
            before = self._snapshot()
            self.images[idx]['tags'].remove(tag)
            self.images[idx]['modified'] = True
            self._push_history(
                tr("history_remove_tag", tag=tag, filename=self.images[idx]['filename'], folder=Path(self.current_folder).name),
                before
            )
            self.image_grid.refresh_card(idx)
            self._reload_tags_panel()

    def nuke_tags_from_selected(self):
        if not self._selected_images:
            QMessageBox.warning(self, tr("warn_no_image"), tr("warn_no_image_msg"))
            return

        # Xác nhận trước khi xóa sạch
        confirm = QMessageBox.question(
            self, 
            tr("ldl_confirm"), 
            tr("nuke_selected_comfirm", selected=len(self._selected_images)),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm != QMessageBox.Yes:
            return

        before = self._snapshot()
        affected = 0
        
        for idx in list(self._selected_images):
            if self.images[idx]['tags']: # Chỉ xử lý nếu ảnh có tag
                self.images[idx]['tags'] = []
                self.images[idx]['modified'] = True
                self.image_grid.refresh_card(idx)
                affected += 1

        if affected > 0:
            lbl = tr("nuke_push_history", affected=affected)
            self._push_history(lbl, before)
            self._reload_tags_panel()
            self.statusBar().showMessage(lbl)
        
        self.deselect_all_images()

    def open_delete_tag_window(self):
        selected = self.tag_panel.get_selected_filter_tags()
        if not selected:
            QMessageBox.warning(self, tr("warn_select_tag_delete"), tr("warn_select_tag_delete_msg"))
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
                                tr("delete_done_msg", tag=", ".join(selected), tag_count=len(selected), img_count=count))
                                
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
        run_remove_duplicates(self)

    def sort_tags(self):
        run_operation_sort_tag(self)

    def open_replace_tag_window(self):
        run_replace_tags(self)
    
    def open_calc_dataset(self):
        dlg = CalcDatasetDialog(root_folder=self.root_folder, standalone_app=False, parent=self)
        dlg.exec()

    # ──────────────────────────────────────────────
    #  Waifu Tagger
    # ──────────────────────────────────────────────
    def open_waifu_tagger(self):
        if not self.root_folder:
            QMessageBox.information(self, tr("ldl_no_images"), tr("resort_no_folder_open_msg"))
            return False
        
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
    #  Dict Manager
    # ──────────────────────────────────────────────
    def _apply_dict_to_panel(self):
        """Build {group: [expanded_tags]} và đẩy vào TagPanel, bỏ qua nhóm có Hidden: true."""
        if not self._dict_data:
            self.tag_panel.set_dict_groups({})
            return

        engine = VirtualTagEngine(self._dict_data)
        tag_map = engine.build_tag_map()              # expanded_tag → group_name
        groups: dict[str, list[str]] = {}
        for tag, gname in tag_map.items():
            groups.setdefault(gname, []).append(tag)

        # 🔍 Hàm kiểm tra nhóm có cấu hình "Hidden": true không
        def is_hidden_group(gname: str) -> bool:
            g_obj = self._dict_data.get(gname, {})
            return isinstance(g_obj, dict) and g_obj.get("Hidden", False)

        # Giữ thứ tự theo order, bỏ BREAK và nhóm Hidden
        ordered = {
            g: groups[g] for g in self._dict_order 
            if g != "BREAK" and g in groups and not is_hidden_group(g)
        }
        # Thêm nhóm còn sót (không có trong order), cũng bỏ Hidden
        for g, v in groups.items():
            if g not in ordered and not is_hidden_group(g):
                ordered[g] = v

        self.tag_panel.set_dict_groups(ordered)

    def dict_new(self):
        name, ok = QInputDialog.getText(self, tr("new_dict_title"), tr("new_dict_prompt"))
        if not ok or not name.strip():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("save_new_dict"), name.strip() + ".json", "JSON (*.json)"
        )
        if not path:
            return
        
        self._dict_data  = {}
        self._dict_order = []
        self._dict_path  = path
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"order": []}, f, indent=2, ensure_ascii=False)
        self._apply_dict_to_panel()
        self._act_dict_open_mgr.setEnabled(True)
        self.statusBar().showMessage(f"{tr('status_new_dict')}: {path}")

    def set_auto_load_dict(self):
        """Mở hộp thoại chọn file và lưu đường dẫn vào settings.ini"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("dlg_load_dict"), "", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.settings.setValue("auto_load_dict_path", file_path)
            self._load_dict_from_path(file_path)
            QMessageBox.information(self, tr("success"), f"Đã thiết lập tự động load:\n{file_path}")

    def check_auto_load_dict(self):
        """Hàm này gọi khi khởi động ứng dụng"""
        path = self.settings.value("auto_load_dict_path", "")
        if path and os.path.exists(path):
            self.dict_load(path)

    def dict_load(self, select_path=None):
        if select_path:
            path = select_path
        else:
            path, _ = QFileDialog.getOpenFileName(self, tr("load_dict_title"), "", "JSON (*.json)")
        
        if path:
            self._do_load_dict(path)

    def _do_load_dict(self, path: str):
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, tr("error_title"), f"{tr('error_read_file')}:\n{e}")
            return
        self._dict_order = raw.get("order", [])
        self._dict_data  = {k: v for k, v in raw.items() if k != "order"}
        self._dict_path  = path
        self._apply_dict_to_panel()
        self._act_dict_open_mgr.setEnabled(True)
        if self._dict_tags_win and self._dict_tags_win.isVisible():
            self._dict_tags_win.load_data(self._dict_data, self._dict_order, path)
        self.statusBar().showMessage(f"{tr('status_loaded_dict')}: {path}")

    def dict_open_manager(self):
        if self._dict_tags_win is None or not self._dict_tags_win.isVisible():
            self._dict_tags_win = DictTagsWidget(
                self._dict_data, self._dict_order,
                current_path=self._dict_path
            )
            self._dict_tags_win.setWindowTitle(tr('dict_manager'))
            self._dict_tags_win.resize(950, 620)
            self._dict_tags_win.data_changed.connect(self._on_dict_manager_saved)
        else:
            # Sync data mới nhất vào window đang mở
            self._dict_tags_win.load_data(self._dict_data, self._dict_order, self._dict_path)
        self._dict_tags_win.show()
        self._dict_tags_win.raise_()
        self._dict_tags_win.activateWindow()

    def _on_dict_manager_saved(self, data: dict, order: list):
        self._dict_data  = data
        self._dict_order = order
        if self._dict_tags_win:
            self._dict_path = self._dict_tags_win.current_path
        self._apply_dict_to_panel()

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