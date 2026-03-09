"""
calc_dataset.py - Máy tính số vòng lặp dataset theo tỉ lệ (Dataset Repeat Calculator)
"""
import os
import re
import math
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSpinBox, QMessageBox, QAbstractItemView, QCheckBox, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor


# ─── helpers ──────────────────────────────────────────────────────────────────

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}
TAG_EXTS   = {".txt", ".caption"}


def _count_tagged_images(folder: str) -> int:
    try:
        entries = os.listdir(folder)
    except PermissionError:
        return 0
    stems_with_tag = {os.path.splitext(f)[0] for f in entries
                      if os.path.splitext(f)[1].lower() in TAG_EXTS}
    return sum(1 for f in entries
               if os.path.splitext(f)[1].lower() in IMAGE_EXTS
               and os.path.splitext(f)[0] in stems_with_tag)


def _extract_repeat_from_name(folder_name: str):
    """'10_name' -> (10, 'name'), else (None, folder_name)"""
    m = re.match(r'^(\d+)_(.+)$', folder_name)
    return (int(m.group(1)), m.group(2)) if m else (None, folder_name)


def _scan_folders(root: str) -> list:
    results = []
    root = os.path.normpath(root)
    for dirpath, dirnames, _ in os.walk(root):
        dirnames.sort()
        count = _count_tagged_images(dirpath)
        if count > 0:
            name = os.path.basename(dirpath)
            existing_repeat, base_name = _extract_repeat_from_name(name)
            results.append({
                "path": dirpath,
                "name": name,
                "base_name": base_name,
                "image_count": count,
                "existing_repeat": existing_repeat,
                "rel_path": os.path.relpath(dirpath, root),
            })
    return results


# ─── dialog ───────────────────────────────────────────────────────────────────

