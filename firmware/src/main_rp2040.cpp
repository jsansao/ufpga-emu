#include <stdio.h>
#include "pico/multicore.h"

#include <Arduino.h>
#include <USB/PluggableUSBSerial.h>

extern "C" {
#include "hal_gpio.h"
#include "hal_timer.h"
#include "hal_serial.h"
#include "emulator.h"
#include "telemetry.h"
}

// -------------------------------------------------------------------
// USB CDC serial wrappers (called from hal_serial.c via extern)
// -------------------------------------------------------------------
extern "C" {

void hal_serial_rp2040_init(uint32_t baud)
{
    (void)baud;
}

void hal_serial_rp2040_send_byte(uint8_t data)
{
    if (!Serial) return;
    Serial.write(data);
}

void hal_serial_rp2040_send_buffer(const uint8_t *data, size_t len)
{
    if (!Serial) return;
    Serial.write(data, len);
}

int hal_serial_rp2040_receive_byte(uint8_t *data)
{
    if (Serial.available()) {
        *data = Serial.read();
        return 0;
    }
    return -1;
}

} // extern "C"

// -------------------------------------------------------------------
// Loop-based telemetry and command processing
// -------------------------------------------------------------------
static emulator_config_t *loop_cfg = NULL;
static uint32_t loop_last_report = 0;
static uint32_t loop_last_cmd = 0;
static uint64_t loop_last_clock = 0;
static char cmd_line[128];
static size_t cmd_line_len = 0;

void loop(void);  // forward declaration

static void send_snapshot_telemetry(const model_state_t *snap, uint32_t now)
{
    uint64_t elapsed_us = (uint64_t)(now - loop_last_report);
    uint64_t clock_delta = (uint64_t)(snap->clock_count - loop_last_clock);
    uint32_t freq_hz = 0;

    if (elapsed_us > 0 && clock_delta > 0) {
        freq_hz = (uint32_t)((clock_delta * 1000000ull) / elapsed_us);
    }

    telemetry_set_freq(freq_hz);
    telemetry_send_state(snap);
    loop_last_report = now;
    loop_last_clock = snap->clock_count;
}

// -------------------------------------------------------------------
// Pin mapping and circuit definition (unchanged from before)
// -------------------------------------------------------------------

/*
 * Pin mapping RP2040:
 *   GPIO 0-1  = UART0 (serial console, não usar)
 *   GPIO 2    = clk (virtual)
 *   GPIO 3    = rst
 *   GPIO 4-11 = inputs (bidirecionais)
 *   GPIO 12-24 = outputs
 *   GPIO 25   = LED onboard (Pico)
 *   GPIO 26-28 = inputs (ADC compartilhado, uso digital)
 */

#if defined(EMU_CIRCUIT_COUNTER)
#include "circuit_counter.c"
#define CIRCUIT_NAME "counter"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":3,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"count[0]\",\"pin\":12,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"count[1]\",\"pin\":13,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"count[2]\",\"pin\":14,\"bit\":2,\"dir\":\"output\"},"
    "  {\"name\":\"count[3]\",\"pin\":15,\"bit\":3,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_FSM_101)
#include "circuit_fsm_101.c"
#define CIRCUIT_NAME "fsm_101"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":3,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"data_in\",\"pin\":4,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"detected\",\"pin\":25,\"bit\":0,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_SHIFT_REGISTER)
#include "circuit_shift_register.c"
#define CIRCUIT_NAME "shift_register"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":3,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"load\",\"pin\":4,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"data_in\",\"pin\":5,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"parallel_load[0]\",\"pin\":6,\"bit\":4,\"dir\":\"input\"},"
    "  {\"name\":\"parallel_load[1]\",\"pin\":7,\"bit\":5,\"dir\":\"input\"},"
    "  {\"name\":\"parallel_load[2]\",\"pin\":8,\"bit\":6,\"dir\":\"input\"},"
    "  {\"name\":\"parallel_load[3]\",\"pin\":9,\"bit\":7,\"dir\":\"input\"},"
    "  {\"name\":\"parallel_load[4]\",\"pin\":10,\"bit\":8,\"dir\":\"input\"},"
    "  {\"name\":\"parallel_load[5]\",\"pin\":11,\"bit\":9,\"dir\":\"input\"},"
    "  {\"name\":\"parallel_load[6]\",\"pin\":26,\"bit\":10,\"dir\":\"input\"},"
    "  {\"name\":\"parallel_load[7]\",\"pin\":27,\"bit\":11,\"dir\":\"input\"},"
    "  {\"name\":\"data_out[0]\",\"pin\":25,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"data_out[1]\",\"pin\":12,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"data_out[2]\",\"pin\":13,\"bit\":2,\"dir\":\"output\"},"
    "  {\"name\":\"data_out[3]\",\"pin\":14,\"bit\":3,\"dir\":\"output\"},"
    "  {\"name\":\"data_out[4]\",\"pin\":15,\"bit\":4,\"dir\":\"output\"},"
    "  {\"name\":\"data_out[5]\",\"pin\":16,\"bit\":5,\"dir\":\"output\"},"
    "  {\"name\":\"data_out[6]\",\"pin\":17,\"bit\":6,\"dir\":\"output\"},"
    "  {\"name\":\"data_out[7]\",\"pin\":18,\"bit\":7,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_PARAM_COUNTER)
