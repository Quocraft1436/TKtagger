"""Local tagger IO regression tests; model inference is mocked, no downloads."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from file_formats import SUPPORTED_FORMATS

# Load the real backend in isolation. These tests exercise caption IO and the
# local pipeline, not numpy/Pillow/ONNX inference; do not require AI packages.
spec = importlib.util.spec_from_file_location(
    '_local_append_backend', Path(__file__).resolve().parents[1] / 'tools/tagger_logic.py')
backend = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'numpy': Mock(), 'PIL': Mock(), 'onnxruntime': None,
                             'huggingface_hub': None, 'gradio_client': None}):
    spec.loader.exec_module(backend)


class LocalAppendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.image = self.folder / 'sample.png'
        self.image.write_bytes(b'image')
        self.caption = self.image.with_suffix('.txt')
        self.caption.write_text('old tag, shared', encoding='utf-8')
        self.output = self.folder / 'scratch.txt'

    def test_checkbox_merges_original_caption_into_temporary_output(self):
        tags = backend._write_caption(self.output, ['shared', 'new tag'],
                                      {'write_mode': 'overwrite', 'append_tags': True},
                                      merge_source=self.caption)
        self.assertEqual(tags, ['old tag', 'shared', 'new tag'])
        self.assertEqual(self.output.read_text(), 'old tag, shared, new tag')
        self.assertEqual(self.caption.read_text(), 'old tag, shared')

    def test_unchecked_append_still_replaces(self):
        tags = backend._write_caption(self.output, ['new tag'],
                                      {'write_mode': 'overwrite', 'append_tags': False},
                                      merge_source=self.caption)
        self.assertEqual(tags, ['new tag'])
        self.assertEqual(self.output.read_text(), 'new tag')

    def test_legacy_append_mode_remains_supported(self):
        tags = backend._write_caption(self.output, ['shared', 'new tag'],
                                      {'write_mode': 'append'}, merge_source=self.caption)
        self.assertEqual(tags, ['old tag', 'shared', 'new tag'])

    def test_append_with_missing_caption(self):
        tags = backend._write_caption(self.output, ['new tag'],
                                      {'append_tags': True}, merge_source=self.folder / 'missing.txt')
        self.assertEqual(tags, ['new tag'])
        self.assertEqual(self.output.read_text(), 'new tag')

    def run_local(self, write_mode, append_tags=True, decoded_tags=None):
        session = Mock()
        session.get_inputs.return_value = [Mock(name='input')]
        session.run.return_value = [[[]]]
        with patch.multiple(backend, _HAS_ORT=True,
                            _resolve_model=Mock(return_value=('model', 'tags')),
                            _load_tags_csv=Mock(return_value=[]),
                            _load_session=Mock(return_value=session),
                            _preprocess_image=Mock(return_value=None),
                            _decode_tags=Mock(return_value=['shared', 'new tag'] if decoded_tags is None else decoded_tags)):
            return backend.run_tagger({'target_folder': str(self.folder),
                                       'write_mode': write_mode, 'append_tags': append_tags})

    def test_empty_overwrite_returns_success_without_waiting_or_changing_original(self):
        with patch.object(backend.time, 'sleep', side_effect=AssertionError('Empty caption should be ready')):
            results = self.run_local('overwrite', append_tags=False, decoded_tags=[])
        self.assertEqual(results, [dict(path=str(self.image), tags=[], skipped=False, error=None)])
        self.assertEqual(self.caption.read_text(), 'old tag, shared')

    def test_empty_append_preserves_original_tags(self):
        results = self.run_local('overwrite', append_tags=True, decoded_tags=[])
        self.assertIsNone(results[0]['error'])
        self.assertFalse(results[0]['skipped'])
        self.assertEqual(results[0]['tags'], ['old tag', 'shared'])

    def test_local_pipeline_returns_merged_tags_without_changing_original(self):
        results = self.run_local('overwrite')
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0]['error'])
        self.assertFalse(results[0]['skipped'])
        self.assertEqual(results[0]['tags'], ['old tag', 'shared', 'new tag'])
        self.assertEqual(self.caption.read_text(), 'old tag, shared')

    def test_skip_takes_priority_over_append(self):
        results = self.run_local('skip')
        self.assertTrue(results[0]['skipped'])
        self.assertEqual(results[0]['tags'], ['old tag', 'shared'])
        self.assertEqual(self.caption.read_text(), 'old tag, shared')

    def test_tagger_reads_same_image_formats_as_folder_loader(self):
        for suffix in SUPPORTED_FORMATS:
            (self.folder / ('other' + suffix.upper())).write_bytes(b'image')
        paths = backend._collect_images({'target_folder': str(self.folder)})
        self.assertEqual({p.suffix.lower() for p in paths}, set(SUPPORTED_FORMATS))

    def test_tagger_rejects_image_caption_extension_and_direct_image_writes(self):
        for ext in ('png', '.PNG', ' .AVIF '):
            with self.subTest(ext=ext), self.assertRaises(ValueError):
                backend._caption_path(self.image, {'ext': ext})
        with self.assertRaises(ValueError):
            backend._write_caption(self.image, ['new tag'], {})
        self.assertEqual(self.image.read_bytes(), b'image')

    def test_tagger_normalizes_caption_extension(self):
        self.assertEqual(backend._caption_path(self.image, {'ext': ' .CAP '}),
                         self.image.with_suffix('.cap'))
