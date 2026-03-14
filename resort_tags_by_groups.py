"""
resort_tags_by_groups.py
Widget sắp xếp thứ tự tag groups theo dict, với:
  - Random preview lấy trực tiếp từ file .txt trong current_folder (kèm tên file)
  - Process folder: sắp xếp current_folder (có checkbox "Global" = root_folder đệ quy)
  - Callback process_fn(folder, order, json_data) do MainWindow truyền vào
"""
from __future__ import annotations
import os, random
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QFrame, QSplitter,
    QMessageBox, QAbstractItemView, QCheckBox, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from i18n import tr


# ── HELPERS ──────────────────────────────────────────────────────────────────
def _section(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    font = QFont(); font.setBold(True)
    lbl.setFont(font)
    return lbl

def _divider() -> QFrame:
    f = QFrame(); f.setFrameShape(QFrame.HLine); f.setFrameShadow(QFrame.Sunken)
    return f


# ── MAIN WIDGET ──────────────────────────────────────────────────────────────
class ResortTagsWidget(QDialog):
    """
    Sắp xếp thứ tự tag groups.

    Params:
        json_data        dict bookdict
        order            thứ tự groups
        current_folder   folder đang xem trong main window (để random preview & process)
        root_folder      folder gốc (cho Global sort)
        process_fn       callable(folder_or_root, order, json_data, global_mode)
                         được gọi khi nhấn Process Folder
    """
    order_changed = Signal(list)

    def __init__(self, json_data=None, order=None, current_folder=None, 
                 root_folder=None, process_fn=None, parent=None):
        super().__init__(parent)
        self.json_data:      dict      = json_data or {}
        self.order:          list[str] = order or []
        self.current_folder: str       = current_folder or ""
        self.root_folder:    str       = root_folder or ""
        self._process_fn               = process_fn   # callable hoặc None
        self._build_ui()
        self._refresh_list()
        self.retranslate_ui()
        self.setWindowModality(Qt.ApplicationModal)

    # ── Public API ───────────────────────────────────────────────────────────
    def load_data(self, json_data: dict, order: list[str]):
        self.json_data = json_data
        self.order     = order[:]
        self._refresh_list()

    def set_folders(self, current_folder: str, root_folder: str):
        self.current_folder = current_folder or ""
        self.root_folder    = root_folder    or ""

    def get_order(self) -> list[str]:
        return self.order[:]

    # ── Build UI ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)

        # ── LEFT: list + buttons ──────────────────────────────────────────
        left = QWidget()
        lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 5, 0)
        self._left_section = _section("")
        lv.addWidget(self._left_section)
        lv.addWidget(_divider())

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)
        lv.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.btn_up   = QPushButton()
        self.btn_down = QPushButton()
        self.btn_brk  = QPushButton()
        self.btn_dbrk = QPushButton()
        for b in [self.btn_up, self.btn_down, self.btn_brk, self.btn_dbrk]:
            btn_row.addWidget(b)
        lv.addLayout(btn_row)

        self.btn_up.clicked.connect(lambda: self._move("up"))
        self.btn_down.clicked.connect(lambda: self._move("down"))
        self.btn_brk.clicked.connect(self._add_break)
        self.btn_dbrk.clicked.connect(self._del_break)

        splitter.addWidget(left)

        # ── RIGHT: preview ────────────────────────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right); rv.setContentsMargins(5, 0, 0, 0)
        self._right_section = _section("")
        rv.addWidget(self._right_section)
        rv.addWidget(_divider())

        self.preview_box = QTextEdit()
        self.preview_box.setReadOnly(True)
        rv.addWidget(self.preview_box)

        # file source label
        self._src_lbl = QLabel()
        self._src_lbl.setObjectName("hint")
        rv.addWidget(self._src_lbl)

        # bottom row: random | global checkbox | process
        prow = QHBoxLayout()
        self.btn_prev = QPushButton()
        self.btn_prev.clicked.connect(self.random_preview)

        self._chk_global = QCheckBox()
        self._chk_global.setToolTip(tr("resort_global_tooltip"))

        self.btn_run = QPushButton()
        self.btn_run.setStyleSheet("background:#4CAF50; color:white; font-weight:bold; padding:4px 12px;")
        self.btn_run.clicked.connect(self._on_run)

        prow.addWidget(self.btn_prev)
        prow.addWidget(self._chk_global)
        prow.addStretch()
        prow.addWidget(self.btn_run)
        rv.addLayout(prow)

        splitter.addWidget(right)
        splitter.setSizes([380, 620])

    # ── i18n ─────────────────────────────────────────────────────────────────
    def retranslate_ui(self):
        self._left_section.setText(tr("resort_group_order_section").upper())
        self._right_section.setText(tr("resort_preview_section").upper())
        self.preview_box.setPlaceholderText(tr("resort_preview_placeholder"))
        self._src_lbl.setText(tr("resort_no_random_yet"))
        self.btn_up.setText(tr("resort_btn_up"))
        self.btn_down.setText(tr("resort_btn_down"))
        self.btn_brk.setText(tr("resort_btn_add_break"))
        self.btn_dbrk.setText(tr("resort_btn_del_break"))
        self.btn_prev.setText(tr("resort_btn_random_file"))
        self._chk_global.setText(tr("resort_global_cb"))
        self._chk_global.setToolTip(tr("resort_global_tooltip"))
        self.btn_run.setText(tr("resort_btn_process"))

    # ── List helpers ─────────────────────────────────────────────────────────
    def _refresh_list(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for item_name in self.order:
            li = QListWidgetItem()
            if item_name == "BREAK":
                li.setText("──────── BREAK ────────")
                font = QFont(); font.setBold(True)
                li.setFont(font)
                li.setTextAlignment(Qt.AlignCenter)
                li.setForeground(Qt.darkGray)
            else:
                gdata     = self.json_data.get(item_name, {})
                emoji     = gdata.get("emoji", "")
                hidden    = gdata.get("Hidden", False)
                tag_count = len(gdata.get("Tags", gdata.get("tags", {})))
                status    = f" ({tr('resort_hidden_label')})" if hidden else ""
                icon      = emoji if emoji else ("🙈" if hidden else "•")
                li.setText(f"{icon} {item_name}  [{tag_count}]{status}")
            li.setData(Qt.UserRole, item_name)
            self.list_widget.addItem(li)
        self.list_widget.blockSignals(False)

    def _sync_order_from_list(self):
        self.order = [self.list_widget.item(i).data(Qt.UserRole)
                      for i in range(self.list_widget.count())]
        self.order_changed.emit(self.order)

    def _on_rows_moved(self, *_):
        self._sync_order_from_list()

    def _move(self, direction: str):
        row = self.list_widget.currentRow()
        if row < 0: return
        if direction == "up"   and row == 0: return
        if direction == "down" and row >= self.list_widget.count() - 1: return
        delta = -1 if direction == "up" else 1
        self.order[row], self.order[row + delta] = self.order[row + delta], self.order[row]
        self._refresh_list()
        self.list_widget.setCurrentRow(row + delta)
        self.order_changed.emit(self.order)

    def _add_break(self):
        row = self.list_widget.currentRow()
        ins = row + 1 if row >= 0 else len(self.order)
        self.order.insert(ins, "BREAK")
        self._refresh_list()
        self.list_widget.setCurrentRow(ins)
        self.order_changed.emit(self.order)

    def _del_break(self):
        row = self.list_widget.currentRow()
        if row < 0: return
        if self.order[row] != "BREAK":
            QMessageBox.warning(self, tr("resort_err_title"), tr("resort_err_not_break"))
            return
        del self.order[row]
        self._refresh_list()
        self.order_changed.emit(self.order)

    # ── Random preview ───────────────────────────────────────────────────────
    def random_preview(self):
        folder = self.current_folder
        if not folder or not os.path.isdir(folder):
            self.preview_box.setPlainText(tr("resort_warn_no_folder"))
            self._src_lbl.setText(tr("resort_no_folder_label"))
            return

        txt_files = [f for f in os.listdir(folder) if f.lower().endswith(".txt")]
        if not txt_files:
            self.preview_box.setPlainText(tr("resort_warn_no_txt"))
            self._src_lbl.setText(tr("resort_no_txt_label"))
            return

        chosen_file = random.choice(txt_files)
        fpath = os.path.join(folder, chosen_file)
        try:
            raw = open(fpath, encoding="utf-8").read().strip()
        except Exception as e:
            self.preview_box.setPlainText(tr("resort_read_error", error=e))
            return

        file_tags = [t.strip() for t in raw.replace("\n", ",").split(",") if t.strip()]
        if not file_tags:
            self.preview_box.setPlainText(tr("resort_empty_file"))
            self._src_lbl.setText(f"📄 {chosen_file}")
            return

        resorted = self._resort_tags(file_tags)
        self.preview_box.setPlainText(resorted)
        self._src_lbl.setText(tr("resort_src_label", filename=chosen_file, count=len(file_tags)))

    def _resort_tags(self, tags: list[str]) -> str:
        from dict_tags import VirtualTagEngine
        engine  = VirtualTagEngine(self.json_data)
        tag_map = engine.build_tag_map()
        tags_lc = {t.lower(): t for t in tags}

        group_buckets: dict[str, list[str]] = {}
        leftover = list(tags)

        for group_name in self.order:
            if group_name == "BREAK":
                continue
            gdata    = self.json_data.get(group_name, {})
            tags_raw = gdata.get("Tags", gdata.get("tags", {}))
            g_keys   = set(tags_raw.keys() if isinstance(tags_raw, dict) else tags_raw)
            expanded = {t for t, g in tag_map.items() if g == group_name}
            all_keys = g_keys | expanded

            matched = []
            for orig in list(leftover):
                if orig.lower() in all_keys or orig in all_keys:
                    matched.append(orig)
                    leftover.remove(orig)
            if matched:
                group_buckets[group_name] = matched

        lines, cur = [], []
        for item in self.order:
            if item == "BREAK":
                if cur:
                    lines.append(", ".join(cur))
                    cur = []
                lines.append("")
            else:
                cur.extend(group_buckets.get(item, []))

        if cur:
            lines.append(", ".join(cur))
        if leftover:
            lines.append(", ".join(leftover) + f"  ← ({tr('resort_ungrouped_suffix')})")

        return ",\n".join(l for l in lines if l != "")

    # ── Process folder ───────────────────────────────────────────────────────
    def _on_run(self):
        global_mode = self._chk_global.isChecked()
        target = self.root_folder if global_mode and self.root_folder else self.current_folder
        if not target:
            QMessageBox.warning(self, tr("resort_no_folder_title"), tr("resort_no_folder_open_msg"))
            return

        scope_txt = (tr("resort_scope_root", target=target) if global_mode
                     else tr("resort_scope_current", target=target))
        if QMessageBox.question(
            self, tr("resort_confirm_title"),
            tr("resort_confirm_msg", scope=scope_txt),
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return

        if self._process_fn:
            self._process_fn(target, self.order, self.json_data, global_mode)
        else:
            self._process_folder_internal(target, global_mode)

    def _process_folder_internal(self, target: str, global_mode: bool):
        from dict_tags import VirtualTagEngine
        engine  = VirtualTagEngine(self.json_data)
        tag_map = engine.build_tag_map()

        def collect_txts(folder):
            if global_mode:
                for root, _, files in os.walk(folder):
                    for f in files:
                        if f.lower().endswith(".txt"):
                            yield os.path.join(root, f)
            else:
                for f in os.listdir(folder):
                    if f.lower().endswith(".txt"):
                        yield os.path.join(folder, f)

        count = 0
        errors = []
        for fpath in collect_txts(target):
            try:
                raw   = open(fpath, encoding="utf-8").read().strip()
                tags  = [t.strip() for t in raw.replace("\n", ",").split(",") if t.strip()]
                if not tags:
                    continue
                group_buckets: dict[str, list] = {}
                leftover = list(tags)
                for gname in self.order:
                    if gname == "BREAK": continue
                    gdata    = self.json_data.get(gname, {})
                    tags_raw = gdata.get("Tags", gdata.get("tags", {}))
                    g_keys   = set(tags_raw.keys() if isinstance(tags_raw, dict) else tags_raw)
                    expanded = {t for t, g in tag_map.items() if g == gname}
                    matched  = [t for t in leftover if t.lower() in (g_keys | expanded) or t in (g_keys | expanded)]
                    for t in matched: leftover.remove(t)
                    if matched: group_buckets[gname] = matched

                out_parts, cur = [], []
                for item in self.order:
                    if item == "BREAK":
                        if cur: out_parts.append(", ".join(cur)); cur = []
                    else:
                        cur.extend(group_buckets.get(item, []))
                if cur: out_parts.append(", ".join(cur))
                if leftover: out_parts[-1] += ", " + ", ".join(leftover) if out_parts else (out_parts.append(", ".join(leftover)) or "")

                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(",\n".join(out_parts))
                count += 1
            except Exception as e:
                errors.append(f"{os.path.basename(fpath)}: {e}")

        msg = tr("resort_process_done", count=count)
        if errors:
            msg += "\n" + tr("resort_process_errors", count=len(errors), errors="\n".join(errors[:5]))
        QMessageBox.information(self, tr("resort_done_title"), msg)