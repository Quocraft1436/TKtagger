"""Entry point executed by an installed tool's Python, never by Qt."""
import json
from pathlib import Path
import sys


def main():
    # -I isolates the worker from the GUI environment; load only our backend.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(1, str(Path(__file__).resolve().parent.parent))
    from tagger_logic import run_tagger
    from external_tagger import PROGRESS_PREFIX
    config = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))

    def progress(current, total, message):
        print(PROGRESS_PREFIX + json.dumps([current, total, message]), flush=True)

    result = run_tagger(config, progress)
    Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
