#include <stdio.h>
#include <pthread.h>
#include <signal.h>

#include <stdlib.h>
#include "hal_gpio.h"
#include "hal_timer.h"
#include "hal_stimulus.h"
#include "emulator.h"
#include "telemetry.h"
#include "vcd_writer.h"

void circuit_init(model_state_t *state);
void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs);

#define VCD_REG_COUNT 5

static const char *pinmap_json =
    "[\n"
    "  {\"name\":\"a[0]\",\"pin\":1,\"bit\":0,\"dir\":\"input\"},\n"
    "  {\"name\":\"a[1]\",\"pin\":2,\"bit\":1,\"dir\":\"input\"},\n"
    "  {\"name\":\"a[2]\",\"pin\":3,\"bit\":2,\"dir\":\"input\"},\n"
    "  {\"name\":\"a[3]\",\"pin\":4,\"bit\":3,\"dir\":\"input\"},\n"
    "  {\"name\":\"b[0]\",\"pin\":5,\"bit\":4,\"dir\":\"input\"},\n"
    "  {\"name\":\"b[1]\",\"pin\":6,\"bit\":5,\"dir\":\"input\"},\n"
    "  {\"name\":\"b[2]\",\"pin\":7,\"bit\":6,\"dir\":\"input\"},\n"
    "  {\"name\":\"b[3]\",\"pin\":8,\"bit\":7,\"dir\":\"input\"},\n"
    "  {\"name\":\"op[0]\",\"pin\":9,\"bit\":8,\"dir\":\"input\"},\n"
    "  {\"name\":\"op[1]\",\"pin\":10,\"bit\":9,\"dir\":\"input\"},\n"
    "  {\"name\":\"y[0]\",\"pin\":11,\"bit\":0,\"dir\":\"output\"},\n"
    "  {\"name\":\"y[1]\",\"pin\":12,\"bit\":1,\"dir\":\"output\"},\n"
    "  {\"name\":\"y[2]\",\"pin\":13,\"bit\":2,\"dir\":\"output\"},\n"
    "  {\"name\":\"y[3]\",\"pin\":14,\"bit\":3,\"dir\":\"output\"},\n"
    "  {\"name\":\"lt\",\"pin\":15,\"bit\":4,\"dir\":\"output\"},\n"
    "  {\"name\":\"gt\",\"pin\":16,\"bit\":5,\"dir\":\"output\"},\n"
    "  {\"name\":\"le\",\"pin\":17,\"bit\":6,\"dir\":\"output\"},\n"
    "  {\"name\":\"ge\",\"pin\":18,\"bit\":7,\"dir\":\"output\"}\n"
    "]\n";

static emulator_config_t emu_cfg;
static vcd_writer_t vcd;
static void _vcd_atexit(void) { vcd_close(&vcd); }
static void _sig_handler(int sig) { (void)sig; exit(0); }

int main(void)
{
    hal_gpio_init();
    hal_timer_init();
    signal(SIGINT, _sig_handler);
    signal(SIGTERM, _sig_handler);
    telemetry_init(115200);

    telemetry_send_string("uFPGA-Emu v1.0 - PC Simulation (alu)\n");

    pin_map_load(&emu_cfg.pin_map, pinmap_json);
    {
        const char *csv = getenv("STIMULUS_CSV");
        if (csv) hal_stimulus_load(csv, &emu_cfg.pin_map);
    }
    {
        const char *vcd_path = getenv("VCD_OUT");
        if (vcd_path && vcd_init(&vcd, vcd_path, &emu_cfg.pin_map, VCD_REG_COUNT, 0) == 0) {
            emu_cfg.vcd = &vcd;
            atexit(_vcd_atexit);
        }
    }
    emu_cfg.init_fn  = circuit_init;
    emu_cfg.eval_fn  = circuit_eval;
    emu_cfg.target_freq_hz = 100000;

    emulator_init(&emu_cfg);

    pthread_t emu_thread;
    pthread_create(&emu_thread, NULL, (void *(*)(void *))emulator_run_core1, &emu_cfg);

    telemetry_run_core0(&emu_cfg);

    pthread_join(emu_thread, NULL);
    vcd_close(&vcd);
    return 0;
}
