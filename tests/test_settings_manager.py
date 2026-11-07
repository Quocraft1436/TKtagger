"""Regression tests for interleaved settings writers and Qt INI values."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QSettings
from settings_manager import settings


class SettingsPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / 'settings.ini')
        backend = QSettings(self.path, QSettings.IniFormat)
        self.override = patch.object(settings, '_settings', backend)
        self.override.start()
        self.addCleanup(self.override.stop)

    def test_interleaved_writes_preserve_latest_values_and_sections(self):
        settings.set_value('language', 'en')
        other = QSettings(self.path, QSettings.IniFormat)
        other.setValue('language', 'vi')
        other.setValue('load_extension', 'cap')
        other.setValue('window/geometry', b'geometry')
        other.sync()

        settings.icon_size = 32
        self.assertEqual(settings.language, 'vi')
        other.sync()
        self.assertEqual(other.value('language'), 'vi')
        self.assertEqual(other.value('load_extension'), 'cap')
        self.assertEqual(other.value('window/geometry'), b'geometry')
        self.assertEqual(other.value('icon_size', type=int), 32)

        other.setValue('max_history', 512)
        other.sync()
        self.assertEqual(settings.value('max_history', type=int), 512)
        settings.set_value('load_extension', 'txt')
        other.sync()
        self.assertEqual(other.value('max_history', type=int), 512)

    def test_recent_paths_round_trip_with_commas_and_unicode(self):
        paths = [str(Path(self.directory.name) / name)
                 for name in ('ảnh, một', 'ảnh hai')]
        for path in paths:
            Path(path).mkdir()
        settings.add_recent_file(paths[1])
        settings.add_recent_file(paths[0])
        self.assertEqual(settings.get_recent_files(), paths)
        self.assertEqual(settings.value('recent_list', [], type=list), paths)
        reader = QSettings(self.path, QSettings.IniFormat)
        self.assertEqual(reader.value('recent_list', type=list), paths)
        settings.set_value('recent_list', [])
        self.assertEqual(settings.get_recent_files(), [])

    def test_legacy_values_and_conversion_defaults(self):
        Path(self.path).write_text(
            '[General]\nlanguage=vi\nicon_size=20\nenabled=yes\n'
            'invalid=abc\npercent=100%\n', encoding='utf-8')
        self.assertEqual(settings.language, 'vi')
        self.assertEqual(settings.icon_size, 20)
        self.assertTrue(settings.value('enabled', type=bool))
        self.assertFalse(settings.value('missing', 'false', type=bool))
        self.assertEqual(settings.value('invalid', 24, type=int), 24)
        self.assertEqual(settings.value('percent'), '100%')
