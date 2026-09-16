/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: fsm_101
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
    uint32_t data_in = GET_BIT(inputs, 2);
    uint8_t clk_edge = (clk == 1) && (state->regs[2] != 1);
    state->regs[2] = (clk) & 0x1;
    if (rst) {
        state->regs[1] = (0) & 0x3;
        state->regs[0] = (0) & 0x1;
    } else if (clk_edge) {
        switch ((state->regs[1])) {
            case 0:
                if (data_in) {
                    state->regs[1] = (1) & 0x3;
                } else {
                    state->regs[1] = (0) & 0x3;
                }
                state->regs[0] = (0) & 0x1;
                break;
            case 1:
                if (data_in) {
                    state->regs[1] = (1) & 0x3;
                } else {
                    state->regs[1] = (2) & 0x3;
                }
                state->regs[0] = (0) & 0x1;
                break;
            case 2:
                if (data_in) {
                    state->regs[1] = (1) & 0x3;
                    state->regs[0] = (1) & 0x1;
                } else {
                    state->regs[1] = (0) & 0x3;
                    state->regs[0] = (0) & 0x1;
                }
                break;
            default:
                state->regs[1] = (0) & 0x3;
                state->regs[0] = (0) & 0x1;
                break;
        }
    }
    *outputs = ((state->regs[0] & 0x1) << 0);
}
