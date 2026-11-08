"""Build trainer-specific dataset TOML without modifying the dataset."""
import json
import os
from pathlib import Path

from libs.file_formats import normalize_caption_extension
from libs.i18n import tr

# Formats supported by both trainer loaders without optional image plugins.
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}


def dataset_images(folder):
    return sorted(path for path in Path(folder).iterdir()
                  if path.is_file() and path.suffix.lower() in IMAGE_EXTS)


def build_dataset_toml(results, trainer, resolution, batch_size, caption_extension):
    if trainer not in ('kohya', 'musubi'):
        raise ValueError('Unknown dataset TOML format')
    if not results or resolution <= 0 or batch_size <= 0:
        raise ValueError('Dataset, resolution and batch size must be positive')
    extension = '.' + normalize_caption_extension(caption_extension)
    def quote(value):
        return json.dumps(str(value), ensure_ascii=False)
    lines = ['# Dataset configuration exported by TKtagger.',
             '# Set epochs, model and optimizer in your trainer.', '[general]',
             f'caption_extension = {quote(extension)}']
    if trainer == 'musubi':
        lines += [f'resolution = [{resolution}, {resolution}]', f'batch_size = {batch_size}',
                  'enable_bucket = true']
    else:
        lines += ['', '[[datasets]]', f'resolution = {resolution}',
                  f'batch_size = {batch_size}', 'enable_bucket = true']
    seen = set()
    for result in results:
        folder = Path(os.path.abspath(result['path']))
        key = os.path.normcase(str(folder.resolve()))
        if key in seen:
            raise ValueError(tr('calc_export_duplicate', path=str(folder)))
        seen.add(key)
        repeat = result['repeat']
        if not isinstance(repeat, int) or repeat < 1:
            raise ValueError('Repeat must be a positive integer')
        images = dataset_images(folder)
        for image in images:
            caption = image.with_suffix(extension)
            if not caption.is_file():
                raise ValueError(tr('calc_export_missing_caption', path=str(caption)))
        if not images or len(images) != result['image_count']:
            raise ValueError(tr('calc_export_stale', path=str(folder)))
        if trainer == 'kohya':
            lines += ['', '[[datasets.subsets]]', f'image_dir = {quote(folder.as_posix())}',
                      f'num_repeats = {repeat}']
        else:
            lines += ['', '[[datasets]]', f'image_directory = {quote(folder.as_posix())}',
                      f'num_repeats = {repeat}']
    return '\n'.join(lines) + '\n'
