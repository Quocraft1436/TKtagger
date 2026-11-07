"""Start from a checkout; --setup installs just the GUI in a private .venv."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def main():
    args = sys.argv[1:]
    if '--setup' in args:
        args.remove('--setup')
        environment = ROOT / '.venv'
        python = environment / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
        if not python.exists():
            venv.EnvBuilder(with_pip=True).create(environment)
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')], check=True)
        return subprocess.call([str(python), str(ROOT / 'launch.py'), *args])
    if importlib.util.find_spec('PySide6') is None:
        print('PySide6 is missing. Run launch.sh --setup (Windows: launch.cmd --setup), or use a packaged build.', file=sys.stderr)
        return 1
    from main import main as run
    sys.argv = [str(ROOT / 'main.py'), *args]
    run()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
