#include <stdio.h>
#include <pthread.h>
#include <stdlib.h>

#include "hal_gpio.h"
#include "hal_timer.h"
#include "emulator.h"
#include "telemetry.h"

/*
 * Circuit selection via -DEMU_CIRCUIT_* at compile time.
 * Same structure as main_esp32.c.
 */
/* Pinmap + selecao de circuito gerados de firmware/pinmaps/rpi.json
 * (pc_tool/pinmap_gen.py). Novos circuitos: editar apenas o JSON. */
#include "pinmap_rpi.h"

static emulator_config_t emu_cfg;

int main(void)
{
    hal_gpio_init();
    hal_timer_init();
    telemetry_init(115200);

    telemetry_send_string("uFPGA-Emu v1.0 - RPi GPIO (" CIRCUIT_NAME ")\n");

    pin_init_t pin_inits[MAX_PIN_INITS];
    int n_inits = pin_map_load_circuit(&emu_cfg.pin_map, PINMAP_JSON,
                                       CIRCUIT_NAME, pin_inits, MAX_PIN_INITS);
    if (n_inits < 0) {
        telemetry_send_string("ERRO: pinmap ausente: " CIRCUIT_NAME "\n");
        return 1;
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

    pthread_t emu_thread;
    pthread_create(&emu_thread, NULL, (void *(*)(void *))emulator_run_core1, &emu_cfg);

    /* measure actual clock frequency over 1s */
    uint32_t m_start;
    uint64_t t0 = hal_timer_get_us();
    emulator_lock();
    m_start = emu_cfg.state.clock_count;
    emulator_unlock();
    hal_timer_delay_us(1000000);
    emulator_lock();
    uint32_t m_delta = emu_cfg.state.clock_count - m_start;
    emulator_unlock();
    uint64_t t1 = hal_timer_get_us();
    uint32_t freq_hz = (uint32_t)((uint64_t)m_delta * 1000000 / (t1 - t0));
    telemetry_set_freq(freq_hz);

    telemetry_run_core0(&emu_cfg);

    pthread_join(emu_thread, NULL);
    return 0;
}
