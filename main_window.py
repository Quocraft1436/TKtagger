"""
main_window.py - Cửa sổ chính của ứng dụng TKtagger (PySide6)
"""
import os
import json
from collections import Counter
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QDockWidget, QLabel, QLineEdit, QPushButton,
    QTreeWidget, QTreeWidgetItem, QMessageBox,
    QFileDialog, QSpinBox, QStatusBar, QToolBar, QInputDialog,
    QComboBox,
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QIcon

from libs.history_manager import HistoryManager
from history_window import HistoryWindow
from libs.file_ops import load_folder_images, save_all_images
from libs.backup_manager import BACKUP_DIR
from libs.folder_loader import FolderLoader
from image_grid import ImageGrid
from tag_panel import TagPanel
from dialogs import AboutDialog

from tools.replace_tags import run_replace_tags
from tools.waifu_tagger_window import WaifuTaggerWindow
from tools.calculator_dataset import CalcDatasetDialog
from tools.dict_tags import DictTagsWidget, VirtualTagEngine
from tools.remove_duplicate_tags import run_remove_duplicates
from tools.underscore_swap import run_underscore_swap
from tools.resort_tag_window_operation import run_operation_sort_tag

from settings_dialog import SettingsDialog
from preview_dock import PreviewDock
from libs.settings_manager import settings
from libs.shortcut_manager import ShortcutManager
from libs.workspace_manager import WorkspaceManager
from libs.i18n import tr, set_language, get_language
from libs.table_icon import get_icon, get_icon_size

