"""Read-only bundle resources and writable application data paths."""
import json
import os
from pathlib import Path
import sys

DEFAULT_REPO = 'SmilingWolf/wd-v1-4-convnextv2-tagger-v2'


def resource_path(*parts):
    return Path(__file__).resolve().parent.parent.joinpath(*parts)


def user_file(name):
    override = os.environ.get('TKTAGGER_DATA_DIR')
    if override:
        root = Path(override).expanduser()
    elif not getattr(sys, 'frozen', False):
        root = resource_path()
    elif sys.platform == 'win32':
        root = Path(os.environ.get('APPDATA', Path.home() / 'AppData/Roaming')) / 'TKtagger'
    elif sys.platform == 'darwin':
        root = Path.home() / 'Library/Application Support/TKtagger'
    else:
        root = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'TKtagger'
    root.mkdir(parents=True, exist_ok=True)
    return root / name


def build_info():
    path = resource_path('build_info.json')
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}


def local_ai_available():
    return build_info().get('with_onnx', True)


def bundled_model(repo_id=None):
    repo_id = repo_id or build_info().get('model_repo') or DEFAULT_REPO
    root = resource_path('bundled_models')
    onnx, csv = root / 'model.onnx', root / 'selected_tags.csv'
    if repo_id == build_info().get('model_repo') and onnx.is_file() and csv.is_file():
        return str(onnx), str(csv)
    return None
