#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "sdkconfig.h"

#include "hal_gpio.h"
#include "hal_timer.h"
#include "emulator.h"
#include "telemetry.h"

/*
 * Selecao de circuito em tempo de compilacao via -DEMU_CIRCUIT_*.
 * O circuito e incluido inline para que apenas main_esp32.c precise
 * ser listado no CMakeLists.txt do ESP-IDF.
 */
/* Pinmap + selecao de circuito gerados de firmware/pinmaps/esp32.json
 * (pc_tool/pinmap_gen.py). Novos circuitos: editar apenas o JSON. */
#include "pinmap_esp32.h"

static emulator_config_t emu_cfg;

void app_main(void)
{
    hal_gpio_init();
    hal_timer_init();
    telemetry_init(115200);

    telemetry_send_string("uFPGA-Emu v1.0 - ESP32 (" CIRCUIT_NAME ")\n");

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

    xTaskCreatePinnedToCore(
        emulator_run_core1, "emu_core1",
        4096, &emu_cfg, 1, NULL, 1
    );

    telemetry_run_core0(&emu_cfg);
}