#include "circuit_param_counter.c"
#define CIRCUIT_NAME "param_counter"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":3,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"count[0]\",\"pin\":4,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"count[1]\",\"pin\":5,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"count[2]\",\"pin\":6,\"bit\":2,\"dir\":\"output\"},"
    "  {\"name\":\"count[3]\",\"pin\":7,\"bit\":3,\"dir\":\"output\"},"
    "  {\"name\":\"count[4]\",\"pin\":8,\"bit\":4,\"dir\":\"output\"},"
    "  {\"name\":\"count[5]\",\"pin\":9,\"bit\":5,\"dir\":\"output\"},"
    "  {\"name\":\"count[6]\",\"pin\":10,\"bit\":6,\"dir\":\"output\"},"
    "  {\"name\":\"count[7]\",\"pin\":11,\"bit\":7,\"dir\":\"output\"},"
    "  {\"name\":\"overflow\",\"pin\":25,\"bit\":8,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_PWM)
#include "circuit_pwm.c"
#define CIRCUIT_NAME "pwm"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":3,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"enable\",\"pin\":4,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"duty[0]\",\"pin\":5,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"duty[1]\",\"pin\":6,\"bit\":4,\"dir\":\"input\"},"
    "  {\"name\":\"duty[2]\",\"pin\":7,\"bit\":5,\"dir\":\"input\"},"
    "  {\"name\":\"duty[3]\",\"pin\":8,\"bit\":6,\"dir\":\"input\"},"
    "  {\"name\":\"duty[4]\",\"pin\":9,\"bit\":7,\"dir\":\"input\"},"
    "  {\"name\":\"duty[5]\",\"pin\":10,\"bit\":8,\"dir\":\"input\"},"
    "  {\"name\":\"duty[6]\",\"pin\":11,\"bit\":9,\"dir\":\"input\"},"
    "  {\"name\":\"duty[7]\",\"pin\":26,\"bit\":10,\"dir\":\"input\"},"
    "  {\"name\":\"period[0]\",\"pin\":27,\"bit\":11,\"dir\":\"input\"},"
    "  {\"name\":\"period[1]\",\"pin\":28,\"bit\":12,\"dir\":\"input\"},"
    "  {\"name\":\"period[2]\",\"pin\":4,\"bit\":13,\"dir\":\"input\"},"
    "  {\"name\":\"period[3]\",\"pin\":5,\"bit\":14,\"dir\":\"input\"},"
    "  {\"name\":\"period[4]\",\"pin\":6,\"bit\":15,\"dir\":\"input\"},"
    "  {\"name\":\"period[5]\",\"pin\":7,\"bit\":16,\"dir\":\"input\"},"
    "  {\"name\":\"period[6]\",\"pin\":8,\"bit\":17,\"dir\":\"input\"},"
    "  {\"name\":\"period[7]\",\"pin\":9,\"bit\":18,\"dir\":\"input\"},"
    "  {\"name\":\"pwm_out\",\"pin\":25,\"bit\":0,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_UART_TX)
