"""
resort_tag_window_operation.py - 
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QCheckBox, QScrollArea, QWidget, QRadioButton, QButtonGroup, QFrame,
    QMessageBox, QStackedWidget, QListWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from i18n import tr
from pathlib import Path

class ResortTagsDialog(QDialog):
    def __init__(self, all_tags: list, dict_data, parent=None):
        super().__init__(parent)
        self.all_tags = all_tags
        self.dict_data = dict_data
        self.dict_order = parent._dict_order
        self.parent_win = parent
        self.setup_ui()
        self.check_requirements()
        # self.retranslate_ui()

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
        self.mode2_ui = ResortTagsGroups(self.dict_data, self.dict_order)

        self.stack.addWidget(self.mode1_ui)
        self.stack.addWidget(self.mode2_ui)
        
        self._layout.addWidget(self.stack)

        self.radio_mode1.toggled.connect(self.display_mode)
        self.radio_mode2.toggled.connect(self.display_mode)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._cancel_btn = QPushButton( tr("ldl_cancel") )
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)
        
        self._process_btn = QPushButton( tr("ldl_process") )
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

    dlg = ResortTagsDialog(all_tags=win.all_folder_tags, dict_data=win._dict_data, parent=win)
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

        # Position radios
        pos_frame = QFrame()
        pos_layout = QHBoxLayout(pos_frame)

        # Label Position
        self._pos_lbl = QLabel()
        pos_layout.addWidget(self._pos_lbl)

        # Radio Buttons
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
            # Lọc ra các tag đang có trong ảnh mà nằm trong danh sách chọn
            present = [t for t in img['tags'] if t in chosen_set]
            if not present:
                continue
                
            # Lọc ra các tag còn lại
            remaining = [t for t in img['tags'] if t not in chosen_set]
            
            # Sắp xếp lại: (Chọn + Còn lại) hoặc (Còn lại + Chọn)
            if position == "beginning":
                img['tags'] = present + remaining
            else:
                img['tags'] = remaining + present
                
            img['modified'] = True
            # Cập nhật hiển thị ngay trên lưới ảnh
            win.image_grid.refresh_card(idx)
            affected += 1

        # 4. Lưu lịch sử và cập nhật Panel
        win._push_history(tr("history_sort_tags", tags=", ".join(chosen), position=position), before)
        win._reload_tags_panel()
        
        return True, tr("sort_done_msg", count=affected)

# ----------- Dictionary Ordering -------------------
from libs.draggable_list import DraggableListManager
from tools.dict_tags import VirtualTagEngine

class ResortTagsGroups(QWidget):
    def __init__(self, json_data=None, dict_order=None):
        super().__init__()
        self.dict_data = json_data
        self.order = dict_order
        self.setup_ui()
        self._refresh_list()
        self.retranslate_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self._header_lbl = QLabel()
        self._header_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self._header_lbl)

        self.list_manager = DraggableListManager()
        self.list_manager.model().rowsMoved.connect(self._on_rows_moved)

        self.btn_add = QPushButton()
        self.btn_add.clicked.connect(self._handle_add)

        layout.addWidget(self.list_manager)
        layout.addWidget(self.btn_add)

    def retranslate_ui(self):
        self._header_lbl.setText( tr("sort_by_dictary_hint"))
        self.btn_add.setText( tr("sort_by_dictary_add_newline"))
    
    def _handle_add(self):
        # current_count = self.list_manager.count() + 1
        text = f"New line"
        # data="BREAK" để đồng nhất với logic nhận diện break
        self.list_manager.add_custom_item(text, data="BREAK", can_delete=True)
        self._sync_order_from_list()

    def _refresh_list(self):
        # 1. Clear danh sách cũ
        self.list_manager.clear()
        
        if not self.order:
            return

        for item_name in self.order:
            # Logic xử lý hiển thị tương tự như cũ
            if item_name == "BREAK":
                display_text = "New line"
                # Với DraggableListManager, item này có thể cho phép xóa hoặc không
                self.list_manager.add_custom_item(
                    text=display_text, 
                    data="BREAK", 
                    can_delete=True
                )
            else:
                gdata     = self.dict_data.get(item_name, {})
                hidden    = gdata.get("Hidden", False)
                if hidden:
                    continue
                
                emoji     = gdata.get("emoji", "")
                tag_count = len(gdata.get("Tags", gdata.get("tags", {})))
                
                icon      = emoji if emoji else "•"
                display_text = f"{icon} {item_name}  [{tag_count}]"
                
                # Thêm vào manager, lưu item_name vào data để sau này truy xuất
                self.list_manager.add_custom_item(
                    text=display_text, 
                    data=item_name, 
                    can_delete=False # Thường các tag group gốc không cho xóa tại đây?
                )

    def _sync_order_from_list(self):
        # get_all_json trả về list[dict] có key "data"
        items_json = self.list_manager.get_all_json()
        self.order = [item["data"] for item in items_json]

    def _on_rows_moved(self, *_):
        self._sync_order_from_list()
        print("Thứ tự mới:", self.order)

    def _on_rows_moved(self, *_):
        self._sync_order_from_list()

    def execute_logic(self, win):
        engine = VirtualTagEngine(self.dict_data)
        tag_map = engine.build_tag_map()

        # --- Snapshot trước khi thay đổi ---
        before = win._snapshot()

        affected = 0
        errors = []

        for idx, img in enumerate(win.images):
            try:
                tags = list(img.get('tags', []))
                if not tags:
                    continue

                # --- Phân loại tags vào từng group ---
                group_buckets: dict[str, list] = {}
                leftover = list(tags)

                for gname in self.order:
                    if gname == "BREAK":
                        continue
                    gdata    = self.dict_data.get(gname, {})
                    tags_raw = gdata.get("Tags", gdata.get("tags", {}))
                    g_keys   = set(tags_raw.keys() if isinstance(tags_raw, dict) else tags_raw)
                    expanded = {t for t, g in tag_map.items() if g == gname}
                    all_keys = g_keys | expanded

                    matched  = [t for t in leftover if t.lower() in all_keys or t in all_keys]
                    for t in matched:
                        leftover.remove(t)
                    if matched:
                        group_buckets[gname] = matched

                # --- Xây dựng lại thứ tự tags theo self.order + BREAK ---
                # BREAK ở đây chỉ mang ý nghĩa visual khi xuất file,
                # còn trong win.images ta chỉ lưu flat list tags đã được sort.
                # Nếu muốn giữ BREAK trong tags, thêm sentinel string vào đây.
                new_tags = []
                cur_group = []

                for item in self.order:
                    if item == "BREAK":
                        # Flush group hiện tại rồi tiếp tục (không thêm sentinel)
                        new_tags.extend(cur_group)
                        cur_group = []
                    else:
                        cur_group.extend(group_buckets.get(item, []))

                new_tags.extend(cur_group)   # Flush group cuối
                new_tags.extend(leftover)    # Tags không thuộc group nào → append cuối

                img['tags']     = new_tags
                img['modified'] = True
                # Cập nhật card trên grid nếu win hỗ trợ
                real_idx = win.images.index(img)
                win.image_grid.refresh_card(real_idx)
                affected += 1

            except Exception as e:
                errors.append(f"[{img.get('name', idx)}]: {e}")

        if errors:
            msg = tr("resort_process_errors", count=len(errors), errors="\n".join(errors[:5]))
            return False, msg

        # --- Push history và reload panel ---
        win._push_history(tr("resort_tags_groups_history", affected=affected, folder=Path(self.current_folder).name), before)
        win._reload_tags_panel()

        return True, tr("resort_process_done", count=affected)