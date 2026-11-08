"""Undo/redo stores tag deltas, rather than two complete dataset snapshots."""
from dataclasses import dataclass


@dataclass
class HistoryEntry:
    action: str
    images_before: dict
    images_after: dict


class HistoryManager:
    def __init__(self, max_history=100):
        self._undo_stack = []
        self._redo_stack = []
        self.max_history = max(1, max_history)
        self._callbacks = []
        self.last_changes = {}

    def add_callback(self, cb):
        self._callbacks.append(cb)

    def _notify(self):
        for cb in self._callbacks:
            cb()

    def snapshot_tags(self, images, indices=None):
        """Capture candidates only; whole-dataset tools can omit indices."""
        return {idx: tuple(images[idx]['tags'])
                for idx in (range(len(images)) if indices is None else indices)}

    def push(self, action, before_snapshot, images):
        if not isinstance(before_snapshot, dict):
            before_snapshot = dict(enumerate(before_snapshot))
        before, after = {}, {}
        for idx, tags in before_snapshot.items():
            current = tuple(images[idx]['tags'])
            if tuple(tags) != current:
                before[idx] = tuple(tags)
                after[idx] = current
        self.last_changes = {idx: (before[idx], after[idx]) for idx in before}
        if not before:
            return False
        self._undo_stack.append(HistoryEntry(action, before, after))
        if len(self._undo_stack) > self.max_history:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._notify()
        return True

    def _apply(self, images, source, target, redo=False):
        if not source:
            self.last_changes = {}
            return None
        entry = source.pop()
        target.append(entry)
        tags_by_idx = entry.images_after if redo else entry.images_before
        self.last_changes = {}
        for idx, tags in tags_by_idx.items():
            old = tuple(images[idx]['tags'])
            images[idx]['tags'] = list(tags)
            images[idx]['modified'] = True
            self.last_changes[idx] = (old, tags)
        self._notify()
        return entry.action

    def undo(self, images):
        return self._apply(images, self._undo_stack, self._redo_stack)

    def redo(self, images):
        return self._apply(images, self._redo_stack, self._undo_stack, redo=True)

    def can_undo(self):
        return bool(self._undo_stack)

    def can_redo(self):
        return bool(self._redo_stack)

    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.last_changes = {}
        self._notify()

    def get_undo_list(self):
        return [entry.action for entry in self._undo_stack]

    def get_redo_list(self):
        return [entry.action for entry in reversed(self._redo_stack)]