class CalcDatasetDialog(QDialog):
    def __init__(self, root_folder: str = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dataset Repeat Calculator")
        self.setMinimumSize(860, 640)
        self.resize(980, 720)
        self.root_folder = root_folder
        self._folders: list = []
        self._results: list = []
        self._build_ui()
        if root_folder:
            self._folder_edit.setText(root_folder)
            self._scan()

    # ── build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(10, 8, 10, 8)

        # ── top bar: folder + all controls inline ──
        top = QHBoxLayout()
        top.setSpacing(6)

        top.addWidget(QLabel("Folder:"))
        self._folder_edit = QLineEdit()
        self._folder_edit.setReadOnly(True)
        self._folder_edit.setPlaceholderText("Select root dataset folder...")
        top.addWidget(self._folder_edit, stretch=1)

        browse_btn = QPushButton("Browse...")
        browse_btn.setFixedWidth(75)
        browse_btn.clicked.connect(self._browse_folder)
        top.addWidget(browse_btn)

        scan_btn = QPushButton("Scan")
        scan_btn.setFixedWidth(65)
        scan_btn.setStyleSheet("background:#2196F3; color:white; font-weight:bold;")
        scan_btn.clicked.connect(self._scan)
        top.addWidget(scan_btn)

        root.addLayout(top)

        # ── folder table header bar ──
        fbar = QHBoxLayout()
        fbar.setSpacing(6)
        self._status_lbl = QLabel("No folder scanned yet.")
        self._status_lbl.setStyleSheet("color:#aaa; font-style:italic;")
        fbar.addWidget(self._status_lbl)
        fbar.addStretch()
        sel_all = QPushButton("All")
        sel_all.setFixedWidth(48)
        sel_all.clicked.connect(self._select_all_folders)
        desel_all = QPushButton("None")
        desel_all.setFixedWidth(50)
        desel_all.clicked.connect(self._deselect_all_folders)
        fbar.addWidget(sel_all)
        fbar.addWidget(desel_all)
        root.addLayout(fbar)

        # ── folder table ──
        self._folder_table = QTableWidget(0, 4)
        self._folder_table.setHorizontalHeaderLabels(
            ["", "Folder (relative path)", "Tagged Images", "Current Repeat"])
        hh = self._folder_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        self._folder_table.setColumnWidth(0, 36)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        self._folder_table.setColumnWidth(2, 110)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        self._folder_table.setColumnWidth(3, 110)
        self._folder_table.setSelectionMode(QAbstractItemView.NoSelection)
        self._folder_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._folder_table.setAlternatingRowColors(True)
        self._folder_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self._folder_table, stretch=2)

        # ── Middle ──
        middle = QHBoxLayout()

        middle.addWidget(QLabel("Ratio:"))
        self._ratio_edit = QLineEdit()
        self._ratio_edit.setPlaceholderText("e.g. 1,1,1.5")
        self._ratio_edit.setFixedWidth(130)
        middle.addWidget(self._ratio_edit)

        middle.addSpacing(8)
        middle.addWidget(QLabel("Batch:"))
        self._batch_spin = QSpinBox()
        self._batch_spin.setRange(1, 512)
        self._batch_spin.setValue(4)
        self._batch_spin.setFixedWidth(60)
        middle.addWidget(self._batch_spin)

        middle.addSpacing(8)
        middle.addWidget(QLabel("Epochs:"))
        self._epoch_spin = QSpinBox()
        self._epoch_spin.setRange(1, 10000)
        self._epoch_spin.setValue(10)
        self._epoch_spin.setFixedWidth(65)
        middle.addWidget(self._epoch_spin)

        middle.addSpacing(8)
        self._ceil_cb = QCheckBox("Ceil steps")
        self._ceil_cb.setChecked(True)
        self._ceil_cb.setToolTip(
            "Checked  -> math.ceil(images / batch) x epochs\n"
            "           Matches accelerate / diffusers trainer behaviour\n"
            "           (runs leftover partial batch at end of epoch)\n\n"
            "Unchecked -> (images // batch) x epochs\n"
            "           Strict floor — drops remainder"
        )
        middle.addWidget(self._ceil_cb)

        middle.addSpacing(8)
        calc_btn = QPushButton("Calculate")
        calc_btn.setStyleSheet("background:#FF9800; color:white; font-weight:bold; padding:4px 14px;")
        calc_btn.clicked.connect(self._calculate)
        middle.addWidget(calc_btn)
        root.addLayout(middle)

        # ── result table header bar ──
        self._result_lbl = QLabel("Results — (not calculated yet)")
        self._result_lbl.setStyleSheet("color:#aaa; font-style:italic;")
        root.addWidget(self._result_lbl)

        # ── result table ──
        self._result_table = QTableWidget(0, 5)
        self._result_table.setHorizontalHeaderLabels(
            ["Folder", "Tagged Images", "Ratio", "Repeats", "Total Images (repeat x count)"])
        rh = self._result_table.horizontalHeader()
        rh.setSectionResizeMode(0, QHeaderView.Stretch)
        for col, w in [(1, 110), (2, 70), (3, 80), (4, 210)]:
            rh.setSectionResizeMode(col, QHeaderView.Fixed)
            self._result_table.setColumnWidth(col, w)
        self._result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._result_table.setAlternatingRowColors(True)
        self._result_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self._result_table, stretch=2)

        # ── summary row ──
        srow = QHBoxLayout()
        self._total_steps_lbl = QLabel("Total steps: -")
        self._total_steps_lbl.setStyleSheet("font-size:14px; font-weight:bold; color:#4CAF50;")
        self._total_images_lbl = QLabel("")
        self._total_images_lbl.setStyleSheet("color:#aaa;")
        srow.addWidget(self._total_steps_lbl)
        srow.addSpacing(24)
        srow.addWidget(self._total_images_lbl)
        srow.addStretch()
        root.addLayout(srow)

        # ── bottom button bar ──
        bot = QHBoxLayout()
        bot.setSpacing(8)
        rename_info = QLabel(
            "Apply: renames each folder  <b>name</b> -> <b>N_name</b>  "
            "(existing numeric prefix is replaced)")
        rename_info.setTextFormat(Qt.RichText)
        rename_info.setStyleSheet("color:#888; font-size:11px;")
        bot.addWidget(rename_info)
        bot.addStretch()

        self._apply_btn = QPushButton("Apply Rename")
        self._apply_btn.setStyleSheet(
            "background:#4CAF50; color:white; font-weight:bold; padding:5px 18px;")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._apply_rename)
        bot.addWidget(self._apply_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        bot.addWidget(cancel_btn)

        root.addLayout(bot)

    # ── scanning ──────────────────────────────────────────────────────────────

    def _browse_folder(self):
        from PySide6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, "Select root dataset folder")
        if folder:
            self.root_folder = folder
            self._folder_edit.setText(folder)
            self._scan()

    def _scan(self):
        root = self._folder_edit.text().strip()
        if not root or not os.path.isdir(root):
            QMessageBox.warning(self, "No Folder", "Please select a valid root folder first.")
            return
        self.root_folder = root
        self._folders = _scan_folders(root)
        self._populate_folder_table()
        self._clear_results()
        self._status_lbl.setText(
            f"Found {len(self._folders)} folder(s) with tagged images")

    def _populate_folder_table(self):
        self._folder_table.setRowCount(0)
        for fd in self._folders:
            row = self._folder_table.rowCount()
            self._folder_table.insertRow(row)

            cb = QCheckBox()
            cb.setChecked(True)
            cb.setStyleSheet("margin-left:10px;")
            self._folder_table.setCellWidget(row, 0, cb)

            def _item(text, align=Qt.AlignVCenter | Qt.AlignLeft):
                it = QTableWidgetItem(text)
                it.setTextAlignment(align)
                it.setFlags(Qt.ItemIsEnabled)
                return it

            self._folder_table.setItem(row, 1, _item(fd["rel_path"]))
            self._folder_table.setItem(row, 2, _item(str(fd["image_count"]), Qt.AlignCenter))
            rep_text = str(fd["existing_repeat"]) if fd["existing_repeat"] is not None else "-"
            self._folder_table.setItem(row, 3, _item(rep_text, Qt.AlignCenter))

    def _select_all_folders(self):
        for row in range(self._folder_table.rowCount()):
            cb = self._folder_table.cellWidget(row, 0)
            if cb:
                cb.setChecked(True)

    def _deselect_all_folders(self):
        for row in range(self._folder_table.rowCount()):
            cb = self._folder_table.cellWidget(row, 0)
            if cb:
                cb.setChecked(False)

    def _get_selected_indices(self):
        return [row for row in range(self._folder_table.rowCount())
                if (cb := self._folder_table.cellWidget(row, 0)) and cb.isChecked()]

    # ── calculation ───────────────────────────────────────────────────────────

    def _parse_ratios(self, text: str, n: int):
        parts = [p.strip() for p in text.split(",") if p.strip()]
        if not parts:
            raise ValueError("Ratio is empty.")
        ratios = []
        for p in parts:
            try:
                ratios.append(float(p))
            except ValueError:
                raise ValueError(f"Invalid ratio value: '{p}'")
        while len(ratios) < n:
            ratios.append(ratios[-1])
        return ratios[:n]

    def _calculate(self):
        sel = self._get_selected_indices()
        if not sel:
            QMessageBox.warning(self, "No Selection", "Please select at least one folder.")
            return

        ratio_text = self._ratio_edit.text().strip()
        if not ratio_text:
            QMessageBox.warning(self, "No Ratio", "Please enter a ratio string.")
            return

        try:
            ratios = self._parse_ratios(ratio_text, len(sel))
        except ValueError as e:
            QMessageBox.critical(self, "Invalid Ratio", str(e))
            return

        batch     = self._batch_spin.value()
        epochs    = self._epoch_spin.value()
        use_ceil  = self._ceil_cb.isChecked()

        min_r   = min(r for r in ratios if r > 0)
        repeats = [max(1, round(r / min_r)) for r in ratios]

        self._results = []
        total_weighted = 0
        for i, idx in enumerate(sel):
            fd  = self._folders[idx]
            rep = repeats[i]
            tot = rep * fd["image_count"]
            total_weighted += tot
            self._results.append({
                "folder_idx": idx,
                "path":        fd["path"],
                "base_name":   fd["base_name"],
                "image_count": fd["image_count"],
                "ratio":       ratios[i],
                "repeat":      rep,
                "total_img":   tot,
            })

        if use_ceil:
            total_steps    = math.ceil(total_weighted / batch) * epochs
            rounding_label = f"ceil({total_weighted}/{batch})"
        else:
            total_steps    = (total_weighted // batch) * epochs
            rounding_label = f"floor({total_weighted}/{batch})"

        # populate result table
        self._result_table.setRowCount(0)
        for r in self._results:
            row = self._result_table.rowCount()
            self._result_table.insertRow(row)
            cells = [
                (self._folders[r["folder_idx"]]["rel_path"], Qt.AlignLeft | Qt.AlignVCenter),
                (str(r["image_count"]),  Qt.AlignCenter),
                (str(r["ratio"]),        Qt.AlignCenter),
                (str(r["repeat"]),       Qt.AlignCenter),
                (f"{r['repeat']} x {r['image_count']} = {r['total_img']}", Qt.AlignCenter),
            ]
            for col, (text, align) in enumerate(cells):
                it = QTableWidgetItem(text)
                it.setTextAlignment(align)
                it.setFlags(Qt.ItemIsEnabled)
                self._result_table.setItem(row, col, it)
            # highlight Repeats cell
            rep_it = self._result_table.item(row, 3)
            rep_it.setBackground(QColor("#1a3d1a"))
            rep_it.setForeground(QColor("#4CAF50"))
            rep_it.setFont(QFont("", -1, QFont.Bold))

        self._result_lbl.setText(
            f"Results - {len(self._results)} folder(s)  |  "
            f"{rounding_label} x {epochs} epochs"
        )
        self._result_lbl.setStyleSheet("color:#ccc;")
        self._total_steps_lbl.setText(f"Total steps: {total_steps:,}")
        self._total_images_lbl.setText(
            f"Weighted images: {total_weighted:,}   "
            f"Batch: {batch}   Epochs: {epochs}"
        )
        self._apply_btn.setEnabled(True)

    def _clear_results(self):
        self._results = []
        self._result_table.setRowCount(0)
        self._total_steps_lbl.setText("Total steps: -")
        self._total_images_lbl.setText("")
        self._result_lbl.setText("Results - (not calculated yet)")
        self._result_lbl.setStyleSheet("color:#aaa; font-style:italic;")
        self._apply_btn.setEnabled(False)

    # ── apply rename ──────────────────────────────────────────────────────────

    def _apply_rename(self):
        if not self._results:
            return

        preview_lines = []
        for r in self._results:
            fd       = self._folders[r["folder_idx"]]
            new_name = f"{r['repeat']}_{r['base_name']}"
            if fd["name"] != new_name:
                preview_lines.append(f"  {fd['name']}  ->  {new_name}")

        if not preview_lines:
            QMessageBox.information(self, "Nothing to rename",
                                    "All folders already have the correct repeat prefix.")
            return

        resp = QMessageBox.question(
            self, "Confirm Rename",
            "The following folders will be renamed:\n\n"
            + "\n".join(preview_lines)
            + "\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp != QMessageBox.Yes:
            return

        errors, renamed = [], 0
        for r in self._results:
            fd       = self._folders[r["folder_idx"]]
            new_name = f"{r['repeat']}_{r['base_name']}"
            new_path = os.path.join(os.path.dirname(fd["path"]), new_name)
            if fd["path"] == new_path:
                continue
            try:
                os.rename(fd["path"], new_path)
                fd.update(path=new_path, name=new_name, existing_repeat=r["repeat"])
                renamed += 1
            except Exception as e:
                errors.append(f"{fd['name']}: {e}")

        self._populate_folder_table()
        msg = f"Renamed {renamed} folder(s) successfully."
        if errors:
            msg += "\n\nErrors:\n" + "\n".join(errors)
        QMessageBox.information(self, "Done", msg)
        self._clear_results()
