"""Exercise bulk replacement through the real dialog, without saving files."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from copy import deepcopy
import unittest
from unittest.mock import Mock, patch
from PySide6.QtCore import QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow
from main_window import MainWindow
from history_manager import HistoryManager
from tools.replace_tags import run_replace_tags


class ReplaceWindow(MainWindow):
    def __init__(self, tags):
        QMainWindow.__init__(self)
        self.images = [dict(tags=list(row), modified=False) for row in tags]
        self.current_folder = 'ram://replace-test'
        self.history = HistoryManager()
        self._undo_folders = []
        self._redo_folders = []
        self.tag_panel = Mock()
        self.image_grid = Mock()
        self._reload_tags_panel = Mock()


class ReplaceTagsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def apply_rules(self, rows, rules, cancel=False):
        win = ReplaceWindow(rows)
        self.addCleanup(win.deleteLater)
        win.tag_panel.get_selected_filter_tags.return_value = list(rules)
        def fill_dialog():
            dialog = self.app.activeModalWidget()
            for tag, replacement in rules.items():
                dialog._entries[tag].setText(replacement)
            QTest.mouseClick(dialog._cancel_btn if cancel else dialog._confirm_btn,
                             Qt.LeftButton)
        QTimer.singleShot(0, fill_dialog)
        with patch('tools.replace_tags.QMessageBox.information'), \
             patch('main_window.save_all_images', side_effect=AssertionError('Must not save')):
            self.result = run_replace_tags(win)
        return win

    def test_chain_is_applied_once_to_original_tags(self):
        win = self.apply_rules([['a'], ['b'], ['a', 'b']], {'a': 'b', 'b': 'c'})
        self.assertEqual([i['tags'] for i in win.images], [['b'], ['c'], ['b', 'c']])
        self.assertTrue(all(i['modified'] for i in win.images))

    def test_rule_order_does_not_change_result(self):
        first = self.apply_rules([['a', 'b', 'x']], {'a': 'b', 'b': 'c'})
        second = self.apply_rules([['a', 'b', 'x']], {'b': 'c', 'a': 'b'})
        self.assertEqual(first.images, second.images)

    def test_swap_keeps_both_tags_in_original_positions(self):
        win = self.apply_rules([['a', 'x', 'b']], {'a': 'b', 'b': 'a'})
        self.assertEqual(win.images[0]['tags'], ['b', 'x', 'a'])

    def test_shared_destination_is_not_duplicated(self):
        win = self.apply_rules([['a', 'x', 'b', 'c']], {'a': 'c', 'b': 'c'})
        self.assertEqual(win.images[0]['tags'], ['c', 'x'])

    def test_unmatched_image_is_untouched(self):
        win = self.apply_rules([['x', 'x'], ['a']], {'a': 'b'})
        self.assertEqual(win.images[0], dict(tags=['x', 'x'], modified=False))
        win.image_grid.refresh_card.assert_called_once_with(1)

    def test_cancel_does_not_edit_or_add_history(self):
        win = self.apply_rules([['a', 'b']], {'a': 'b', 'b': 'c'}, cancel=True)
        self.assertFalse(self.result)
        self.assertEqual(win.images[0], dict(tags=['a', 'b'], modified=False))
        self.assertFalse(win.history.can_undo())

    def test_undo_and_redo_restore_exact_tag_lists(self):
        original = [['a', 'b', 'x'], ['b']]
        win = self.apply_rules(original, {'a': 'b', 'b': 'c'})
        after = deepcopy([img['tags'] for img in win.images])
        win.history.undo(win.images)
        self.assertEqual([img['tags'] for img in win.images], original)
        win.history.redo(win.images)
        self.assertEqual([img['tags'] for img in win.images], after)
