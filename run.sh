#!/usr/bin/env bash
# ====================================================================
#  CuteMix - MOTU PCIe-424 + 24i Mixer Console Launcher (Unix/macOS)
# ====================================================================

set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -f ".venv/bin/python" ]; then
    exec ".venv/bin/python" app.py "$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 app.py "$@"
else
    echo "Python 3 is required but not installed." >&2
    exit 1
fi
