#!/bin/bash
# Generate C code from Verilog using pc_tool
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INPUT="$1"
OUTPUT="${2:-${SCRIPT_DIR}/generated/$(basename "$INPUT" .v).c}"
mkdir -p "$(dirname "$OUTPUT")"
python3 -m pc_tool.cli "$INPUT" -o "$OUTPUT"
echo "Generated: $OUTPUT"