#include "circuit_uart_tx.c"
#define CIRCUIT_NAME "uart_tx"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":3,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"send\",\"pin\":4,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"data[0]\",\"pin\":5,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"data[1]\",\"pin\":6,\"bit\":4,\"dir\":\"input\"},"
    "  {\"name\":\"data[2]\",\"pin\":7,\"bit\":5,\"dir\":\"input\"},"
    "  {\"name\":\"data[3]\",\"pin\":8,\"bit\":6,\"dir\":\"input\"},"
    "  {\"name\":\"data[4]\",\"pin\":9,\"bit\":7,\"dir\":\"input\"},"
    "  {\"name\":\"data[5]\",\"pin\":10,\"bit\":8,\"dir\":\"input\"},"
    "  {\"name\":\"data[6]\",\"pin\":11,\"bit\":9,\"dir\":\"input\"},"
    "  {\"name\":\"data[7]\",\"pin\":26,\"bit\":10,\"dir\":\"input\"},"
    "  {\"name\":\"tx\",\"pin\":25,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"busy\",\"pin\":12,\"bit\":1,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_TINY_CPU)
#include "circuit_tiny_cpu.c"
#define CIRCUIT_NAME "tiny_cpu"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":3,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"run\",\"pin\":4,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"instr[0]\",\"pin\":5,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"instr[1]\",\"pin\":6,\"bit\":4,\"dir\":\"input\"},"
    "  {\"name\":\"instr[2]\",\"pin\":7,\"bit\":5,\"dir\":\"input\"},"
    "  {\"name\":\"instr[3]\",\"pin\":8,\"bit\":6,\"dir\":\"input\"},"
    "  {\"name\":\"instr[4]\",\"pin\":9,\"bit\":7,\"dir\":\"input\"},"
    "  {\"name\":\"instr[5]\",\"pin\":10,\"bit\":8,\"dir\":\"input\"},"
    "  {\"name\":\"instr[6]\",\"pin\":11,\"bit\":9,\"dir\":\"input\"},"
    "  {\"name\":\"instr[7]\",\"pin\":26,\"bit\":10,\"dir\":\"input\"},"
    "  {\"name\":\"instr[8]\",\"pin\":27,\"bit\":11,\"dir\":\"input\"},"
    "  {\"name\":\"instr[9]\",\"pin\":28,\"bit\":12,\"dir\":\"input\"},"
    "  {\"name\":\"instr[10]\",\"pin\":4,\"bit\":13,\"dir\":\"input\"},"
    "  {\"name\":\"instr[11]\",\"pin\":5,\"bit\":14,\"dir\":\"input\"},"
    "  {\"name\":\"instr[12]\",\"pin\":6,\"bit\":15,\"dir\":\"input\"},"
    "  {\"name\":\"instr[13]\",\"pin\":7,\"bit\":16,\"dir\":\"input\"},"
    "  {\"name\":\"instr[14]\",\"pin\":8,\"bit\":17,\"dir\":\"input\"},"
    "  {\"name\":\"instr[15]\",\"pin\":9,\"bit\":18,\"dir\":\"input\"},"
    "  {\"name\":\"pc[0]\",\"pin\":12,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"pc[1]\",\"pin\":13,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"pc[2]\",\"pin\":14,\"bit\":2,\"dir\":\"output\"},"
    "  {\"name\":\"pc[3]\",\"pin\":15,\"bit\":3,\"dir\":\"output\"},"
    "  {\"name\":\"pc[4]\",\"pin\":16,\"bit\":4,\"dir\":\"output\"},"
    "  {\"name\":\"halted\",\"pin\":25,\"bit\":16,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_TASK_FUNC)
#include "circuit_task_func.c"
#define CIRCUIT_NAME "task_func"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":3,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"a[0]\",\"pin\":4,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"a[1]\",\"pin\":5,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"a[2]\",\"pin\":6,\"bit\":4,\"dir\":\"input\"},"
    "  {\"name\":\"a[3]\",\"pin\":7,\"bit\":5,\"dir\":\"input\"},"
    "  {\"name\":\"b[0]\",\"pin\":8,\"bit\":6,\"dir\":\"input\"},"
    "  {\"name\":\"b[1]\",\"pin\":9,\"bit\":7,\"dir\":\"input\"},"
    "  {\"name\":\"b[2]\",\"pin\":10,\"bit\":8,\"dir\":\"input\"},"
    "  {\"name\":\"b[3]\",\"pin\":11,\"bit\":9,\"dir\":\"input\"},"
    "  {\"name\":\"result[0]\",\"pin\":25,\"bit\":0,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_REDUCTION)
