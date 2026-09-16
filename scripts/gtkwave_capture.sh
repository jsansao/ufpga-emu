#!/bin/bash
# Script para abrir GTKWave em Xvfb, esperar carregar, capturar PNG.
# Uso: bash scripts/gtkwave_capture.sh <vcd_file> <png_output>

VCD_FILE="$1"
PNG_FILE="${2:-/tmp/gtkwave_waveform.png}"

if [ -z "$VCD_FILE" ] || [ ! -f "$VCD_FILE" ]; then
    echo "Uso: $0 <vcd_file> [png_output]"
    exit 1
fi

# Limpar
pkill -9 Xvfb 2>/dev/null
pkill -9 gtkwave 2>/dev/null
sleep 1

# Iniciar Xvfb em :99
Xvfb :99 -screen 0 1920x1080x24 -ac &
XVFB_PID=$!
sleep 2

export DISPLAY=:99

# Verificar que Xvfb está rodando
if ! xdpyinfo -display :99 >/dev/null 2>&1; then
    echo "Erro: Xvfb não iniciou"
    kill -9 $XVFB_PID
    exit 1
fi

# Iniciar GTKWave em background
gtkwave "$VCD_FILE" > /tmp/gtkwave.log 2>&1 &
GTK_PID=$!

# Esperar carregar
echo "Aguardando GTKWave carregar..."
sleep 8

# Capturar
echo "Capturando screenshot..."
import -window root "$PNG_FILE" 2>&1

# Matar tudo
kill -9 $GTK_PID 2>/dev/null
kill -9 $XVFB_PID 2>/dev/null
pkill -9 gtkwave 2>/dev/null
pkill -9 Xvfb 2>/dev/null
sleep 1

if [ -f "$PNG_FILE" ]; then
    SIZE=$(stat -c%s "$PNG_FILE")
    echo "OK: $PNG_FILE ($SIZE bytes)"
    identify "$PNG_FILE" 2>/dev/null || file "$PNG_FILE"
else
    echo "Erro: PNG não gerado"
    exit 1
fi
