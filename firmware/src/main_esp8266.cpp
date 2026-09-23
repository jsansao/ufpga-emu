#include <Arduino.h>

extern "C" {
#include "hal_gpio.h"
#include "hal_timer.h"
#include "hal_serial.h"
#include "emulator.h"
#include "telemetry.h"
}

/*
 * Pin mapping ESP8266 (Wemos D1 Mini):
 *   GPIO 0   = D3 (boot flag HIGH, usar com cuidado)
 *   GPIO 1   = TX (UART0) — nao usar
 *   GPIO 2   = D4 (LED onboard) — saida
 *   GPIO 3   = RX (UART0) — nao usar
 *   GPIO 4   = D2 — clk (virtual)
 *   GPIO 5   = D1 — rst (virtual)
 *   GPIO 6-11 = SPI flash — nao usar
 *   GPIO 12  = D6 (MISO) — I/O real
 *   GPIO 13  = D7 (MOSI) — I/O real
 *   GPIO 14  = D5 (SCLK) — I/O real
 *   GPIO 15  = D8 (CS) — I/O real
 *   GPIO 16  = D0 — I/O real
 *   GPIO 17+ = inexistentes — tratados como virtual_values
 *
 * Pinmaps copiados do ESP32: pinos >=17 viram virtual values
 * automaticamente via hal_gpio (HAL_GPIO_MAX_PINS=17).
 */

// -------------------------------------------------------------------
// Serial wrappers (C-linkage para hal_serial.c)
// -------------------------------------------------------------------
extern "C" {

void hal_serial_esp8266_init(uint32_t baud)
{
    Serial.begin(baud);
}

void hal_serial_esp8266_send_byte(uint8_t data)
{
    Serial.write(data);
}

void hal_serial_esp8266_send_buffer(const uint8_t *data, size_t len)
{
    Serial.write(data, len);
}

int hal_serial_esp8266_receive_byte(uint8_t *data)
{
    if (Serial.available()) {
        *data = Serial.read();
        return 0;
    }
    return -1;
}

} // extern "C"

/* Pinmap + selecao de circuito gerados de firmware/pinmaps/esp8266.json
 * (pc_tool/pinmap_gen.py). Novos circuitos: editar apenas o JSON. */
#include "pinmap_esp8266.h"

static emulator_config_t emu_cfg;
static char cmd_line[128];
static size_t cmd_line_len = 0;
static uint32_t last_report = 0;
static uint32_t last_cmd = 0;
static uint64_t last_clock = 0;
static bool boot_banner_sent = false;

static void send_snapshot(uint32_t now)
{
    uint64_t elapsed_us = (uint64_t)(now - last_report);
    uint64_t clock_delta = (uint64_t)(emu_cfg.state.clock_count - last_clock);
    uint32_t freq_hz = 0;
    if (elapsed_us > 0 && clock_delta > 0) {
        freq_hz = (uint32_t)((clock_delta * 1000000ull) / elapsed_us);
    }
    telemetry_set_freq(freq_hz);
    telemetry_send_state(&emu_cfg.state);
    last_report = now;
    last_clock = emu_cfg.state.clock_count;
}

void setup(void)
{
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
    emu_cfg.target_freq_hz = 0;

    emulator_init(&emu_cfg);

    int clk_pin = pin_map_get_physical(&emu_cfg.pin_map, "clk");
    if (clk_pin >= 0) hal_gpio_set_clk((uint8_t)clk_pin, 100000);
    int rst_pin = pin_map_get_physical(&emu_cfg.pin_map, "rst");
    if (rst_pin >= 0) hal_gpio_set_virtual((uint8_t)rst_pin, 0);
    for (int i = 0; i < n_inits && i < MAX_PIN_INITS; i++) {
        int pin = pin_map_get_physical(&emu_cfg.pin_map, pin_inits[i].name);
        if (pin >= 0) hal_gpio_set_virtual((uint8_t)pin, pin_inits[i].value);
    }

    last_report = (uint32_t)hal_timer_get_us();
    last_cmd = last_report;
}

void loop(void)
{
    uint32_t now = (uint32_t)hal_timer_get_us();

    if (!boot_banner_sent && now > 2000000) {
        Serial.print("uFPGA-Emu v1.0 - ESP8266 (" CIRCUIT_NAME ")\n");
        boot_banner_sent = true;
    }

    uint32_t period_us = (emu_cfg.target_freq_hz > 0)
                            ? (1000000u / emu_cfg.target_freq_hz) : 0;

    uint64_t start = hal_timer_get_us();
    hal_gpio_set_cached_now(now);
    emulator_step(&emu_cfg);
    if (period_us > 0) {
        uint64_t elapsed = hal_timer_get_us() - start;
        if (elapsed < period_us) {
            hal_timer_delay_us((uint32_t)(period_us - elapsed));
        }
    }

    if (now - last_report > 1000000) {
        send_snapshot(now);
    }

    if (now - last_cmd > 50000) {
        uint8_t byte;
        while (cmd_line_len < sizeof(cmd_line) - 1 &&
               hal_serial_receive_byte(&byte) == 0) {
            if (byte == '\n' || byte == '\r') {
                if (cmd_line_len > 0) {
                    cmd_line[cmd_line_len] = '\0';
                    char *p = cmd_line;
                    while (*p == ' ') p++;
                    char *token = p;
                    while (*p && *p != ' ') p++;
                    if (*p) *p++ = '\0';
                    while (*p == ' ') p++;
                    char *args = (*p) ? p : NULL;

                    if (strcmp(token, "reset") == 0) {
                        if (emu_cfg.init_fn) emu_cfg.init_fn(&emu_cfg.state);
                        telemetry_send_string("OK reset\n");
                    } else if (strcmp(token, "status") == 0) {
                        send_snapshot(now);
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
        last_cmd = now;
    }
}