#include "circuit_reduction.c"
#define CIRCUIT_NAME "reduction"
static const char *pinmap_json =
    "["
    "  {\"name\":\"data[0]\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"data[1]\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"data[2]\",\"pin\":6,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"data[3]\",\"pin\":7,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"data[4]\",\"pin\":8,\"bit\":4,\"dir\":\"input\"},"
    "  {\"name\":\"data[5]\",\"pin\":9,\"bit\":5,\"dir\":\"input\"},"
    "  {\"name\":\"data[6]\",\"pin\":10,\"bit\":6,\"dir\":\"input\"},"
    "  {\"name\":\"data[7]\",\"pin\":11,\"bit\":7,\"dir\":\"input\"},"
    "  {\"name\":\"parity\",\"pin\":25,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"all_ones\",\"pin\":12,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"any_one\",\"pin\":13,\"bit\":2,\"dir\":\"output\"},"
    "  {\"name\":\"not_zero\",\"pin\":14,\"bit\":3,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_PRIORITY_ENCODER)
#include "circuit_priority_encoder.c"
#define CIRCUIT_NAME "priority_encoder"
static const char *pinmap_json =
    "["
    "  {\"name\":\"req[0]\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"req[1]\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"req[2]\",\"pin\":6,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"req[3]\",\"pin\":7,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"code[0]\",\"pin\":12,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"code[1]\",\"pin\":13,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"valid\",\"pin\":25,\"bit\":2,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_DECODER)
#include "circuit_decoder.c"
#define CIRCUIT_NAME "decoder"
static const char *pinmap_json =
    "["
    "  {\"name\":\"addr[0]\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"addr[1]\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"y[0]\",\"pin\":25,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"y[1]\",\"pin\":12,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"y[2]\",\"pin\":13,\"bit\":2,\"dir\":\"output\"},"
    "  {\"name\":\"y[3]\",\"pin\":14,\"bit\":3,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_MIXED)
#include "circuit_mixed.c"
#define CIRCUIT_NAME "mixed"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":3,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"a\",\"pin\":4,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"b\",\"pin\":5,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"count[0]\",\"pin\":12,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"count[1]\",\"pin\":13,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"y\",\"pin\":25,\"bit\":2,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_MUX)
#include "circuit_mux.c"
#define CIRCUIT_NAME "mux"
static const char *pinmap_json =
    "["
    "  {\"name\":\"a\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"b\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"sel\",\"pin\":6,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"y\",\"pin\":25,\"bit\":0,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_MUX2)
#include "circuit_mux2.c"
#define CIRCUIT_NAME "mux2"
static const char *pinmap_json =
    "["
    "  {\"name\":\"a[0]\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"a[1]\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"b[0]\",\"pin\":6,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"b[1]\",\"pin\":7,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"sel\",\"pin\":8,\"bit\":4,\"dir\":\"input\"},"
    "  {\"name\":\"y[0]\",\"pin\":25,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"y[1]\",\"pin\":12,\"bit\":1,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_NEGEDGE_COUNTER)
#include "circuit_negedge_counter.c"
#define CIRCUIT_NAME "negedge_counter"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":3,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"count[0]\",\"pin\":12,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"count[1]\",\"pin\":13,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"count[2]\",\"pin\":14,\"bit\":2,\"dir\":\"output\"},"
    "  {\"name\":\"count[3]\",\"pin\":15,\"bit\":3,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_SIGN_EXTEND)
#include "circuit_sign_extend.c"
#define CIRCUIT_NAME "sign_extend"
static const char *pinmap_json =
    "["
    "  {\"name\":\"value[0]\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"value[1]\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"value[2]\",\"pin\":6,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"value[3]\",\"pin\":7,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"extended[0]\",\"pin\":10,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"extended[1]\",\"pin\":11,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"extended[2]\",\"pin\":12,\"bit\":2,\"dir\":\"output\"},"
    "  {\"name\":\"extended[3]\",\"pin\":13,\"bit\":3,\"dir\":\"output\"},"
    "  {\"name\":\"extended[4]\",\"pin\":14,\"bit\":4,\"dir\":\"output\"},"
    "  {\"name\":\"extended[5]\",\"pin\":15,\"bit\":5,\"dir\":\"output\"},"
    "  {\"name\":\"extended[6]\",\"pin\":16,\"bit\":6,\"dir\":\"output\"},"
    "  {\"name\":\"extended[7]\",\"pin\":17,\"bit\":7,\"dir\":\"output\"},"
    "  {\"name\":\"sign_bit\",\"pin\":25,\"bit\":8,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_CONCAT_MULTI)
