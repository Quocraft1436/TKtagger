#!/bin/sh
# Double-click (Run) or invoke from any working directory.
set -eu
APP_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -x "$APP_ROOT/.venv/bin/python" ]; then
    APP_PYTHON="$APP_ROOT/.venv/bin/python"
elif [ -x "$APP_ROOT/venv/bin/python" ]; then
    APP_PYTHON="$APP_ROOT/venv/bin/python"
else
    APP_PYTHON=python3
fi
exec "$APP_PYTHON" "$APP_ROOT/launch.py" "$@"
