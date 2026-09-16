/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: shift_register
 */
#include "model.h"

#define GET_BIT(w, b)  (((w) >> (b)) & 1u)
#define GET_BITS(w, h, l) (((w) >> (l)) & ((1u << ((h)-(l)+1)) - 1u))

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
    uint32_t clk = GET_BIT(inputs, 0);
    uint32_t rst = GET_BIT(inputs, 1);
    uint32_t load = GET_BIT(inputs, 2);
    uint32_t data_in = GET_BIT(inputs, 3);
    uint32_t parallel_load = GET_BITS(inputs, 11, 4);
    uint8_t clk_edge = (clk == 1) && (state->regs[1] != 1);
    state->regs[1] = (clk) & 0x1;
    if (rst) {
        state->regs[0] = (0) & 0xFF;
    } else if (clk_edge) {
        if (load) {
            state->regs[0] = (parallel_load) & 0xFF;
        } else {
            state->regs[0] = ((data_in & 0x1) | (((GET_BITS(state->regs[0], 6, 0) & 0x7F)) << 1)) & 0xFF;
        }
    }
    *outputs = ((state->regs[0] & 0xFF) << 0);
}
