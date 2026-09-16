#!/bin/bash
# Full CI: generate all examples + build both targets
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "=== Gerando C dos exemplos ==="
for v in examples/*.v; do
    scripts/generate.sh "$v"
done

echo ""
echo "=== Build ESP32 ==="
scripts/build.sh esp32

echo ""
echo "=== Build RP2040 ==="
scripts/build.sh rp2040

echo ""
echo "=== CI OK ==="