class MainWindow(QMainWindow):

    tagging_completed = Signal(list)
    tagging_progress = Signal(str)
    tagging_failed = Signal(str)

    def __init__(self, initial_path=None):
        super().__init__()
        
        self.root_folder = None
        self.current_folder = None
        self.images: list = []
        self.all_folder_tags: list = []
        self.folder_tag_counts: dict = {}
        self._folder_cache: dict[str, list] = {}

        # Load max history from settings
        max_history_setting = int(settings.value("max_history", "256"))
        self.history = HistoryManager(max_history=max_history_setting)

        self.history_win: HistoryWindow = None

        # Parallel stacks to track which folder each history entry belongs to.
        # These mirror the undo/redo stacks inside HistoryManager so that
        # do_undo / do_redo can navigate to the correct folder before applying.
        self._undo_folders: list[str] = []   # folder for each undo entry (top = last)
        self._redo_folders: list[str] = []   # folder for each redo entry (top = last)

        # Dict Manager state
        self._dict_data:      dict = {}
        self._dict_order:     list = []
        self._dict_path:      str  = ""
        self._dict_tags_win:  DictTagsWidget = None
        self._resort_win                     = None   # ResortTagsWidget window
        self._pending_unknown_tags: list     = []     # tags folder chưa có trong dict

        self.setup_menu()
        self.setup_ui()
        self.folder_loader = FolderLoader(self)
        self.folder_loader.loaded.connect(self._on_folder_loaded)
        self._tree_requests = {}
        self._pending_folder = None
        self.dir_tree.itemExpanded.connect(self._expand_folder_tree)
        self.retranslate_ui()           # first paint with correct language

        self.check_auto_load_dict()
        if initial_path and os.path.exists(initial_path):
            self.select_root_folder(initial_path)

        self._connect_tagging_signals()

        self.resize(1024, 720)
        self.workspace = WorkspaceManager(self)

    # ──────────────────────────────────────────────
    #  Language switcher
    # ──────────────────────────────────────────────
    def switch_language(self, lang: str):
        settings.language = lang  # Save to settings.ini
        set_language(lang)
        self.retranslate_ui()
        # Also retranslate history window if already open
        if self.history_win:
            self.history_win.retranslate_ui()
        
        if self._preview_dock:
            self._preview_dock.retranslate_ui()

    # ──────────────────────────────────────────────
    #  Retranslate – update every stored widget ref
    # ──────────────────────────────────────────────
    def retranslate_ui(self):

        # Menu bar
        self._file_menu.setTitle(tr("menu_file"))
        self._act_settings.setText(tr("menu_preferences"))
        self._act_open.setText(tr("menu_open_folder"))
        self.recent_menu.setTitle(tr("menu_open_recent"))
        self._act_clear_recent.setText(tr("recent_clear"))
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
        self._act_underscore_swap.setText(tr("menu_underscore_swap"))
        self._act_waifu.setText(tr("menu_waifu_tagger"))
        self._act_calc_dataset.setText(tr("menu_calc_dataset"))
        self._help_menu.setTitle(tr("menu_help"))
        self._act_about.setText(tr("menu_about"))

        # Dict menu
        self._dict_menu.setTitle(tr("menu_dict"))
        self._act_dict_new.setText(tr("menu_dict_new"))
        self._act_dict_load.setText(tr("menu_dict_load"))
        self._act_dict_reload.setText(tr("menu_dict_reload"))
        self._act_dict_auto_load.setText(tr("menu_dict_setpath"))
        self._act_dict_open_mgr.setText(tr("menu_dict_manager"))

        # Left panel
        self._folder_dock.setWindowTitle(tr("folder_label"))

        # Right panel
        self._tag_dock.setWindowTitle(tr("tag_panel_title"))

        # Top toolbar
        self._sel_all_btn.setToolTip(tr("ldl_select_all"))
        self._inv_sel_btn.setToolTip(tr("ldl_invert_selection"))
        self._desel_btn.setToolTip(tr("ldl_deselect_all"))
        self._save_btn.setToolTip(tr("ldl_save"))
        self._preview_btn.setToolTip(tr("menu_preview_dock"))
        self._hist_btn.setToolTip(tr("history_btn"))

        # Column label
        self._col_lbl.setText(tr("col_display"))

        # Bottom tag bar
        self._global_tag_entry.setPlaceholderText(tr("tag_placeholder"))

        self._order_tag_combo.setItemText(0, tr("tag_order_begin"))
        self._order_tag_combo.setItemText(1, tr("tag_order_last"))
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
        self.settings = settings

        # File – use empty strings; retranslate_ui fills them
        self._file_menu = menubar.addMenu("")
        self._act_open = QAction("", self)
        self._act_open.triggered.connect(self.select_root_folder)

        self._act_clear_recent = QAction("", self)
        self._act_clear_recent.triggered.connect(self.clear_recent_history)
        self.recent_menu = self._file_menu.addMenu("")
        self.update_recent_menu()

        self._act_save = QAction("", self)
        self._act_save.triggered.connect(self.save_all)

        self._act_settings = QAction("", self)
        self._act_settings.triggered.connect(self.open_settings)

        self._act_quit = QAction("", self)
        self._act_quit.triggered.connect(self.close)

        self._file_menu.addAction(self._act_open)
        self._file_menu.addAction(self._act_save)
        self._file_menu.addAction(self._act_settings)
        self._file_menu.addSeparator()
        self._file_menu.addAction(self._act_quit)

        # Edit
        self._edit_menu = menubar.addMenu("")
        self.act_undo = QAction("", self)
        self.act_undo.setEnabled(False)
        self.act_undo.triggered.connect(self.do_undo)

        self.act_redo = QAction("", self)
        self.act_redo.setEnabled(False)
        self.act_redo.triggered.connect(self.do_redo)

        self._act_history_action = QAction("", self)
        self._act_history_action.triggered.connect(self.show_history_window)

        self.act_select_all = QAction("", self)
        self.act_select_all.triggered.connect(self.select_all_images)

        self.act_deselect_all = QAction("", self)
        self.act_deselect_all.triggered.connect(self.deselect_all_images)

        self.act_invert_selection = QAction("", self)
        self.act_invert_selection.triggered.connect(self.invert_image_selection)

        self._edit_menu.addAction(self.act_undo)
        self._edit_menu.addAction(self.act_redo)
        self._edit_menu.addSeparator()
        self._edit_menu.addAction(self._act_history_action)
        self._edit_menu.addSeparator()
        self._edit_menu.addAction(self.act_select_all)
        self._edit_menu.addAction(self.act_deselect_all)
        self._edit_menu.addAction(self.act_invert_selection)

        # Tool
        self.tool_menu = menubar.addMenu("")
        # self.tool_menu.setEnabled(False)

        self._act_rm_dup = QAction("", self)
        self._act_rm_dup.triggered.connect(self.remove_duplicate_tags)

        self.act_nuke_selection = QAction("", self)
        self.act_nuke_selection.triggered.connect(self.nuke_tags_from_selected)

        self._act_sort = QAction("", self)
        self._act_sort.triggered.connect(self.sort_tags)

        self._act_underscore_swap = QAction("", self)
        self._act_underscore_swap.triggered.connect(self.underscore_swap_tags)

        self._act_waifu = QAction("", self)
        self._act_waifu.triggered.connect(self.open_waifu_tagger)

        self._act_calc_dataset = QAction("", self)
        self._act_calc_dataset.triggered.connect(self.open_calc_dataset)

        self.tool_menu.addAction(self._act_rm_dup)
        self.tool_menu.addAction(self.act_nuke_selection)
        self.tool_menu.addAction(self._act_sort)
        self.tool_menu.addAction(self._act_underscore_swap)
        self.tool_menu.addSeparator()
        self.tool_menu.addAction(self._act_waifu)
        self.tool_menu.addAction(self._act_calc_dataset)

        # Dict Manager menu
        self._dict_menu = menubar.addMenu("")
        self._act_dict_new = QAction("", self); self._act_dict_new.triggered.connect(self.dict_new)
        self._act_dict_load = QAction("", self); self._act_dict_load.triggered.connect(self.dict_load)
        self._act_dict_reload = QAction("", self); self._act_dict_reload.triggered.connect(self.dict_reload)
        self._act_dict_auto_load = QAction("", self); self._act_dict_auto_load.triggered.connect(self.set_auto_load_dict)
        self._act_dict_open_mgr = QAction("", self); self._act_dict_open_mgr.triggered.connect(self.dict_open_manager)

        self._act_dict_open_mgr.setEnabled(False)

        self._dict_menu.addAction(self._act_dict_new)
        self._dict_menu.addAction(self._act_dict_load)
        self._dict_menu.addAction(self._act_dict_reload)
        self._dict_menu.addAction(self._act_dict_auto_load)
        self._dict_menu.addSeparator()
        self._dict_menu.addAction(self._act_dict_open_mgr)

        # Help
        self._help_menu = menubar.addMenu("")
        self._act_about = QAction("", self)
        self._act_about.triggered.connect(lambda: AboutDialog(self).exec())
        self._help_menu.addAction(self._act_about)

        self.shortcut_manager = ShortcutManager(self)
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
        # self._sel_all_btn.setStyleSheet("background:#4CAF50; color:white; font-weight:bold; padding:4px 8px;")
        self._sel_all_btn.setIcon(get_icon("select_all"))
        self._sel_all_btn.setIconSize(get_icon_size())
        self._sel_all_btn.clicked.connect(self.select_all_images)

        self._inv_sel_btn = QPushButton()
        # self._inv_sel_btn.setStyleSheet("background:#FF9800; color:white; font-weight:bold; padding:4px 8px;")
        self._inv_sel_btn.setIcon(get_icon("select_invert"))
        self._inv_sel_btn.setIconSize(get_icon_size())
        self._inv_sel_btn.clicked.connect(self.invert_image_selection)

        self._desel_btn = QPushButton()
        # self._desel_btn.setStyleSheet("background:#f44336; color:white; font-weight:bold; padding:4px 8px;")
        self._desel_btn.setIcon(get_icon("select_none"))
        self._desel_btn.setIconSize(get_icon_size())
        self._desel_btn.clicked.connect(self.deselect_all_images)

        self._save_btn = QPushButton()
        # self._save_btn.setStyleSheet("background:#2196F3; color:white; font-weight:bold; padding:4px 8px;")
        self._save_btn.setIcon(get_icon("save"))
        self._save_btn.setIconSize(get_icon_size())
        self._save_btn.clicked.connect(self.save_all)

        self._preview_btn = QPushButton()
        self._preview_btn.setIcon(get_icon("view-preview"))
        self._preview_btn.setIconSize(get_icon_size())
        # self._preview_btn.setStyleSheet("background:#37474F; color:white; padding:4px 8px;")
        self._preview_btn.clicked.connect(self._toggle_preview_dock)

        self._hist_btn = QPushButton()
        self._hist_btn.setIcon(get_icon("view-history"))
        self._hist_btn.setIconSize(get_icon_size())
        # self._hist_btn.setStyleSheet("background:#607D8B; color:white; padding:4px 8px;")
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
        top_layout.addWidget(self._preview_btn)
        top_layout.addWidget(self._hist_btn)
        top_layout.addWidget(self._save_btn)
        center_layout.addWidget(top_bar)

        # Image grid
        self.image_grid = ImageGrid()
        self.image_grid.selection_changed.connect(self._on_selection_changed)
        self.image_grid.tag_add_requested.connect(self._on_individual_tag_add)
        self.image_grid.tag_insert_requested.connect(self._insert_tag_to_global)
        self.image_grid.tag_remove_requested.connect(self._on_individual_tag_remove)
        center_layout.addWidget(self.image_grid, stretch=1)
        self.image_grid.columns_changed.connect(self._sync_grid_columns)
        self.image_grid.set_card_height_mode(settings.value("grid_card_height", "medium"))
        self.apply_grid_layout(settings.value("grid_layout_mode", "classic"))
        self._sync_grid_columns(self.image_grid._cols)

        # Bottom global tag bar
        bottom_bar = QWidget()
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(8, 6, 8, 6)

        self.global_tag_entry = self._global_tag_entry = QLineEdit()        

        self.global_tag_entry.addAction(QIcon.fromTheme("tag"), QLineEdit.ActionPosition.LeadingPosition)
        self._global_tag_entry.setClearButtonEnabled(True)
        self._global_tag_entry.setFixedHeight(30)
        bottom_layout.addWidget(self._global_tag_entry, stretch=1)

        self._order_tag_combo = QComboBox()
        self._order_tag_combo.addItems(["Begin", "Last"])
        bottom_layout.addWidget(self._order_tag_combo)

        self._add_tag_btn = QPushButton()
        # self._add_tag_btn.setStyleSheet("background:#4CAF50; color:white; font-weight:bold; padding:4px 10px;")
        self._add_tag_btn.setIcon(get_icon("add"))
        self._add_tag_btn.setIconSize(get_icon_size())
        self._add_tag_btn.clicked.connect(self.add_tag_to_selected)

        self._rem_tag_btn = QPushButton()
        # self._rem_tag_btn.setStyleSheet("background:#f44336; color:white; font-weight:bold; padding:4px 10px;")
        self._rem_tag_btn.setIcon(get_icon("delete"))
        self._rem_tag_btn.setIconSize(get_icon_size())
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

        self.addDockWidget(Qt.LeftDockWidgetArea, tag_dock)

        self.splitDockWidget(folder_dock, tag_dock, Qt.Horizontal)

        self._folder_dock = folder_dock
        self._tag_dock = tag_dock

        self._selected_images: set = set()

        # Preview Dock
        self._preview_dock = PreviewDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self._preview_dock)
        self._preview_dock.hide()
        self._preview_dock.visibilityChanged.connect(self._on_preview_dock_visibility)

        # Kết nối preview signal từ image_grid
        self.image_grid.preview_requested.connect(self._preview_dock.show_image)
        self.image_grid.preview_requested.connect(lambda _: self._preview_dock.show())
        self.history_dock = HistoryWindow(self.history, parent=self)
        self.history_win = self.history_dock
        self.addDockWidget(Qt.RightDockWidgetArea, self.history_dock)
        self.history_dock.hide()

    def open_settings(self):
        """Open Settings/Preferences dialog"""
        dlg = SettingsDialog(parent=self, main_window=self)
        dlg.exec()

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
            self._act_clear_recent.setEnabled(False)
            self.recent_menu.addAction(self._act_clear_recent)
            return

        for folder in recent_folders:
            if os.path.exists(folder):
                action = QAction(folder, self)
                action.triggered.connect(lambda checked=False, f=folder: self._load_recent_folder(f))
                self.recent_menu.addAction(action)

        self.recent_menu.addSeparator()
        self._act_clear_recent.setEnabled(True)
        self.recent_menu.addAction(self._act_clear_recent)

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

        self.settings.set_value("recent_list", recent_folders)
        self.update_recent_menu()

    def clear_recent_history(self):
        self.settings.set_value("recent_list", [])
        self.update_recent_menu()

    # ──────────────────────────────────────────────
    #  Folder / File operations
    # ──────────────────────────────────────────────

    def select_root_folder(self, path=None):
        if not path:
            path = QFileDialog.getExistingDirectory(self, tr("dlg_open_folder"))
        
        if path:
            self._set_active_directory(path)

    def _populate_tree(self, root_path: str, children=None):
        self.dir_tree.clear()
        self._tree_requests = {}
        root = QTreeWidgetItem(self.dir_tree, [os.path.basename(root_path) or root_path])
        root.setData(0, Qt.UserRole, root_path)
        root.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        if children is not None:
            self._fill_tree_children(root, children)
        root.setExpanded(True)

    def _fill_tree_children(self, item, paths):
        item.setData(0, Qt.UserRole + 1, True)
        for path in paths:
            child = QTreeWidgetItem(item, [os.path.basename(path)])
            child.setData(0, Qt.UserRole, path)
            child.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        if not paths:
            item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicator)

    def _expand_folder_tree(self, item):
        if item.data(0, Qt.UserRole + 1):
            return
        item.setData(0, Qt.UserRole + 1, True)
        token = self.folder_loader.request(item.data(0, Qt.UserRole))
        self._tree_requests[token] = item

    def _request_folder(self, folder, new_root=False):
        if getattr(self, "_pending_folder", None):
            return
        if not hasattr(self, 'folder_loader'):
            return self._load_folder(folder)
        if not new_root and folder in self._folder_cache:
            self._load_folder(folder)
            return
        extension = settings.value('load_extension', 'txt').lstrip('.')
        token = self.folder_loader.request(folder, extension=extension)
        self._pending_folder = (token, new_root)
        # Keep editing stable while metadata is read; commit only after success.
        controls = [self.centralWidget(), self._edit_menu, *self.findChildren(QDockWidget)]
        if hasattr(self, 'tool_menu'):
            controls.append(self.tool_menu)
        self._loading_controls = [(control, control.isEnabled()) for control in controls]
        for control, _ in self._loading_controls:
            control.setEnabled(False)
        self._act_waifu.setEnabled(False)
        self.statusBar().showMessage(tr('folder_loading', folder=folder))

    @Slot(object)
    def _on_folder_loaded(self, payload):
        token = payload['token']
        item = self._tree_requests.pop(token, None)
        if item is not None:
            if payload.get('error'):
                item.setData(0, Qt.UserRole + 1, False)
            else:
                self._fill_tree_children(item, payload['children'])
            return
        if not self._pending_folder or self._pending_folder[0] != token:
            return
        _, new_root = self._pending_folder
        self._pending_folder = None
        for control, enabled in self._loading_controls:
            control.setEnabled(enabled)
        self._loading_controls = []
        self._act_waifu.setEnabled(not getattr(self, "_tagging_running", False))
        if payload.get('error'):
            QMessageBox.critical(self, tr('ldl_error'), payload['error'])
            if self.current_folder:
                self._highlight_tree_item(self.current_folder)
            return
        folder = payload['path']
        if new_root:
            self.history.clear()
            self._undo_folders.clear()
            self._redo_folders.clear()
            self._folder_cache.clear()
            self.root_folder = folder
            self._populate_tree(folder, payload['children'])
        else:
            self._save_current_folder_state()
        self.images = (self._folder_cache.get(folder, payload['images'])
                       if not new_root else payload['images'])
        self.current_folder = folder
        self._folder_cache[folder] = self.images
        self._load_all_folder_tags()
        self.statusBar().showMessage(tr('status_loaded', count=len(self.images), folder=folder))
        if new_root:
            self.save_to_recent(folder)

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        path = item.data(0, Qt.UserRole)
        if path and os.path.isdir(path):
            self._request_folder(path)

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
        self._counts_images = self.images
        self._pending_tag_deltas = []
        self.all_folder_tags = sorted(counts.keys())
        self.tag_panel.load_tags(self.all_folder_tags, self.folder_tag_counts)
        self.image_grid.set_data(self.images, {})
        self._check_unknown_tags()

    def _check_unknown_tags(self):
        """So sánh all_folder_tags với dict hiện tại, báo status nếu có tag mới."""
        if not self._dict_data:
            return  # Chưa load dict → bỏ qua

        engine = VirtualTagEngine(self._dict_data)
        known = set(engine.build_tag_map().keys())

        unknown = sorted(t for t in self.all_folder_tags if t.lower() not in known)

        # Cập nhật nút trong dict manager nếu đang mở
        if self._dict_tags_win and not self._dict_tags_win.isHidden():
            self._dict_tags_win.set_unknown_tags(unknown)

        # Lưu lại để dùng khi user mở dict manager sau
        self._pending_unknown_tags = unknown

        if unknown:
            self.statusBar().showMessage(
                tr("status_unknown_tags", count=len(unknown)), 0  # 0 = không tự xóa
            )

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

        if getattr(self, "_tagging_running", False):
            QMessageBox.information(self, tr("waifu_win_title"), tr("waifu_wait_running"))
            return

        if getattr(self, "_pending_folder", None):
            return

        if not os.path.isdir(folder):
            raise NotADirectoryError(f"The path does not exist or is not a directory: {folder}")

        if self._has_unsaved():
            resp = QMessageBox.question(
                self, tr("dlg_save_before_switch"), tr("dlg_save_before_switch_msg"),
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if resp == QMessageBox.Yes:
                if not self.save_all():
                    return
            elif resp == QMessageBox.Cancel:
                return
        
        if hasattr(self, "folder_loader"):
            self._request_folder(folder, new_root=True)
            return

        self.history.clear()
        self._undo_folders.clear()
        self._redo_folders.clear()

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
    def save_all(self) -> bool:
        """Return success so callers can stop closing or switching on failure."""
        # Gom tất cả images từ cache + folder hiện tại
        all_images = list(self.images)
        for path, cached in self._folder_cache.items():
            if path != self.current_folder:
                all_images.extend(cached)

        try:
            count = save_all_images(all_images)
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Backup/save failed: {exc}")
            return False
        if count:
            QMessageBox.information(self, tr("save_success"),
                                    tr("save_success_msg", count=count))
        else:
            QMessageBox.information(self, tr("save_nothing"), tr("save_nothing_msg"))
        self.statusBar().showMessage(tr("status_saved", count=count))
        return True

    # ──────────────────────────────────────────────
    #  Undo / Redo
    # ──────────────────────────────────────────────
    def _snapshot(self, indices=None) -> dict:
        return self.history.snapshot_tags(self.images, indices)

    def _queue_tag_deltas(self):
        pending = getattr(self, '_pending_tag_deltas', [])
        pending.extend(self.history.last_changes.values())
        self._pending_tag_deltas = pending

    def _push_history(self, action: str, before):
        if not self.history.push(action, before, self.images):
            return
        self._queue_tag_deltas()
        self._undo_folders.append(self.current_folder)
        self._undo_folders = self._undo_folders[-self.history.max_history:]
        self._redo_folders.clear()

    def do_undo(self):
        if not self.history.can_undo():
            self.statusBar().showMessage(tr("undo_nothing"))
            return

        # Determine which folder this undo entry belongs to.
        target_folder = self._undo_folders[-1] if self._undo_folders else None

        # Navigate to that folder first (silently, no history push).
        if target_folder and target_folder != self.current_folder:
            self._navigate_to_folder_for_undo_redo(target_folder)

        action = self.history.undo(self.images)
        if action:
            # Move folder token from undo stack → redo stack.
            if self._undo_folders:
                self._redo_folders.append(self._undo_folders.pop())
            self._queue_tag_deltas()
            self._refresh_after_tag_change()
            self.statusBar().showMessage(tr("undo_done", action=action))
        else:
            self.statusBar().showMessage(tr("undo_nothing"))

    def do_redo(self):
        if not self.history.can_redo():
            self.statusBar().showMessage(tr("redo_nothing"))
            return

        target_folder = self._redo_folders[-1] if self._redo_folders else None

        if target_folder and target_folder != self.current_folder:
            self._navigate_to_folder_for_undo_redo(target_folder)

        action = self.history.redo(self.images)
        if action:
            # Move folder token from redo stack → undo stack.
            if self._redo_folders:
                self._undo_folders.append(self._redo_folders.pop())
            self._queue_tag_deltas()
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
        if self.image_grid._images is not self.images:
            self._load_all_folder_tags()
        else:
            self._reload_tags_panel()
            self.image_grid.refresh_tags()
            self.image_grid.deselect_all()

    def _navigate_to_folder_for_undo_redo(self, folder: str):
        """Navigate silently to `folder` for undo/redo — no save dialog, no history clear."""
        # Flush current folder's live images back to cache.
        self._save_current_folder_state()

        if folder in self._folder_cache:
            self.images = self._folder_cache[folder]
        else:
            try:
                self.images = load_folder_images(folder)
            except PermissionError:
                return
            self._folder_cache[folder] = self.images

        self.current_folder = folder
        self._selected_images.clear()

        # Sync the folder-tree highlight so the user sees where we jumped.
        self._highlight_tree_item(folder)

    def _highlight_tree_item(self, folder: str):
        """Select the QTreeWidget item that matches `folder` without triggering _on_tree_item_clicked."""
        def _find(item: QTreeWidgetItem) -> QTreeWidgetItem | None:
            if item.data(0, Qt.UserRole) == folder:
                return item
            for i in range(item.childCount()):
                found = _find(item.child(i))
                if found:
                    return found
            return None

        root = self.dir_tree.invisibleRootItem()
        for i in range(root.childCount()):
            match = _find(root.child(i))
            if match:
                self.dir_tree.blockSignals(True)
                self.dir_tree.setCurrentItem(match)
                self.dir_tree.blockSignals(False)
                break

    # ──────────────────────────────────────────────
    def show_history_window(self):
        if not hasattr(self, 'history_dock') or self.history_dock is None:
            self.history_dock = HistoryWindow(self.history, parent=self)
            self.history_win = self.history_dock
            self.addDockWidget(Qt.RightDockWidgetArea, self.history_dock)
            self.history_dock.show()
            return

        if self.history_dock.isVisible():
            self.history_dock.hide()
        else:
            self.history_dock.show()
            self.history_dock.raise_()

    def _toggle_preview_dock(self):
        if self._preview_dock.isVisible():
            self._preview_dock.hide()
        else:
            self._preview_dock.show()

    def _on_preview_dock_visibility(self, visible: bool):
        """Đồng bộ trạng thái checked của nút khi dock bị đóng bằng nút X."""
        self._preview_btn.setChecked(visible)

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

    def _on_individual_tag_add(self, idx: int, raw: str):
        # Tách chuỗi theo dấu phẩy, lọc trùng và rỗng
        new_tags = [t.strip() for t in raw.split(',') if t.strip()]
        new_tags = [t for t in new_tags if t not in self.images[idx]['tags']]
        if not new_tags:
            return

        before = self._snapshot([idx])
        for tag in new_tags:
            self.images[idx]['tags'].append(tag)
        self.images[idx]['modified'] = True

        label = (
            tr("history_add_tag", tag=new_tags[0], filename=self.images[idx]['filename'])
            if len(new_tags) == 1
            else tr("history_add_tag_bulk", tag=", ".join(new_tags), count=len(new_tags))
        )
        self._push_history(label, before)
        self.image_grid.refresh_card(idx)
        self._reload_tags_panel()

    def add_tag_to_selected(self):
        raw = self.global_tag_entry.text().strip()
        if not raw:
            QMessageBox.warning(self, tr("warn_no_tag"), tr("warn_no_tag_msg"))
            return
        if not self._selected_images:
            QMessageBox.warning(self, tr("warn_no_image"), tr("warn_no_image_msg"))
            return

        # Tách chuỗi theo dấu phẩy
        tags_to_add = list(dict.fromkeys(t.strip() for t in raw.split(',') if t.strip()))
        if not tags_to_add:
            QMessageBox.warning(self, tr("warn_no_tag"), tr("warn_no_tag_msg"))
            return

        before = self._snapshot(self._selected_images)
        count = 0

        insert_at_beginning = self._order_tag_combo.currentIndex() == 0

        for idx in list(self._selected_images):
            tags = self.images[idx]['tags']
            existing = set(tags)
            new_tags = [tag for tag in tags_to_add if tag not in existing]
            if new_tags:
                if insert_at_beginning:
                    tags[:0] = new_tags
                else:
                    tags.extend(new_tags)
                self.images[idx]['modified'] = True
                self.image_grid.refresh_card(idx)
                count += 1

        tag_label = tags_to_add[0] if len(tags_to_add) == 1 else ", ".join(tags_to_add)
        self._push_history(tr("history_add_tag_bulk", tag=tag_label, count=count), before)
        self.global_tag_entry.clear()
        self._reload_tags_panel()
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

        before = self._snapshot(self._selected_images)
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
            before = self._snapshot([idx])
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

        before = self._snapshot(self._selected_images)
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
                                
    def _sync_grid_columns(self, columns):
        self.col_spin.blockSignals(True)
        self.col_spin.setMaximum(max(8, columns))
        self.col_spin.setValue(columns)
        self.col_spin.blockSignals(False)

    def apply_grid_layout(self, mode):
        self.image_grid.set_layout_mode(mode)
        manual = self.image_grid.layout_mode == "classic"
        self.col_spin.setEnabled(manual)
        self._col_lbl.setEnabled(manual)
        if hasattr(self, 'workspace'):
            self.workspace.schedule_save()

    def _set_columns(self, n: int):
        self.image_grid.set_columns(n)

    def _reload_tags_panel(self):
        if getattr(self, '_counts_images', None) is self.images:
            counts = Counter(self.folder_tag_counts)
            for old, new in getattr(self, '_pending_tag_deltas', []):
                counts.subtract(old)
                counts.update(new)
            counts = {tag: count for tag, count in counts.items() if count > 0}
        else:
            counts = Counter(tag for image in self.images for tag in image['tags'])
        self._counts_images = self.images
        self._pending_tag_deltas = []
        self.folder_tag_counts = counts
        self.all_folder_tags = sorted(counts)
        self.tag_panel.load_tags(self.all_folder_tags, counts, preserve_filters=True)
        self.image_grid.set_tag_filters(self.tag_panel._tag_filters)

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

    def underscore_swap_tags(self):
        if not self.images:
            QMessageBox.information(self, tr("underscore_dialog_title"), tr("underscore_no_folder"))
            return

        run_underscore_swap(self)

    # ──────────────────────────────────────────────
    #  Waifu Tagger
    # ──────────────────────────────────────────────
    def _connect_tagging_signals(self):
        # All receivers belong to MainWindow on the GUI thread.
        self.tagging_completed.connect(self._on_tagging_finished, Qt.QueuedConnection)
        self.tagging_progress.connect(self._on_tagging_progress, Qt.QueuedConnection)
        self.tagging_failed.connect(self._on_tagging_failed, Qt.QueuedConnection)

    @Slot(str)
    def _on_tagging_progress(self, message):
        self.statusBar().showMessage(message)

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
        if getattr(self, '_tagging_running', False) or getattr(self, '_pending_folder', None):
            return
        self._tagging_running = True
        self._act_waifu.setEnabled(False)
        self.statusBar().showMessage(tr("waifu_running", mode=config['mode']))
        from threading import Thread
        extension = settings.value('load_extension', 'txt').lstrip('.')
        cached_folders = {os.path.abspath(folder) for folder in getattr(self, '_folder_cache', {})}
        if getattr(self, 'current_folder', None):
            cached_folders.add(os.path.abspath(self.current_folder))

        def thread_wrapper():
            try:
                # Import the AI backend only inside the selected execution path.
                if config['mode'] == 'external':
                    from tools.external_tagger import run_external_tagger
                    target_func = run_external_tagger
                else:
                    from tools.tagger_logic import run_tagger
                    target_func = run_tagger
                results = target_func(config, lambda c, t, m:
                                      self.tagging_progress.emit(f"[{c}/{t}] {m}"))
                # Prepare unopened folders on the worker too. The UI still
                # prefers live cache entries, preserving edits made during AI.
                prepared = set(cached_folders)
                for item in results or []:
                    if item.get('skipped') or item.get('error') or item.get('tags') is None:
                        continue
                    folder = os.path.dirname(os.path.abspath(item['path']))
                    if folder not in prepared:
                        item['_folder_images'] = load_folder_images(folder, extension=extension)
                        prepared.add(folder)
                self.tagging_completed.emit(results or [])
            except Exception as exc:
                self.tagging_failed.emit(str(exc))

        Thread(target=thread_wrapper, daemon=True).start()

    def _finish_tagging_job(self):
        self._tagging_running = False
        self._act_waifu.setEnabled(not bool(getattr(self, "_pending_folder", None)))

    @Slot(str)
    def _on_tagging_failed(self, message):
        self._finish_tagging_job()
        self.statusBar().showMessage(tr("waifu_error", error=message))
        QMessageBox.critical(self, tr("waifu_win_title"), message)

    @Slot(list)
    def _on_tagging_finished(self, results: list):
        try:
            self._merge_tagging_results(results)
        except Exception as exc:
            self._on_tagging_failed(str(exc))
        finally:
            self._finish_tagging_job()

    def _merge_tagging_results(self, results: list):
        # Group by source folder, not the folder visible when the worker finishes.
        grouped = {}
        prepared_images = {}
        for item in results:
            # [] is a successful overwrite that clears old tags; only None
            # means no tag result was supplied.
            if item.get('skipped') or item.get('error') or item.get('tags') is None:
                continue
            path = os.path.abspath(item['path'])
            folder = os.path.dirname(path)
            grouped.setdefault(folder, {})[path] = item['tags']
            if '_folder_images' in item:
                prepared_images[folder] = item['_folder_images']

        updated_count = 0
        for folder, tags_by_path in grouped.items():
            if self.current_folder and os.path.abspath(self.current_folder) == folder:
                images = self.images
                history_folder = self.current_folder
            else:
                history_folder = next((key for key in self._folder_cache
                                       if os.path.abspath(key) == folder), folder)
                images = self._folder_cache.get(history_folder)
                if images is None:
                    images = prepared_images.get(folder)
                    if images is None:
                        images = load_folder_images(folder)
                    self._folder_cache[history_folder] = images
            before = self.history.snapshot_tags(images,
                [idx for idx, image in enumerate(images) if os.path.abspath(image['path']) in tags_by_path])
            count = 0
            for image in images:
                path = os.path.abspath(image['path'])
                if path in tags_by_path:
                    image['tags'] = list(tags_by_path[path])
                    image['modified'] = True
                    count += 1
            if count:
                if self.history.push(tr("history_waifu_tag", count=count), before, images):
                    if images is self.images:
                        self._queue_tag_deltas()
                    self._undo_folders.append(history_folder)
                    self._undo_folders = self._undo_folders[-self.history.max_history:]
                    self._redo_folders.clear()
                updated_count += count

        # No-result jobs must not reload disk over unsaved edits.
        if updated_count:
            self._refresh_after_tag_change()
        self.statusBar().showMessage(tr("waifu_done_status", count=updated_count))
        errors = [str(item['error']) for item in results if item.get('error')]
        if errors:
            QMessageBox.warning(self, tr("waifu_win_title"),
                                tr("waifu_done_msg", count=updated_count) + "\n" + "\n".join(errors[:10]))
        else:
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
        path, _ = QFileDialog.getSaveFileName(
            self, tr("save_new_dict"), "dictionary.json", "JSON (*.json)"
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
            self.settings.set_value("auto_load_dict_path", file_path)
            self.dict_load(file_path)
            QMessageBox.information(self, tr("success"), tr("auto_load_dict_set", path=file_path))

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
        
    def dict_reload(self):
        """Reload dict from the last loaded path."""
        if not self._dict_path or not os.path.exists(self._dict_path):
            QMessageBox.warning(self, tr("warn_no_dict"), tr("warn_no_dict_msg"))
            return
        self._do_load_dict(self._dict_path)
    
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
        
        self._check_unknown_tags()
        # Luôn đồng bộ danh sách tag chưa có trong dict
        self._dict_tags_win.set_unknown_tags(self._pending_unknown_tags)

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
        if getattr(self, '_tagging_running', False):
            QMessageBox.information(self, tr("waifu_win_title"), tr("waifu_wait_running"))
            event.ignore()
            return
        if self._has_unsaved():
            resp = QMessageBox.question(
                self, tr("close_save_title"), tr("close_save_msg"),
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if resp == QMessageBox.Yes:
                if not self.save_all():
                    event.ignore()
                    return
                event.accept()
            elif resp == QMessageBox.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
        if event.isAccepted() and hasattr(self, 'workspace'):
            self.workspace.finish_close()
