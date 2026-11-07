"""Installed tool discovery, isolated worker transport and dialog configuration."""
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from tools import external_tagger as external
from tools.waifu_tagger_window import WaifuTaggerWindow


class ExternalTaggerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='tool with spaces ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'kohya_gui').mkdir()
        self.python = self.root / '.venv/bin/python'
        self.python.parent.mkdir(parents=True)
        self.python.symlink_to(sys.executable)
        self.model = self.root / 'wd14_tagger_model/SmilingWolf_model/model.onnx'
        self.model.parent.mkdir(parents=True)
        self.model.write_bytes(b'onnx placeholder')
        self.csv = self.model.with_name('selected_tags.csv')
        self.csv.write_text('name,category\ntag,0\n')
        self.dataset = self.root / 'dataset'
        self.dataset.mkdir()
        self.image = self.dataset / 'ảnh.png'
        self.image.write_bytes(b'placeholder')
        self.caption = self.image.with_suffix('.txt')
        self.caption.write_text('original')
        self.config = dict(mode='external', tool_path=str(self.root), tool_type='auto',
                           onnx_path=str(self.model), csv_path=str(self.csv),
                           target_folder=str(self.dataset), root_folder=str(self.dataset))

    def test_discovery_maps_kohya_models_and_ignores_incomplete_models(self):
        (self.model.parent.parent / 'empty').mkdir()
        (self.model.parent.parent / 'empty/model.onnx').touch()
        info = external.discover_tool(self.root)
        self.assertEqual(info['tool_type'], 'kohya_ss')
        self.assertEqual(info['python_path'], str(self.python))
        self.assertEqual(len(info['models']), 1)
        self.assertEqual(info['models'][0]['onnx_path'], str(self.model))
        self.assertEqual(info['models'][0]['csv_path'], str(self.csv))

    def test_sd_scripts_mapping_and_unknown_tool(self):
        (self.root / 'kohya_gui').rmdir()
        with self.assertRaises(ValueError):
            external.discover_tool(self.root)
        (self.root / 'finetune').mkdir()
        (self.root / 'library').mkdir()
        self.assertEqual(external.discover_tool(self.root)['tool_type'], 'sd_scripts')
        self.assertEqual(len(external.discover_tool(self.root)['models']), 1)

    def test_missing_python_and_model_are_rejected_without_download(self):
        self.python.unlink()
        self.python.symlink_to(self.root / 'missing-python')
        self.assertEqual(external.discover_tool(self.root)['python_path'], '')
        with self.assertRaises(ValueError):
            external.validate_external_config(self.config)
        self.config['python_path'] = sys.executable
        self.model.unlink()
        with self.assertRaises(ValueError):
            external.validate_external_config(self.config)

    def test_worker_transport_uses_tool_python_and_local_model_without_writing_dataset(self):
        # Real subprocess; stub inference only, so the test needs no AI packages.
        worker = self.root / 'tagger_worker.py'
        worker.write_text('''import json, os, sys
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
assert sys.flags.isolated
assert Path(sys.executable) == Path(config['tool_path']) / '.venv/bin/python'
assert os.getcwd() == config['tool_path']
assert 'PYTHONPATH' not in os.environ
assert os.environ['HF_HUB_OFFLINE'] == '1'
assert config['force_download'] is False
assert Path(config['onnx_path']).is_file()
print('ordinary library log')
print('@@TKTAGGER@@' + json.dumps([1, 1, 'done']))
Path(sys.argv[2]).write_text(json.dumps([{'path': str(Path(config['target_folder']) / 'ảnh.png'), 'tags': ['new'], 'skipped': False, 'error': None}]), encoding='utf-8')
''')
        progress = []
        with patch.object(external, '__file__', str(self.root / 'external_tagger.py')), \
             patch.dict(os.environ, {'PYTHONPATH': '/should/not/leak'}):
            result = external.run_external_tagger(self.config, lambda *args: progress.append(args))
        self.assertEqual(progress, [(1, 1, 'done')])
        self.assertEqual(result[0]['tags'], ['new'])
        self.assertEqual(self.caption.read_text(), 'original')

    def test_failed_worker_surfaces_diagnostic(self):
        (self.root / 'tagger_worker.py').write_text("raise RuntimeError('missing dependency')")
        with patch.object(external, '__file__', str(self.root / 'external_tagger.py')):
            with self.assertRaisesRegex(RuntimeError, 'missing dependency'):
                external.run_external_tagger(self.config)

    def test_dialog_emits_external_config_and_persists_selection(self):
        with patch('tools.waifu_tagger_window.settings.value', side_effect=lambda key, default=None: default), \
             patch('tools.waifu_tagger_window.settings.set_value') as save:
            dialog = WaifuTaggerWindow(current_folder=str(self.dataset))
            self.addCleanup(dialog.deleteLater)
            dialog.tool_path.setText(str(self.root))
            dialog.run_mode.setCurrentIndex(1)
            self.assertEqual(dialog.detected_models.count(), 1)
            self.assertEqual(dialog.python_path.text(), str(self.python))
            self.assertEqual(dialog.onnx_path.text(), str(self.model))
            self.assertFalse(dialog.force_download.isEnabled())
            captured = []
            dialog.tagging_started.connect(captured.append)
            dialog._collect_and_run()
        self.assertEqual(captured[0]['mode'], 'external')
        self.assertEqual(captured[0]['onnx_path'], str(self.model))
        self.assertNotIn('api_url', captured[0])
        save.assert_any_call('wd14/tool_path', str(self.root))
        save.assert_any_call('wd14/model_path', str(self.model))

    def test_gui_only_build_selects_external_mode(self):
        with patch('tools.waifu_tagger_window.settings.value', side_effect=lambda key, default=None: default), \
             patch('tools.waifu_tagger_window.local_ai_available', return_value=False):
            dialog = WaifuTaggerWindow(current_folder=str(self.dataset))
            self.addCleanup(dialog.deleteLater)
            self.assertEqual(dialog.run_mode.currentIndex(), 1)
            self.assertFalse(dialog.run_mode.model().item(0).isEnabled())
            self.assertFalse(dialog.force_download.isEnabled())

    def test_gui_discovery_does_not_import_ai_packages(self):
        result = subprocess.run([sys.executable, '-c',
            'import sys; from tools.external_tagger import discover_tool; '
            'assert not any(m in sys.modules for m in ("numpy", "onnxruntime", "PIL", "gradio_client"))'],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
