"""
settings_dialog.py - Preferences/Settings dialog for TKtagger
FIXED: Load Extension (Radio buttons) in General tab, simplified File Formats with i18n support
"""
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QComboBox, QSpinBox, QPushButton,
    QGroupBox, QCheckBox, QLineEdit, QFileDialog,
    QMessageBox, QWidget, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from i18n import tr


class SettingsDialog(QDialog):
    """Settings/Preferences dialog for TKtagger"""
    
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        from PySide6.QtCore import QSettings
        self.settings = QSettings("settings.ini", QSettings.IniFormat)
        
        self.setWindowTitle(tr("settings_title"))
        self.setGeometry(100, 100, 550, 450)
        
        self._init_ui()
        self._load_settings()
        
    def _init_ui(self):
        """Initialize UI with tabs"""
        layout = QVBoxLayout()
        
        # Tab widget
        tabs = QTabWidget()
        
        # Tab 1: General (with Load Extension)
        self.general_tab = self._create_general_tab()
        tabs.addTab(self.general_tab, tr("settings_tab_general"))
        
        # Tab 2: History
        self.history_tab = self._create_history_tab()
        tabs.addTab(self.history_tab, tr("settings_tab_history"))
        
        layout.addWidget(tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._on_ok)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._on_apply)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def _create_general_tab(self) -> QWidget:
        """Create General settings tab with Language and Load Extension"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # ── Language selection ────────────────────────────────────────────────
        lang_group = QGroupBox(tr("settings_lang_group"))
        lang_layout = QVBoxLayout()
        
        lang_lbl = QLabel(tr("settings_ui_lang"))
        self.lang_combo = QComboBox()
        
        # Load supported languages
        from settings_manager import settings
        languages = settings.get_supported_languages()
        for code, label in languages:
            self.lang_combo.addItem(label, code)
        
        lang_layout.addWidget(lang_lbl)
        lang_layout.addWidget(self.lang_combo)
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)
        
        # ── Load Extension (Radio buttons) ────────────────────────────────────
        ext_group = QGroupBox(tr("settings_ext_group"))
        ext_layout = QVBoxLayout()
        
        ext_lbl = QLabel(tr("settings_ext_label"))
        ext_layout.addWidget(ext_lbl)
        
        # Radio button group
        self.ext_button_group = QButtonGroup()
        
        # Radio 1: .txt
        self.radio_txt = QRadioButton(tr("settings_radio_txt"))
        self.ext_button_group.addButton(self.radio_txt, 0)
        ext_layout.addWidget(self.radio_txt)
        
        # Radio 2: .cap
        self.radio_cap = QRadioButton(tr("settings_radio_cap"))
        self.ext_button_group.addButton(self.radio_cap, 1)
        ext_layout.addWidget(self.radio_cap)
        
        # Radio 3: Custom
        self.radio_custom = QRadioButton(tr("settings_radio_custom"))
        self.ext_button_group.addButton(self.radio_custom, 2)
        ext_layout.addWidget(self.radio_custom)
        
        # Custom extension input (disabled by default)
        custom_layout = QHBoxLayout()
        custom_layout.setContentsMargins(20, 0, 0, 0)
        
        self.custom_ext_input = QLineEdit()
        self.custom_ext_input.setPlaceholderText(tr("settings_custom_placeholder"))
        self.custom_ext_input.setMaximumWidth(200)
        self.custom_ext_input.setEnabled(False)
        
        custom_layout.addWidget(self.custom_ext_input)
        custom_layout.addStretch()
        ext_layout.addLayout(custom_layout)
        
        # Connect radio button changes to enable/disable custom input
        self.radio_txt.toggled.connect(lambda checked: self._on_ext_changed())
        self.radio_cap.toggled.connect(lambda checked: self._on_ext_changed())
        self.radio_custom.toggled.connect(lambda checked: self._on_ext_changed())
        
        # Info text
        info_txt = QLabel(tr("settings_ext_info"))
        info_txt.setWordWrap(True)
        info_txt.setStyleSheet("font-size: 10px; color: #666;")
        ext_layout.addSpacing(10)
        ext_layout.addWidget(info_txt)
        
        ext_group.setLayout(ext_layout)
        layout.addWidget(ext_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _on_ext_changed(self):
        """Enable/disable custom extension input based on radio selection"""
        is_custom = self.radio_custom.isChecked()
        self.custom_ext_input.setEnabled(is_custom)
        if is_custom:
            self.custom_ext_input.setFocus()
    
    def _create_history_tab(self) -> QWidget:
        """Create History settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Max history entries
        history_group = QGroupBox(tr("settings_history_group"))
        history_layout = QVBoxLayout()
        
        max_lbl = QLabel(tr("settings_max_history_lbl"))
        max_lbl.setToolTip(tr("settings_max_history_tooltip"))
        
        history_layout.addWidget(max_lbl)
        
        spinbox_layout = QHBoxLayout()
        self.history_spin = QSpinBox()
        self.history_spin.setRange(10, 1000)
        self.history_spin.setSingleStep(10)
        self.history_spin.setValue(256)
        
        spinbox_layout.addWidget(self.history_spin)
        spinbox_layout.addStretch()
        history_layout.addLayout(spinbox_layout)
        
        warning = QLabel(tr("settings_history_warning"))
        warning.setStyleSheet("color: #FF9800; font-size: 10px;")
        warning.setWordWrap(True)
        history_layout.addWidget(warning)
        
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        # Clear history button
        clear_group = QGroupBox(tr("settings_clear_history_group"))
        clear_layout = QVBoxLayout()
        
        clear_btn = QPushButton(tr("settings_clear_history_btn"))
        clear_btn.setStyleSheet("background: #f44336; color: white;")
        clear_btn.clicked.connect(self._on_clear_history)
        clear_layout.addWidget(clear_btn)
        
        clear_group.setLayout(clear_layout)
        layout.addWidget(clear_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _load_settings(self):
        """Load current settings from QSettings"""
        current_lang = self.settings.value("language", "en")
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == current_lang:
                self.lang_combo.setCurrentIndex(i)
                break
        
        ext_format = self.settings.value("load_extension", "txt")
        
        if ext_format == "cap":
            self.radio_cap.setChecked(True)
        elif ext_format == "txt":
            self.radio_txt.setChecked(True)
        else:
            self.radio_custom.setChecked(True)
            self.custom_ext_input.setText(ext_format)
        
        self._on_ext_changed()
        
        max_history = int(self.settings.value("max_history", "256"))
        self.history_spin.setValue(max_history)
    
    def _on_apply(self):
        """Apply settings without closing dialog"""
        self._save_settings()
        QMessageBox.information(self, "Success", "Settings saved successfully!")
    
    def _on_ok(self):
        """Apply settings and close"""
        self._save_settings()
        self.accept()
        
    def _save_settings(self):
        """Save settings to QSettings"""
        lang_code = self.lang_combo.currentData()
        self.settings.setValue("language", lang_code)

        if self.main_window and hasattr(self.main_window, 'switch_language'):
            self.main_window.switch_language(lang_code)

        old_ext = self.settings.value("load_extension", "txt")

        if self.radio_txt.isChecked():
            ext = "txt"
        elif self.radio_cap.isChecked():
            ext = "cap"
        else:
            ext = self.custom_ext_input.text().strip()
            if not ext:
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    "Please enter a custom extension or select another format."
                )
                return
            ext = ext.lstrip('.')

        self.settings.setValue("load_extension", ext)

        if old_ext != ext:
            QMessageBox.information(
                self,
                "Restart Required",
                "The Load Extension setting has been changed.\n\n"
                "Please restart the application for the change to take effect."
            )

        self.settings.setValue("max_history", self.history_spin.value())

    def _on_clear_history(self):
        """Clear all undo/redo history"""
        confirm = QMessageBox.question(
            self,
            "Clear History?",
            "Are you sure you want to clear all undo/redo history?\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            if self.main_window and hasattr(self.main_window, 'history'):
                self.main_window.history.clear()
                self.main_window._undo_folders.clear()
                self.main_window._redo_folders.clear()
                QMessageBox.information(self, "Success", "History cleared!")
            else:
                QMessageBox.warning(self, "Error", "Could not clear history")