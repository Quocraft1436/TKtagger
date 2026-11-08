"""Regression: edit A, browse empty child, then open a different root."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from main_window import MainWindow
from libs.history_manager import HistoryManager


class FolderSwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.a, self.b = base / 'A', base / 'B'
        self.empty = self.a / 'empty'
        self.empty.mkdir(parents=True)
        self.b.mkdir()
        (self.a / 'image.png').write_bytes(b'image placeholder')
        self.caption = self.a / 'image.txt'
        self.caption.write_text('original')
        # Use actual navigation/save methods, without startup settings writes or rendering.
        class TestWindow(MainWindow):
            def __init__(self):
                QMainWindow.__init__(self)
        self.win = TestWindow()
        self.addCleanup(self.win.deleteLater)
        self.win.images = []
        self.win._folder_cache = {}
        self.win.current_folder = None
        self.win.root_folder = str(self.a)
        self.win._selected_images = set()
        self.win.history = HistoryManager()
        self.win._undo_folders = [str(self.a)]
        self.win._redo_folders = []
        self.win._load_all_folder_tags = Mock()
        self.win._populate_tree = Mock()
        self.win.save_to_recent = Mock()
        for target, kwargs in [
            ('libs.file_ops._get_tag_extension', {'return_value': 'txt'}),
            ('main_window.QMessageBox.information', {}),
            ('main_window.QMessageBox.critical', {}),
        ]:
            mocked = patch(target, **kwargs)
            mocked.start()
            self.addCleanup(mocked.stop)
        self.win._load_folder(str(self.a))
        self.edited = self.win.images[0]
        self.edited.update(tags=['unsaved tag'], modified=True)
        self.win._load_folder(str(self.empty))
        self.assertEqual(self.win.images, [])
        self.assertTrue(self.win._has_unsaved())

    def switch(self, reply):
        with patch('main_window.QMessageBox.question', return_value=reply) as question:
            self.win._set_active_directory(str(self.b))
            question.assert_called_once()

    def assert_retained(self):
        self.assertEqual(self.win.root_folder, str(self.a))
        self.assertEqual(self.win.current_folder, str(self.empty))
        self.assertIs(self.win._folder_cache[str(self.a)][0], self.edited)
        self.assertEqual(self.edited['tags'], ['unsaved tag'])
        self.assertTrue(self.edited['modified'])
        self.assertEqual(self.win._undo_folders, [str(self.a)])
        self.assertEqual(self.caption.read_text(), 'original')
        self.win._populate_tree.assert_not_called()

    def test_cancel_retains_cached_tags_and_navigation(self):
        self.switch(QMessageBox.Cancel)
        self.assert_retained()

    def test_yes_saves_cached_tags_before_switch(self):
        self.switch(QMessageBox.Yes)
        self.assertEqual(self.caption.read_text(), 'unsaved tag')
        self.assertFalse(self.edited['modified'])
        self.assertEqual(self.win.root_folder, str(self.b))
        self.assertNotIn(str(self.a), self.win._folder_cache)

    def test_save_failure_retains_cache_and_navigation(self):
        with patch('libs.file_ops.backup_folder', side_effect=OSError('backup unavailable')):
            self.switch(QMessageBox.Yes)
        self.assert_retained()

    def test_write_failure_retains_cache_and_navigation(self):
        with patch('libs.file_ops.backup_folder'), \
             patch('libs.file_ops._write_tags', side_effect=OSError('disk full')):
            self.switch(QMessageBox.Yes)
        self.assert_retained()

    def close_with_reply(self, reply):
        event = QCloseEvent()
        with patch('main_window.QMessageBox.question', return_value=reply) as question:
            self.win.closeEvent(event)
            question.assert_called_once()
        return event

    def test_failed_backup_or_write_prevents_close(self):
        for target in ('libs.file_ops.backup_folder', 'libs.file_ops._write_tags'):
            with self.subTest(target=target), \
                 patch('libs.file_ops.backup_folder'), \
                 patch(target, side_effect=OSError('save unavailable')):
                event = self.close_with_reply(QMessageBox.Yes)
                self.assertFalse(event.isAccepted())
                self.assert_retained()

    def test_cancel_close_retains_cached_edits(self):
        event = self.close_with_reply(QMessageBox.Cancel)
        self.assertFalse(event.isAccepted())
        self.assert_retained()

    def test_successful_save_allows_close(self):
        event = self.close_with_reply(QMessageBox.Yes)
        self.assertTrue(event.isAccepted())
        self.assertEqual(self.caption.read_text(), 'unsaved tag')
        self.assertFalse(self.win._has_unsaved())

    def test_explicit_discard_allows_close_without_saving(self):
        with patch('main_window.save_all_images') as save:
            event = self.close_with_reply(QMessageBox.No)
        self.assertTrue(event.isAccepted())
        save.assert_not_called()
        self.assertEqual(self.caption.read_text(), 'original')

    def test_partial_save_blocks_close_and_can_be_retried(self):
        (self.a / 'second.png').write_bytes(b'image placeholder')
        second_caption = self.a / 'second.txt'
        second_caption.write_text('second original')
        second = dict(path=str(self.a / 'second.png'),
                      txt_path=str(second_caption), filename='second.png',
                      tags=['second edited'], modified=True)
        self.win._folder_cache[str(self.a)].append(second)
        from libs.file_ops import _write_tags

        def fail_second(path, tags):
            if Path(path) == second_caption:
                raise OSError('disk full')
            return _write_tags(path, tags)

        with patch('libs.file_ops._write_tags', side_effect=fail_second):
            event = self.close_with_reply(QMessageBox.Yes)
        self.assertFalse(event.isAccepted())
        self.assertEqual(self.win.current_folder, str(self.empty))
        self.assertEqual(self.win._undo_folders, [str(self.a)])
        self.assertFalse(self.edited['modified'])
        self.assertTrue(second['modified'])
        self.assertEqual(self.caption.read_text(), 'unsaved tag')
        self.assertEqual(second_caption.read_text(), 'second original')

        event = self.close_with_reply(QMessageBox.Yes)
        self.assertTrue(event.isAccepted())
        self.assertFalse(self.win._has_unsaved())
        self.assertEqual(second_caption.read_text(), 'second edited')

    def test_no_explicitly_discards_cached_tags(self):
        self.switch(QMessageBox.No)
        self.assertEqual(self.caption.read_text(), 'original')
        self.assertEqual(self.win.root_folder, str(self.b))
        self.assertNotIn(str(self.a), self.win._folder_cache)

    def test_clean_empty_folder_switches_without_prompt(self):
        self.edited['modified'] = False
        with patch('main_window.QMessageBox.question') as question:
            self.win._set_active_directory(str(self.b))
            question.assert_not_called()
        self.assertEqual(self.win.root_folder, str(self.b))
