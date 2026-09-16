#include "telemetry.h"
#include "emulator.h"
#include "hal_serial.h"
#include "hal_timer.h"
#include "hal_gpio.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    char name[32];
    int  active;
} watch_config_t;

static watch_config_t watch_cfg = { .active = 0 };
static uint32_t telemetry_freq_hz = 0;

void telemetry_set_freq(uint32_t freq_hz)
{
    telemetry_freq_hz = freq_hz;
}

static void cmd_read(emulator_config_t *config, char *args)
{
    if (!args) {
        telemetry_send_string("ERR: read <signal>\n");
        return;
    }

    char buf[128];

    if (args[0] == 'r' && args[1] == 'e' && args[2] == 'g') {
        int n = atoi(args + 3);
        if (n >= 0 && n < MAX_REGS) {
            uint32_t val;
            emulator_lock();
            val = config->state.regs[n];
            emulator_unlock();
            snprintf(buf, sizeof(buf), "%s=0x%08lX\n", args, (unsigned long)val);
            telemetry_send_string(buf);
        } else {
            telemetry_send_string("ERR: reg index out of range\n");
        }
        return;
    }

    if (args[0] == 'w' && args[1] == 'i' && args[2] == 'r' && args[3] == 'e') {
        int n = atoi(args + 4);
        if (n >= 0 && n < MAX_WIRES) {
            uint32_t val;
            emulator_lock();
            val = config->state.wires[n];
            emulator_unlock();
            snprintf(buf, sizeof(buf), "%s=0x%08lX\n", args, (unsigned long)val);
            telemetry_send_string(buf);
        } else {
            telemetry_send_string("ERR: wire index out of range\n");
        }
        return;
    }

    for (int i = 0; i < config->pin_map.count; i++) {
        pin_binding_t *b = &config->pin_map.bindings[i];
        if (strcmp(args, b->name) == 0) {
            uint32_t val;
            emulator_lock();
            uint32_t word = (b->direction == PIN_DIR_INPUT)
                                ? config->state.inputs
                                : config->state.outputs;
            val = (word >> b->bit_pos) & 1u;
            emulator_unlock();
            snprintf(buf, sizeof(buf), "%s=%lu\n", args, (unsigned long)val);
            telemetry_send_string(buf);
            return;
        }
    }

    telemetry_send_string("ERR: signal not found\n");
}

static void cmd_write(emulator_config_t *config, char *args)
{
    if (!args) {
        telemetry_send_string("ERR: write <signal> <value>\n");
        return;
    }

    char *signal = strtok(args, " ");
    char *val_str = strtok(NULL, " ");
    if (!signal || !val_str) {
        telemetry_send_string("ERR: write <signal> <value>\n");
        return;
    }

    uint32_t val = (uint32_t)strtoul(val_str, NULL, 0);

    if (signal[0] == 'r' && signal[1] == 'e' && signal[2] == 'g') {
        int n = atoi(signal + 3);
        if (n >= 0 && n < MAX_REGS) {
            emulator_lock();
            config->state.regs[n] = val;
            emulator_unlock();
            telemetry_send_string("OK\n");
        } else {
            telemetry_send_string("ERR: reg index out of range\n");
        }
        return;
    }

    if (signal[0] == 'w' && signal[1] == 'i' && signal[2] == 'r' && signal[3] == 'e') {
        int n = atoi(signal + 4);
        if (n >= 0 && n < MAX_WIRES) {
            emulator_lock();
            config->state.wires[n] = val;
            emulator_unlock();
            telemetry_send_string("OK\n");
        } else {
            telemetry_send_string("ERR: wire index out of range\n");
        }
        return;
    }

    for (int i = 0; i < config->pin_map.count; i++) {
        pin_binding_t *b = &config->pin_map.bindings[i];
        if (strcmp(signal, b->name) == 0 && b->direction == PIN_DIR_OUTPUT) {
            emulator_lock();
            if (val) {
                config->state.outputs |= (1u << b->bit_pos);
            } else {
                config->state.outputs &= ~(1u << b->bit_pos);
            }
            emulator_unlock();
            telemetry_send_string("OK\n");
            return;
        }
    }

    telemetry_send_string("ERR: output signal not found\n");
}

static void cmd_step(emulator_config_t *config, char *args)
{
    if (!args) {
        telemetry_send_string("ERR: step <count>\n");
        return;
    }

    int n = atoi(args);
    if (n <= 0) {
        telemetry_send_string("ERR: step count must be > 0\n");
        return;
    }

    emulator_paused = 1;
    hal_timer_delay_us(2000);

    for (int i = 0; i < n; i++) {
        emulator_step(config);
        telemetry_send_state(&config->state);
    }

    emulator_paused = 0;
}

static void cmd_vset(emulator_config_t *config, char *args)
{
    if (!args) {
        telemetry_send_string("ERR: vset <pin> <value>\n");
        return;
    }
    char *pin_str = strtok(args, " ");
    char *val_str = strtok(NULL, " ");
    if (!pin_str || !val_str) {
        telemetry_send_string("ERR: vset <pin> <value>\n");
        return;
    }
    int pin = atoi(pin_str);
    int val = atoi(val_str);
    hal_gpio_set_virtual((uint8_t)pin, val ? 1 : 0);
    telemetry_send_string("OK\n");
}

