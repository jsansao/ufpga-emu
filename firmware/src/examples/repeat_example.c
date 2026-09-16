/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: repeat_example
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
    uint32_t value = ((inputs >> 2) & 0xFFu);
    uint32_t n = ((inputs >> 10) & 0x7u);
    *outputs = 0;
    uint8_t clk_rise = (clk == 1) && (state->regs[2] != 1);
    uint8_t rst_rise = (rst == 1) && (state->regs[3] != 1);
    if (clk_rise || rst_rise) {
        if (rst) {
            state->regs[0] = 0;
        } else {
            state->regs[1] = (value) & 0xFF;
            for (int __repeat_i = 0; __repeat_i < n; __repeat_i++) {
                state->regs[1] = ((state->regs[1] << 1)) & 0xFF;
            }
            state->regs[0] = (state->regs[1]) & 0xFF;
        }
    }
    state->regs[2] = (clk) & 0x1;
    state->regs[3] = (rst) & 0x1;
    *outputs |= (state->regs[0] & 0xFF);
}
