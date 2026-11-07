"""Discover installed WD14 assets and run inference in their Python environment.

This module deliberately imports only the standard library. AI dependencies are
loaded by the worker, using the selected tool's interpreter.
"""
from collections import deque
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

TOOL_TYPES = {'kohya_ss': ('wd14_tagger_model',),
              'sd_scripts': ('wd14_tagger_model', 'models')}
PROGRESS_PREFIX = '@@TKTAGGER@@'


def detect_tool_type(root):
    root = Path(root).expanduser()
    if (root / 'kohya_gui').is_dir() or (root / 'kohya_gui.py').is_file():
        return 'kohya_ss'
    if (root / 'finetune').is_dir() and (root / 'library').is_dir():
        return 'sd_scripts'
    raise ValueError('Cannot identify this tool. Select Kohya_ss or sd-scripts explicitly.')


def discover_tool(tool_path, tool_type='auto'):
    if not str(tool_path).strip():
        raise ValueError('Select the installed tool folder first.')
    root = Path(tool_path).expanduser().absolute()
    if not root.is_dir():
        raise ValueError(f'Tool folder not found: {root}')
    kind = detect_tool_type(root) if tool_type == 'auto' else tool_type
    if kind not in TOOL_TYPES:
        raise ValueError(f'Unsupported tool type: {kind}')
    interpreters = [root / name / suffix for name in ('.venv', 'venv', 'env')
                    for suffix in ('bin/python', 'Scripts/python.exe')]
    python = next((p for p in interpreters if p.is_file() and os.access(p, os.X_OK)), None)
    models = []
    seen = set()
    for relative in TOOL_TYPES[kind]:
        model_root = root / relative
        if not model_root.is_dir():
            continue
        for onnx in sorted(model_root.rglob('*.onnx')):
            csv = onnx.with_name('selected_tags.csv')
            if csv.is_file() and onnx.resolve() not in seen:
                seen.add(onnx.resolve())
                models.append({'name': str(onnx.relative_to(root)),
                               'onnx_path': str(onnx), 'csv_path': str(csv)})
    return {'tool_path': str(root), 'tool_type': kind,
            'python_path': str(python) if python else '', 'models': models}


def validate_external_config(config):
    info = discover_tool(config.get('tool_path', ''), config.get('tool_type', 'auto'))
    python = Path(config.get('python_path') or info['python_path']).expanduser()
    if not str(config.get('python_path') or info['python_path']).strip() or not python.is_file() or not os.access(python, os.X_OK):
        raise ValueError('No working tool Python found. Select its Python executable; a moved venv may contain broken symlinks.')
    onnx = Path(config.get('onnx_path') or '').expanduser()
    csv = Path(config.get('csv_path') or '').expanduser()
    if not onnx.is_file() or not csv.is_file():
        raise ValueError('Select an installed ONNX model with selected_tags.csv.')
    return info, python.absolute(), onnx.absolute(), csv.absolute()


def run_external_tagger(config, progress_cb=None):
    info, python, onnx, csv = validate_external_config(config)
    worker_config = dict(config, onnx_path=str(onnx), csv_path=str(csv),
                         force_download=False)
    # Absolute paths survive the worker's tool-specific working directory.
    for key in ('target_folder', 'root_folder'):
        if worker_config.get(key):
            worker_config[key] = str(Path(worker_config[key]).absolute())
    worker = Path(__file__).with_name('tagger_worker.py')
    with tempfile.TemporaryDirectory(prefix='tktagger-worker-') as directory:
        request = Path(directory) / 'request.json'
        response = Path(directory) / 'response.json'
        request.write_text(json.dumps(worker_config, ensure_ascii=False), encoding='utf-8')
        env = dict(os.environ)
        for key in ('PYTHONPATH', 'PYTHONHOME'):
            env.pop(key, None)
        # Frozen Linux builds prepend their own libraries; external Python must
        # use the tool's native libraries instead of the bundle's copies.
        if 'LD_LIBRARY_PATH_ORIG' in env:
            env['LD_LIBRARY_PATH'] = env['LD_LIBRARY_PATH_ORIG']
        elif getattr(sys, 'frozen', False):
            env.pop('LD_LIBRARY_PATH', None)
        env['HF_HUB_OFFLINE'] = '1'
        env['VIRTUAL_ENV'] = str(python.parent.parent)
        env['PATH'] = str(python.parent) + os.pathsep + env.get('PATH', '')
        restore_dll_directory = None
        if sys.platform == 'win32' and getattr(sys, 'frozen', False):
            import ctypes
            restore_dll_directory = getattr(sys, '_MEIPASS', None)
            ctypes.windll.kernel32.SetDllDirectoryW(None)
        try:
            process = subprocess.Popen(
                [str(python), '-I', '-B', '-u', str(worker), str(request), str(response)],
                cwd=info['tool_path'], env=env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        finally:
            if restore_dll_directory is not None:
                ctypes.windll.kernel32.SetDllDirectoryW(restore_dll_directory)
        tail = deque(maxlen=30)
        try:
            for line in process.stdout:
                tail.append(line.rstrip())
                if line.startswith(PROGRESS_PREFIX):
                    message = json.loads(line[len(PROGRESS_PREFIX):])
                    if progress_cb:
                        progress_cb(*message)
            code = process.wait()
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        if code or not response.is_file():
            raise RuntimeError('Tool Python could not run WD14. Check numpy, Pillow and onnxruntime in that venv.\n' + '\n'.join(tail))
        return json.loads(response.read_text(encoding='utf-8'))
