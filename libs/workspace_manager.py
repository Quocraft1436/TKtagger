"""Save UI layouts and editing preferences without dataset or history state."""
import base64
import json
from pathlib import Path

from PySide6.QtCore import QObject, QEvent, QTimer, QByteArray, QSaveFile, QIODevice
from PySide6.QtGui import QGuiApplication

from libs.i18n import tr
from libs.settings_manager import settings


class WorkspaceManager(QObject):
    VERSION = 1
    MAX_FILE_BYTES = 2 * 1024 * 1024

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self._restoring = False
        self._closed = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._autosave)
        self.defaults = self.capture()
        self.defaults['preferences'] = dict(grid_mode='classic', card_height='medium',
                                            columns=3, tag_insert_order=0)
        window.installEventFilter(self)
        for dock in (window._folder_dock, window._tag_dock, window._preview_dock, window.history_dock):
            dock.installEventFilter(self)
            dock.dockLocationChanged.connect(self.schedule_save)
            dock.topLevelChanged.connect(self.schedule_save)
            dock.visibilityChanged.connect(self.schedule_save)
        window.col_spin.valueChanged.connect(self.schedule_save)
        window._order_tag_combo.currentIndexChanged.connect(self.schedule_save)
        window.image_grid.columns_changed.connect(self.schedule_save)
        saved = settings.value('workspace/snapshot', '')
        if saved:
            try:
                self.apply(json.loads(saved))
            except (ValueError, TypeError):
                # An unreadable saved workspace must not prevent startup.
                window.statusBar().showMessage(tr('workspace_invalid'))

    @property
    def autosave_enabled(self):
        return settings.value('workspace/autosave', False, type=bool)

    def set_autosave(self, enabled):
        settings.set_value('workspace/autosave', bool(enabled))
        self.timer.stop()
        if enabled:
            self.schedule_save()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Move, QEvent.Resize, QEvent.Show, QEvent.Hide):
            self.schedule_save()
        return super().eventFilter(watched, event)

    def schedule_save(self, *_):
        if (self.autosave_enabled and not self._restoring and not self._closed
                and self.window.isVisible()):
            self.timer.start()

    def _autosave(self):
        if self.autosave_enabled and not self._restoring and not self._closed and self.window.isVisible():
            self.save()

    def finish_close(self):
        self.timer.stop()
        if self.autosave_enabled:
            self.save()
        self._closed = True

    @staticmethod
    def _encode(value):
        return base64.b64encode(bytes(value)).decode('ascii')

    def capture(self):
        window = self.window
        return dict(format='TKtagger.workspace', version=self.VERSION,
                    geometry=self._encode(window.saveGeometry()),
                    docks=self._encode(window.saveState(self.VERSION)),
                    preferences=dict(grid_mode=window.image_grid.layout_mode,
                                     card_height=window.image_grid.card_height_mode,
                                     columns=window.image_grid._manual_cols,
                                     tag_insert_order=window._order_tag_combo.currentIndex()))

    @classmethod
    def validate(cls, data):
        try:
            if (not isinstance(data, dict) or data.get('format') != 'TKtagger.workspace'
                    or type(data.get('version')) is not int or data['version'] != cls.VERSION):
                raise ValueError
            for key in ('geometry', 'docks'):
                value = data[key]
                if not isinstance(value, str) or len(value) > cls.MAX_FILE_BYTES:
                    raise ValueError
                if not base64.b64decode(value, validate=True):
                    raise ValueError
            prefs = data['preferences']
            if (prefs['grid_mode'] not in ('classic', 'adaptive')
                    or prefs['card_height'] not in ('medium', 'tall', 'full')
                    or type(prefs['columns']) is not int or not 1 <= prefs['columns'] <= 8
                    or type(prefs['tag_insert_order']) is not int or prefs['tag_insert_order'] not in (0, 1)):
                raise ValueError
            return {key: data[key] for key in ('format', 'version', 'geometry', 'docks', 'preferences')}
        except (KeyError, TypeError, ValueError):
            raise ValueError(tr('workspace_invalid')) from None

    def _restore(self, data):
        window = self.window
        geometry = QByteArray(base64.b64decode(data['geometry']))
        docks = QByteArray(base64.b64decode(data['docks']))
        if not window.restoreGeometry(geometry) or not window.restoreState(docks, self.VERSION):
            raise ValueError(tr('workspace_invalid'))
        prefs = data['preferences']
        window.image_grid.set_columns(prefs['columns'])
        window.apply_grid_layout(prefs['grid_mode'])
        window.image_grid.set_card_height_mode(prefs['card_height'])
        window._sync_grid_columns(window.image_grid._cols)
        window._order_tag_combo.setCurrentIndex(prefs['tag_insert_order'])
        # Floating docks from a disconnected monitor must remain reachable.
        for dock in (window._folder_dock, window._tag_dock, window._preview_dock, window.history_dock):
            if dock.isFloating() and not QGuiApplication.screenAt(dock.frameGeometry().center()):
                screen = window.screen() or QGuiApplication.primaryScreen()
                if screen:
                    dock.move(screen.availableGeometry().topLeft())

    def apply(self, data):
        data = self.validate(data)
        previous = self.capture()
        self.timer.stop()
        self._restoring = True
        try:
            try:
                self._restore(data)
            except ValueError:
                self._restore(previous)
                raise
            settings.set_value('grid_layout_mode', data['preferences']['grid_mode'])
            settings.set_value('grid_card_height', data['preferences']['card_height'])
        finally:
            self._restoring = False

    def save(self):
        self.timer.stop()
        settings.set_value('workspace/snapshot', json.dumps(self.capture(), ensure_ascii=False))

    def reset(self):
        self.apply(self.defaults)
        self.save()

    def export_file(self, path):
        data = json.dumps(self.capture(), ensure_ascii=False, indent=2).encode('utf-8')
        output = QSaveFile(str(path))
        if not output.open(QIODevice.WriteOnly):
            raise OSError(output.errorString())
        if output.write(data) != len(data):
            error = output.errorString()
            output.cancelWriting()
            raise OSError(error)
        if not output.commit():
            raise OSError(output.errorString())

    def import_file(self, path):
        path = Path(path)
        if path.stat().st_size > self.MAX_FILE_BYTES:
            raise ValueError(tr('workspace_invalid'))
        self.apply(json.loads(path.read_text(encoding='utf-8')))
        self.save()
