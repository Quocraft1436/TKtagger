"""Verify bounded cards/cache, sparse history, and inexpensive tag refresh."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QImage, QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow
from libs.history_manager import HistoryManager
from image_grid import ImageGrid
from main_window import MainWindow
from tag_panel import TagPanel


class LargeGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name) / 'sample.png')
        image = QImage(64, 64, QImage.Format_RGB32)
        image.fill(QColor('red'))
        image.save(self.path)
        self.images = [dict(path=self.path, tags=['original'], modified=False,
                            filename=f'{idx}.png') for idx in range(10000)]
        self.grid = ImageGrid()
        self.grid.resize(1000, 800)
        self.grid.set_data(self.images)
        self.grid.show()
        self.addCleanup(self.cleanup_grid)
        self.app.processEvents()

    def cleanup_grid(self):
        self.grid.thumbnails.set_visible([])
        self.wait_for(lambda: not self.grid.thumbnails.active)
        self.grid.close()
        self.grid.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def wait_for(self, condition):
        deadline = time.monotonic() + 3
        while not condition() and time.monotonic() < deadline:
            QTest.qWait(2)
        self.assertTrue(condition())

    def test_cards_are_bounded_and_selection_survives_scrolling(self):
        self.assertLess(len(self.grid._cards), 30)
        self.grid._cards[0].toggle_select()
        self.grid.scroll_area.verticalScrollBar().setValue(
            self.grid.scroll_area.verticalScrollBar().maximum())
        self.app.processEvents()
        self.assertLess(len(self.grid._cards), 30)
        self.assertIn(9999, self.grid._cards)
        self.assertNotIn(0, self.grid._cards)
        self.assertEqual(self.grid.get_selected(), {0})
        self.grid.scroll_area.verticalScrollBar().setValue(0)
        self.app.processEvents()
        self.assertTrue(self.grid._cards[0].is_selected())

    def test_adaptive_grid_fills_width_and_restores_manual_columns(self):
        self.grid.set_columns(3)
        self.grid._cards[0].toggle_select()
        self.grid.set_layout_mode("adaptive")
        QTest.qWait(150)
        wide_cols = self.grid._cols
        self.assertGreater(wide_cols, 3)
        self.assertEqual(self.grid.scroll_area.horizontalScrollBar().maximum(), 0)
        last = self.grid._cards[wide_cols - 1]
        self.assertLessEqual(abs(last.geometry().right() + 19 - self.grid.scroll_area.viewport().width()), wide_cols + 2)
        self.grid.resize(540, 800)
        QTest.qWait(200)
        self.assertLess(self.grid._cols, wide_cols)
        self.assertEqual(self.grid.scroll_area.horizontalScrollBar().maximum(), 0)
        self.assertEqual(self.grid.get_selected(), {0})
        self.assertLess(len(self.grid._cards), 30)
        self.grid.set_layout_mode("classic")
        self.assertEqual(self.grid._cols, 3)
        self.assertEqual(self.grid._img_width, 200)
        self.assertTrue(self.grid._cards[0].is_selected())

    def test_grid_setting_applies_immediately_and_reopens_saved_mode(self):
        from PySide6.QtCore import QSettings
        from libs.settings_manager import settings
        from settings_dialog import SettingsDialog
        backend = QSettings(str(Path(self.tmp.name) / "settings.ini"), QSettings.IniFormat)
        window = QMainWindow()
        window.image_grid = self.grid
        from PySide6.QtWidgets import QSpinBox, QLabel
        window.col_spin = QSpinBox()
        window._col_lbl = QLabel()
        window.apply_grid_layout = lambda mode: MainWindow.apply_grid_layout(window, mode)
        with patch.object(settings, "_settings", backend):
            settings.language = "en"
            dialog = SettingsDialog(main_window=window)
            dialog.grid_mode_combo.setCurrentIndex(dialog.grid_mode_combo.findData("adaptive"))
            dialog.card_height_combo.setCurrentIndex(dialog.card_height_combo.findData("full"))
            self.assertTrue(dialog._save_settings())
            self.assertEqual(self.grid.layout_mode, "adaptive")
            self.assertEqual(self.grid.card_height_mode, "full")
            self.assertFalse(window.col_spin.isEnabled())
            self.assertEqual(QSettings(backend.fileName(), QSettings.IniFormat).value("grid_layout_mode"), "adaptive")
            reopened = SettingsDialog(main_window=window)
            self.assertEqual(reopened.grid_mode_combo.currentData(), "adaptive")
            self.assertEqual(reopened.card_height_combo.currentData(), "full")
            self.assertEqual(QSettings(backend.fileName(), QSettings.IniFormat).value("grid_card_height"), "full")
            reopened.grid_mode_combo.setCurrentIndex(reopened.grid_mode_combo.findData("classic"))
            self.assertTrue(reopened._save_settings())
            self.assertTrue(window.col_spin.isEnabled())
            dialog.close()
            reopened.close()
        window.close()

    def test_height_modes_expand_tags_and_full_rows_remain_virtual(self):
        self.grid._cards[0].toggle_select()
        medium_height = self.grid._cards[0].height()
        self.grid.set_card_height_mode("tall")
        self.assertGreater(self.grid._cards[0].height(), medium_height)
        self.assertEqual(self.grid._cards[0].tag_scroll.height(), 240)
        self.images[0]['tags'] = [f'long_caption_tag_{i}' for i in range(80)]
        self.images[3]['tags'] = ['a_very_long_tag_' * 30]
        self.grid.set_card_height_mode("full")
        self.app.processEvents()
        offsets = self.grid._row_offsets[0]
        self.assertGreater(offsets[1] - offsets[0], offsets[3] - offsets[2])
        self.assertEqual(self.grid.get_selected(), {0})
        self.assertLess(len(self.grid._cards), 30)
        for card in self.grid._cards.values():
            self.assertLessEqual(card.tag_display.minimumHeight(), card.tag_scroll.viewport().height())
            self.assertEqual(card.tag_scroll.verticalScrollBar().maximum(), 0)
        bar = self.grid.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())
        self.app.processEvents()
        self.assertIn(9999, self.grid._cards)
        self.assertLess(len(self.grid._cards), 30)
        self.grid.set_card_height_mode("medium")
        self.assertEqual(self.grid._row_height, self.grid._img_width + 174)

    def test_full_content_reflows_after_edit_and_wraps_long_tag_actions(self):
        from PySide6.QtCore import Qt
        tag = 'very_long_tag_' * 50
        self.grid.set_data([dict(path=self.path, tags=[tag])])
        self.grid.set_card_height_mode("full")
        self.app.processEvents()
        card = self.grid._cards[0]
        display = card.tag_display
        self.assertGreater(len(display.tag_rects), 1)
        self.assertEqual(''.join(entry[2] for entry in display.tag_rects), tag)
        self.assertTrue(all(rect.right() <= display.width() for rect, _, _, _ in display.tag_rects))
        removed = []
        display.tag_remove_requested.connect(removed.append)
        QTest.mouseClick(display, Qt.MiddleButton, pos=display.tag_rects[1][0].center())
        self.assertEqual(removed, [tag])
        old_height = self.grid._virtual_height
        self.grid._images[0]['tags'] = ['short']
        self.grid.refresh_card(0)
        self.app.processEvents()
        self.assertLess(self.grid._virtual_height, old_height)
        self.assertLessEqual(self.grid._cards[0].tag_display.minimumHeight(), self.grid._cards[0].tag_scroll.viewport().height())

    def test_adaptive_resize_keeps_visible_anchor_and_section_indices(self):
        self.grid.set_layout_mode("adaptive")
        QTest.qWait(150)
        bar = self.grid.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum() // 2)
        self.app.processEvents()
        start, indices = self.grid._sections[0]
        position = max(0, (self.grid._logical_top() - start) // self.grid._row_height) * self.grid._cols
        anchor = indices[position]
        self.grid.resize(540, 800)
        QTest.qWait(200)
        self.assertIs(self.grid._sections[0][1], indices)
        self.assertIn(anchor, self.grid._cards)
        self.assertLess(abs(self.grid._cards[anchor].y() - bar.value()), self.grid._row_height)
        bar.setValue(bar.maximum())
        self.app.processEvents()
        self.assertIn(9999, self.grid._cards)

    def test_logical_scrolling_reaches_end_beyond_qwidget_height_limit(self):
        # Shared metadata keeps this correctness test small; it is not a RAM benchmark.
        images = [self.images[0]] * 200000
        self.grid.set_data(images)
        bar = self.grid.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())
        self.app.processEvents()
        self.assertGreater(self.grid._virtual_height, 16777215)
        self.assertLessEqual(self.grid._container.height(), 8_000_000)
        self.assertIn(len(images) - 1, self.grid._cards)
        self.assertLess(len(self.grid._cards), 30)

    def test_decoding_runs_off_ui_and_cache_survives_rebuild(self):
        # Force a fresh path to observe the real reader invocation.
        new_path = str(Path(self.tmp.name) / 'new.png')
        Path(new_path).write_bytes(Path(self.path).read_bytes())
        from libs.thumbnail_loader import QImageReader
        threads = []
        def reader(path):
            threads.append(threading.get_ident())
            return QImageReader(path)
        with patch('libs.thumbnail_loader.QImageReader', side_effect=reader):
            self.grid.set_data([dict(path=new_path, tags=[])])
            self.wait_for(lambda: self.grid._cards[0]._image_loaded)
        self.assertTrue(threads)
        self.assertTrue(all(ident != threading.get_ident() for ident in threads))
        count = self.grid.thumbnails.decode_count
        self.grid.set_columns(2)
        self.wait_for(lambda: self.grid._cards[0]._image_loaded)
        self.assertEqual(self.grid.thumbnails.decode_count, count)
        self.assertLessEqual(self.grid.thumbnails.cache_bytes, self.grid.thumbnails.max_bytes)

    def test_unchanged_filters_do_not_rebuild_and_filter_edits_coalesce(self):
        count = self.grid.rebuild_count
        card = self.grid._cards[0]
        self.grid.set_tag_filters({})
        self.images[0]['tags'].append('new')
        self.grid.refresh_card(0)
        self.assertEqual(self.grid.rebuild_count, count)
        self.assertIs(self.grid._cards[0], card)
        self.grid.set_tag_filters({'original': True})
        count = self.grid.rebuild_count
        for idx in range(100):
            self.grid.refresh_card(idx)
        self.app.processEvents()
        self.assertEqual(self.grid.rebuild_count, count + 1)
        self.assertLess(len(self.grid._cards), 30)

    def test_sparse_history_only_marks_changed_images(self):
        history = HistoryManager()
        before = history.snapshot_tags(self.images, [5])
        self.images[5]['tags'].append('new')
        self.assertTrue(history.push('edit', before, self.images))
        entry = history._undo_stack[-1]
        self.assertEqual(set(entry.images_before), {5})
        history.undo(self.images)
        self.assertEqual(self.images[5]['tags'], ['original'])
        self.assertEqual([idx for idx, img in enumerate(self.images) if img['modified']], [5])
        self.images[5]['modified'] = False
        history.redo(self.images)
        self.assertEqual([idx for idx, img in enumerate(self.images) if img['modified']], [5])

    def test_single_tag_edit_updates_counts_without_rebuilding_grid(self):
        class Window(MainWindow):
            def __init__(self):
                QMainWindow.__init__(self)
        win = Window()
        self.addCleanup(win.deleteLater)
        win.images = self.images
        win.image_grid = self.grid
        win.tag_panel = TagPanel(win)
        win.history = HistoryManager()
        win.current_folder = self.tmp.name
        win._undo_folders, win._redo_folders = [], []
        win._dict_data = {}
        win._load_all_folder_tags()
        # Restoring filters and counts must not emit checkbox signals.
        emissions = []
        win.tag_panel.filter_changed.connect(emissions.append)
        initial = self.grid.rebuild_count
        card = self.grid._cards[0]
        win._on_individual_tag_add(0, 'new')
        self.assertEqual(win.folder_tag_counts, {'original': 10000, 'new': 1})
        self.assertEqual(len(win.history._undo_stack[-1].images_before), 1)
        self.assertEqual(self.grid.rebuild_count, initial)
        self.assertIs(self.grid._cards[0], card)
        self.assertEqual(emissions, [])
        win.do_undo()
        self.assertEqual(win.folder_tag_counts, {'original': 10000})
        self.assertEqual(self.grid.rebuild_count, initial)