#include "circuit_concat_multi.c"
#define CIRCUIT_NAME "concat_multi"
static const char *pinmap_json =
    "["
    "  {\"name\":\"value[0]\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"value[1]\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"value[2]\",\"pin\":6,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"value[3]\",\"pin\":7,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"out[0]\",\"pin\":12,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"out[1]\",\"pin\":13,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"out[2]\",\"pin\":14,\"bit\":2,\"dir\":\"output\"},"
    "  {\"name\":\"out[3]\",\"pin\":15,\"bit\":3,\"dir\":\"output\"},"
    "  {\"name\":\"out[4]\",\"pin\":16,\"bit\":4,\"dir\":\"output\"},"
    "  {\"name\":\"out[5]\",\"pin\":17,\"bit\":5,\"dir\":\"output\"},"
    "  {\"name\":\"out[6]\",\"pin\":18,\"bit\":6,\"dir\":\"output\"},"
    "  {\"name\":\"out[7]\",\"pin\":19,\"bit\":7,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_PART_SELECT_LHS)
#include "circuit_part_select_lhs.c"
#define CIRCUIT_NAME "part_select_lhs"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"value[0]\",\"pin\":4,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"value[1]\",\"pin\":5,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"value[2]\",\"pin\":6,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"value[3]\",\"pin\":7,\"bit\":4,\"dir\":\"input\"},"
    "  {\"name\":\"load\",\"pin\":8,\"bit\":5,\"dir\":\"input\"},"
    "  {\"name\":\"out[0]\",\"pin\":12,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"out[1]\",\"pin\":13,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"out[2]\",\"pin\":14,\"bit\":2,\"dir\":\"output\"},"
    "  {\"name\":\"out[3]\",\"pin\":15,\"bit\":3,\"dir\":\"output\"},"
    "  {\"name\":\"out[4]\",\"pin\":16,\"bit\":4,\"dir\":\"output\"},"
    "  {\"name\":\"out[5]\",\"pin\":17,\"bit\":5,\"dir\":\"output\"},"
    "  {\"name\":\"out[6]\",\"pin\":18,\"bit\":6,\"dir\":\"output\"},"
    "  {\"name\":\"out[7]\",\"pin\":19,\"bit\":7,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_ADDER_N)
#include "circuit_adder_n.c"
#define CIRCUIT_NAME "adder_n"
static const char *pinmap_json =
    "["
    "  {\"name\":\"a[0]\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"a[1]\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"a[2]\",\"pin\":6,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"a[3]\",\"pin\":7,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"b[0]\",\"pin\":8,\"bit\":4,\"dir\":\"input\"},"
    "  {\"name\":\"b[1]\",\"pin\":9,\"bit\":5,\"dir\":\"input\"},"
    "  {\"name\":\"b[2]\",\"pin\":10,\"bit\":6,\"dir\":\"input\"},"
    "  {\"name\":\"b[3]\",\"pin\":11,\"bit\":7,\"dir\":\"input\"},"
    "  {\"name\":\"sum[0]\",\"pin\":12,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"sum[1]\",\"pin\":13,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"sum[2]\",\"pin\":14,\"bit\":2,\"dir\":\"output\"},"
    "  {\"name\":\"sum[3]\",\"pin\":15,\"bit\":3,\"dir\":\"output\"},"
    "  {\"name\":\"carry\",\"pin\":25,\"bit\":4,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_CASE_EQUALITY)
