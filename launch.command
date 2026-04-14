#!/bin/bash
# Double-click this file in Finder to launch the make_collages UI.
# On first run it will create a virtual environment and install dependencies.

set -e

# Always run relative to this script's location (works when double-clicked)
cd "$(dirname "$0")"

DEPS_MARKER="env/.deps-installed"
PYTHON_BIN=""

find_python() {
    for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 9) else 1)
PY
            then
                command -v "$candidate"
                return 0
            fi
        fi
    done

    return 1
}

if [ -f "env/bin/python" ]; then
    if ! env/bin/python - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 9) else 1)
PY
    then
        echo "Existing virtual environment uses an older Python; recreating it..."
        rm -rf env
    fi
fi

# ── Set up virtualenv on first run ────────────────────────────────────────────
if [ ! -f "env/bin/python" ]; then
    PYTHON_BIN="$(find_python)" || {
        echo "Python 3.9 or newer is required, but none was found."
        echo "Install a current Python from https://www.python.org/downloads/ and try again."
        exit 1
    }
    echo "First run: creating virtual environment..."
    "$PYTHON_BIN" -m venv env
    rm -f "$DEPS_MARKER"
fi

# ── Install / upgrade dependencies if needed ──────────────────────────────────
if [ ! -f "$DEPS_MARKER" ] || [ "pyproject.toml" -nt "$DEPS_MARKER" ] || [ "requirements.txt" -nt "$DEPS_MARKER" ]; then
    echo "Installing dependencies..."
    env/bin/python -m pip install --upgrade pip setuptools wheel
    env/bin/python -m pip install -q -e ".[heic,ui]"
    touch "$DEPS_MARKER"
else
    echo "Dependencies already installed; skipping check."
fi

# ── Launch the UI ─────────────────────────────────────────────────────────────
echo ""
echo "Starting make_collages UI — opening in your browser..."
echo "Press Ctrl+C in this window to stop the server."
echo ""
env/bin/python app.py
