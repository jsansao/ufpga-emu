#include "emulator.h"
#include "hal_gpio.h"
#include "hal_timer.h"

volatile int emulator_paused = 0;
static hal_mutex_t emu_mutex;

void emulator_lock(void)
{
    hal_mutex_lock(&emu_mutex);
}

void emulator_unlock(void)
{
    hal_mutex_unlock(&emu_mutex);
}

void emulator_init(emulator_config_t *config)
{
    hal_mutex_init(&emu_mutex);

    if (config->init_fn) {
        config->init_fn(&config->state);
    }

    for (int i = 0; i < config->pin_map.count; i++) {
        pin_binding_t *b = &config->pin_map.bindings[i];
        hal_gpio_set_mode(b->physical_pin,
            (b->direction == PIN_DIR_INPUT) ? HAL_GPIO_INPUT : HAL_GPIO_OUTPUT);
    }

    config->state.clock_count = 0;
}

void emulator_step(emulator_config_t *config)
{
    emulator_lock();

    uint32_t inputs = 0;
    int i;
    pin_binding_t *b;

    for (i = 0; i < config->pin_map.count; i++) {
        b = &config->pin_map.bindings[i];
        if (b->direction == PIN_DIR_INPUT) {
            uint8_t val = hal_gpio_read(b->physical_pin);
            if (val) inputs |= (1u << b->bit_pos);
        }
    }

    if (config->eval_fn) {
        config->state.inputs = inputs;
        config->eval_fn(&config->state, inputs, &config->state.outputs);
    }

    for (i = 0; i < config->pin_map.count; i++) {
        b = &config->pin_map.bindings[i];
        if (b->direction == PIN_DIR_OUTPUT) {
            uint8_t val = (config->state.outputs >> b->bit_pos) & 1u;
            hal_gpio_write(b->physical_pin, val);
        }
    }

    config->state.clock_count++;

    if (config->vcd) {
        vcd_record(config->vcd,
                   config->state.inputs,
                   config->state.outputs,
                   config->state.regs,
                   config->state.wires,
                   config->state.clock_count);
    }

    emulator_unlock();
}

void emulator_run_core1(void *param)
{
    emulator_config_t *config = (emulator_config_t *)param;
    uint32_t period_us = (config->target_freq_hz > 0)
                            ? (1000000u / config->target_freq_hz) : 0;
    uint32_t yield_div = 0;

    while (1) {
        if (emulator_paused) {
            hal_timer_yield();
            continue;
        }

        uint64_t start = hal_timer_get_us();
        hal_gpio_set_cached_now(start);

        emulator_step(config);

        if (period_us > 0) {
            uint64_t elapsed = hal_timer_get_us() - start;
            if (elapsed < period_us) {
                hal_timer_delay_us((uint32_t)(period_us - elapsed));
            }
        }

        if (++yield_div >= 10000) {
            yield_div = 0;
            hal_timer_yield();
        }
    }
}
