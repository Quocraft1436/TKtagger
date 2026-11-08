"""Background metadata reads commit on the GUI thread and preserve failed roots."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QTreeWidget
from libs.folder_loader import FolderLoader
from libs.history_manager import HistoryManager
from main_window import MainWindow


class FolderLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.other = self.root / 'other'
        self.other.mkdir()
        (self.other / 'child').mkdir()
        class Window(MainWindow):
            def __init__(self):
                QMainWindow.__init__(self)
        self.win = Window()
        self.addCleanup(self.win.deleteLater)
        win = self.win
        win.setCentralWidget(QWidget())
        win.dir_tree = QTreeWidget(win)
        win.folder_loader = FolderLoader(win)
        win.folder_loader.loaded.connect(win._on_folder_loaded)
        win.dir_tree.itemExpanded.connect(win._expand_folder_tree)
        win._pending_folder = None
        win._tree_requests = {}
        win._edit_menu = Mock()
        win._act_waifu = Mock()
        win.current_folder = win.root_folder = str(self.root)
        win.images = [dict(path=str(self.root / 'old.png'), tags=['unsaved'], modified=False)]
        win._folder_cache = {str(self.root): win.images}
        win.history = HistoryManager()
        win._undo_folders, win._redo_folders = ['old edit'], []
        win._load_all_folder_tags = Mock()
        win._highlight_tree_item = Mock()
        win.save_to_recent = Mock()

    def wait_for(self, condition):
        deadline = time.monotonic() + 3
        while not condition() and time.monotonic() < deadline:
            QTest.qWait(2)
        self.assertTrue(condition())

    def test_metadata_read_runs_off_ui_and_commits_after_success(self):
        win = self.win
        started, release = threading.Event(), threading.Event()
        threads = []
        def read(folder, extension):
            threads.append(threading.get_ident())
            started.set()
            release.wait(2)
            return [dict(path=str(self.other / 'new.png'), tags=['new'], modified=False)]
        old_images = win.images
        with patch('libs.folder_loader.load_folder_images', side_effect=read):
            win._set_active_directory(str(self.other))
            self.assertTrue(started.wait(1))
            self.assertIs(win.images, old_images)
            self.assertEqual(win.root_folder, str(self.root))
            self.assertFalse(win.centralWidget().isEnabled())
            release.set()
            self.wait_for(lambda: win._pending_folder is None)
        self.assertNotEqual(threads[0], threading.get_ident())
        self.assertEqual(win.current_folder, str(self.other))
        self.assertEqual(win.images[0]['tags'], ['new'])
        self.assertTrue(win.centralWidget().isEnabled())
        self.assertEqual(win._undo_folders, [])
        # Root scan adds only immediate children, not the entire subtree.
        item = win.dir_tree.topLevelItem(0)
        self.assertEqual(item.childCount(), 1)
        self.assertEqual(item.child(0).childCount(), 0)

    def test_failed_read_keeps_current_cache_and_history(self):
        win = self.win
        images, cache = win.images, win._folder_cache
        with patch('libs.folder_loader.load_folder_images', side_effect=OSError('disk unavailable')), \
             patch('main_window.QMessageBox.critical') as error:
            win._request_folder(str(self.other), new_root=True)
            self.wait_for(lambda: win._pending_folder is None)
        error.assert_called_once()
        self.assertIs(win.images, images)
        self.assertIs(win._folder_cache, cache)
        self.assertEqual(win.root_folder, str(self.root))
        self.assertEqual(win._undo_folders, ['old edit'])
        self.assertTrue(win.centralWidget().isEnabled())

    def test_read_does_not_overwrite_ai_results_cached_while_loading(self):
        win = self.win
        started, release = threading.Event(), threading.Event()
        def read(folder, extension):
            started.set()
            release.wait(2)
            return [dict(tags=['old disk caption'])]
        live = [dict(tags=['AI result'], modified=True)]
        with patch('libs.folder_loader.load_folder_images', side_effect=read):
            win._request_folder(str(self.other))
            self.assertTrue(started.wait(1))
            win._folder_cache[str(self.other)] = live
            release.set()
            self.wait_for(lambda: win._pending_folder is None)
        self.assertIs(win.images, live)
        self.assertTrue(win.images[0]['modified'])
