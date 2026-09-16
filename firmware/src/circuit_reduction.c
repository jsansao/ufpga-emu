/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: reduction
 */
#include "model.h"

#define GET_BIT(w, b)  (((w) >> (b)) & 1u)
#define GET_BITS(w, h, l) (((w) >> (l)) & ((1u << ((h)-(l)+1)) - 1u))

#define REG_COUNT 4

void circuit_init(model_state_t *state)
{
    state->regs[0] = 0;
    state->regs[1] = 0;
    state->regs[2] = 0;
    state->regs[3] = 0;
    state->outputs = 0;
    state->clock_count = 0;
}

void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs)
{
    uint32_t data = ((inputs >> 0) & 0xFFu);
    *outputs = 0;
    state->regs[0] = ((__builtin_popcount(data) & 1)) & 0x1;
    state->regs[1] = ((data == 0xFFu)) & 0x1;
    state->regs[2] = ((data != 0u)) & 0x1;
    state->regs[3] = ((((__builtin_popcount(data) & 1)) ? 1 : 0)) & 0x1;
    *outputs |= (state->regs[0] & 0x1);
    *outputs |= (((state->regs[1] & 0x1)) << 1);
    *outputs |= (((state->regs[2] & 0x1)) << 2);
    *outputs |= (((state->regs[3] & 0x1)) << 3);
}
