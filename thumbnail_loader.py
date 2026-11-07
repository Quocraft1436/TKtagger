"""Bounded asynchronous thumbnail decoding; QPixmap creation stays on the UI thread."""
from collections import OrderedDict

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot, QSize, Qt
from PySide6.QtGui import QImageReader


class _Signals(QObject):
    finished = Signal(object, object)


class _Decode(QRunnable):
    def __init__(self, key):
        super().__init__()
        self.key = key
        self.signals = _Signals()

    def run(self):
        from PySide6.QtGui import QImage
        image = QImage()
        try:
            path, width = self.key
            if not path:
                self.signals.finished.emit(self.key, image)
                return
            reader = QImageReader(path)
            reader.setAutoTransform(True)
            size = reader.size()
            if size.isValid():
                reader.setScaledSize(size.scaled(QSize(width, width), Qt.KeepAspectRatio))
            image = reader.read()
            # Some image plugins ignore scaledSize.
            if not image.isNull() and (image.width() > width or image.height() > width):
                image = image.scaled(width, width, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception:
            pass
        try:
            self.signals.finished.emit(self.key, image)
        except RuntimeError:
            pass  # The grid/application was destroyed during decoding.


class ThumbnailLoader(QObject):
    ready = Signal(object, object)

    def __init__(self, parent=None, max_bytes=64 * 1024 * 1024, workers=2):
        super().__init__(parent)
        self.max_bytes = max_bytes
        self.workers = workers
        self.cache = OrderedDict()
        self.cache_bytes = 0
        self.wanted = set()
        self.delivered = set()
        self.active = {}
        self.decode_count = 0
        self.cache_hits = 0
        self.pool = QThreadPool.globalInstance()

    def set_visible(self, keys):
        self.wanted = set(keys)
        self.delivered.intersection_update(self.wanted)
        for key in keys:
            if key in self.cache:
                self.cache.move_to_end(key)
                self.cache_hits += 1
                self.delivered.add(key)
                self.ready.emit(key, self.cache[key])
        self._start_next()

    def _start_next(self):
        for key in self.wanted:
            if len(self.active) >= self.workers:
                break
            if key in self.cache or key in self.active or key in self.delivered:
                continue
            task = _Decode(key)
            task.signals.finished.connect(self._finished, Qt.QueuedConnection)
            self.active[key] = task
            self.decode_count += 1
            self.pool.start(task)

    @Slot(object, object)
    def _finished(self, key, image):
        self.active.pop(key, None)
        size = image.sizeInBytes()
        if size <= self.max_bytes:
            self.cache[key] = image
            self.cache_bytes += size
            while self.cache and self.cache_bytes > self.max_bytes:
                _, removed = self.cache.popitem(last=False)
                self.cache_bytes -= removed.sizeInBytes()
        # Don't retain a huge failure cache (null images have zero size).
        while len(self.cache) > 4096:
            _, removed = self.cache.popitem(last=False)
            self.cache_bytes -= removed.sizeInBytes()
        if key in self.wanted:
            self.delivered.add(key)
            self.ready.emit(key, image)
        self._start_next()
