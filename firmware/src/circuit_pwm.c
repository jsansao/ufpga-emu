/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: pwm
 */
#include "model.h"

#define GET_BIT(w, b)  (((w) >> (b)) & 1u)
#define GET_BITS(w, h, l) (((w) >> (l)) & ((1u << ((h)-(l)+1)) - 1u))

#define WIDTH 8

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
    uint32_t enable = GET_BIT(inputs, 2);
    uint32_t duty = GET_BITS(inputs, 10, 3);
    uint32_t period = GET_BITS(inputs, 18, 11);
    uint8_t clk_edge = (clk == 1) && (state->regs[2] != 1);
    state->regs[2] = (clk) & 0x1;
    if (rst) {
        state->regs[1] = (0) & 0xFF;
        state->regs[0] = (0) & 0x1;
    } else if (clk_edge) {
        if (!enable) {
            state->regs[1] = (0) & 0xFF;
            state->regs[0] = (0) & 0x1;
        } else {
            if ((state->regs[1] >= period)) {
                state->regs[1] = (0) & 0xFF;
                state->regs[0] = (((duty != 0))) & 0x1;
            } else {
                if ((state->regs[1] < duty)) {
                    state->regs[1] = ((state->regs[1] + 1)) & 0xFF;
                    state->regs[0] = (1) & 0x1;
                } else {
                    state->regs[1] = ((state->regs[1] + 1)) & 0xFF;
                    state->regs[0] = (0) & 0x1;
                }
            }
        }
    }
    *outputs = ((state->regs[0] & 0x1) << 0);
}
