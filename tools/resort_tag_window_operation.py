import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QCheckBox, QScrollArea, QWidget, QRadioButton, QButtonGroup, QFrame,
    QMessageBox, QStackedWidget, QComboBox, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from i18n import tr
from pathlib import Path
from libs.draggable_list import DraggableListManager
from tools.dict_tags import VirtualTagEngine
from table_icon import get_icon, get_icon_size

class ResortTagsDialog(QDialog):
    def __init__(self, all_tags: list, dict_data, dict_path=None, parent=None):
        super().__init__(parent)
        self.all_tags = all_tags
        self.dict_data = dict_data
        self.dict_order = parent._dict_order if parent else []
        self.parent_win = parent
        self.dict_path = dict_path or getattr(parent, "dict_path", getattr(parent, "_dict_path", "default_dict"))
        self.setup_ui()
        self.check_requirements()

    def setup_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 10, 14, 10)
        
        self._header = QHBoxLayout()
        self._operation_mode_lbl = QLabel(tr("sort_operation_mode_label"))
        self._header.addWidget(self._operation_mode_lbl)
        
        self.radio_mode1 = QRadioButton(tr("sort_simple_title"))
        self.radio_mode2 = QRadioButton(tr("sort_by_dictary_title"))
        self.radio_mode1.setChecked(True)
        self._header.addWidget(self.radio_mode1)
        self._header.addWidget(self.radio_mode2)
        self._layout.addLayout(self._header)

        self.stack = QStackedWidget()
        self.mode1_ui = ResortTagsSimple(self.all_tags)
        self.mode2_ui = ResortTagsGroups(self.dict_data, self.dict_order, self.dict_path)

        self.stack.addWidget(self.mode1_ui)
        self.stack.addWidget(self.mode2_ui)
        
        self._layout.addWidget(self.stack)

        self.radio_mode1.toggled.connect(self.display_mode)
        self.radio_mode2.toggled.connect(self.display_mode)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._cancel_btn = QPushButton(tr("ldl_cancel"))
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)
        
        self._process_btn = QPushButton(tr("ldl_process"))
        self._process_btn.setStyleSheet("font-weight: bold; background: #4CAF50; color: white;")
        self._process_btn.clicked.connect(self.handle_confirm)
        btn_layout.addWidget(self._process_btn)

        self._layout.addLayout(btn_layout)

    def display_mode(self):
        if self.radio_mode1.isChecked():
            self.stack.setCurrentWidget(self.mode1_ui)
        else:
            self.stack.setCurrentWidget(self.mode2_ui)

    def check_requirements(self):
        if not self.dict_data and not self.dict_order:
            self.radio_mode2.setEnabled(False)
            self.radio_mode2.setToolTip("Cần nạp file JSON Dictionary để dùng chế độ này!")
            print("Warning, Dict data is not loaded!")

    def handle_confirm(self):
        current_mode_ui = self.stack.currentWidget()
        
        success, message = current_mode_ui.execute_logic(self.parent_win)
        
        if success:
            QMessageBox.information(self, tr("done"), message)
            self.accept()
        else:
            QMessageBox.warning(self, tr("error"), message)

def run_operation_sort_tag(win):
    if not win.images:
        QMessageBox.information(win, tr("ldl_no_images"), tr("notify_no_image_msg"))
        return False

    if not win.all_folder_tags:
        QMessageBox.information(win, tr("ldl_no_tags"), tr("notify_no_tags_msg"))
        return False

    dict_path = getattr(win, "dict_path", getattr(win, "_dict_path", "default_dict"))
    dlg = ResortTagsDialog(all_tags=win.all_folder_tags, dict_data=win._dict_data, dict_path=dict_path, parent=win)
    dlg.exec()