#include "circuit_case_equality.c"
#define CIRCUIT_NAME "case_equality"
static const char *pinmap_json =
    "["
    "  {\"name\":\"a[0]\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"a[1]\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"a[2]\",\"pin\":6,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"a[3]\",\"pin\":7,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"b[0]\",\"pin\":8,\"bit\":4,\"dir\":\"input\"},"
    "  {\"name\":\"b[1]\",\"pin\":9,\"bit\":5,\"dir\":\"input\"},"
    "  {\"name\":\"b[2]\",\"pin\":10,\"bit\":6,\"dir\":\"input\"},"
    "  {\"name\":\"b[3]\",\"pin\":11,\"bit\":7,\"dir\":\"input\"},"
    "  {\"name\":\"eq\",\"pin\":25,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"neq\",\"pin\":12,\"bit\":1,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_NOT_KEYWORD)
#include "circuit_not_keyword.c"
#define CIRCUIT_NAME "not_keyword"
static const char *pinmap_json =
    "["
    "  {\"name\":\"a\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"b\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"y\",\"pin\":25,\"bit\":0,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_LOCALPARAM_EXAMPLE)
#include "circuit_localparam_example.c"
#define CIRCUIT_NAME "localparam_example"
static const char *pinmap_json =
    "["
    "  {\"name\":\"in[0]\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"in[1]\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"in[2]\",\"pin\":6,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"in[3]\",\"pin\":7,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"out[0]\",\"pin\":25,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"out[1]\",\"pin\":12,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"out[2]\",\"pin\":13,\"bit\":2,\"dir\":\"output\"},"
    "  {\"name\":\"out[3]\",\"pin\":14,\"bit\":3,\"dir\":\"output\"},"
    "  {\"name\":\"out[4]\",\"pin\":15,\"bit\":4,\"dir\":\"output\"},"
    "  {\"name\":\"out[5]\",\"pin\":16,\"bit\":5,\"dir\":\"output\"},"
    "  {\"name\":\"out[6]\",\"pin\":17,\"bit\":6,\"dir\":\"output\"},"
    "  {\"name\":\"out[7]\",\"pin\":18,\"bit\":7,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_MODULE_INST)
#include "circuit_module_inst.c"
#define CIRCUIT_NAME "module_inst"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"d\",\"pin\":4,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"q\",\"pin\":25,\"bit\":0,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_REPEAT_EXAMPLE)
#include "circuit_repeat_example.c"
#define CIRCUIT_NAME "repeat_example"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":3,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"value[0]\",\"pin\":4,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"value[1]\",\"pin\":5,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"value[2]\",\"pin\":6,\"bit\":4,\"dir\":\"input\"},"
    "  {\"name\":\"value[3]\",\"pin\":7,\"bit\":5,\"dir\":\"input\"},"
    "  {\"name\":\"value[4]\",\"pin\":8,\"bit\":6,\"dir\":\"input\"},"
    "  {\"name\":\"value[5]\",\"pin\":9,\"bit\":7,\"dir\":\"input\"},"
    "  {\"name\":\"value[6]\",\"pin\":10,\"bit\":8,\"dir\":\"input\"},"
    "  {\"name\":\"value[7]\",\"pin\":11,\"bit\":9,\"dir\":\"input\"},"
    "  {\"name\":\"n[0]\",\"pin\":12,\"bit\":10,\"dir\":\"input\"},"
    "  {\"name\":\"n[1]\",\"pin\":13,\"bit\":11,\"dir\":\"input\"},"
    "  {\"name\":\"n[2]\",\"pin\":14,\"bit\":12,\"dir\":\"input\"},"
    "  {\"name\":\"result[0]\",\"pin\":25,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"result[1]\",\"pin\":15,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"result[2]\",\"pin\":16,\"bit\":2,\"dir\":\"output\"},"
    "  {\"name\":\"result[3]\",\"pin\":17,\"bit\":3,\"dir\":\"output\"},"
    "  {\"name\":\"result[4]\",\"pin\":18,\"bit\":4,\"dir\":\"output\"},"
    "  {\"name\":\"result[5]\",\"pin\":19,\"bit\":5,\"dir\":\"output\"},"
    "  {\"name\":\"result[6]\",\"pin\":20,\"bit\":6,\"dir\":\"output\"},"
    "  {\"name\":\"result[7]\",\"pin\":21,\"bit\":7,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_ALU)
