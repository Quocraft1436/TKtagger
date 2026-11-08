"""Reject unsafe caption extensions before settings or dataset changes."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication
from libs.file_formats import SUPPORTED_FORMATS, normalize_caption_extension
from settings_dialog import SettingsDialog


class CaptionExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self, extension):
        dialog = SettingsDialog()
        self.addCleanup(dialog.deleteLater)
        dialog.settings = Mock()
        dialog.settings.value.return_value = 'txt'
        dialog.radio_custom.setChecked(True)
        dialog.custom_ext_input.setText(extension)
        return dialog

    def test_image_extensions_do_not_save_close_or_report_success(self):
        for suffix in SUPPORTED_FORMATS:
            for ext in (suffix[1:], suffix, suffix.upper(), ' ' + suffix.upper() + ' '):
                with self.subTest(ext=ext):
                    dialog = self.dialog(ext)
                    with patch.object(dialog, 'accept') as accept, \
                         patch('settings_dialog.QMessageBox.critical') as error, \
                         patch('settings_dialog.QMessageBox.information') as success:
                        dialog._on_ok()
                        dialog._on_apply()
                    self.assertEqual(error.call_count, 2)
                    dialog.settings.set_value.assert_not_called()
                    accept.assert_not_called()
                    success.assert_not_called()

    def test_valid_caption_extension_saves_normalized_value(self):
        dialog = self.dialog(' .CAP ')
        with patch('settings_dialog.QMessageBox.information'):
            self.assertTrue(dialog._save_settings())
        dialog.settings.set_value.assert_any_call('load_extension', 'cap')

    def test_empty_or_path_extensions_are_rejected(self):
        for ext in ('', '.', '../png', 'x/png', 'foo.png', 'x\\png', 'cap\x00'):
            with self.subTest(ext=ext), self.assertRaises(ValueError):
                normalize_caption_extension(ext)
