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

/* Pinmap + selecao de circuito gerados de firmware/pinmaps/rp2040.json
 * (pc_tool/pinmap_gen.py). Novos circuitos: editar apenas o JSON. */
#include "pinmap_rp2040.h"

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

    pin_init_t pin_inits[MAX_PIN_INITS];
    int n_inits = pin_map_load_circuit(&emu_cfg.pin_map, PINMAP_JSON,
                                       CIRCUIT_NAME, pin_inits, MAX_PIN_INITS);
    if (n_inits < 0) {
        telemetry_send_string("ERRO: pinmap ausente: " CIRCUIT_NAME "\n");
        for (;;) { hal_timer_delay_us(1000000); }
    }
    emu_cfg.init_fn  = circuit_init;
    emu_cfg.eval_fn  = circuit_eval;
    emu_cfg.target_freq_hz = 100000;

    emulator_init(&emu_cfg);

    int clk_pin = pin_map_get_physical(&emu_cfg.pin_map, "clk");
    if (clk_pin >= 0) hal_gpio_set_clk((uint8_t)clk_pin, 100000);
    int rst_pin = pin_map_get_physical(&emu_cfg.pin_map, "rst");
    if (rst_pin >= 0) hal_gpio_set_virtual((uint8_t)rst_pin, 0);
    for (int i = 0; i < n_inits && i < MAX_PIN_INITS; i++) {
        int pin = pin_map_get_physical(&emu_cfg.pin_map, pin_inits[i].name);
        if (pin >= 0) hal_gpio_set_virtual((uint8_t)pin, pin_inits[i].value);
    }

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
