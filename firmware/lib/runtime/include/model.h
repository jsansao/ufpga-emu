#ifndef MODEL_H
#define MODEL_H

#include <stdint.h>
#include <stddef.h>

#define MAX_INPUTS  32
#define MAX_OUTPUTS 32
#define MAX_REGS    32
#define MAX_WIRES   32

typedef struct {
    uint32_t inputs;
    uint32_t outputs;
    uint32_t regs[MAX_REGS];
    uint32_t wires[MAX_WIRES];
    uint32_t clock_count;
} model_state_t;

typedef void (*circuit_init_fn)(model_state_t *state);
typedef void (*circuit_eval_fn)(model_state_t *state, uint32_t inputs, uint32_t *outputs);

#endif
