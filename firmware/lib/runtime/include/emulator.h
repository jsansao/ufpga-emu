#ifndef EMULATOR_H
#define EMULATOR_H

#include "model.h"
#include "pin_map.h"
#include "hal_mutex.h"
#include "vcd_writer.h"

typedef struct {
    model_state_t    state;
    pin_map_t        pin_map;
    circuit_init_fn  init_fn;
    circuit_eval_fn  eval_fn;
    uint32_t         target_freq_hz;
    uint8_t          clk_gpio_pin;
    vcd_writer_t    *vcd;
} emulator_config_t;

void emulator_init(emulator_config_t *config);
void emulator_step(emulator_config_t *config);
void emulator_run_core1(void *param);
void emulator_lock(void);
void emulator_unlock(void);

extern volatile int emulator_paused;

#endif
