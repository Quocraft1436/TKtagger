"""Translation coverage, interpolation safety and actual Qt language selection."""
import ast
from collections import Counter
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from string import Formatter
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QPushButton
from libs import i18n
from main_window import MainWindow
from settings_dialog import SettingsDialog
from libs.settings_manager import settings
from tools.waifu_tagger_window import WaifuTaggerWindow

ROOT = Path(__file__).resolve().parents[1]
NEW_LANGUAGES = {'zh': '简体中文', 'ko': '한국어', 'ja': '日本語', 'ru': 'Русский'}


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate translation key: {key}')
        result[key] = value
    return result


def fields(value):
    return Counter((name, spec, conversion) for _, name, spec, conversion in Formatter().parse(value)
                   if name is not None)


class LanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.english = json.loads((ROOT / 'lang/en.json').read_text())

    def setUp(self):
        self.previous_language = i18n.get_language()
        self.addCleanup(i18n.set_language, self.previous_language)

    def test_all_languages_have_exact_keys_and_preserve_placeholders(self):
        for path in (ROOT / 'lang').glob('*.json'):
            with self.subTest(language=path.stem):
                data = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=strict_object)
                self.assertEqual(set(data), set(self.english))
                for key, english in self.english.items():
                    with self.subTest(key=key):
                        self.assertIsInstance(data[key], str)
                        self.assertTrue(data[key].strip())
                        self.assertEqual(fields(data[key]), fields(english))

    def test_new_languages_have_native_names_and_real_translations(self):
        supported = dict(settings.get_supported_languages())
        for code, name in NEW_LANGUAGES.items():
            with self.subTest(language=code):
                data = json.loads((ROOT / 'lang' / f'{code}.json').read_text())
                self.assertEqual(data['language_name'], name)
                self.assertEqual(supported[code], name)
                for key in ('menu_file', 'settings_title', 'waifu_tool_hint', 'calc_export_info', 'dict_hint_hidden'):
                    self.assertNotEqual(data[key], self.english[key])
                i18n.set_language(code)
                self.assertEqual(i18n.tr('status_selected', count=7), data['status_selected'].format(count=7))
                self.assertIn('${Size}', i18n.tr('dict_hint_virtual'))
                self.assertIn('${Color}_${Eye}', i18n.tr('dict_hint_virtual'))

    def test_locale_forms_and_jp_alias(self):
        for locale, expected in [('ZH_CN', 'zh'), ('ko-KR', 'ko'), ('JP', 'ja'), ('ja_JP', 'ja'), ('ru_RU', 'ru')]:
            with self.subTest(locale=locale):
                i18n.set_language(locale)
                self.assertEqual(i18n.get_language(), expected)
                self.assertNotEqual(i18n.tr('menu_file'), 'menu_file')
        with patch.object(settings, 'value', return_value='JP'):
            self.assertEqual(settings.language, 'ja')

    def test_literal_translation_keys_in_app_are_defined(self):
        used = set()
        for path in [*ROOT.glob('*.py'), *(ROOT / 'tools').glob('*.py')]:
            for node in ast.walk(ast.parse(path.read_text())):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == 'tr' and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)):
                    used.add(node.args[0].value)
        self.assertEqual(used - self.english.keys(), set())

    def test_main_window_settings_and_wd14_in_each_new_language(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = QSettings(str(Path(directory) / 'settings.ini'), QSettings.IniFormat)
            with patch.object(settings, '_settings', backend), \
                 patch.object(MainWindow, 'check_auto_load_dict'):
                for code in NEW_LANGUAGES:
                    with self.subTest(language=code):
                        settings.set_value('language', code)
                        i18n.set_language(code)
                        win = MainWindow()
                        self.addCleanup(win.deleteLater)
                        self.assertEqual(win._file_menu.title(), i18n.tr('menu_file'))
                        dialog = SettingsDialog(win, win)
                        self.addCleanup(dialog.deleteLater)
                        self.assertEqual(dialog.lang_combo.currentData(), code)
                        self.assertEqual(dialog.windowTitle(), i18n.tr('settings_title'))
                        buttons = {button.text() for button in dialog.findChildren(QPushButton)}
                        self.assertIn(i18n.tr('settings_apply'), buttons)
                        self.assertIn(i18n.tr('ldl_cancel'), buttons)
                        wd14 = WaifuTaggerWindow(win)
                        self.addCleanup(wd14.deleteLater)
                        self.assertEqual(wd14.windowTitle(), i18n.tr('waifu_win_title'))
                        self.assertEqual(wd14._tool_path_lbl.text(), i18n.tr('waifu_tool_path'))
