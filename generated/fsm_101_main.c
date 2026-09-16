#include <stdio.h>
#include <pthread.h>

#include <stdlib.h>
#include "hal_gpio.h"
#include "hal_timer.h"
#include "hal_stimulus.h"
#include "emulator.h"
#include "telemetry.h"

void circuit_init(model_state_t *state);
void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs);

static const char *pinmap_json =
    "[\n"
    "  {\"name\":\"clk\",\"pin\":1,\"bit\":0,\"dir\":\"input\"},\n"
    "  {\"name\":\"rst\",\"pin\":2,\"bit\":1,\"dir\":\"input\"},\n"
    "  {\"name\":\"data_in\",\"pin\":3,\"bit\":2,\"dir\":\"input\"},\n"
    "  {\"name\":\"detected\",\"pin\":4,\"bit\":0,\"dir\":\"output\"}\n"
    "]\n";

static emulator_config_t emu_cfg;

int main(void)
{
    hal_gpio_init();
    hal_gpio_set_clk(1, 100000);
    hal_timer_init();
    telemetry_init(115200);

    telemetry_send_string("uFPGA-Emu v1.0 - PC Simulation (fsm_101)\n");

    pin_map_load(&emu_cfg.pin_map, pinmap_json);
    {
        const char *csv = getenv("STIMULUS_CSV");
        if (csv) hal_stimulus_load(csv, &emu_cfg.pin_map);
    }
    emu_cfg.init_fn  = circuit_init;
    emu_cfg.eval_fn  = circuit_eval;
    emu_cfg.target_freq_hz = 100000;

    emulator_init(&emu_cfg);

    pthread_t emu_thread;
    pthread_create(&emu_thread, NULL, (void *(*)(void *))emulator_run_core1, &emu_cfg);

    telemetry_run_core0(&emu_cfg);

    pthread_join(emu_thread, NULL);
    return 0;
}
