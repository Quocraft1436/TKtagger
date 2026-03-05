"""
history_manager.py - Quản lý lịch sử thao tác (Undo/Redo)
"""
import copy
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class HistoryEntry:
    action: str          # Mô tả hành động
    images_before: Any   # Snapshot tags trước khi thay đổi
    images_after: Any    # Snapshot tags sau khi thay đổi


class HistoryManager:
    def __init__(self, max_history: int = 100):
        self._undo_stack: List[HistoryEntry] = []
        self._redo_stack: List[HistoryEntry] = []
        self.max_history = max_history
        self._callbacks = []  # Callbacks khi history thay đổi

    def add_callback(self, cb):
        self._callbacks.append(cb)

    def _notify(self):
        for cb in self._callbacks:
            cb()

    def snapshot_tags(self, images: list) -> list:
        """Tạo snapshot danh sách tags của tất cả ảnh."""
        return [list(img['tags']) for img in images]

    def push(self, action: str, before_snapshot: list, images: list):
        """Lưu trạng thái mới vào lịch sử."""
        after_snapshot = self.snapshot_tags(images)
        entry = HistoryEntry(
            action=action,
            images_before=before_snapshot,
            images_after=after_snapshot,
        )
        self._undo_stack.append(entry)
        if len(self._undo_stack) > self.max_history:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._notify()

    def undo(self, images: list) -> Optional[str]:
        """Hoàn tác thao tác cuối. Trả về tên action hoặc None."""
        if not self._undo_stack:
            return None
        entry = self._undo_stack.pop()
        self._redo_stack.append(entry)
        for img, tags in zip(images, entry.images_before):
            img['tags'] = list(tags)
            img['modified'] = True
        self._notify()
        return entry.action

    def redo(self, images: list) -> Optional[str]:
        """Làm lại thao tác. Trả về tên action hoặc None."""
        if not self._redo_stack:
            return None
        entry = self._redo_stack.pop()
        self._undo_stack.append(entry)
        for img, tags in zip(images, entry.images_after):
            img['tags'] = list(tags)
            img['modified'] = True
        self._notify()
        return entry.action

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify()

    def get_undo_list(self) -> List[str]:
        return [e.action for e in reversed(self._undo_stack)]

    def get_redo_list(self) -> List[str]:
        return [e.action for e in reversed(self._redo_stack)]