#include "circuit_alu.c"
#define CIRCUIT_NAME "alu"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":3,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"a[0]\",\"pin\":4,\"bit\":2,\"dir\":\"input\"},"
    "  {\"name\":\"a[1]\",\"pin\":5,\"bit\":3,\"dir\":\"input\"},"
    "  {\"name\":\"a[2]\",\"pin\":6,\"bit\":4,\"dir\":\"input\"},"
    "  {\"name\":\"a[3]\",\"pin\":7,\"bit\":5,\"dir\":\"input\"},"
    "  {\"name\":\"b[0]\",\"pin\":8,\"bit\":6,\"dir\":\"input\"},"
    "  {\"name\":\"b[1]\",\"pin\":9,\"bit\":7,\"dir\":\"input\"},"
    "  {\"name\":\"b[2]\",\"pin\":10,\"bit\":8,\"dir\":\"input\"},"
    "  {\"name\":\"b[3]\",\"pin\":11,\"bit\":9,\"dir\":\"input\"},"
    "  {\"name\":\"op[0]\",\"pin\":26,\"bit\":10,\"dir\":\"input\"},"
    "  {\"name\":\"op[1]\",\"pin\":27,\"bit\":11,\"dir\":\"input\"},"
    "  {\"name\":\"op[2]\",\"pin\":28,\"bit\":12,\"dir\":\"input\"},"
    "  {\"name\":\"result[0]\",\"pin\":12,\"bit\":0,\"dir\":\"output\"},"
    "  {\"name\":\"result[1]\",\"pin\":13,\"bit\":1,\"dir\":\"output\"},"
    "  {\"name\":\"result[2]\",\"pin\":14,\"bit\":2,\"dir\":\"output\"},"
    "  {\"name\":\"result[3]\",\"pin\":15,\"bit\":3,\"dir\":\"output\"},"
    "  {\"name\":\"result[4]\",\"pin\":16,\"bit\":4,\"dir\":\"output\"},"
    "  {\"name\":\"result[5]\",\"pin\":17,\"bit\":5,\"dir\":\"output\"},"
    "  {\"name\":\"result[6]\",\"pin\":18,\"bit\":6,\"dir\":\"output\"},"
    "  {\"name\":\"result[7]\",\"pin\":19,\"bit\":7,\"dir\":\"output\"},"
    "  {\"name\":\"valid\",\"pin\":25,\"bit\":8,\"dir\":\"output\"}"
    "]";
#elif defined(EMU_CIRCUIT_BLINKY)
#include "circuit_blinky.c"
#define CIRCUIT_NAME "blinky"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":3,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"led\",\"pin\":25,\"bit\":0,\"dir\":\"output\"}"
    "]";
#else
#include "circuit_blinky.c"
#define CIRCUIT_NAME "blinky"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":2,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":3,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"led\",\"pin\":25,\"bit\":0,\"dir\":\"output\"}"
    "]";
#endif

static emulator_config_t emu_cfg;

static void emu_core1_entry(void)
{
    emulator_run_core1(&emu_cfg);
}

void setup(void)
{
    // Wait for USB CDC connection (up to 5 seconds)
    for (int i = 0; i < 500; i++) {
        if (Serial) break;
        delay(10);
    }

    hal_gpio_init();
    hal_timer_init();
    telemetry_init(115200);

    pin_map_load(&emu_cfg.pin_map, pinmap_json);
    emu_cfg.init_fn  = circuit_init;
    emu_cfg.eval_fn  = circuit_eval;
    emu_cfg.target_freq_hz = 100000;

    emulator_init(&emu_cfg);

    hal_gpio_set_clk(2, 100000);
    hal_gpio_set_virtual(3, 0);

#if defined(EMU_CIRCUIT_FSM_101)
#elif defined(EMU_CIRCUIT_SHIFT_REGISTER)
#elif defined(EMU_CIRCUIT_PWM)
#elif defined(EMU_CIRCUIT_UART_TX)
#elif defined(EMU_CIRCUIT_TINY_CPU)
#elif defined(EMU_CIRCUIT_TASK_FUNC)
#elif defined(EMU_CIRCUIT_REDUCTION)
#elif defined(EMU_CIRCUIT_PRIORITY_ENCODER)
#elif defined(EMU_CIRCUIT_NEGEDGE_COUNTER)
#elif defined(EMU_CIRCUIT_SIGN_EXTEND)
#elif defined(EMU_CIRCUIT_CONCAT_MULTI)
#elif defined(EMU_CIRCUIT_PART_SELECT_LHS)
#elif defined(EMU_CIRCUIT_ADDER_N)
#elif defined(EMU_CIRCUIT_CASE_EQUALITY)
#elif defined(EMU_CIRCUIT_NOT_KEYWORD)
#elif defined(EMU_CIRCUIT_LOCALPARAM_EXAMPLE)
#elif defined(EMU_CIRCUIT_MODULE_INST)
#elif defined(EMU_CIRCUIT_REPEAT_EXAMPLE)
#elif defined(EMU_CIRCUIT_ALU)
#elif defined(EMU_CIRCUIT_DECODER)
#elif defined(EMU_CIRCUIT_MIXED)
#elif defined(EMU_CIRCUIT_MUX)
#elif defined(EMU_CIRCUIT_MUX2)
#elif defined(EMU_CIRCUIT_PARAM_COUNTER)
#endif

    loop_cfg = &emu_cfg;
    multicore_launch_core1(emu_core1_entry);
    loop_last_report = (uint32_t)hal_timer_get_us();
    loop_last_cmd = loop_last_report;
    loop_last_clock = 0;
}

