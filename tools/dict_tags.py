"""
dict_tags.py - Dictionary tag manager widget for editing tag groups and tags in a JSON structure.
Provides UI for adding/removing groups and tags, marking groups as hidden, and saving to JSON.
"""
from __future__ import annotations
import json, re
from itertools import product

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTreeWidget, QTreeWidgetItem,
    QFrame, QSplitter, QFileDialog, QMessageBox,
    QGroupBox, QFormLayout, QCheckBox
)

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from i18n import tr

def _divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setFrameShadow(QFrame.Sunken)
    return f

# ─────────────────────────────────────────────────────────────────────────────
class VirtualTagEngine:
    """Phân tích và sinh virtual tags theo cú pháp ${Param}_base_word"""

    PARAM_RE = re.compile(r'\$\{([^}]+)\}')
    OLD_RE   = re.compile(r'\[([^\]]+)\]')

    def __init__(self, json_data: dict):
        self.json_data = json_data
        self._param_values: dict[str, list[str]] = {}
        self._build_param_values()

    def _build_param_values(self):
        for gname, gdata in self.json_data.items():
            if not isinstance(gdata, dict): continue
            tags_raw = gdata.get("Tags", gdata.get("tags", {}))
            if gdata.get("Hidden", False) or gname.endswith("_para"):
                if isinstance(tags_raw, dict):
                    self._param_values[gname] = list(tags_raw.keys())
                elif isinstance(tags_raw, list):
                    self._param_values[gname] = tags_raw

    def is_virtual(self, tag: str) -> bool:
        return bool(self.PARAM_RE.search(tag) or self.OLD_RE.search(tag))

    def expand(self, tag: str, group_name: str) -> list[str]:
        params_new = self.PARAM_RE.findall(tag)
        params_old = self.OLD_RE.findall(tag)
        params = params_new or params_old

        if not params:
            return [tag.lower().strip()]

        pattern = tag
        for p in params_new: pattern = pattern.replace(f"${{{p}}}", "__PARAM__", 1)
        for p in params_old: pattern = pattern.replace(f"[{p}]", "__PARAM__", 1)

        param_vals = [self._param_values.get(p, [p]) for p in params]
        results = []
        for combo in product(*param_vals):
            result = pattern
            for val in combo:
                result = result.replace("__PARAM__", val, 1)
            results.append(result.lower().strip())
        return results

    def build_tag_map(self) -> dict[str, str]:
        tag_map: dict[str, str] = {}
        for gname, gdata in self.json_data.items():
            if not isinstance(gdata, dict): continue
            tags_raw = gdata.get("Tags", gdata.get("tags", {}))
            tag_keys = list(tags_raw.keys()) if isinstance(tags_raw, dict) else (tags_raw if isinstance(tags_raw, list) else [])
            for tag in tag_keys:
                if self.is_virtual(tag):
                    for expanded in self.expand(tag, gname):
                        tag_map[expanded] = gname
                else:
                    tag_map[tag.lower().strip()] = gname
        return tag_map

