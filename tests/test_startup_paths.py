"""Launch Qt from a working directory without application resources."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StartupPathTests(unittest.TestCase):
    def run_elsewhere(self, script):
        with tempfile.TemporaryDirectory(prefix='tktagger unrelated cwd ') as directory:
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
            bootstrap = 'import sys\nsys.path.insert(0, ' + repr(str(ROOT)) + ')\n'
            result = subprocess.run([sys.executable, '-c', bootstrap + script],
                                    cwd=directory, env=env, capture_output=True,
                                    text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((Path(directory) / 'icons').exists())

    def test_all_bundled_icons_load_from_unrelated_directory(self):
        self.run_elsewhere('''
from PySide6.QtWidgets import QApplication
from table_icon import ICON_MAP, get_icon
app = QApplication([])
for name in ICON_MAP:
    assert not get_icon(name).isNull(), name
''')

    def test_entrypoint_opens_window_from_unrelated_directory(self):
        self.run_elsewhere('''
from unittest.mock import patch
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
import main

class TimedApplication(QApplication):
    def __init__(self, args):
        super().__init__(args)
        QTimer.singleShot(100, self.quit)

# Avoid loading a user's saved dictionary; exercise actual menu/UI and icons.
with patch.object(main, 'QApplication', TimedApplication), \\
     patch.object(main.MainWindow, 'check_auto_load_dict'):
    sys.argv = [str(main.__file__)]
    main.main()
''')
