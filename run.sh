#!/usr/bin/env bash
# ==============================================================================
# XTTS Studio - Standalone Desktop Launcher
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=5222

echo "🎙️ Starting XTTS Studio..."

# 1. Check if XTTS Studio server is running
if ! curl -s "http://127.0.0.1:${PORT}/api/status" >/dev/null 2>&1; then
    echo "🚀 Launching XTTS Studio server on http://127.0.0.1:${PORT}..."
    python3 "$SCRIPT_DIR/app.py" &
    sleep 0.8
else
    echo "ℹ️ XTTS Studio server already active on port ${PORT}."
fi

# 2. Open UI in standalone App mode
URL="http://127.0.0.1:${PORT}"
if [ -x "/opt/google/chrome/google-chrome" ]; then
    echo "🖥️ Opening Chrome App window..."
    exec /opt/google/chrome/google-chrome --app="$URL" "$@"
elif command -v xdg-open >/dev/null 2>&1; then
    exec xdg-open "$URL"
else
    echo "Please open $URL in your web browser."
fi
