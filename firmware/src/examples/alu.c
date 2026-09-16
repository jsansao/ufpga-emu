/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: alu
 */
#include "model.h"

#define GET_BIT(w, b)  (((w) >> (b)) & 1u)
#define GET_BITS(w, h, l) (((w) >> (l)) & ((1u << ((h)-(l)+1)) - 1u))

#define REG_COUNT 5

void circuit_init(model_state_t *state)
{
    state->regs[0] = 0;
    state->regs[1] = 0;
    state->regs[2] = 0;
    state->regs[3] = 0;
    state->regs[4] = 0;
    state->outputs = 0;
    state->clock_count = 0;
}

void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs)
{
    uint32_t a = GET_BITS(inputs, 3, 0);
    uint32_t b = GET_BITS(inputs, 7, 4);
    uint32_t op = GET_BITS(inputs, 9, 8);
    switch ((op)) {
        case 0:
            state->regs[0] = ((a + b)) & 0xF;
            break;
        case 1:
            state->regs[0] = ((a * b)) & 0xF;
            break;
        case 2:
            state->regs[0] = ((a / b)) & 0xF;
            break;
        case 3:
            state->regs[0] = ((a % b)) & 0xF;
            break;
        default:
            state->regs[0] = (0) & 0xF;
            break;
    }
    state->regs[1] = (((a < b))) & 0x1;
    state->regs[2] = (((a > b))) & 0x1;
    state->regs[3] = (((a <= b))) & 0x1;
    state->regs[4] = (((a >= b))) & 0x1;
    *outputs = ((state->regs[0] & 0xF) << 0) | ((state->regs[1] & 0x1) << 4) | ((state->regs[2] & 0x1) << 5) | ((state->regs[3] & 0x1) << 6) | ((state->regs[4] & 0x1) << 7);
}
