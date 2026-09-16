/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: mixed
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
    uint32_t clk = GET_BIT(inputs, 0);
    uint32_t rst = GET_BIT(inputs, 1);
    uint32_t a = GET_BIT(inputs, 2);
    uint32_t b = GET_BIT(inputs, 3);
    *outputs = 0;
    uint8_t clk_rise = (clk == 1) && (state->regs[2] != 1);
    uint8_t rst_rise = (rst == 1) && (state->regs[3] != 1);
    if ((a & b)) {
        state->regs[1] = 1;
    } else {
        state->regs[1] = 0;
    }
    if (clk_rise || rst_rise) {
        if (rst) {
            state->regs[0] = 0;
        } else {
            state->regs[0] = ((state->regs[0] + 1)) & 0x3;
        }
    }
    state->regs[2] = (clk) & 0x1;
    state->regs[3] = (rst) & 0x1;
    *outputs |= (state->regs[0] & 0x3);
    *outputs |= (((state->regs[1] & 0x1)) << 2);
}
