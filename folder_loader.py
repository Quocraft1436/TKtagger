"""Read image metadata and lazy tree branches without blocking the Qt thread."""
import os
from PySide6.QtCore import QObject, Signal, Slot, QRunnable, QThreadPool, Qt
from backup_manager import BACKUP_DIR
from file_ops import load_folder_images


def child_directories(path):
    with os.scandir(path) as entries:
        return sorted(entry.path for entry in entries
                      if entry.name != BACKUP_DIR and entry.is_dir(follow_symlinks=False))


class _Signals(QObject):
    done = Signal(object)


class _Read(QRunnable):
    def __init__(self, token, path, extension):
        super().__init__()
        self.token, self.path, self.extension = token, path, extension
        self.signals = _Signals()

    def run(self):
        try:
            payload = dict(token=self.token, path=self.path,
                           images=load_folder_images(self.path, extension=self.extension)
                           if self.extension is not None else None,
                           children=child_directories(self.path), error='')
        except Exception as exc:
            payload = dict(token=self.token, path=self.path, error=str(exc))
        try:
            self.signals.done.emit(payload)
        except RuntimeError:
            pass  # The window/application was destroyed during this read.


class FolderLoader(QObject):
    loaded = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._next = 0
        self._tasks = {}
        self.pool = QThreadPool.globalInstance()

    def request(self, path, extension=None):
        self._next += 1
        task = _Read(self._next, path, extension)
        task.signals.done.connect(self._finished, Qt.QueuedConnection)
        self._tasks[self._next] = task
        self.pool.start(task)
        return self._next

    @Slot(object)
    def _finished(self, payload):
        self._tasks.pop(payload['token'], None)
        self.loaded.emit(payload)
