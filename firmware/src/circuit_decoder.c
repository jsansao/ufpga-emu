/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: decoder
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
    uint32_t addr = ((inputs >> 0) & 0x3u);
    *outputs = 0;
    switch ((addr)) {
        case 0:
            state->regs[0] = 1;
            break;
        case 1:
            state->regs[0] = 2;
            break;
        case 2:
            state->regs[0] = 4;
            break;
        case 3:
            state->regs[0] = 8;
            break;
        default:
            state->regs[0] = 0;
            break;
    }
    *outputs |= (state->regs[0] & 0xF);
}
