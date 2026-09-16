#ifndef TELEMETRY_H
#define TELEMETRY_H

#include "model.h"

#define TELEMETRY_BUF_SIZE 1024

typedef struct {
    uint8_t            buffer[TELEMETRY_BUF_SIZE];
    volatile uint16_t  head;
    volatile uint16_t  tail;
} ringbuf_t;

void telemetry_init(uint32_t baud);
void telemetry_send_state(const model_state_t *state);
int  telemetry_receive_cmd(uint8_t *cmd, size_t len);
void telemetry_send_string(const char *str);
void telemetry_run_core0(void *param);
void telemetry_set_freq(uint32_t freq_hz);

#endif
