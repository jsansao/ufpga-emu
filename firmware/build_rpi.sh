#!/usr/bin/env bash
#
# build_rpi.sh — Compila o uFPGA-Emu para Raspberry Pi com GPIO real
#
# Uso:
#   ./build_rpi.sh                           # compila blinky (padrão)
#   ./build_rpi.sh counter                    # compila counter
#   ./build_rpi.sh blinky                     # compila blinky
#   CIRCUIT=counter ./build_rpi.sh            # via env var
#   ./build_rpi.sh blinky clean               # compila e limpa objetos
#
# Pré-requisitos na Pi:
#   sudo apt install gcc make

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"
LIB_DIR="$SCRIPT_DIR/lib"

CIRCUIT="${CIRCUIT:-${1:-blinky}}"
CLEAN="${2:-}"

# Mapeia nome do circuito para define
case "$CIRCUIT" in
    counter)         DEFINE="EMU_CIRCUIT_COUNTER" ;;
    fsm_101)         DEFINE="EMU_CIRCUIT_FSM_101" ;;
    shift_register)  DEFINE="EMU_CIRCUIT_SHIFT_REGISTER" ;;
    param_counter)   DEFINE="EMU_CIRCUIT_PARAM_COUNTER" ;;
    pwm)             DEFINE="EMU_CIRCUIT_PWM" ;;
    uart_tx)         DEFINE="EMU_CIRCUIT_UART_TX" ;;
    tiny_cpu)        DEFINE="EMU_CIRCUIT_TINY_CPU" ;;
    task_func)       DEFINE="EMU_CIRCUIT_TASK_FUNC" ;;
    reduction)       DEFINE="EMU_CIRCUIT_REDUCTION" ;;
    priority_encoder) DEFINE="EMU_CIRCUIT_PRIORITY_ENCODER" ;;
    decoder)         DEFINE="EMU_CIRCUIT_DECODER" ;;
    mixed)           DEFINE="EMU_CIRCUIT_MIXED" ;;
    mux)             DEFINE="EMU_CIRCUIT_MUX" ;;
    mux2)            DEFINE="EMU_CIRCUIT_MUX2" ;;
    negedge_counter) DEFINE="EMU_CIRCUIT_NEGEDGE_COUNTER" ;;
    sign_extend)     DEFINE="EMU_CIRCUIT_SIGN_EXTEND" ;;
    concat_multi)    DEFINE="EMU_CIRCUIT_CONCAT_MULTI" ;;
    part_select_lhs) DEFINE="EMU_CIRCUIT_PART_SELECT_LHS" ;;
    adder_n)         DEFINE="EMU_CIRCUIT_ADDER_N" ;;
    case_equality)   DEFINE="EMU_CIRCUIT_CASE_EQUALITY" ;;
    not_keyword)     DEFINE="EMU_CIRCUIT_NOT_KEYWORD" ;;
    localparam)      DEFINE="EMU_CIRCUIT_LOCALPARAM_EXAMPLE" ;;
    module_inst)     DEFINE="EMU_CIRCUIT_MODULE_INST" ;;
    repeat_example)  DEFINE="EMU_CIRCUIT_REPEAT_EXAMPLE" ;;
    blinky|*)        DEFINE="EMU_CIRCUIT_BLINKY" ;;
esac

OUTPUT="ufpga_emu_${CIRCUIT}"

CFLAGS="-DRPI_GPIO -D$DEFINE"
CFLAGS="$CFLAGS -I$LIB_DIR/hal/include -I$LIB_DIR/runtime/include"
CFLAGS="$CFLAGS -O2 -Wall -Wextra -Wno-unused-parameter"
LDFLAGS="-lpthread -lm"

RUNTIME_SRC="$LIB_DIR/runtime/src"
HAL_SRC="$LIB_DIR/hal/src"

set -x

if [ "$CLEAN" = "clean" ]; then
    rm -f "$SCRIPT_DIR"/ufpga_emu_*
    echo "Limpou."
    exit 0
fi

gcc $CFLAGS \
    "$SRC_DIR/main_rpi.c" \
    "$HAL_SRC/hal_gpio.c" \
    "$HAL_SRC/hal_mutex.c" \
    "$HAL_SRC/hal_timer.c" \
    "$HAL_SRC/hal_serial.c" \
    "$RUNTIME_SRC/emulator.c" \
    "$RUNTIME_SRC/pin_map.c" \
    "$RUNTIME_SRC/telemetry.c" \
    "$RUNTIME_SRC/vcd_writer.c" \
    $LDFLAGS \
    -o "$SCRIPT_DIR/$OUTPUT"

echo "OK: $OUTPUT"