static void cmd_watch(emulator_config_t *config, char *args)
{
    if (!args || strcmp(args, "off") == 0) {
        watch_cfg.active = 0;
        telemetry_send_string("watch off\n");
        return;
    }

    strncpy(watch_cfg.name, args, sizeof(watch_cfg.name) - 1);
    watch_cfg.name[sizeof(watch_cfg.name) - 1] = '\0';
    watch_cfg.active = 1;

    char buf[64];
    snprintf(buf, sizeof(buf), "watching %s\n", watch_cfg.name);
    telemetry_send_string(buf);
}

static void report_watched_signal(const emulator_config_t *config)
{
    if (!watch_cfg.active) return;

    char buf[128];
    const char *name = watch_cfg.name;

    if (name[0] == 'r' && name[1] == 'e' && name[2] == 'g') {
        int n = atoi(name + 3);
        if (n >= 0 && n < MAX_REGS) {
            uint32_t val;
            emulator_lock();
            val = config->state.regs[n];
            emulator_unlock();
            snprintf(buf, sizeof(buf), "  %s=0x%08lX\n", name, (unsigned long)val);
            telemetry_send_string(buf);
        }
        return;
    }

    if (name[0] == 'w' && name[1] == 'i' && name[2] == 'r' && name[3] == 'e') {
        int n = atoi(name + 4);
        if (n >= 0 && n < MAX_WIRES) {
            uint32_t val;
            emulator_lock();
            val = config->state.wires[n];
            emulator_unlock();
            snprintf(buf, sizeof(buf), "  %s=0x%08lX\n", name, (unsigned long)val);
            telemetry_send_string(buf);
        }
        return;
    }

    for (int i = 0; i < config->pin_map.count; i++) {
        const pin_binding_t *b = &config->pin_map.bindings[i];
        if (strcmp(name, b->name) == 0) {
            uint32_t val;
            emulator_lock();
            uint32_t word = (b->direction == PIN_DIR_INPUT)
                                ? config->state.inputs
                                : config->state.outputs;
            val = (word >> b->bit_pos) & 1u;
            emulator_unlock();
            snprintf(buf, sizeof(buf), "  %s=%lu\n", name, (unsigned long)val);
            telemetry_send_string(buf);
            return;
        }
    }
}

void telemetry_init(uint32_t baud)
{
    hal_serial_init(baud);
}

void telemetry_send_state(const model_state_t *state)
{
    char buf[128];
    int len = snprintf(buf, sizeof(buf),
        "CLK=%lu IN=0x%08lX OUT=0x%08lX REG0=0x%08lX FREQ=%luHz\n",
        (unsigned long)state->clock_count,
        (unsigned long)state->inputs,
        (unsigned long)state->outputs,
        (unsigned long)state->regs[0],
        (unsigned long)telemetry_freq_hz);
    hal_serial_send_buffer((const uint8_t *)buf, (size_t)len);
}

int telemetry_receive_cmd(uint8_t *cmd, size_t len)
{
    size_t i = 0;
    uint8_t byte;
    while (i < len - 1 && hal_serial_receive_byte(&byte) == 0) {
        if (byte == '\n' || byte == '\r') break;
        cmd[i++] = byte;
    }
    cmd[i] = '\0';
    return (i > 0) ? 0 : -1;
}

void telemetry_send_string(const char *str)
{
    hal_serial_send_buffer((const uint8_t *)str, strlen(str));
}

void telemetry_run_core0(void *param)
{
    emulator_config_t *config = (emulator_config_t *)param;
    uint32_t last_report = 0;

    while (1) {
        uint32_t now = (uint32_t)hal_timer_get_us();
        if (now - last_report > 1000000) {
            model_state_t snap;
            emulator_lock();
            snap = config->state;
            emulator_unlock();
            telemetry_send_state(&snap);
            report_watched_signal(config);
            last_report = now;
        }

        uint8_t cmd[64];
        if (telemetry_receive_cmd(cmd, sizeof(cmd)) == 0) {
            char *p = (char *)cmd;
            while (*p == ' ') p++;
            char *token = p;
            while (*p && *p != ' ') p++;
            if (*p) *p++ = '\0';
            while (*p == ' ') p++;
            char *args = (*p) ? p : NULL;

            if (strcmp(token, "reset") == 0) {
                emulator_lock();
                if (config->init_fn) config->init_fn(&config->state);
                emulator_unlock();
                telemetry_send_string("OK reset\n");
            } else if (strcmp(token, "status") == 0) {
                model_state_t snap;
                emulator_lock();
                snap = config->state;
                emulator_unlock();
                telemetry_send_state(&snap);
                report_watched_signal(config);
            } else if (strcmp(token, "read") == 0) {
                cmd_read(config, args);
            } else if (strcmp(token, "write") == 0) {
                cmd_write(config, args);
            } else if (strcmp(token, "step") == 0) {
                cmd_step(config, args);
            } else if (strcmp(token, "vset") == 0) {
                cmd_vset(config, args);
            } else if (strcmp(token, "watch") == 0) {
                cmd_watch(config, args);
            }
        }

        hal_timer_yield();
    }
}