# ----------- Simple Ordering -----------------------
class ResortTagsSimple(QWidget):
    def __init__(self, all_tags: list):
        super().__init__()

        self.all_tags = all_tags
        self._check_boxes = {}
        self._row_widgets = {}
        self.setup_ui()
        self.retranslate_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)

        self._header_lbl = QLabel()
        self._header_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.layout.addWidget(self._header_lbl)

        self.search_edit = QLineEdit()
        self.search_edit.addAction(QIcon.fromTheme("edit-find"), QLineEdit.ActionPosition.LeadingPosition)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter)
        self.layout.addWidget(self.search_edit)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(1)
        self.content_layout.addStretch()
        scroll.setWidget(self.content_widget)
        self.layout.addWidget(scroll, stretch=1)

        for tag in self.all_tags:
            cb = QCheckBox(tag)
            self._check_boxes[tag] = cb
            self.content_layout.insertWidget(self.content_layout.count() - 1, cb)
            self._row_widgets[tag] = cb

        pos_frame = QFrame()
        pos_layout = QHBoxLayout(pos_frame)

        self._pos_lbl = QLabel()
        pos_layout.addWidget(self._pos_lbl)

        self._pos_group = QButtonGroup(self)
        self._rb_begin = QRadioButton()
        self._rb_end = QRadioButton()
        self._rb_begin.setChecked(True)
        self._pos_group.addButton(self._rb_begin)
        self._pos_group.addButton(self._rb_end)
        pos_layout.addWidget(self._rb_begin)
        pos_layout.addWidget(self._rb_end)

        pos_layout.addStretch()

        self._deselect_btn = QPushButton()
        self._deselect_btn.clicked.connect(self._deselect_all)
        pos_layout.addWidget(self._deselect_btn)

        self.layout.addWidget(pos_frame)

    def retranslate_ui(self):
        self._header_lbl.setText(tr("sort_dialog_header"))
        self.search_edit.setPlaceholderText(tr("sort_search_placeholder"))
        self._pos_lbl.setText(tr("sort_position_label"))
        self._rb_begin.setText(tr("sort_pos_begin"))
        self._rb_end.setText(tr("sort_pos_end"))
        self._deselect_btn.setText(tr("ldl_deselect_all"))

    def _filter(self, text: str):
        text = text.lower().strip()
        for tag, widget in self._row_widgets.items():
            widget.setVisible(not text or text in tag.lower())

    def _deselect_all(self):
        for cb in self._check_boxes.values():
            cb.setChecked(False)

    def get_selected_tags(self) -> list:
        return [tag for tag, cb in self._check_boxes.items() if cb.isChecked()]

    def get_position(self) -> str:
        return "beginning" if self._rb_begin.isChecked() else "ending"
    
    def execute_logic(self, win):
        chosen = self.get_selected_tags()
        if not chosen:
            return False, tr("notify_no_tag_selected")
            
        position = self.get_position()
        chosen_set = set(chosen)
        
        before = win._snapshot()
        affected = 0

        for idx, img in enumerate(win.images):
            present = [t for t in img['tags'] if t in chosen_set]
            if not present:
                continue
                
            remaining = [t for t in img['tags'] if t not in chosen_set]
            
            if position == "beginning":
                img['tags'] = present + remaining
            else:
                img['tags'] = remaining + present
                
            img['modified'] = True
            win.image_grid.refresh_card(idx)
            affected += 1

        win._push_history(tr("history_sort_tags", tags=", ".join(chosen), position=position), before)
        win._reload_tags_panel()
        
        return True, tr("sort_done_msg", count=affected)

