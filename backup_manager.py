"""Folder snapshots completed before any persistent dataset mutation."""
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import shutil
import uuid

BACKUP_DIR = '.tktagger-backups'


def backup_folder(folder, action='change'):
    """Copy the complete folder, preserving symlinks and excluding old backups.

    On failure raises before the caller may mutate data. Incomplete snapshots
    retain a .partial suffix and must not be used for restore.
    """
    source = Path(folder).resolve(strict=True)
    if not source.is_dir():
        raise NotADirectoryError(source)
    root = source.parent / BACKUP_DIR
    if root.is_symlink():
        raise ValueError('Backup directory must not be a symlink')
    root.mkdir(exist_ok=True)
    root = root / (source.name + "_" + hashlib.sha256(str(source).encode()).hexdigest()[:12])
    if root.is_symlink():
        raise ValueError("Backup namespace must not be a symlink")
    root.mkdir(exist_ok=True)
    name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ') + '_' + uuid.uuid4().hex[:8]
    partial = root / (name + '.partial')
    partial.mkdir()
    shutil.copytree(source, partial / 'data', symlinks=True,
                    ignore=shutil.ignore_patterns(BACKUP_DIR))
    (partial / 'manifest.json').write_text(json.dumps({
        'source': str(source), 'action': action, 'created_utc': name,
        'excluded_directory': BACKUP_DIR,
    }, indent=2), encoding='utf-8')
    complete = root / name
    partial.rename(complete)
    return complete


def backup_api_folder(folder, recursive=False):
    """The external API has no backup-directory exclusion option."""
    if not folder:
        raise ValueError('API target folder is required for backup')
    source = Path(folder).resolve(strict=True)
    if recursive:
        import os
        for _, dirs, _ in os.walk(source):
            if BACKUP_DIR in dirs:
                raise ValueError(
                    'Recursive API tagging would include existing backup archives. '
                    'Use local tagging or disable recursive API tagging.')
    return backup_folder(source, 'tagger_api')
