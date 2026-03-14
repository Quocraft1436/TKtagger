from __future__ import annotations
import json, re
from itertools import product
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTreeWidget, QTreeWidgetItem,
    QFrame, QSplitter, QFileDialog, QMessageBox,
    QGroupBox, QFormLayout, QCheckBox, QScrollArea,
    QSizePolicy, QToolButton, QApplication,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor

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
class DictTagsWidget(QWidget):
    data_changed = Signal(dict, list)

    def __init__(self, json_data: dict | None = None, order: list | None = None,
                 current_path: str = "", parent=None):
        super().__init__(parent)
        self.json_data: dict   = json_data or {}
        self.order: list[str]  = order or []
        self.current_path: str = current_path
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
        self.btn_add_tag.clicked.connect(self._add_tag)
        tl.addWidget(self.btn_add_tag)
        left_v.addWidget(self._gb_tag)

        # Remove
        self._gb_rm = QGroupBox()
        rl = QVBoxLayout(self._gb_rm)
        self.lbl_selected = QLabel()
        rl.addWidget(self.lbl_selected)
        self.btn_remove = QPushButton()
        self.btn_remove.clicked.connect(self._remove_selected)
        rl.addWidget(self.btn_remove)
        left_v.addWidget(self._gb_rm)
        left_v.addStretch()

        # ── Right Panel ───────────────────────────────────────────────────────
        right_w = QWidget()
        right_v = QVBoxLayout(right_w)

        sh = QHBoxLayout()
        self.inp_search = QLineEdit()
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
        self.btn_save     = QPushButton()
        self.btn_expand.clicked.connect(self.tree.expandAll)
        self.btn_collapse.clicked.connect(self.tree.collapseAll)
        self.btn_save.clicked.connect(self._save_json)
        brow.addWidget(self.btn_expand)
        brow.addWidget(self.btn_collapse)
        brow.addStretch()
        brow.addWidget(self.btn_save)
        right_v.addLayout(brow)

        splitter.addWidget(left_w)
        splitter.addWidget(right_w)
        splitter.setSizes([300, 700])

    # ── i18n ──────────────────────────────────────────────────────────────────
    def retranslate_ui(self):
        # GroupBox titles
        self._gb_grp.setTitle(tr("dict_gb_add_group"))
        self._gb_tag.setTitle(tr("dict_gb_add_tag"))
        self._gb_rm.setTitle(tr("dict_gb_remove"))

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
        self.btn_add_group.setText(tr("dict_btn_add_group"))
        self.btn_add_tag.setText(tr("dict_btn_add_tag"))
        self.btn_remove.setText(tr("dict_btn_remove"))
        self.btn_expand.setText(tr("dict_btn_expand"))
        self.btn_collapse.setText(tr("dict_btn_collapse"))
        self.btn_save.setText(tr("dict_btn_save_json"))

        # Tree headers
        self.tree.setHeaderLabels([
            tr("dict_tree_col_name"),
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
            group_item = QTreeWidgetItem([f"{emoji} {gname}", hidden_mark, str(len(tag_items))])
            group_item.setData(0, Qt.UserRole, ("group", gname))
            if hidden:
                group_item.setForeground(0, Qt.darkCyan)

            for tag, tdata in visible_tags:
                is_v = engine.is_virtual(tag)
                desc = tdata.get("description", "") if isinstance(tdata, dict) else ""
                display = f"{'⚡' if is_v else '🏷'} {tag}" + (f" — {desc[:40]}" if desc else "")
                tag_item = QTreeWidgetItem([display, "", ""])
                tag_item.setData(0, Qt.UserRole, ("tag", gname, tag))
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
                tr("dict_confirm_title"),
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