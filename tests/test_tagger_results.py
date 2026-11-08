"""Worker results survive browsing and remain saveable/undoable per folder."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow
from libs.file_ops import load_folder_images
from libs.history_manager import HistoryManager
from main_window import MainWindow


class TaggerResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.child = self.root / 'child'
        self.child.mkdir()
        self.paths = [self.root / 'a.png', self.child / 'b.png']
        for image in self.paths:
            image.write_bytes(b'image')
            image.with_suffix('.txt').write_text('original')
        extension = patch('libs.file_ops._get_tag_extension', return_value='txt')
        extension.start()
        self.addCleanup(extension.stop)
        class TestWindow(MainWindow):
            def __init__(self):
                QMainWindow.__init__(self)
        self.win = TestWindow()
        self.addCleanup(self.win.deleteLater)
        win = self.win
        win.root_folder = str(self.root)
        win.current_folder = str(self.root)
        win.images = load_folder_images(str(self.root))
        win._folder_cache = {}
        win._selected_images = set()
        win.history = HistoryManager()
        win._undo_folders = []
        win._redo_folders = []
        win._refresh_after_tag_change = Mock()
        win._highlight_tree_item = Mock()
        win._act_waifu = Mock()
        self.messages = patch('main_window.QMessageBox.information')
        self.messages.start()
        self.addCleanup(self.messages.stop)

    def result(self, image, tags):
        return dict(path=str(image), tags=tags, error=None, skipped=False)

    def test_recursive_results_populate_unopened_folder_and_undo_redo(self):
        win = self.win
        win._on_tagging_finished([self.result(self.paths[0], ['root tag']),
                                  self.result(self.paths[1], ['child tag'])])
        self.assertEqual(win.images[0]['tags'], ['root tag'])
        child_images = win._folder_cache[str(self.child)]
        self.assertEqual(child_images[0]['tags'], ['child tag'])
        self.assertTrue(child_images[0]['modified'])
        self.assertEqual(win._undo_folders, [str(self.root), str(self.child)])
        win.do_undo()
        self.assertEqual(win.current_folder, str(self.child))
        self.assertEqual(win.images[0]['tags'], ['original'])
        win.do_redo()
        self.assertEqual(win.images[0]['tags'], ['child tag'])
        self.assertEqual(self.paths[1].with_suffix('.txt').read_text(), 'original')
        self.assertTrue(win.save_all())
        self.assertEqual(self.paths[0].with_suffix('.txt').read_text(), 'root tag')
        self.assertEqual(self.paths[1].with_suffix('.txt').read_text(), 'child tag')

    def test_browsing_during_inference_updates_source_not_visible_folder(self):
        win = self.win
        source = win.images
        win._save_current_folder_state()
        win.current_folder = str(self.child)
        win.images = load_folder_images(str(self.child))
        win._on_tagging_finished([self.result(self.paths[0], ['generated'])])
        self.assertEqual(win.current_folder, str(self.child))
        self.assertEqual(win.images[0]['tags'], ['original'])
        self.assertEqual(source[0]['tags'], ['generated'])
        self.assertEqual(win._undo_folders, [str(self.root)])

    def test_worker_prepared_metadata_avoids_disk_io_in_completion_slot(self):
        images = [dict(path=str(self.paths[1]), tags=['original'], modified=False)]
        result = self.result(self.paths[1], ['generated'])
        result['_folder_images'] = images
        with patch('main_window.load_folder_images', side_effect=AssertionError('UI disk read')):
            self.win._on_tagging_finished([result])
        self.assertIs(self.win._folder_cache[str(self.child)], images)
        self.assertEqual(images[0]['tags'], ['generated'])

    def test_empty_results_preserve_unsaved_edits_and_history(self):
        win = self.win
        win.images[0].update(tags=['unsaved'], modified=True)
        win._on_tagging_finished([])
        self.assertEqual(win.images[0]['tags'], ['unsaved'])
        self.assertTrue(win.images[0]['modified'])
        self.assertFalse(win.history.can_undo())
        win._refresh_after_tag_change.assert_not_called()

    def test_empty_tag_list_is_a_valid_result(self):
        self.win._on_tagging_finished([self.result(self.paths[0], [])])
        self.assertEqual(self.win.images[0]['tags'], [])
        self.assertTrue(self.win.images[0]['modified'])
        self.assertEqual(self.paths[0].with_suffix('.txt').read_text(), 'original')
        self.win.do_undo()
        self.assertEqual(self.win.images[0]['tags'], ['original'])
        self.win.do_redo()
        self.assertEqual(self.win.images[0]['tags'], [])
        self.assertTrue(self.win.save_all())
        self.assertEqual(self.paths[0].with_suffix('.txt').read_text(), '')

    def test_empty_tags_from_skipped_failed_or_missing_results_preserve_edits(self):
        for overrides in ({'skipped': True}, {'error': 'inference failed'}, {'tags': None}):
            with self.subTest(overrides=overrides), patch('main_window.QMessageBox.warning'):
                self.win.images[0].update(tags=['unsaved'], modified=True)
                result = self.result(self.paths[0], [])
                result.update(overrides)
                self.win._on_tagging_finished([result])
                self.assertEqual(self.win.images[0]['tags'], ['unsaved'])
                self.assertTrue(self.win.images[0]['modified'])
                self.assertFalse(self.win.history.can_undo())

    def test_running_job_blocks_close_and_root_replacement(self):
        win = self.win
        win._tagging_running = True
        images = win.images
        event = QCloseEvent()
        win.closeEvent(event)
        self.assertFalse(event.isAccepted())
        win._set_active_directory(str(self.child))
        self.assertIs(win.images, images)
        self.assertEqual(win.root_folder, str(self.root))
        self.assertEqual(win.current_folder, str(self.root))
