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

#define VCD_REG_COUNT 16

static const char *pinmap_json =
    "[\n"
    "  {\"name\":\"clk\",\"pin\":1,\"bit\":0,\"dir\":\"input\"},\n"
    "  {\"name\":\"rst\",\"pin\":2,\"bit\":1,\"dir\":\"input\"},\n"
    "  {\"name\":\"run\",\"pin\":3,\"bit\":2,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[0]\",\"pin\":4,\"bit\":3,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[1]\",\"pin\":5,\"bit\":4,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[2]\",\"pin\":6,\"bit\":5,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[3]\",\"pin\":7,\"bit\":6,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[4]\",\"pin\":8,\"bit\":7,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[5]\",\"pin\":9,\"bit\":8,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[6]\",\"pin\":10,\"bit\":9,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[7]\",\"pin\":11,\"bit\":10,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[8]\",\"pin\":12,\"bit\":11,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[9]\",\"pin\":13,\"bit\":12,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[10]\",\"pin\":14,\"bit\":13,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[11]\",\"pin\":15,\"bit\":14,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[12]\",\"pin\":16,\"bit\":15,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[13]\",\"pin\":17,\"bit\":16,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[14]\",\"pin\":18,\"bit\":17,\"dir\":\"input\"},\n"
    "  {\"name\":\"instr[15]\",\"pin\":19,\"bit\":18,\"dir\":\"input\"},\n"
    "  {\"name\":\"pc[0]\",\"pin\":20,\"bit\":0,\"dir\":\"output\"},\n"
    "  {\"name\":\"pc[1]\",\"pin\":21,\"bit\":1,\"dir\":\"output\"},\n"
    "  {\"name\":\"pc[2]\",\"pin\":22,\"bit\":2,\"dir\":\"output\"},\n"
    "  {\"name\":\"pc[3]\",\"pin\":23,\"bit\":3,\"dir\":\"output\"},\n"
    "  {\"name\":\"pc[4]\",\"pin\":24,\"bit\":4,\"dir\":\"output\"},\n"
    "  {\"name\":\"pc[5]\",\"pin\":25,\"bit\":5,\"dir\":\"output\"},\n"
    "  {\"name\":\"pc[6]\",\"pin\":26,\"bit\":6,\"dir\":\"output\"},\n"
    "  {\"name\":\"pc[7]\",\"pin\":27,\"bit\":7,\"dir\":\"output\"},\n"
    "  {\"name\":\"dout[0]\",\"pin\":28,\"bit\":8,\"dir\":\"output\"},\n"
    "  {\"name\":\"dout[1]\",\"pin\":29,\"bit\":9,\"dir\":\"output\"},\n"
    "  {\"name\":\"dout[2]\",\"pin\":30,\"bit\":10,\"dir\":\"output\"},\n"
    "  {\"name\":\"dout[3]\",\"pin\":31,\"bit\":11,\"dir\":\"output\"},\n"
    "  {\"name\":\"dout[4]\",\"pin\":32,\"bit\":12,\"dir\":\"output\"},\n"
    "  {\"name\":\"dout[5]\",\"pin\":33,\"bit\":13,\"dir\":\"output\"},\n"
    "  {\"name\":\"dout[6]\",\"pin\":34,\"bit\":14,\"dir\":\"output\"},\n"
    "  {\"name\":\"dout[7]\",\"pin\":35,\"bit\":15,\"dir\":\"output\"},\n"
    "  {\"name\":\"halted\",\"pin\":36,\"bit\":16,\"dir\":\"output\"}\n"
    "]\n";

static emulator_config_t emu_cfg;
static vcd_writer_t vcd;
static void _vcd_atexit(void) { vcd_close(&vcd); }
static void _sig_handler(int sig) { (void)sig; exit(0); }

int main(void)
{
    hal_gpio_init();
    hal_gpio_set_clk(1, 100000);
    hal_timer_init();
    signal(SIGINT, _sig_handler);
    signal(SIGTERM, _sig_handler);
    telemetry_init(115200);

    telemetry_send_string("uFPGA-Emu v1.0 - PC Simulation (tiny_cpu)\n");

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
