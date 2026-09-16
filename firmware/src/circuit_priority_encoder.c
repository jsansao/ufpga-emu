/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: priority_encoder
 */
#include "model.h"

#define GET_BIT(w, b)  (((w) >> (b)) & 1u)
#define GET_BITS(w, h, l) (((w) >> (l)) & ((1u << ((h)-(l)+1)) - 1u))

#define REG_COUNT 2

void circuit_init(model_state_t *state)
{
    state->regs[0] = 0;
    state->regs[1] = 0;
    state->outputs = 0;
    state->clock_count = 0;
}

void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs)
{
    uint32_t req = ((inputs >> 0) & 0xFu);
    *outputs = 0;
    state->regs[0] = 0;
    state->regs[1] = 0;
    for (int i = 3; (i >= 0); i = (i - 1)) {
        if (GET_BIT(req, i)) {
            state->regs[0] = (i) & 0x3;
            state->regs[1] = 1;
        }
    }
    *outputs |= (state->regs[0] & 0x3);
    *outputs |= (((state->regs[1] & 0x1)) << 2);
}
