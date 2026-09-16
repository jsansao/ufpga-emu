/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: tiny_cpu
 */
#include "model.h"

#define GET_BIT(w, b)  (((w) >> (b)) & 1u)
#define GET_BITS(w, h, l) (((w) >> (l)) & ((1u << ((h)-(l)+1)) - 1u))

#define REG_COUNT 16

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
    state->regs[8] = 0;
    state->regs[9] = 0;
    state->regs[10] = 0;
    state->regs[11] = 0;
    state->regs[12] = 0;
    state->regs[13] = 0;
    state->regs[14] = 0;
    state->regs[15] = 0;
    state->outputs = 0;
    state->clock_count = 0;
}

void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs)
{
    uint32_t clk = GET_BIT(inputs, 0);
    uint32_t rst = GET_BIT(inputs, 1);
    uint32_t run = GET_BIT(inputs, 2);
    uint32_t instr = GET_BITS(inputs, 18, 3);
    uint8_t clk_edge = (clk == 1) && (state->regs[14] != 1);
    state->regs[14] = (clk) & 0x1;
    if (rst) {
        state->regs[0] = (0) & 0xFF;
        state->regs[3] = (0) & 0xFF;
        state->regs[4] = (0) & 0xFF;
        state->regs[5] = (0) & 0xFF;
        state->regs[6] = (0) & 0xFF;
        state->regs[7] = (0) & 0xFF;
        state->regs[8] = (0) & 0xF;
        state->regs[9] = (0) & 0x3;
        state->regs[10] = (0) & 0x3;
        state->regs[11] = (0) & 0x1;
        state->regs[12] = (0) & 0xFF;
        state->regs[13] = (0) & 0xFF;
        state->regs[1] = (0) & 0xFF;
        state->regs[2] = (0) & 0x1;
    } else if (clk_edge) {
        if (run) {
            if (!state->regs[11]) {
                state->regs[8] = (GET_BITS(instr, 15, 12)) & 0xF;
                state->regs[9] = (GET_BITS(instr, 11, 10)) & 0x3;
                state->regs[10] = (GET_BITS(instr, 9, 8)) & 0x3;
                state->regs[7] = (GET_BITS(instr, 7, 0)) & 0xFF;
                state->regs[0] = ((state->regs[0] + 1)) & 0xFF;
                state->regs[11] = (1) & 0x1;
            } else {
                switch ((state->regs[8])) {
                    case 0:
                        state->regs[11] = (0) & 0x1;
                        break;
                    case 1:
                        switch ((state->regs[9])) {
                            case 0:
                                state->regs[3] = (state->regs[7]) & 0xFF;
                                break;
                            case 1:
                                state->regs[4] = (state->regs[7]) & 0xFF;
                                break;
                            case 2:
                                state->regs[5] = (state->regs[7]) & 0xFF;
                                break;
                            case 3:
                                state->regs[6] = (state->regs[7]) & 0xFF;
                                break;
                        }
                        state->regs[1] = (state->regs[7]) & 0xFF;
                        state->regs[11] = (0) & 0x1;
                        break;
                    case 2:
                        switch ((state->regs[10])) {
                            case 0:
                                state->regs[12] = (state->regs[3]) & 0xFF;
                                break;
                            case 1:
                                state->regs[12] = (state->regs[4]) & 0xFF;
                                break;
                            case 2:
                                state->regs[12] = (state->regs[5]) & 0xFF;
                                break;
                            case 3:
                                state->regs[12] = (state->regs[6]) & 0xFF;
                                break;
                        }
                        switch ((state->regs[9])) {
                            case 0:
                                state->regs[3] = (state->regs[12]) & 0xFF;
                                break;
                            case 1:
                                state->regs[4] = (state->regs[12]) & 0xFF;
                                break;
                            case 2:
                                state->regs[5] = (state->regs[12]) & 0xFF;
                                break;
                            case 3:
                                state->regs[6] = (state->regs[12]) & 0xFF;
                                break;
                        }
                        state->regs[1] = (state->regs[12]) & 0xFF;
                        state->regs[11] = (0) & 0x1;
                        break;
                    case 3:
                        switch ((state->regs[10])) {
                            case 0:
                                state->regs[12] = (state->regs[3]) & 0xFF;
                                break;
                            case 1:
                                state->regs[12] = (state->regs[4]) & 0xFF;
                                break;
                            case 2:
                                state->regs[12] = (state->regs[5]) & 0xFF;
                                break;
                            case 3:
                                state->regs[12] = (state->regs[6]) & 0xFF;
                                break;
                        }
                        switch ((state->regs[9])) {
                            case 0:
                                state->regs[13] = (state->regs[3]) & 0xFF;
                                break;
                            case 1:
                                state->regs[13] = (state->regs[4]) & 0xFF;
                                break;
                            case 2:
                                state->regs[13] = (state->regs[5]) & 0xFF;
                                break;
                            case 3:
                                state->regs[13] = (state->regs[6]) & 0xFF;
                                break;
                        }
                        switch ((state->regs[9])) {
                            case 0:
                                state->regs[3] = ((state->regs[13] + state->regs[12])) & 0xFF;
                                break;
                            case 1:
                                state->regs[4] = ((state->regs[13] + state->regs[12])) & 0xFF;
                                break;
                            case 2:
                                state->regs[5] = ((state->regs[13] + state->regs[12])) & 0xFF;
                                break;
                            case 3:
                                state->regs[6] = ((state->regs[13] + state->regs[12])) & 0xFF;
                                break;
                        }
                        state->regs[1] = ((state->regs[13] + state->regs[12])) & 0xFF;
                        state->regs[11] = (0) & 0x1;
                        break;
                    case 4:
                        state->regs[0] = (state->regs[7]) & 0xFF;
                        state->regs[11] = (0) & 0x1;
                        break;
                    case 5:
                        switch ((state->regs[9])) {
                            case 0:
                                state->regs[1] = (state->regs[3]) & 0xFF;
                                break;
                            case 1:
                                state->regs[1] = (state->regs[4]) & 0xFF;
                                break;
                            case 2:
                                state->regs[1] = (state->regs[5]) & 0xFF;
                                break;
                            case 3:
                                state->regs[1] = (state->regs[6]) & 0xFF;
                                break;
                        }
                        state->regs[11] = (0) & 0x1;
                        break;
                    case 6:
                        state->regs[2] = (1) & 0x1;
                        state->regs[11] = (0) & 0x1;
                        break;
                    default:
                        state->regs[11] = (0) & 0x1;
                        break;
                }
            }
        }
    }
    *outputs = ((state->regs[0] & 0xFF) << 0) | ((state->regs[1] & 0xFF) << 8) | ((state->regs[2] & 0x1) << 16);
}
