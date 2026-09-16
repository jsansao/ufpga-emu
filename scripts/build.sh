#!/bin/bash
# Build firmware for target (esp32 or rp2040)
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-esp32}"
PIO="${SCRIPT_DIR}/.venv/bin/pio"
if [ ! -x "$PIO" ]; then
    PIO="$(which pio 2>/dev/null || /tmp/opencode/venv/bin/pio)"
fi
cd "$SCRIPT_DIR"
echo "Building for: $TARGET"
$PIO run -e "$TARGET"
echo "Build complete: $TARGET"