static bool boot_banner_sent = false;

void loop(void)
{
    if (!loop_cfg) return;
    
    uint32_t now = (uint32_t)hal_timer_get_us();
    
    if (!boot_banner_sent && now > 2000000) {
        if (Serial) {
            Serial.print("uFPGA-Emu v1.0 - RP2040 (" CIRCUIT_NAME ")\n");
            boot_banner_sent = true;
        }
    }
    
    if (now - loop_last_report > 1000000) {
        if (Serial) {
            model_state_t snap;
            emulator_lock();
            snap = loop_cfg->state;
            emulator_unlock();
            send_snapshot_telemetry(&snap, now);
        }
    }

    if (now - loop_last_cmd > 50000) {
        // Accumulate serial bytes in persistent line buffer
        uint8_t byte;
        while (cmd_line_len < sizeof(cmd_line) - 1 &&
               hal_serial_receive_byte(&byte) == 0) {
            if (byte == '\n' || byte == '\r') {
                if (cmd_line_len > 0) {
                    // Complete command received
                    cmd_line[cmd_line_len] = '\0';
                    char *p = cmd_line;
                    while (*p == ' ') p++;
                    char *token = p;
                    while (*p && *p != ' ') p++;
                    if (*p) *p++ = '\0';
                    while (*p == ' ') p++;
                    char *args = (*p) ? p : NULL;

                    if (strcmp(token, "reset") == 0) {
                        emulator_lock();
                        if (loop_cfg->init_fn) loop_cfg->init_fn(&loop_cfg->state);
                        emulator_unlock();
                        telemetry_send_string("OK reset\n");
                    } else if (strcmp(token, "status") == 0) {
                        model_state_t snap;
                        emulator_lock();
                        snap = loop_cfg->state;
                        emulator_unlock();
                        send_snapshot_telemetry(&snap, now);
                    } else if (strcmp(token, "vset") == 0) {
                        if (args) {
                            unsigned pin, val;
                            if (sscanf(args, "%u %u", &pin, &val) == 2) {
                                hal_gpio_set_virtual(pin, val);
                                char ok[64];
                                snprintf(ok, sizeof(ok), "OK vset %u %u\n", pin, val);
                                telemetry_send_string(ok);
                            } else {
                                telemetry_send_string("ERR: vset <pin> <value>\n");
                            }
                        } else {
                            telemetry_send_string("ERR: vset <pin> <value>\n");
                        }
                    } else if (strcmp(token, "read") == 0) {
                        if (args) {
                            unsigned pin;
                            if (sscanf(args, "%u", &pin) == 1) {
                                int v = hal_gpio_read(pin);
                                char ok[64];
                                snprintf(ok, sizeof(ok), "OK read %u = %d\n", pin, v);
                                telemetry_send_string(ok);
                            } else {
                                telemetry_send_string("ERR: read <pin>\n");
                            }
                        } else {
                            telemetry_send_string("ERR: read <pin>\n");
                        }
                    }
                    cmd_line_len = 0;
                }
            } else {
                cmd_line[cmd_line_len++] = (char)byte;
            }
        }
        loop_last_cmd = now;
    }
    
    delay(1);
}
