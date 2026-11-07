"""
waifu_tagger_window.py - WD14 Tagger Settings Dialog (PySide6)
Restyled to match app-wide tone: dark-friendly, compact QGroupBox sections,
green primary action button consistent with resort_tag_window_operation.py
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QCheckBox, QSlider, QComboBox, QPushButton,
    QGroupBox, QScrollArea, QFileDialog, QWidget, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from i18n import tr
from app_paths import build_info, bundled_model, local_ai_available
from settings_manager import settings
from tools.external_tagger import discover_tool, validate_external_config

# ── App-wide style constants (mirror what the rest of the app uses) ──────────
_BTN_PRIMARY = (
    "QPushButton {"
    "  font-weight: bold;"
    "  background: #4CAF50;"       # same green as resort_tag process btn
    "  color: white;"
    "  border: none;"
    "  border-radius: 3px;"
    "  padding: 4px 12px;"
    "}"
    "QPushButton:hover { background: #43A047; }"
    "QPushButton:pressed { background: #388E3C; }"
    "QPushButton:disabled { background: #555; color: #888; }"
)

_BTN_SECONDARY = (
    "QPushButton {"
    "  background: transparent;"
    "  border: 1px solid #555;"
    "  border-radius: 3px;"
    "  padding: 4px 12px;"
    "}"
    "QPushButton:hover { background: #3a3a3a; }"
)

_BTN_BROWSE = (
    "QPushButton {"
    "  background: #2d2d2d;"
    "  border: 1px solid #555;"
    "  border-radius: 3px;"
    "  padding: 3px 8px;"
    "  min-width: 72px;"
    "}"
    "QPushButton:hover { background: #3a3a3a; }"
)


class WaifuTaggerWindow(QDialog):
    tagging_started = Signal(dict)

    def __init__(self, parent=None, current_folder: str = None, root_folder: str = None):
        super().__init__(parent)
        self.current_folder = current_folder or ""
        self.root_folder = root_folder or current_folder or ""
        self.resize(580, 780)
        self.setup_ui()
        self.retranslate_ui()
        self.tool_path.setText(settings.value("wd14/tool_path", ""))
        self.tool_type.setCurrentIndex(max(0, self.tool_type.findData(settings.value("wd14/tool_type", "auto"))))
        self.python_path.setText(settings.value("wd14/python_path", ""))
        self._scan_tool()
        saved_model = settings.value("wd14/model_path", "")
        for index in range(self.detected_models.count()):
            if self.detected_models.itemData(index)["onnx_path"] == saved_model:
                self.detected_models.setCurrentIndex(index)
                break
        model = bundled_model()
        if model and not self.onnx_path.text():
            self.onnx_path.setText(model[0])
            self.csv_path.setText(model[1])
            self.repo_id.setText(build_info()['model_repo'])
        if not local_ai_available():
            self.run_mode.model().item(0).setEnabled(False)
        self.run_mode.setCurrentIndex(1 if not local_ai_available() or settings.value("wd14/mode", "local") == "external" else 0)

    # ─────────────────────────────────────────────
    #  UI
    # ─────────────────────────────────────────────
    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        # ── Scrollable body ───────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(2, 2, 4, 2)
        layout.setSpacing(6)

        # ── 0. Execution Mode ─────────────────────
        self._mode_group = QGroupBox()
        v_mode = QVBoxLayout(self._mode_group)
        v_mode.setSpacing(4)

        mode_row = QHBoxLayout()
        self._run_mode_lbl = QLabel()
        mode_row.addWidget(self._run_mode_lbl)
        self.run_mode = QComboBox()
        self.run_mode.addItems(["Local", "Installed tool"])
        self.run_mode.setCurrentIndex(0)
        mode_row.addWidget(self.run_mode, 1)
        v_mode.addLayout(mode_row)

        self.tool_frame = QWidget()
        tool_layout = QGridLayout(self.tool_frame)
        tool_layout.setContentsMargins(0, 0, 0, 0)
        self._tool_path_lbl = QLabel()
        self.tool_path = QLineEdit()
        self._tool_browse_btn = QPushButton()
        self._tool_browse_btn.clicked.connect(self._browse_tool)
        tool_layout.addWidget(self._tool_path_lbl, 0, 0)
        tool_layout.addWidget(self.tool_path, 0, 1)
        tool_layout.addWidget(self._tool_browse_btn, 0, 2)
        self._tool_type_lbl = QLabel()
        self.tool_type = QComboBox()
        self.tool_type.addItem("Auto", "auto")
        self.tool_type.addItem("Kohya_ss", "kohya_ss")
        self.tool_type.addItem("sd-scripts", "sd_scripts")
        self._tool_scan_btn = QPushButton()
        self._tool_scan_btn.clicked.connect(self._scan_tool)
        tool_layout.addWidget(self._tool_type_lbl, 1, 0)
        tool_layout.addWidget(self.tool_type, 1, 1)
        tool_layout.addWidget(self._tool_scan_btn, 1, 2)
        self._python_lbl = QLabel()
        self.python_path = QLineEdit()
        self._python_browse_btn = QPushButton()
        self._python_browse_btn.clicked.connect(self._browse_python)
        tool_layout.addWidget(self._python_lbl, 2, 0)
        tool_layout.addWidget(self.python_path, 2, 1)
        tool_layout.addWidget(self._python_browse_btn, 2, 2)
        self._detected_models_lbl = QLabel()
        self.detected_models = QComboBox()
        self.detected_models.currentIndexChanged.connect(self._select_detected_model)
        tool_layout.addWidget(self._detected_models_lbl, 3, 0)
        tool_layout.addWidget(self.detected_models, 3, 1, 1, 2)
        self.tool_status = QLabel()
        self.tool_status.setWordWrap(True)
        tool_layout.addWidget(self.tool_status, 4, 0, 1, 3)
        v_mode.addWidget(self.tool_frame)
        self.run_mode.currentIndexChanged.connect(self._set_execution_mode)
        self.tool_frame.setVisible(False)
        self.tool_path.editingFinished.connect(self._scan_tool)
        self.tool_type.currentIndexChanged.connect(self._scan_tool)
        layout.addWidget(self._mode_group)

        # ── 1. Model Settings ─────────────────────
        self._model_group = QGroupBox()
        grid = QGridLayout(self._model_group)
        grid.setColumnStretch(1, 1)
        grid.setVerticalSpacing(4)
        grid.setHorizontalSpacing(6)

        self._repo_id_lbl = QLabel()
        grid.addWidget(self._repo_id_lbl, 0, 0)
        self.repo_id = QLineEdit("SmilingWolf/wd-v1-4-convnextv2-tagger-v2")
        grid.addWidget(self.repo_id, 0, 1, 1, 2)

        self._onnx_lbl = QLabel()
        grid.addWidget(self._onnx_lbl, 1, 0)
        self.onnx_path = QLineEdit()
        grid.addWidget(self.onnx_path, 1, 1)
        self._btn_browse_onnx = QPushButton()
        self._btn_browse_onnx.setStyleSheet(_BTN_BROWSE)
        self._btn_browse_onnx.clicked.connect(self._browse_onnx)
        grid.addWidget(self._btn_browse_onnx, 1, 2)

        self._csv_lbl = QLabel()
        grid.addWidget(self._csv_lbl, 2, 0)
        self.csv_path = QLineEdit()
        grid.addWidget(self.csv_path, 2, 1)
        self._btn_browse_csv = QPushButton()
        self._btn_browse_csv.setStyleSheet(_BTN_BROWSE)
        self._btn_browse_csv.clicked.connect(self._browse_csv)
        grid.addWidget(self._btn_browse_csv, 2, 2)

        self.force_download = QCheckBox()
        grid.addWidget(self.force_download, 3, 0, 1, 3)

        layout.addWidget(self._model_group)

        # ── 3. Scope / Folder ─────────────────────
        self._scope_group = QGroupBox()
        v_scope = QVBoxLayout(self._scope_group)
        v_scope.setSpacing(4)

        scope_row = QHBoxLayout()
        self._target_folder_lbl = QLabel()
        scope_row.addWidget(self._target_folder_lbl)
        self.folder_label = QLabel(self.current_folder or "")
        self.folder_label.setStyleSheet("color: #888; font-size: 11px;")
        self.folder_label.setWordWrap(True)
        scope_row.addWidget(self.folder_label, 1)
        v_scope.addLayout(scope_row)

        self.include_subfolders = QCheckBox()
        self.include_subfolders.setChecked(False)
        v_scope.addWidget(self.include_subfolders)

        self.alpha_to_white = QCheckBox()
        self.alpha_to_white.setChecked(True)
        v_scope.addWidget(self.alpha_to_white)
        layout.addWidget(self._scope_group)

        # ── 4. Tag Processing ─────────────────────
        self._opt_group = QGroupBox()
        v_opt = QVBoxLayout(self._opt_group)
        v_opt.setSpacing(4)

        # TODO add HBox layout with Label here
        mode_layout = QHBoxLayout()
        self._write_mode_lbl = QLabel(tr("waifu_write_mode"))
        self.write_mode = QComboBox()
        self.write_mode.addItems([ tr("waifu_mode_skip") , tr("waifu_mode_overwrite")])
        self.write_mode.setCurrentIndex(1) # Mặc định là Overwrite
        mode_layout.addWidget(self._write_mode_lbl)
        mode_layout.addWidget(self.write_mode, 1)
        v_opt.addLayout(mode_layout)

        self.char_expand      = QCheckBox()
        self.remove_underscore = QCheckBox()
        self.remove_underscore.setChecked(True)
        self.append_tags      = QCheckBox()
        self.use_rating       = QCheckBox()
        self.rating_last      = QCheckBox()

        for w in [self.char_expand, self.remove_underscore, self.append_tags,
                  self.use_rating, self.rating_last]:
            v_opt.addWidget(w)

        layout.addWidget(self._opt_group)

        # ── 5. Filters ────────────────────────────
        self._filter_group = QGroupBox()
        v_filter = QVBoxLayout(self._filter_group)
        v_filter.setSpacing(4)

        self._prefix_lbl = QLabel()
        v_filter.addWidget(self._prefix_lbl)
        self.prefix = QLineEdit()
        v_filter.addWidget(self.prefix)

        self._undesired_lbl = QLabel()
        v_filter.addWidget(self._undesired_lbl)
        self.undesired = QLineEdit()
        v_filter.addWidget(self.undesired)

        layout.addWidget(self._filter_group)

        # ── 6. Thresholds ─────────────────────────
        self._thresh_group = QGroupBox()
        t_grid = QGridLayout(self._thresh_group)
        t_grid.setVerticalSpacing(6)

        self._gen_lbl = QLabel()
        self.gen_slider, self.gen_val = self._create_slider(35)
        t_grid.addWidget(self._gen_lbl, 0, 0)
        t_grid.addWidget(self.gen_slider, 0, 1)
        t_grid.addWidget(self.gen_val, 0, 2)

        self._char_lbl = QLabel()
        self.char_slider, self.char_val = self._create_slider(35)
        t_grid.addWidget(self._char_lbl, 1, 0)
        t_grid.addWidget(self.char_slider, 1, 1)
        t_grid.addWidget(self.char_val, 1, 2)

        layout.addWidget(self._thresh_group)
        layout.addStretch()

        scroll.setWidget(body)
        root.addWidget(scroll, stretch=1)

        # ── Bottom action bar ─────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #444;")
        root.addWidget(sep)

        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        self._cancel_btn = QPushButton()
        self._cancel_btn.setStyleSheet(_BTN_SECONDARY)
        self._cancel_btn.clicked.connect(self.reject)
        btn_bar.addWidget(self._cancel_btn)

        self.btn_run = QPushButton()
        self.btn_run.setFixedHeight(34)
        self.btn_run.setStyleSheet(_BTN_PRIMARY)
        self.btn_run.clicked.connect(self._collect_and_run)
        btn_bar.addWidget(self.btn_run)

        root.addLayout(btn_bar)

    def retranslate_ui(self):
        self.setWindowTitle(tr("waifu_win_title"))

        # Execution mode
        self._mode_group.setTitle(tr("waifu_exec_mode"))
        self._run_mode_lbl.setText(tr("waifu_run_mode_label"))
        current_idx = self.run_mode.currentIndex()
        self.run_mode.blockSignals(True)
        self.run_mode.clear()
        self.run_mode.addItems([tr("waifu_mode_local"), tr("waifu_mode_external")])
        self.run_mode.setCurrentIndex(current_idx)
        self.run_mode.blockSignals(False)
        self._tool_path_lbl.setText(tr("waifu_tool_path"))
        self._tool_type_lbl.setText(tr("waifu_tool_type"))
        self.tool_type.setItemText(0, tr("waifu_tool_auto"))
        self._python_lbl.setText(tr("waifu_tool_python"))
        self._detected_models_lbl.setText(tr("waifu_installed_models"))
        self._tool_scan_btn.setText(tr("waifu_scan_tool"))
        self._tool_browse_btn.setText(tr("waifu_browse"))
        self._python_browse_btn.setText(tr("waifu_browse"))

        # Model settings
        self._model_group.setTitle(tr("waifu_model_settings"))
        self._repo_id_lbl.setText(tr("waifu_repo_id"))
        self._onnx_lbl.setText(tr("waifu_onnx_label"))
        self.onnx_path.setPlaceholderText(tr("waifu_onnx_placeholder"))
        self._btn_browse_onnx.setText(tr("waifu_browse"))
        self._csv_lbl.setText(tr("waifu_csv_label"))
        self.csv_path.setPlaceholderText(tr("waifu_csv_placeholder"))
        self._btn_browse_csv.setText(tr("waifu_browse"))
        self.force_download.setText(tr("waifu_force_download"))

        # Scope
        self._scope_group.setTitle(tr("waifu_scope"))
        self._target_folder_lbl.setText(tr("waifu_target_folder"))
        if not self.folder_label.text():
            self.folder_label.setText(tr("waifu_no_folder"))
        self.include_subfolders.setText(tr("waifu_include_sub"))
        self.include_subfolders.setToolTip(tr("waifu_include_sub_tooltip"))
        self.alpha_to_white.setText(tr("waifu_alpha_white"))
        self.alpha_to_white.setToolTip(tr("waifu_alpha_tooltip"))

        # Tag processing
        self._opt_group.setTitle(tr("waifu_tag_processing"))
        self.char_expand.setText(tr("waifu_char_expand"))
        self.remove_underscore.setText(tr("waifu_remove_underscore"))
        self.append_tags.setText(tr("waifu_append_tags"))
        self.use_rating.setText(tr("waifu_use_rating"))
        self.rating_last.setText(tr("waifu_rating_last"))

        # Filters
        self._filter_group.setTitle(tr("waifu_filters"))
        self._prefix_lbl.setText(tr("waifu_prefix_label"))
        self._undesired_lbl.setText(tr("waifu_undesired_label"))

        # Thresholds
        self._thresh_group.setTitle(tr("waifu_thresholds"))
        self._gen_lbl.setText(tr("waifu_general"))
        self._char_lbl.setText(tr("waifu_character"))

        # Buttons
        self._cancel_btn.setText(tr("ldl_cancel"))
        self.btn_run.setText(tr("waifu_run_btn"))

    # ─────────────────────────────────────────────
    #  Helpers
    # ─────────────────────────────────────────────
    def _create_slider(self, default: int = 35):
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(default)
        val_lbl = QLabel(f"{default / 100:.2f}")
        val_lbl.setFixedWidth(36)
        slider.valueChanged.connect(lambda v: val_lbl.setText(f"{v / 100:.2f}"))
        return slider, val_lbl

    def _set_execution_mode(self, index):
        self.tool_frame.setVisible(index == 1)
        self.repo_id.setEnabled(index == 0)
        self.force_download.setEnabled(index == 0)
        if index == 1:
            self.force_download.setChecked(False)
            self._scan_tool()

    def _browse_tool(self):
        path = QFileDialog.getExistingDirectory(self, tr("waifu_tool_path"), self.tool_path.text())
        if path:
            self.tool_path.setText(path)
            self.python_path.clear()
            self._scan_tool()

    def _browse_python(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("waifu_tool_python"), self.tool_path.text())
        if path:
            self.python_path.setText(path)

    def _scan_tool(self):
        path = self.tool_path.text().strip()
        previous_path = getattr(self, '_last_scanned_path', path)
        if path != previous_path:
            self.python_path.clear()
        self._last_scanned_path = path
        previous = self.detected_models.currentData()
        self.detected_models.clear()
        if not self.tool_path.text().strip():
            self.tool_status.setText(tr("waifu_tool_hint"))
            return
        try:
            info = discover_tool(self.tool_path.text(), self.tool_type.currentData())
        except ValueError as exc:
            self.tool_status.setText(str(exc))
            return
        if not self.python_path.text().strip():
            self.python_path.setText(info['python_path'])
        for model in info['models']:
            name = os.path.basename(os.path.dirname(model['onnx_path']))
            if os.path.basename(model['onnx_path']) != 'model.onnx':
                name += ' / ' + os.path.basename(model['onnx_path'])
            self.detected_models.addItem(name, model)
            self.detected_models.setItemData(self.detected_models.count() - 1, model['onnx_path'], Qt.ToolTipRole)
        if previous:
            for index in range(self.detected_models.count()):
                if self.detected_models.itemData(index)['onnx_path'] == previous['onnx_path']:
                    self.detected_models.setCurrentIndex(index)
                    break
        message = tr("waifu_tool_found", tool=info['tool_type'], count=len(info['models']))
        if not info['models']:
            message += "\n" + tr("waifu_tool_no_models")
        if not info['python_path']:
            message += "\n" + tr("waifu_tool_no_python")
        self.tool_status.setText(message)

    def _select_detected_model(self, index):
        model = self.detected_models.itemData(index)
        if model:
            self.onnx_path.setText(model['onnx_path'])
            self.csv_path.setText(model['csv_path'])

    def _browse_onnx(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("waifu_browse_onnx_title"),
            "",
            tr("waifu_browse_onnx_filter")
        )
        if path:
            self.onnx_path.setText(path)
            candidate_csv = os.path.join(os.path.dirname(path), "selected_tags.csv")
            if os.path.isfile(candidate_csv) and not self.csv_path.text():
                self.csv_path.setText(candidate_csv)

    def _browse_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("waifu_browse_csv_title"),
            "",
            tr("waifu_browse_csv_filter")
        )
        if path:
            self.csv_path.setText(path)

    # ─────────────────────────────────────────────
    #  Collect config & emit signal
    # ─────────────────────────────────────────────
    def _collect_and_run(self):
        onnx = self.onnx_path.text().strip()
        csv  = self.csv_path.text().strip()

        config = {
            "mode":               "local" if self.run_mode.currentIndex() == 0 else "external",
            "tool_path":          self.tool_path.text().strip(),
            "tool_type":          self.tool_type.currentData(),
            "python_path":        self.python_path.text().strip(),

            "repo_id":            self.repo_id.text().strip(),
            "onnx_path":          onnx if onnx else None,
            "csv_path":           csv  if csv  else None,
            "force_download":     self.force_download.isChecked(),

            "alpha_to_white":     self.alpha_to_white.isChecked(),

            "target_folder":      self.current_folder,
            "root_folder":        self.root_folder,
            "include_subfolders": self.include_subfolders.isChecked(),

            "write_mode":         ["skip", "overwrite"][self.write_mode.currentIndex()],
            "gen_threshold":      self.gen_slider.value() / 100,
            "char_threshold":     self.char_slider.value() / 100,
            "char_expand":        self.char_expand.isChecked(),
            "remove_underscore":  self.remove_underscore.isChecked(),
            "append_tags":        self.append_tags.isChecked(),
            "use_rating":         self.use_rating.isChecked(),
            "rating_as_last":     self.rating_last.isChecked(),

            "prefix_tags":        [t.strip() for t in self.prefix.text().split(",")    if t.strip()],
            "undesired_tags":     [t.strip() for t in self.undesired.text().split(",") if t.strip()],

            "replacement_map":    {},
        }

        if config['mode'] == 'external':
            try:
                validate_external_config(config)
            except ValueError as exc:
                QMessageBox.warning(self, tr("waifu_exec_mode"), str(exc))
                return
        for key in ('tool_path', 'tool_type', 'python_path', 'mode'):
            settings.set_value('wd14/' + key, config[key])
        settings.set_value('wd14/model_path', config['onnx_path'] or '')
        self.tagging_started.emit(config)
        self.accept()