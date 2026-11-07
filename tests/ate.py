"""Reproducible dummy dataset and real Qt render benchmark (no AI/network)."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import platform
import resource
import statistics
import sys
import time
import uuid

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QCoreApplication, QEvent, QByteArray, QBuffer, QIODevice, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QImageReader
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtTest import QTest
from history_manager import HistoryManager
from main_window import MainWindow
from tag_panel import TagPanel
from collections import Counter
from file_ops import load_folder_images
from image_grid import ImageGrid
from unittest.mock import patch


def positive(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError('Must be positive')
    return number


def png_variants(size):
    """Encode a small pool in RAM, reused by virtual dataset entries."""
    variants = []
    for i in range(16):
        image = QImage(size, size, QImage.Format_RGB32)
        image.fill(QColor.fromHsv(i * 22, 180, 210))
        painter = QPainter(image)
        painter.drawText(8, 24, f'Dummy {i}')
        painter.end()
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.WriteOnly)
        if not image.save(buffer, 'PNG'):
            raise RuntimeError('PNG encoding failed')
        variants.append(bytes(data))
    return variants


def generate(folder, count, size, tags, extension):
    folder.mkdir(parents=True, exist_ok=False)
    variants = png_variants(size)
    for i in range(count):
        stem = folder / f'image_{i:08d}'
        stem.with_suffix('.png').write_bytes(variants[i % len(variants)])
        stem.with_suffix('.' + extension).write_text(
            ', '.join([f'group_{i % 16}'] + [f'tag_{j}' for j in range(tags)]), encoding='utf-8')


def memory_reader(variants):
    """Feed real Qt PNG decoding with QBuffer instead of filesystem paths."""
    def reader(path):
        index = int(path.rsplit('/', 1)[1].split('.')[0])
        buffer = QBuffer()
        buffer.setData(QByteArray(variants[index % len(variants)]))
        buffer.open(QIODevice.ReadOnly)
        result = QImageReader(buffer, b'PNG')
        result._ate_buffer = buffer  # keep the device alive until reader destruction
        return result
    return reader


def benchmark(args, app, run):
    dataset = None
    started = time.perf_counter()
    if args.storage == 'ram':
        variants = png_variants(args.size)
        common_tags = [f'tag_{j}' for j in range(args.tags)]
        images = [dict(path=f'ram:///{i}.png', txt_path=None,
                       filename=f'image_{i:08d}.png', modified=False,
                       tags=[f'group_{i % 16}'] + common_tags)
                  for i in range(args.count)]
        generation = time.perf_counter() - started
        load_seconds = None  # RAM mode does not measure folder/caption IO
        reader_context = patch('thumbnail_loader.QImageReader', new=memory_reader(variants))
    else:
        dataset = run / 'dataset'
        generate(dataset, args.count, args.size, args.tags, args.extension)
        generation = time.perf_counter() - started
        with patch('file_ops._get_tag_extension', return_value=args.extension):
            started = time.perf_counter()
            images = load_folder_images(str(dataset))
            load_seconds = time.perf_counter() - started
        reader_context = contextlib.nullcontext()
    assert len(images) == args.count
    assert all(len(img['tags']) == args.tags + 1 for img in images)
    heartbeat_gaps = []
    last_heartbeat = [time.perf_counter()]
    heartbeat = QTimer()
    heartbeat.setInterval(10)
    def beat():
        now = time.perf_counter()
        heartbeat_gaps.append(now - last_heartbeat[0])
        last_heartbeat[0] = now
    heartbeat.timeout.connect(beat)
    heartbeat.start()
    first_view = None
    max_live_cards = 0
    with reader_context:
        grid = ImageGrid()
        grid.resize(1000, 800)
        grid.show()
        app.processEvents()
        latencies = []
        rendered_indices = set()
        batch = args.batch_size if args.mode == 'batch' else args.count
        started = time.perf_counter()
        for offset in range(0, len(images), batch):
            chunk = images[offset:offset + batch]
            grid.set_data(chunk)
            scrollbar = grid.scroll_area.verticalScrollBar()
            scrollbar.setValue(0)
            position = 0
            while True:
                tick = time.perf_counter()
                scrollbar.setValue(position)
                app.processEvents()
                deadline = time.monotonic() + 15
                while not all(card._image_loaded for card in grid._cards.values()):
                    if time.monotonic() > deadline:
                        raise AssertionError('Thumbnail workers timed out')
                    QTest.qWait(1)
                if first_view is None:
                    first_view = time.perf_counter() - started
                max_live_cards = max(max_live_cards, len(grid._cards))
                for idx, card in grid._cards.items():
                    absolute_idx = offset + idx
                    if absolute_idx in rendered_indices:
                        continue
                    if card.img_label.pixmap().isNull():
                        raise AssertionError(f'Image decode failed: {card.img_data["path"]}')
                    if card.grab().isNull():
                        raise AssertionError('Card paint failed')
                    rendered_indices.add(absolute_idx)
                if offset == 0 and position == 0:
                    if not grid.grab().save(str(run / 'render_preview.png')):
                        raise AssertionError('Screenshot failed')
                app.processEvents()
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                latencies.append(time.perf_counter() - tick)
                if position >= scrollbar.maximum():
                    break
                position = min(scrollbar.maximum(), position + grid.scroll_area.viewport().height())
            if offset % 1000 == 0:
                print(f'Rendered {len(rendered_indices)}/{len(images)}', flush=True)
        elapsed = time.perf_counter() - started
        rendered = len(rendered_indices)
        if rendered != len(images):
            raise AssertionError(f'Only rendered {rendered}/{len(images)}')
        # Measure the real single-image edit path, including tag count/panel
        # refresh and a paint, while keeping the current visible cards.
        class EditWindow(MainWindow):
            def __init__(self):
                QMainWindow.__init__(self)
        win = EditWindow()
        win.images = grid._images
        win.image_grid = grid
        win.tag_panel = TagPanel(win)
        win.current_folder = str(dataset) if dataset else 'ram://benchmark'
        win.history = HistoryManager()
        win._undo_folders, win._redo_folders = [], []
        win.folder_tag_counts = Counter(tag for image in win.images for tag in image['tags'])
        win._counts_images = win.images
        win._pending_tag_deltas = []
        win._dict_data = {}
        win.tag_panel.load_tags(sorted(win.folder_tag_counts), win.folder_tag_counts)
        idx = min(grid._cards)
        rebuilds_before = grid.rebuild_count
        tick = time.perf_counter()
        win._on_individual_tag_add(idx, 'benchmark_edit')
        app.processEvents()
        grid.grab()
        single_edit_seconds = time.perf_counter() - tick
        history_entries = len(win.history._undo_stack[-1].images_before)
        tick = time.perf_counter()
        win.do_undo()
        app.processEvents()
        undo_seconds = time.perf_counter() - tick
        tick = time.perf_counter()
        win.do_redo()
        app.processEvents()
        redo_seconds = time.perf_counter() - tick
        edit_rebuilds = grid.rebuild_count - rebuilds_before
        assert history_entries == 1 and edit_rebuilds == 0
        win.deleteLater()
        decode_count = grid.thumbnails.decode_count
        cache_bytes = grid.thumbnails.cache_bytes
        # Active tasks finish before the QImageReader test patch is removed.
        grid.thumbnails.set_visible([])
        while grid.thumbnails.active:
            QTest.qWait(1)
        grid.close()
        grid.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    heartbeat.stop()
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mb = peak / (1024 * 1024 if sys.platform == 'darwin' else 1024)
    report = dict(count=args.count, rendered=rendered, mode=('batch' if args.mode == 'batch' else 'virtual-grid'), storage=args.storage,
                  first_view_seconds=first_view, max_live_cards=max_live_cards,
                  thumbnail_cache_mb=cache_bytes / 1024**2, thumbnail_decodes=decode_count,
                  longest_ui_heartbeat_gap_seconds=max(heartbeat_gaps, default=0),
                  single_edit_seconds=single_edit_seconds, undo_seconds=undo_seconds, redo_seconds=redo_seconds,
                  edit_grid_rebuilds=edit_rebuilds, history_images_for_single_edit=history_entries,
                  batch_size=batch, image_size=args.size, tags_per_image=args.tags + 1,
                  generation_seconds=generation, load_seconds=load_seconds,
                  render_seconds=elapsed, render_images_per_second=rendered / elapsed,
                  batch_p50_seconds=statistics.median(latencies),
                  batch_p95_seconds=sorted(latencies)[min(len(latencies)-1, int(len(latencies)*.95))],
                  longest_batch_seconds=max(latencies), peak_rss_mb=peak_mb,
                  platform=platform.platform(), python=sys.version, dataset=str(dataset) if dataset else None,
                  note=('16 shared PNG variants; real Qt decoding/painting. RAM mode excludes disk IO. '
                        'Disk load time measures the loader; production UI calls it in a worker. First-view timing starts after metadata load. Disk mode uses warm filesystem cache. Every image was decoded and painted by scrolling the virtual grid; only viewport cards exist at once.'))
    failures = []
    for name, value, limit in [('load_seconds', load_seconds, args.max_load_seconds),
                               ('render_seconds', elapsed, args.max_render_seconds),
                               ('peak_rss_mb', peak_mb, args.max_rss_mb)]:
        if limit is not None and value is not None and value > limit:
            failures.append(f'{name}: {value:.3f} > {limit}')
    report.update(passed=not failures, failures=failures)
    (run / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--storage', choices=['ram', 'disk'], default='ram')
    parser.add_argument('--count', type=positive, default=100000)
    parser.add_argument('--size', type=positive, default=64)
    parser.add_argument('--tags', type=positive, default=12)
    parser.add_argument('--extension', choices=['txt', 'cap', 'caption'], default='txt')
    parser.add_argument('--batch-size', type=positive, default=100)
    parser.add_argument('--mode', choices=['batch', 'full-grid', 'virtual-grid'], default='virtual-grid')
    parser.add_argument('--output', type=Path, default=Path('tests/artifacts'))
    parser.add_argument('--max-load-seconds', type=float)
    parser.add_argument('--max-render-seconds', type=float)
    parser.add_argument('--max-rss-mb', type=float)
    args = parser.parse_args()
    # Never overwrite a prior run or touch a real dataset.
    run = args.output / ('run_' + time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8])
    run.mkdir(parents=True, exist_ok=False)
    app = QApplication.instance() or QApplication([])
    try:
        return benchmark(args, app, run)
    except Exception as exc:
        (run / 'error.json').write_text(json.dumps({'passed': False, 'error': str(exc)}))
        raise


if __name__ == '__main__':
    raise SystemExit(main())