# ─────────────────────────────────────────────────────────────────────────────
class ImportNewTagsDialog(QWidget):
    """
    Cửa sổ import tag mới chưa có trong dict.
    Hiển thị từng tag, cho chọn nhóm, bấm Process để thêm tất cả.
    """
    import_done = Signal()   # emit sau khi apply xong

    def __init__(self, unknown_tags: list[str], json_data: dict, order: list[str], parent=None):
        super().__init__(parent, Qt.Window)
        self._unknown_tags = list(unknown_tags)   # copy, không mutate ngoài
        self._json_data    = json_data
        self._order        = order
        self._assignments: dict[str, str] = {}    # tag → group name
        self._build_ui()
        self.setWindowTitle(tr("import_new_tags_title"))
        self.resize(640, 520)

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)

        # Header info
        self._lbl_count = QLabel()
        self._lbl_count.setWordWrap(True)
        root.addWidget(self._lbl_count)

        root.addWidget(_divider())

        # Scroll area chứa bảng tag ↔ group
        from PySide6.QtWidgets import QScrollArea, QGridLayout
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self._grid = QGridLayout(container)
        self._grid.setContentsMargins(8, 8, 8, 8)
        self._grid.setSpacing(6)
        scroll.setWidget(container)
        root.addWidget(scroll, stretch=1)

        self._build_rows()

        root.addWidget(_divider())

        # Bottom bar
        bot = QHBoxLayout()
        self._lbl_hint = QLabel()
        self._lbl_hint.setWordWrap(True)
        self._lbl_hint.setStyleSheet("color: #888; font-size: 11px;")
        bot.addWidget(self._lbl_hint, stretch=1)

        self.btn_skip_all  = QPushButton()
        self.btn_skip_all.clicked.connect(self._skip_all)
        self.btn_process   = QPushButton()
        self.btn_process.setStyleSheet("background:#4CAF50; color:white; font-weight:bold; padding:6px 16px;")
        self.btn_process.clicked.connect(self._process)
        bot.addWidget(self.btn_skip_all)
        bot.addWidget(self.btn_process)
        root.addLayout(bot)

        self._retranslate()

    def _group_names(self) -> list[str]:
        """Trả về list tên nhóm theo order, bỏ BREAK."""
        return [g for g in self._order if g != "BREAK" and g in self._json_data]

    def _build_rows(self):
        # Header row
        from PySide6.QtWidgets import QGridLayout
        hdr_tag   = QLabel(tr("import_col_tag"))
        hdr_group = QLabel(tr("import_col_group"))
        hdr_skip  = QLabel(tr("import_col_skip"))
        for lbl in (hdr_tag, hdr_group, hdr_skip):
            lbl.setStyleSheet("font-weight:bold;")
        self._grid.addWidget(hdr_tag,   0, 0)
        self._grid.addWidget(hdr_group, 0, 1)
        self._grid.addWidget(hdr_skip,  0, 2)

        self._combos:    list[QComboBox]  = []
        self._skips:     list[QCheckBox]  = []

        groups = self._group_names()

        for i, tag in enumerate(self._unknown_tags):
            row = i + 1

            lbl = QLabel(tag)
            lbl.setStyleSheet("font-family: monospace;")
            self._grid.addWidget(lbl, row, 0)

            cmb = QComboBox()
            cmb.addItems(groups)
            self._grid.addWidget(cmb, row, 1)
            self._combos.append(cmb)

            chk = QCheckBox()
            chk.setToolTip(tr("import_skip_tooltip"))
            # khi tick skip → disable combo
            idx = i  # capture
            chk.stateChanged.connect(lambda state, c=cmb: c.setEnabled(state != Qt.Checked.value and state != Qt.Checked))
            self._grid.addWidget(chk, row, 2)
            self._skips.append(chk)

    # ── Actions ───────────────────────────────────────────────────────────────
    def _skip_all(self):
        for chk in self._skips:
            chk.setChecked(True)

    def _process(self):
        added = 0
        for i, tag in enumerate(self._unknown_tags):
            if self._skips[i].isChecked():
                continue
            gname = self._combos[i].currentText()
            if not gname or gname not in self._json_data:
                continue
            tags_raw = self._json_data[gname].get("Tags", self._json_data[gname].get("tags", {}))
            if tag not in tags_raw:
                if isinstance(tags_raw, dict):
                    tags_raw[tag] = {}
                else:
                    tags_raw.append(tag)
                added += 1

        QMessageBox.information(
            self,
            tr("import_done_title"),
            tr("import_done_msg", count=added),
        )
        self.import_done.emit()
        self.close()

    def _retranslate(self):
        self.setWindowTitle(tr("import_new_tags_title"))
        n = len(self._unknown_tags)
        self._lbl_count.setText(tr("import_count_msg", count=n))
        self._lbl_hint.setText(tr("import_hint"))
        self.btn_skip_all.setText(tr("import_btn_skip_all"))
        self.btn_process.setText(tr("import_btn_process"))


