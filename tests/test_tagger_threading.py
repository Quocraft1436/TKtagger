"""Exercise the real worker thread and Qt queued delivery without AI packages."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
import threading
import time
import types
import unittest
from unittest.mock import Mock, patch

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow
from main_window import MainWindow


class TaggerThreadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def run_worker(self, mode, fail, unopened=False):
        class TestWindow(MainWindow):
            def __init__(self):
                QMainWindow.__init__(self)
        win = TestWindow()
        self.addCleanup(win.deleteLater)
        gui_thread = threading.get_ident()
        ui_calls = []
        messages = []
        worker_threads = []
        backend_finished = threading.Event()
        merged = []

        def record_ui(*args):
            ui_calls.append(threading.get_ident())

        def status(message):
            record_ui()
            messages.append(message)

        def merge(results):
            record_ui()
            merged.append(results)

        win.current_folder = '/other' if unopened else '/example'
        win._folder_cache = {}
        win.statusBar = Mock(return_value=Mock(showMessage=status))
        win._act_waifu = Mock(setEnabled=record_ui)
        win._merge_tagging_results = merge
        win._connect_tagging_signals()
        result = [dict(path='/example/image.png', tags=['tag'])]

        def backend(config, progress):
            worker_threads.append(threading.get_ident())
            progress(1, 2, 'worker progress')
            backend_finished.set()
            if fail:
                raise RuntimeError('worker failure')
            return result

        metadata_threads = []
        metadata = [dict(path='/example/image.png', tags=['original'])]
        def read_metadata(folder, extension):
            metadata_threads.append(threading.get_ident())
            return metadata

        module = types.ModuleType('tools.tagger_logic')
        module.run_tagger = backend
        with patch.dict(sys.modules, {'tools.tagger_logic': module}), \
             patch('tools.external_tagger.run_external_tagger', side_effect=backend), \
             patch('main_window.load_folder_images', side_effect=read_metadata), \
             patch('main_window.QMessageBox.critical', side_effect=record_ui) as error:
            win._on_tagging_started({'mode': mode})
            self.assertTrue(backend_finished.wait(timeout=3))
            # No Qt event processing yet: worker progress must remain queued.
            self.assertNotIn('[1/2] worker progress', messages)
            self.assertEqual(merged, [])
            deadline = time.monotonic() + 3
            while win._tagging_running and time.monotonic() < deadline:
                QTest.qWait(10)
            self.assertFalse(win._tagging_running)
            self.assertIn('[1/2] worker progress', messages)
            self.assertEqual(bool(error.call_count), fail)
        self.assertEqual(len(worker_threads), 1)
        self.assertNotEqual(worker_threads[0], gui_thread)
        self.assertTrue(ui_calls)
        self.assertTrue(all(thread == gui_thread for thread in ui_calls))
        self.assertEqual(merged, [] if fail else [result])
        if unopened and not fail:
            self.assertEqual(metadata_threads, worker_threads)
            self.assertIs(result[0]['_folder_images'], metadata)

    def test_progress_and_completion_are_delivered_on_gui_thread(self):
        for mode in ('local', 'external'):
            with self.subTest(mode=mode):
                self.run_worker(mode, fail=False)

    def test_progress_and_failure_are_delivered_on_gui_thread(self):
        for mode in ('local', 'external'):
            with self.subTest(mode=mode):
                self.run_worker(mode, fail=True)

    def test_unopened_folder_metadata_is_prepared_on_worker(self):
        self.run_worker('external', fail=False, unopened=True)
