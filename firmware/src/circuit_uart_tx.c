/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: uart_tx
 */
#include "model.h"

#define GET_BIT(w, b)  (((w) >> (b)) & 1u)
#define GET_BITS(w, h, l) (((w) >> (l)) & ((1u << ((h)-(l)+1)) - 1u))

#define CLK_DIV 8

#define REG_COUNT 8

void circuit_init(model_state_t *state)
{
    state->regs[0] = 0;
    state->regs[1] = 0;
    state->regs[2] = 0;
    state->regs[3] = 0;
    state->regs[4] = 0;
    state->regs[5] = 0;
    state->regs[6] = 0;
    state->regs[7] = 0;
    state->outputs = 0;
    state->clock_count = 0;
}

void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs)
{
    uint32_t clk = GET_BIT(inputs, 0);
    uint32_t rst = GET_BIT(inputs, 1);
    uint32_t send = GET_BIT(inputs, 2);
    uint32_t data = GET_BITS(inputs, 10, 3);
    uint8_t clk_edge = (clk == 1) && (state->regs[6] != 1);
    state->regs[6] = (clk) & 0x1;
    if (rst) {
        state->regs[2] = (0) & 0xF;
        state->regs[3] = (0) & 0xF;
        state->regs[4] = (0) & 0xFF;
        state->regs[5] = (0) & 0x1;
        state->regs[0] = (1) & 0x1;
        state->regs[1] = (0) & 0x1;
    } else if (clk_edge) {
        if (!state->regs[5]) {
            if (send) {
                state->regs[5] = (1) & 0x1;
                state->regs[4] = (data) & 0xFF;
                state->regs[3] = (0) & 0xF;
                state->regs[2] = (0) & 0xF;
                state->regs[0] = (0) & 0x1;
                state->regs[1] = (1) & 0x1;
            }
        } else {
            if ((state->regs[2] == (CLK_DIV - 1))) {
                state->regs[2] = (0) & 0xF;
                if ((state->regs[3] == 9)) {
                    state->regs[5] = (0) & 0x1;
                    state->regs[1] = (0) & 0x1;
                    state->regs[0] = (1) & 0x1;
                } else {
                    state->regs[3] = ((state->regs[3] + 1)) & 0xF;
                    if ((state->regs[3] < 8)) {
                        state->regs[0] = (GET_BIT(state->regs[4], 0)) & 0x1;
                    } else {
                        state->regs[0] = (1) & 0x1;
                    }
                    state->regs[4] = ((0 & 0x1) | (((GET_BITS(state->regs[4], 6, 0) & 0x7F)) << 1)) & 0xFF;
                }
            } else {
                state->regs[2] = ((state->regs[2] + 1)) & 0xF;
            }
        }
    }
    *outputs = ((state->regs[0] & 0x1) << 0) | ((state->regs[1] & 0x1) << 1);
}