# ----------- Dictionary Ordering (Lưu Preset file riêng preset_user.json) -------------------
class ResortTagsGroups(QWidget):
    def __init__(self, json_data=None, dict_order=None, dict_path=None):
        super().__init__()
        self.dict_data = json_data if json_data is not None else {}
        self.dict_order = list(dict_order or [])
        self.order = list(self.dict_order)
        self.dict_path = str(dict_path or "default_dict")

        # Khởi tạo bộ lưu trữ presets từ file riêng preset_user.json theo dict_path
        self.presets = self._load_presets_from_file()

        self.setup_ui()
        self._populate_presets_combo()
        self._refresh_list()
        self.retranslate_ui()

    def _load_presets_from_file(self) -> dict:
        """Đọc danh sách preset từ tệp preset_user.json dựa theo location path của dictionary gốc."""
        preset_file = Path("preset_user.json")
        if preset_file.exists():
            try:
                with open(preset_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if self.dict_path in data and isinstance(data[self.dict_path], dict):
                            return data[self.dict_path]
            except Exception as e:
                print(f"Error loading preset_user.json: {e}")
        return {}

    def _save_presets_to_file(self):
        """Lưu lại danh sách preset vào tệp preset_user.json phân định theo dict_path."""
        preset_file = Path("preset_user.json")
        all_data = {}
        if preset_file.exists():
            try:
                with open(preset_file, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
                    if not isinstance(all_data, dict):
                        all_data = {}
            except Exception:
                all_data = {}

        all_data[self.dict_path] = self.presets
        try:
            with open(preset_file, "w", encoding="utf-8") as f:
                json.dump(all_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving preset_user.json: {e}")

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self._header_lbl = QLabel()
        self._header_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self._header_lbl)

        self.list_manager = DraggableListManager()
        self.list_manager.model().rowsMoved.connect(self._on_rows_moved)
        layout.addWidget(self.list_manager)

        self.btn_add = QPushButton()
        self.btn_add.clicked.connect(self._handle_add)
        self.btn_add.setIcon(get_icon("add"))
        layout.addWidget(self.btn_add)

        # HLayout quản lý Preset ngay dưới nút addline
        preset_layout = QHBoxLayout()
        preset_layout.setContentsMargins(0, 4, 0, 0)

        self.preset_lbl = QLabel()
        preset_layout.addWidget(self.preset_lbl)

        self.combo_presets = QComboBox()
        self.combo_presets.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.combo_presets, stretch=1)

        self.btn_add_preset = QPushButton()
        self.btn_add_preset.setIcon(get_icon("add"))
        self.btn_add_preset.setIconSize(get_icon_size())
        self.btn_add_preset.clicked.connect(self._handle_add_preset)
        preset_layout.addWidget(self.btn_add_preset)

        self.btn_del_preset = QPushButton()
        self.btn_del_preset.setIcon(get_icon("delete"))
        self.btn_del_preset.setIconSize(get_icon_size())
        self.btn_del_preset.clicked.connect(self._handle_del_preset)
        preset_layout.addWidget(self.btn_del_preset)

        layout.addLayout(preset_layout)

    def retranslate_ui(self):
        self._header_lbl.setText(tr("sort_by_dictary_hint"))
        self.btn_add.setText(tr("sort_by_dictary_add_newline"))
        self.preset_lbl.setText(tr("sort_by_dictary_preset_label"))

        self.btn_add_preset.setToolTip(tr("sort_by_dictary_add_preset_tooltip"))
        self.btn_del_preset.setToolTip(tr("sort_by_dictary_del_preset_tooltip"))

    def _populate_presets_combo(self, select_name="default"):
        """Nạp danh sách preset vào ComboBox."""
        self.combo_presets.blockSignals(True)
        self.combo_presets.clear()
        
        # Luôn có preset "default" từ order mặc định của JSON
        self.combo_presets.addItem("default")
        
        # Thêm các preset tùy chỉnh đã lưu
        for p_name in sorted(self.presets.keys()):
            if p_name != "default":
                self.combo_presets.addItem(p_name)

        idx = self.combo_presets.findText(select_name)
        if idx >= 0:
            self.combo_presets.setCurrentIndex(idx)
        else:
            self.combo_presets.setCurrentIndex(0)
            
        self.combo_presets.blockSignals(False)
        self._update_preset_buttons_state()

    def _update_preset_buttons_state(self):
        """Khóa/mở nút xóa tùy theo preset hiện tại."""
        is_default = (self.combo_presets.currentText() == "default")
        self.btn_del_preset.setEnabled(not is_default)

    def _on_preset_changed(self, preset_name: str):
        """Khi chọn preset khác từ ComboBox."""
        if not preset_name:
            return

        if preset_name == "default":
            self.order = list(self.dict_order)
        elif preset_name in self.presets:
            self.order = list(self.presets[preset_name])

        self._update_preset_buttons_state()
        self._refresh_list()

    def _handle_add_preset(self):
        """Tạo preset mới từ thứ tự sắp xếp hiện tại."""
        name, ok = QInputDialog.getText(self, "Thêm Preset Mới", "Nhập tên preset:")
        if ok and name:
            name = name.strip()
            if not name:
                return
            if name.lower() == "default":
                QMessageBox.warning(self, tr("error"), "Không thể tạo hoặc đè lên tên 'default'!")
                return
            
            # Lưu danh sách thứ tự hiện tại vào preset mới và ghi file preset_user.json
            self.presets[name] = list(self.order)
            self._save_presets_to_file()
            self._populate_presets_combo(select_name=name)

    def _handle_del_preset(self):
        """Xóa preset đang chọn (không áp dụng cho 'default')."""
        current = self.combo_presets.currentText()
        if current == "default":
            return
            
        reply = QMessageBox.question(
            self, "Xác nhận xóa", 
            f"Bạn có chắc muốn xóa preset '{current}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if current in self.presets:
                del self.presets[current]
                self._save_presets_to_file()
            self.order = list(self.dict_order)
            self._populate_presets_combo(select_name="default")
            self._refresh_list()

    def _handle_add(self):
        text = "New line"
        self.list_manager.add_custom_item(text, data="BREAK", can_delete=True)
        self._sync_order_from_list()

    def _refresh_list(self):
        self.list_manager.clear()
        
        if not self.order:
            return

        for item_name in self.order:
            if item_name == "BREAK":
                display_text = "New line"
                self.list_manager.add_custom_item(
                    text=display_text, 
                    data="BREAK", 
                    can_delete=True
                )
            else:
                gdata = self.dict_data.get(item_name, {})
                hidden = gdata.get("Hidden", False)
                if hidden:
                    continue
                
                emoji = gdata.get("emoji", "")
                tag_count = len(gdata.get("Tags", gdata.get("tags", {})))
                
                icon = emoji if emoji else "•"
                display_text = f"{icon} {item_name}  [{tag_count}]"
                
                self.list_manager.add_custom_item(
                    text=display_text, 
                    data=item_name, 
                    can_delete=False
                )

    def _sync_order_from_list(self):
        """Cập nhật thứ tự hiển thị và tự động lưu vào preset đang chọn (nếu không phải default)."""
        items_json = self.list_manager.get_all_json()
        self.order = [item["data"] for item in items_json]

        # Tự động lưu thay đổi thứ tự vào preset hiện tại và cập nhật tệp preset_user.json
        cur_preset = self.combo_presets.currentText()
        if cur_preset and cur_preset != "default":
            self.presets[cur_preset] = list(self.order)
            self._save_presets_to_file()

    def _on_rows_moved(self, *_):
        self._sync_order_from_list()

    def execute_logic(self, win):
        engine = VirtualTagEngine(self.dict_data)
        tag_map = engine.build_tag_map()

        before = win._snapshot()

        affected = 0
        errors = []

        for idx, img in enumerate(win.images):
            try:
                tags = list(img.get('tags', []))
                if not tags:
                    continue

                group_buckets: dict[str, list] = {}
                leftover = list(tags)

                for gname in self.order:
                    if gname == "BREAK":
                        continue
                    gdata = self.dict_data.get(gname, {})
                    tags_raw = gdata.get("Tags", gdata.get("tags", {}))
                    g_keys = set(tags_raw.keys() if isinstance(tags_raw, dict) else tags_raw)
                    expanded = {t for t, g in tag_map.items() if g == gname}
                    all_keys = g_keys | expanded

                    matched = [t for t in leftover if t.lower() in all_keys or t in all_keys]
                    for t in matched:
                        leftover.remove(t)
                    if matched:
                        group_buckets[gname] = matched

                new_tags = []
                cur_group = []

                for item in self.order:
                    if item == "BREAK":
                        new_tags.extend(cur_group)
                        cur_group = []
                    else:
                        cur_group.extend(group_buckets.get(item, []))

                new_tags.extend(cur_group)
                new_tags.extend(leftover)

                img['tags'] = new_tags
                img['modified'] = True
                win.image_grid.refresh_card(idx)
                affected += 1

            except Exception as e:
                errors.append(f"[{img.get('name', idx)}]: {e}")

        if errors:
            msg = tr("resort_process_errors", count=len(errors), errors="\n".join(errors[:5]))
            return False, msg

        folder_name = Path(win.current_folder).name if getattr(win, "current_folder", None) else ""
        win._push_history(tr("resort_tags_groups_history", affected=affected, folder=folder_name), before)
        win._reload_tags_panel()

        return True, tr("resort_process_done", count=affected)