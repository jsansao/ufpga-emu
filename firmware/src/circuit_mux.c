/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: mux
 */
#include "model.h"

#define GET_BIT(w, b)  (((w) >> (b)) & 1u)
#define GET_BITS(w, h, l) (((w) >> (l)) & ((1u << ((h)-(l)+1)) - 1u))

#define REG_COUNT 1

void circuit_init(model_state_t *state)
{
    state->regs[0] = 0;
    state->outputs = 0;
    state->clock_count = 0;
}

void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs)
{
    uint32_t a = GET_BIT(inputs, 0);
    uint32_t b = GET_BIT(inputs, 1);
    uint32_t sel = GET_BIT(inputs, 2);
    *outputs = 0;
    if (sel) {
        state->regs[0] = (a) & 0x1;
    } else {
        state->regs[0] = (b) & 0x1;
    }
    *outputs |= (state->regs[0] & 0x1);
}
