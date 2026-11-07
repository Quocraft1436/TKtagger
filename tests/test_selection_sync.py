"""Selection cleared by a grid refresh must also clear bulk action targets."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from copy import deepcopy
import unittest
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication, QMainWindow, QLineEdit
from history_manager import HistoryManager
from image_grid import ImageGrid
from main_window import MainWindow


class SelectionSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        class TestWindow(MainWindow):
            def __init__(self):
                QMainWindow.__init__(self)
        self.win = TestWindow()
        self.addCleanup(self.win.deleteLater)
        win = self.win
        win.images = [dict(path='', tags=['original'], modified=False)]
        win.current_folder = 'ram://selection-test'
        win._selected_images = set()
        win._undo_folders = []
        win._redo_folders = []
        win.history = HistoryManager()
        win.tag_panel = Mock()
        win.tag_panel._tag_filters = {}
        win._dict_data = {}
        win.global_tag_entry = QLineEdit(win)
        win.image_grid = ImageGrid(win)
        win.image_grid.selection_changed.connect(win._on_selection_changed)
        win._load_all_folder_tags()

    def select_card(self):
        self.win.image_grid._cards[0].toggle_select()
        self.assertEqual(self.win._selected_images, {0})

    def assert_cleared(self):
        self.assertEqual(self.win._selected_images, set())
        self.assertEqual(self.win.image_grid._selected, set())
        self.assertTrue(all(not card.is_selected()
                            for card in self.win.image_grid._cards.values()))

    def test_replacing_or_emptying_data_clears_action_targets(self):
        for images in (self.win.images, []):
            self.select_card()
            self.win.image_grid.set_data(images)
            self.assert_cleared()

    def test_undo_redo_clear_selection_and_block_bulk_edits(self):
        win = self.win
        before = win._snapshot()
        win.images[0]['tags'] = ['edited']
        win._push_history('edit', before)
        for refresh, expected_tags in ((win.do_undo, ['original']),
                                       (win.do_redo, ['edited'])):
            self.select_card()
            refresh()
            self.assert_cleared()
            self.assertEqual(win.images[0]['tags'], expected_tags)
            expected = deepcopy(win.images)
            for operation in (win.add_tag_to_selected,
                              win.remove_tag_from_selected,
                              win.nuke_tags_from_selected):
                win.global_tag_entry.setText('original, edited, new')
                with patch('main_window.QMessageBox.warning') as warning, \
                     patch('main_window.QMessageBox.question') as question:
                    operation()
                warning.assert_called_once()
                question.assert_not_called()
                self.assertEqual(win.images, expected)

    def test_layout_filter_and_language_rebuilds_preserve_visible_selection(self):
        self.select_card()
        grid = self.win.image_grid
        for rebuild in (lambda: grid.set_columns(2),
                        lambda: grid.set_tag_filters({'original': True}),
                        grid.retranslate_ui):
            rebuild()
            self.assertTrue(grid._cards[0].is_selected())
            self.assertEqual(grid._selected, {0})
            self.assertEqual(self.win._selected_images, {0})
