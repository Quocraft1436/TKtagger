"""
waifu_tagger_window.py - WD14 Tagger Settings Dialog (PySide6)
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QCheckBox, QSlider, QComboBox, QPushButton,
    QGroupBox, QScrollArea, QFileDialog, QSizePolicy, QWidget
)
from PySide6.QtCore import Qt, Signal
from i18n import tr


class WaifuTaggerWindow(QDialog):
    tagging_started = Signal(dict)

    def __init__(self, parent=None, current_folder: str = None, root_folder: str = None):
        super().__init__(parent)
        self.current_folder = current_folder or ""
        self.root_folder = root_folder or current_folder or ""
        self.resize(640, 860)
        self.setup_ui()
        self.retranslate_ui()

    # ─────────────────────────────────────────────
    #  UI
    # ─────────────────────────────────────────────
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self._container = QGroupBox()
        layout = QVBoxLayout(self._container)
        layout.setSpacing(8)

        # ── 0. Execution Mode ──────────────────────────────
        self._mode_group = QGroupBox()
        v_mode = QVBoxLayout(self._mode_group)

        mode_row = QHBoxLayout()
        self._run_mode_lbl = QLabel()
        mode_row.addWidget(self._run_mode_lbl)
        self.run_mode = QComboBox()
        mode_row.addWidget(self.run_mode, 1)
        
        self.run_mode.addItems(["Local", "API"]) 
        self.run_mode.setCurrentIndex(0)
        v_mode.addLayout(mode_row)

        self.api_url_frame = QWidget()
        api_layout = QHBoxLayout(self.api_url_frame)
        api_layout.setContentsMargins(0, 0, 0, 0)
        self._api_url_lbl = QLabel()
        api_layout.addWidget(self._api_url_lbl)
        self.api_url = QLineEdit("http://127.0.0.1:7860/")
        api_layout.addWidget(self.api_url)
        v_mode.addWidget(self.api_url_frame)

        self.run_mode.currentIndexChanged.connect(
            lambda i: self.api_url_frame.setVisible(i == 1)
        )
        self.api_url_frame.setVisible(False)

        layout.addWidget(self._mode_group)

        # ── 1. Model Settings ──────────────────────────────
        self._model_group = QGroupBox()
        grid = QGridLayout(self._model_group)
        grid.setColumnStretch(1, 1)

        self._repo_id_lbl = QLabel()
        grid.addWidget(self._repo_id_lbl, 0, 0)
        self.repo_id = QLineEdit("SmilingWolf/wd-v1-4-convnextv2-tagger-v2")
        grid.addWidget(self.repo_id, 0, 1, 1, 2)

        self._onnx_lbl = QLabel()
        grid.addWidget(self._onnx_lbl, 1, 0)
        self.onnx_path = QLineEdit()
        self.onnx_path.setReadOnly(False)
        grid.addWidget(self.onnx_path, 1, 1)

        self._btn_browse_onnx = QPushButton()
        self._btn_browse_onnx.setFixedWidth(90)
        self._btn_browse_onnx.clicked.connect(self._browse_onnx)
        grid.addWidget(self._btn_browse_onnx, 1, 2)

        self._csv_lbl = QLabel()
        grid.addWidget(self._csv_lbl, 2, 0)
        self.csv_path = QLineEdit()
        grid.addWidget(self.csv_path, 2, 1)
        self._btn_browse_csv = QPushButton()
        self._btn_browse_csv.setFixedWidth(90)
        self._btn_browse_csv.clicked.connect(self._browse_csv)
        grid.addWidget(self._btn_browse_csv, 2, 2)

        self.force_download = QCheckBox()
        grid.addWidget(self.force_download, 3, 1, 1, 2)

        layout.addWidget(self._model_group)

        # ── 2. Image Pre-processing ────────────────────────
        self._preproc_group = QGroupBox()
        v_pre = QVBoxLayout(self._preproc_group)

        self.alpha_to_white = QCheckBox()
        self.alpha_to_white.setChecked(True)
        v_pre.addWidget(self.alpha_to_white)

        layout.addWidget(self._preproc_group)

        # ── 3. Scope / Folder ──────────────────────────────
        self._scope_group = QGroupBox()
        v_scope = QVBoxLayout(self._scope_group)

        scope_row = QHBoxLayout()
        self._target_folder_lbl = QLabel()
        scope_row.addWidget(self._target_folder_lbl)
        self.folder_label = QLabel(self.current_folder or "")
        self.folder_label.setStyleSheet("color:#aaa; font-size:11px;")
        self.folder_label.setWordWrap(True)
        scope_row.addWidget(self.folder_label, 1)
        v_scope.addLayout(scope_row)

        self.include_subfolders = QCheckBox()
        self.include_subfolders.setChecked(False)
        v_scope.addWidget(self.include_subfolders)

        layout.addWidget(self._scope_group)

        # ── 4. Tag Processing ──────────────────────────────
        self._opt_group = QGroupBox()
        v_opt = QVBoxLayout(self._opt_group)

        self.char_expand = QCheckBox()
        self.remove_underscore = QCheckBox()
        self.remove_underscore.setChecked(True)
        self.append_tags = QCheckBox()
        self.use_rating = QCheckBox()
        self.rating_last = QCheckBox()

        for w in [self.char_expand, self.remove_underscore, self.append_tags,
                  self.use_rating, self.rating_last]:
            v_opt.addWidget(w)

        layout.addWidget(self._opt_group)

        # ── 5. Filters ────────────────────────────────────
        self._filter_group = QGroupBox()
        v_filter = QVBoxLayout(self._filter_group)

        self._prefix_lbl = QLabel()
        v_filter.addWidget(self._prefix_lbl)
        self.prefix = QLineEdit()
        v_filter.addWidget(self.prefix)

        self._undesired_lbl = QLabel()
        v_filter.addWidget(self._undesired_lbl)
        self.undesired = QLineEdit()
        v_filter.addWidget(self.undesired)

        layout.addWidget(self._filter_group)

        # ── 6. Thresholds ─────────────────────────────────
        self._thresh_group = QGroupBox()
        t_grid = QGridLayout(self._thresh_group)

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

        # ── Run button ────────────────────────────────────
        self.btn_run = QPushButton()
        self.btn_run.setFixedHeight(44)
        self.btn_run.setStyleSheet(
            "QPushButton { background-color:#4a90d9; color:white; font-weight:bold; font-size:14px; border-radius:4px; }"
            "QPushButton:hover { background-color:#357abd; }"
        )
        self.btn_run.clicked.connect(self._collect_and_run)

        scroll.setWidget(self._container)
        main_layout.addWidget(scroll, stretch=1)
        main_layout.addWidget(self.btn_run)

    def retranslate_ui(self):
        self.setWindowTitle(tr("waifu_win_title"))
        self._container.setTitle(tr("waifu_section_config"))

        # Execution mode
        self._mode_group.setTitle(tr("waifu_exec_mode"))
        self._run_mode_lbl.setText(tr("waifu_run_mode_label"))
        # Repopulate combo to update translated items
        current_idx = self.run_mode.currentIndex()
        self.run_mode.blockSignals(True)
        self.run_mode.clear()
        self.run_mode.addItems([tr("waifu_mode_local"), tr("waifu_mode_api")])
        self.run_mode.setCurrentIndex(current_idx)
        self.run_mode.blockSignals(False)
        self._api_url_lbl.setText(tr("waifu_api_url_label"))

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

        # Pre-processing
        self._preproc_group.setTitle(tr("waifu_preproc"))
        self.alpha_to_white.setText(tr("waifu_alpha_white"))
        self.alpha_to_white.setToolTip(tr("waifu_alpha_tooltip"))

        # Scope
        self._scope_group.setTitle(tr("waifu_scope"))
        self._target_folder_lbl.setText(tr("waifu_target_folder"))
        if not self.folder_label.text():
            self.folder_label.setText(tr("waifu_no_folder"))
        self.include_subfolders.setText(tr("waifu_include_sub"))
        self.include_subfolders.setToolTip(tr("waifu_include_sub_tooltip"))

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

        # Run button
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
            "mode":               "local" if self.run_mode.currentIndex() == 0 else "api",
            "api_url":            self.api_url.text().strip(),

            "repo_id":            self.repo_id.text().strip(),
            "onnx_path":          onnx if onnx else None,
            "csv_path":           csv  if csv  else None,
            "force_download":     self.force_download.isChecked(),

            "alpha_to_white":     self.alpha_to_white.isChecked(),

            "target_folder":      self.current_folder,
            "root_folder":        self.root_folder,
            "include_subfolders": self.include_subfolders.isChecked(),

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

        self.tagging_started.emit(config)
        self.accept()