# ─────────────────────────────────────────────────────────────────────────────
class DictTagsWidget(QWidget):
    data_changed = Signal(dict, list)

    def __init__(self, json_data: dict | None = None, order: list | None = None,
                 current_path: str = "", parent=None):
        super().__init__(parent)
        self.json_data: dict   = json_data or {}
        self.order: list[str]  = order or []
        self.current_path: str = current_path
        self._unknown_tags: list[str] = []        # tags chưa có trong dict
        self._import_dialog: ImportNewTagsDialog | None = None
        self._build_ui()
        self._refresh_all()
        self._update_title()
        self.retranslate_ui()

    def load_data(self, json_data: dict, order: list[str], current_path: str = ""):
        self.json_data    = json_data
        self.order        = order[:]
        if current_path:
            self.current_path = current_path
        self._refresh_all()
        self._update_title()

    def get_data(self) -> tuple[dict, list]:
        return self.json_data, self.order[:]

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)

        # ── Left Panel ────────────────────────────────────────────────────────
        left_w = QWidget()
        left_v = QVBoxLayout(left_w)

        # Add Group
        self._gb_grp = QGroupBox()
        gl = QVBoxLayout(self._gb_grp)
        fl = QFormLayout()
        self.inp_group_name  = QLineEdit()
        self.inp_group_emoji = QLineEdit()
        self.chk_hidden      = QCheckBox()
        self._lbl_group_name  = QLabel()
        self._lbl_group_emoji = QLabel()
        fl.addRow(self._lbl_group_name,  self.inp_group_name)
        fl.addRow(self._lbl_group_emoji, self.inp_group_emoji)
        fl.addRow("", self.chk_hidden)
        gl.addLayout(fl)

        self._hint_hidden = QLabel()
        self._hint_hidden.setObjectName("hint")
        self._hint_hidden.setWordWrap(True)
        gl.addWidget(self._hint_hidden)

        self.btn_add_group = QPushButton()
        self.btn_add_group.setIcon(QIcon.fromTheme("list-add"))
        self.btn_add_group.clicked.connect(self._add_group)
        gl.addWidget(self.btn_add_group)
        left_v.addWidget(self._gb_grp)

        # Add Tag
        self._gb_tag = QGroupBox()
        tl = QVBoxLayout(self._gb_tag)
        fl2 = QFormLayout()
        self.cmb_group    = QComboBox()
        self.inp_tag_name = QLineEdit()
        self.inp_tag_desc = QLineEdit()
        self._lbl_tag_group = QLabel()
        self._lbl_tag_name  = QLabel()
        self._lbl_tag_desc  = QLabel()
        fl2.addRow(self._lbl_tag_group, self.cmb_group)
        fl2.addRow(self._lbl_tag_name,  self.inp_tag_name)
        fl2.addRow(self._lbl_tag_desc,  self.inp_tag_desc)
        tl.addLayout(fl2)

        self._hint_virtual = QLabel()
        self._hint_virtual.setObjectName("hint")
        self._hint_virtual.setWordWrap(True)
        tl.addWidget(self._hint_virtual)

        self.btn_add_tag = QPushButton()
        self.btn_add_tag.setIcon(QIcon.fromTheme("list-add"))
        self.btn_add_tag.clicked.connect(self._add_tag)
        tl.addWidget(self.btn_add_tag)
        left_v.addWidget(self._gb_tag)

        # Remove
        self._gb_rm = QGroupBox()
        rl = QVBoxLayout(self._gb_rm)
        self.lbl_selected = QLabel()
        rl.addWidget(self.lbl_selected)
        self.btn_remove = QPushButton()
        self.btn_remove.setIcon(QIcon.fromTheme("list-remove"))
        self.btn_remove.clicked.connect(self._remove_selected)
        rl.addWidget(self.btn_remove)
        left_v.addWidget(self._gb_rm)
        left_v.addStretch()

        # ── Right Panel ───────────────────────────────────────────────────────
        right_w = QWidget()
        right_v = QVBoxLayout(right_w)

        sh = QHBoxLayout()
        self.inp_search = QLineEdit()
        self.inp_search.addAction(QIcon.fromTheme("edit-find"), QLineEdit.ActionPosition.LeadingPosition)
        self.inp_search.setClearButtonEnabled(True)
        self.inp_search.textChanged.connect(self._filter_tree)
        sh.addWidget(self.inp_search)

        self.cmb_filter_group = QComboBox()
        self.cmb_filter_group.currentIndexChanged.connect(self._filter_tree)
        sh.addWidget(self.cmb_filter_group)
        right_v.addLayout(sh)

        self.tree = QTreeWidget()
        self.tree.itemSelectionChanged.connect(self._on_tree_selection)
        right_v.addWidget(self.tree)

        brow = QHBoxLayout()
        self.btn_expand   = QPushButton()
        self.btn_collapse = QPushButton()
        self.btn_import_new = QPushButton()
        self.btn_import_new.setIcon(QIcon.fromTheme("list-add"))
        self.btn_import_new.setEnabled(False)   # gray out cho đến khi có unknown tags
        self.btn_import_new.clicked.connect(self._open_import_dialog)
        self.btn_export_new = QPushButton()
        self.btn_export_new.setIcon(QIcon.fromTheme("document-save-as"))
        self.btn_export_new.setEnabled(False)   # gray out cho đến khi có unknown tags
        self.btn_export_new.clicked.connect(self._export_unknown_tags)
        self.btn_save     = QPushButton()
        
        self.btn_expand.clicked.connect(self.tree.expandAll)
        self.btn_collapse.clicked.connect(self.tree.collapseAll)
        self.btn_save.clicked.connect(self._save_json)

        self.btn_expand.setIcon(QIcon.fromTheme("view-expand"))
        self.btn_collapse.setIcon(QIcon.fromTheme("view-collapse"))
        self.btn_save.setIcon(QIcon.fromTheme("document-save"))
        
        brow.addWidget(self.btn_expand)
        brow.addWidget(self.btn_collapse)
        brow.addStretch()
        brow.addWidget(self.btn_import_new)
        brow.addWidget(self.btn_export_new)
        brow.addWidget(self.btn_save)
        right_v.addLayout(brow)

        splitter.addWidget(left_w)
        splitter.addWidget(right_w)
        splitter.setSizes([300, 700])

    # ── i18n ──────────────────────────────────────────────────────────────────
    def retranslate_ui(self):
        # GroupBox titles
        self._gb_grp.setTitle(tr("ldl_add_group"))
        self._gb_tag.setTitle(tr("ldl_add_tag"))
        self._gb_rm.setTitle(tr("ldl_remove_tag"))

        # Form labels
        self._lbl_group_name.setText(tr("dict_lbl_name"))
        self._lbl_group_emoji.setText(tr("dict_lbl_emoji"))
        self.chk_hidden.setText(tr("dict_chk_hidden"))
        self._lbl_tag_group.setText(tr("dict_lbl_group"))
        self._lbl_tag_name.setText(tr("dict_lbl_tag"))
        self._lbl_tag_desc.setText(tr("dict_lbl_desc"))

        # Placeholders
        self.inp_group_name.setPlaceholderText(tr("dict_ph_group_name"))
        self.inp_group_emoji.setPlaceholderText(tr("dict_ph_group_emoji"))
        self.inp_tag_name.setPlaceholderText(tr("dict_ph_tag_name"))
        self.inp_tag_desc.setPlaceholderText(tr("dict_ph_tag_desc"))

        # Hints
        self._hint_hidden.setText(tr("dict_hint_hidden"))
        self._hint_virtual.setText(tr("dict_hint_virtual"))

        # Buttons
        self.btn_add_group.setText(tr("ldl_add_group"))
        self.btn_add_tag.setText(tr("ldl_add_tag"))
        self.btn_remove.setText(tr("ldl_remove_tag"))
        self.btn_expand.setText(tr("dict_btn_expand"))
        self.btn_collapse.setText(tr("dict_btn_collapse"))
        self.btn_import_new.setText(tr("dict_btn_import_new"))
        self.btn_export_new.setText(tr("dict_btn_export_new"))
        self.btn_save.setText(tr("ldl_save"))

        # Tree headers
        self.tree.setHeaderLabels([
            tr("dict_tree_col_name"),
            tr("dict_tree_desc"),
            tr("dict_tree_col_hidden"),
            tr("dict_tree_col_count"),
        ])

        # Search
        self.inp_search.setPlaceholderText(tr("dict_search_placeholder"))

        # Filter combo "All groups" item
        if self.cmb_filter_group.count() > 0:
            self.cmb_filter_group.setItemText(0, tr("dict_filter_all_groups"))

        # Selected label default
        items = self.tree.selectedItems()
        if not items:
            self.lbl_selected.setText(tr("dict_nothing_selected"))

        self._update_title()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _update_title(self):
        if self.current_path:
            import os
            name = os.path.basename(self.current_path)
            self.setWindowTitle(f"🗂 {tr('dict_manager')} — {name}  [{self.current_path}]")
        else:
            self.setWindowTitle(f"🗂 {tr('dict_manager')} — {tr('dict_unsaved')}")

    def _autosave(self):
        if not self.current_path:
            return
        save_data = {"order": self.order, **self.json_data}
        with open(self.current_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        self.data_changed.emit(self.json_data, self.order)

    def _refresh_all(self):
        self._refresh_combo()
        self._refresh_filter_combo()
        self._refresh_tree()

    def _refresh_combo(self):
        self.cmb_group.clear()
        for gname in self.order:
            if gname != "BREAK" and gname in self.json_data:
                self.cmb_group.addItem(gname)

    def _refresh_filter_combo(self):
        cur = self.cmb_filter_group.currentText()
        self.cmb_filter_group.blockSignals(True)
        self.cmb_filter_group.clear()
        self.cmb_filter_group.addItem(tr("dict_filter_all_groups"))
        for gname in self.order:
            if gname != "BREAK" and gname in self.json_data:
                self.cmb_filter_group.addItem(gname)
        idx = self.cmb_filter_group.findText(cur)
        self.cmb_filter_group.setCurrentIndex(max(0, idx))
        self.cmb_filter_group.blockSignals(False)

    def _refresh_tree(self, filter_text: str = "", filter_group: str = ""):
        self.tree.clear()
        all_groups_label = tr("dict_filter_all_groups")
        if not filter_group:
            filter_group = all_groups_label

        engine = VirtualTagEngine(self.json_data)
        for gname in self.order:
            if gname == "BREAK" or gname not in self.json_data: continue
            if filter_group != all_groups_label and gname != filter_group: continue

            gdata    = self.json_data[gname]
            hidden   = gdata.get("Hidden", False)
            emoji    = gdata.get("emoji") or ("🙈" if hidden else "📁")
            tags_raw = gdata.get("Tags", gdata.get("tags", {}))
            tag_items = list(tags_raw.items()) if isinstance(tags_raw, dict) else [(t, {}) for t in tags_raw]

            visible_tags = [(t, d) for t, d in tag_items if not filter_text or filter_text.lower() in t.lower()]
            if filter_text and not visible_tags: continue

            hidden_mark = "●" if hidden else ""
            group_item = QTreeWidgetItem([f"{emoji} {gname}", "", hidden_mark, str(len(tag_items))])
            group_item.setData(0, Qt.UserRole, ("group", gname))
            if hidden:
                group_item.setForeground(0, Qt.darkCyan)

            for tag, tdata in visible_tags:
                is_v = engine.is_virtual(tag)
                desc = tdata.get("description", "") if isinstance(tdata, dict) else ""

                display = f"{'⚡' if is_v else '🏷'} {tag}"
                tag_item = QTreeWidgetItem([display, desc, "", ""])
                tag_item.setData(0, Qt.UserRole, ("tag", gname, tag))
                tag_item.setData(0, Qt.UserRole + 1, desc)

                if is_v:
                    tag_item.setForeground(0, Qt.blue)
                group_item.addChild(tag_item)

            self.tree.addTopLevelItem(group_item)
            if filter_text:
                group_item.setExpanded(True)

    def _filter_tree(self):
        self._refresh_tree(self.inp_search.text().strip(), self.cmb_filter_group.currentText())

    def _on_tree_selection(self):
        items = self.tree.selectedItems()
        if not items:
            self.lbl_selected.setText(tr("dict_nothing_selected"))
            return
        data = items[0].data(0, Qt.UserRole)
        if data[0] == "group":
            self.lbl_selected.setText(tr("dict_selected_group", group=data[1]))
        else:
            self.lbl_selected.setText(tr("dict_selected_tag", tag=data[2], group=data[1]))

    def _add_group(self):
        name = self.inp_group_name.text().strip()
        if not name or name in self.json_data:
            return
        self.json_data[name] = {
            "emoji":  self.inp_group_emoji.text().strip() or None,
            "Hidden": self.chk_hidden.isChecked(),
            "Tags":   {},
        }
        self.order.append(name)
        self.inp_group_name.clear()
        self.inp_group_emoji.clear()
        self.chk_hidden.setChecked(False)
        self._refresh_all()
        self._autosave()

    def _add_tag(self):
        gname = self.cmb_group.currentText()
        tag   = self.inp_tag_name.text().strip()
        if not gname or not tag:
            return
        tags = self.json_data[gname].get("Tags", self.json_data[gname].get("tags", {}))
        if tag in tags:
            return
        entry = {"description": self.inp_tag_desc.text().strip()} if self.inp_tag_desc.text().strip() else {}
        if isinstance(tags, dict):
            tags[tag] = entry
        else:
            tags.append(tag)
        self.inp_tag_name.clear()
        self.inp_tag_desc.clear()
        self._refresh_tree()
        self._autosave()

    def _remove_selected(self):
        items = self.tree.selectedItems()
        if not items:
            return
        data = items[0].data(0, Qt.UserRole)
        if data[0] == "group":
            if QMessageBox.question(
                self,
                tr("ldl_comfirm"),
                tr("dict_confirm_remove_group", group=data[1]),
            ) == QMessageBox.Yes:
                del self.json_data[data[1]]
                if data[1] in self.order:
                    self.order.remove(data[1])
                self._refresh_all()
                self._autosave()
        else:
            tags = self.json_data[data[1]].get("Tags", self.json_data[data[1]].get("tags", {}))
            if data[2] in tags:
                if isinstance(tags, dict):
                    del tags[data[2]]
                else:
                    tags.remove(data[2])
                self._refresh_tree()
                self._autosave()

    def set_unknown_tags(self, tags: list[str]):
        """
        Nhận list tag chưa có trong dict (do main_window tính).
        Enable/disable nút import/export tương ứng.
        """
        self._unknown_tags = [t for t in tags if t]
        has_new = bool(self._unknown_tags)
        self.btn_import_new.setEnabled(has_new)
        self.btn_export_new.setEnabled(has_new)
        tooltip = (
            tr("import_btn_tooltip_count", count=len(self._unknown_tags))
            if has_new
            else tr("import_btn_tooltip_none")
        )
        self.btn_import_new.setToolTip(tooltip)
        self.btn_export_new.setToolTip(
            tr("export_btn_tooltip_count", count=len(self._unknown_tags))
            if has_new
            else tr("export_btn_tooltip_none")
        )

    def _open_import_dialog(self):
        if not self._unknown_tags:
            return
        # Đóng dialog cũ nếu còn mở
        if self._import_dialog and self._import_dialog.isVisible():
            self._import_dialog.raise_()
            self._import_dialog.activateWindow()
            return

        self._import_dialog = ImportNewTagsDialog(
            unknown_tags=self._unknown_tags,
            json_data=self.json_data,
            order=self.order,
            parent=self,
        )
        self._import_dialog.import_done.connect(self._on_import_done)
        self._import_dialog.show()
        self._import_dialog.raise_()

    def _on_import_done(self):
        """Sau khi import xong: autosave, refresh tree, xóa danh sách unknown."""
        self._autosave()
        self._refresh_all()
        self.set_unknown_tags([])   # clear → gray out nút

    def _export_unknown_tags(self):
        """Xuất danh sách tag mới chưa có trong dict (đã sắp xếp) ra file JSON."""
        if not self._unknown_tags:
            return

        sorted_tags = sorted(set(self._unknown_tags), key=str.lower)

        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("dict_dialog_export_new"),
            "new_tags.json",
            "JSON (*.json)",
        )
        if not path:
            return

        export_data = {
            "count": len(sorted_tags),
            "tags": sorted_tags,
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        except OSError as exc:
            QMessageBox.warning(self, tr("dict_export_fail_title"), tr("dict_export_fail_msg", error=str(exc)))
            return

        QMessageBox.information(
            self, tr("dict_export_ok_title"),
            tr("dict_export_ok_msg", count=len(sorted_tags), path=path),
        )

    def _save_json(self):
        if self.current_path:
            self._autosave()
            QMessageBox.information(self, tr("dict_save_ok_title"), tr("dict_save_ok_msg", path=self.current_path))
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("dict_dialog_save"),
            "bookdict.json",
            "JSON (*.json)",
        )
        if not path:
            return
        self.current_path = path
        self._autosave()
        self._update_title()
        QMessageBox.information(self, tr("dict_save_ok_title"), tr("dict_save_ok_msg", path=path))