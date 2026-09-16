/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: adder_n
 */
#include "model.h"

#define GET_BIT(w, b)  (((w) >> (b)) & 1u)
#define GET_BITS(w, h, l) (((w) >> (l)) & ((1u << ((h)-(l)+1)) - 1u))

#define N 4

#define REG_COUNT 3

void circuit_init(model_state_t *state)
{
    state->regs[0] = 0;
    state->regs[1] = 0;
    state->regs[2] = 0;
    state->outputs = 0;
    state->clock_count = 0;
}

void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs)
{
    uint32_t a = ((inputs >> 0) & 0xFu);
    uint32_t b = ((inputs >> 4) & 0xFu);
    *outputs = 0;
    state->regs[2] = ((a + b)) & 0x1F;
    state->regs[0] = (GET_BITS(state->regs[2], (N - 1), 0)) & 0xF;
    state->regs[1] = (GET_BIT(state->regs[2], N)) & 0x1;
    *outputs |= (state->regs[0] & 0xF);
    *outputs |= (((state->regs[1] & 0x1)) << 4);
}
