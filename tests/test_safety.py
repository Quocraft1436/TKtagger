import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backup_manager import backup_folder, backup_api_folder, BACKUP_DIR
from file_ops import load_folder_images, save_all_images, save_tags, populate_folder_tree, _write_tags, load_tags
from file_formats import SUPPORTED_FORMATS
from history_manager import HistoryManager


class DatasetSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "dataset"
        self.folder.mkdir()
        self.caption = self.folder / 'sample.txt'
        self.caption.write_text('original, tag', encoding='utf-8')
        (self.folder / 'sample.png').write_bytes(b'original image bytes')
        self.ext = patch('file_ops._get_tag_extension', return_value='txt')
        self.ext.start()
        self.addCleanup(self.ext.stop)

    def images(self):
        return load_folder_images(str(self.folder))

    def snapshots(self):
        return sorted((self.folder.parent / BACKUP_DIR).glob('*/*/data'))

    def test_save_preserves_complete_folder_and_previous_versions(self):
        nested = self.folder / 'nested'
        nested.mkdir()
        (nested / 'keep.bin').write_bytes(b'other data')
        self.assertTrue(save_tags(str(self.caption), ['new']))
        first = self.snapshots()[0]
        self.assertEqual((first / 'sample.txt').read_text(), 'original, tag')
        self.assertEqual((first / 'sample.png').read_bytes(), b'original image bytes')
        self.assertEqual((first / 'nested/keep.bin').read_bytes(), b'other data')
        self.assertTrue(save_tags(str(self.caption), ['latest']))
        self.assertEqual(len(self.snapshots()), 2)
        self.assertFalse(any(p.name == BACKUP_DIR for p in self.snapshots()[1].rglob('*')))
        self.assertEqual((self.snapshots()[1] / 'sample.txt').read_text(), 'new')

    def test_batch_one_snapshot_per_folder(self):
        (self.folder / 'second.png').write_bytes(b'image2')
        images = self.images()
        for img in images:
            img.update(tags=['updated'], modified=True)
        self.assertEqual(save_all_images(images), 2)
        self.assertEqual(len(self.snapshots()), 1)
        self.assertTrue(all(not img['modified'] for img in images))
        self.assertEqual(save_all_images(images), 0)
        self.assertEqual(len(self.snapshots()), 1)

    def test_failed_backup_prevents_all_batch_writes(self):
        other = self.folder / 'other'
        other.mkdir()
        (other / 'b.png').write_bytes(b'image')
        (other / 'b.txt').write_text('untouched')
        images = self.images() + load_folder_images(str(other))
        for img in images:
            img.update(tags=['changed'], modified=True)
        with patch('file_ops.backup_folder', side_effect=[Path('unused'), OSError('disk full')]):
            with self.assertRaises(OSError):
                save_all_images(images)
        self.assertEqual(self.caption.read_text(), 'original, tag')
        self.assertEqual((other / 'b.txt').read_text(), 'untouched')
        self.assertTrue(all(img['modified'] for img in images))

    def test_partial_copy_never_becomes_complete_backup(self):
        with patch('backup_manager.shutil.copytree', side_effect=OSError('copy failed')):
            self.assertFalse(save_tags(str(self.caption), ['lost']))
        self.assertEqual(self.caption.read_text(), 'original, tag')
        entries = list((self.folder.parent / BACKUP_DIR).glob('*/*'))
        self.assertTrue(entries)
        self.assertTrue(all(p.name.endswith('.partial') for p in entries))

    def test_atomic_failure_preserves_original_and_modified_flag(self):
        images = self.images()
        images[0].update(tags=['changed'], modified=True)
        with patch('file_ops.os.replace', side_effect=OSError('replace failed')):
            with self.assertRaises(OSError):
                save_all_images(images)
        self.assertEqual(self.caption.read_text(), 'original, tag')
        self.assertTrue(images[0]['modified'])
        self.assertEqual({p.name for p in self.folder.iterdir()},
                         {'sample.png', 'sample.txt'})

    def test_custom_extension_and_unicode(self):
        with patch('file_ops._get_tag_extension', return_value='cap'):
            self.assertTrue(save_tags(str(self.caption), ['tiếng Việt', 'ảnh']))
            self.assertEqual(self.images()[0]['tags'], ['tiếng Việt', 'ảnh'])
        self.assertEqual(self.caption.read_text(), 'original, tag')

    def test_image_extensions_cannot_overwrite_images_even_from_old_settings(self):
        for suffix in SUPPORTED_FORMATS:
            image = self.folder / ('sample' + suffix)
            image.write_bytes(b'original image bytes')
            for ext in (suffix[1:], suffix, suffix.upper(), ' ' + suffix.upper() + ' '):
                with self.subTest(ext=ext), patch('file_ops._get_tag_extension', return_value=ext), \
                     patch('file_ops.backup_folder') as backup:
                    self.assertFalse(save_tags(str(self.caption), ['new tag']))
                    images = [dict(txt_path=str(self.caption), tags=['new tag'], modified=True)]
                    with self.assertRaises(ValueError):
                        save_all_images(images)
                    self.assertTrue(images[0]['modified'])
                    backup.assert_not_called()
                    self.assertEqual(image.read_bytes(), b'original image bytes')

    def test_low_level_writer_rejects_image_target(self):
        for suffix in SUPPORTED_FORMATS:
            image = self.folder / ('direct' + suffix.upper())
            image.write_bytes(b'keep image')
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                _write_tags(image, ['new tag'])
            self.assertEqual(image.read_bytes(), b'keep image')

    def test_reading_cannot_treat_an_image_as_a_caption(self):
        for ext in ('png', '.PNG', 'avif', '.WEBP'):
            with self.subTest(ext=ext):
                with self.assertRaises(ValueError):
                    load_tags(str(self.caption), extension=ext)
                with self.assertRaises(ValueError):
                    load_folder_images(str(self.folder), extension=ext)

    def test_caption_extension_is_normalized_for_read_and_write(self):
        with patch('file_ops._get_tag_extension', return_value=' .CAP '):
            self.assertTrue(save_tags(str(self.caption), ['caption tag']))
            self.assertEqual(load_tags(str(self.caption)), ['caption tag'])
        self.assertEqual(self.caption.with_suffix('.cap').read_text(), 'caption tag')

    def test_folder_loading_recognizes_all_shared_image_extensions(self):
        for suffix in SUPPORTED_FORMATS:
            (self.folder / ('other' + suffix.upper())).write_bytes(b'image')
        names = {image['filename'] for image in self.images()}
        self.assertTrue({('other' + suffix.upper()) for suffix in SUPPORTED_FORMATS} <= names)

    def test_symlink_target_is_not_overwritten(self):
        target = self.folder / 'real.txt'
        target.write_text('keep')
        link = self.folder / 'link.txt'
        link.symlink_to(target)
        self.assertFalse(save_tags(str(link), ['changed']))
        self.assertEqual(target.read_text(), 'keep')

    def test_tree_excludes_backups(self):
        backup_folder(self.folder)
        tree = populate_folder_tree(str(self.folder.parent))
        self.assertFalse(any(BACKUP_DIR in path for path in tree))

    def test_recursive_api_cannot_process_nested_backups(self):
        nested = self.folder / 'child'
        nested.mkdir()
        backup_folder(nested)
        with self.assertRaisesRegex(ValueError, 'existing backup archives'):
            backup_api_folder(self.folder, recursive=True)
        self.assertTrue(backup_api_folder(self.folder, recursive=False).is_dir())

    def test_api_requires_explicit_folder(self):
        with self.assertRaises(ValueError):
            backup_api_folder('')

    def test_undo_redo_does_not_write_disk(self):
        images = self.images()
        history = HistoryManager()
        before = history.snapshot_tags(images)
        images[0].update(tags=['edited'], modified=True)
        history.push('edit', before, images)
        history.undo(images)
        self.assertEqual(images[0]['tags'], ['original', 'tag'])
        history.redo(images)
        self.assertEqual(images[0]['tags'], ['edited'])
        self.assertEqual(self.caption.read_text(), 'original, tag')


if __name__ == '__main__':
    unittest.main()
