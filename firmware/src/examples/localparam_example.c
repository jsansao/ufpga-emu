/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: localparam_example
 */
#include "model.h"

#define GET_BIT(w, b)  (((w) >> (b)) & 1u)
#define GET_BITS(w, h, l) (((w) >> (l)) & ((1u << ((h)-(l)+1)) - 1u))

#define WIDTH 4
#define SHIFT 2

#define REG_COUNT 1

void circuit_init(model_state_t *state)
{
    state->regs[0] = 0;
    state->outputs = 0;
    state->clock_count = 0;
}

void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs)
{
    uint32_t in = ((inputs >> 0) & 0xFu);
    *outputs = 0;
    state->regs[0] = (in << SHIFT);
    *outputs |= (state->regs[0] & 0xFF);
}
