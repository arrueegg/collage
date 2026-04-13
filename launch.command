#!/bin/bash
# Double-click this file in Finder to launch the make_collages UI.
# On first run it will create a virtual environment and install dependencies.

set -e

# Always run relative to this script's location (works when double-clicked)
cd "$(dirname "$0")"

# ── Set up virtualenv on first run ────────────────────────────────────────────
if [ ! -f "env/bin/python" ]; then
    echo "First run: creating virtual environment..."
    python3 -m venv env
fi

# ── Install / upgrade dependencies if needed ──────────────────────────────────
echo "Checking dependencies..."
env/bin/pip install -q -e ".[heic,ui]"

# ── Launch the UI ─────────────────────────────────────────────────────────────
echo ""
echo "Starting make_collages UI — opening in your browser..."
echo "Press Ctrl+C in this window to stop the server."
echo ""
env/bin/python app.py
