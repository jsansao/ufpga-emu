/*
 * circuit_blinky.c — Exemplo manual de circuito.
 * Alterna o LED a cada 50000 ciclos de clock (~0.5s a 100kHz).
 */
#include "model.h"

#define REG_EDGE   0
#define REG_COUNTER 1
#define REG_CLK_OLD 2

void circuit_init(model_state_t *state)
{
    state->regs[REG_COUNTER] = 0;
    state->regs[REG_EDGE] = 0;
    state->regs[REG_CLK_OLD] = 0;
    state->outputs = 0;
    state->clock_count = 0;
}

void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs)
{
    uint8_t clk = (inputs >> 0) & 1u;
    uint8_t rst = (inputs >> 1) & 1u;

    if (rst) {
        state->regs[REG_COUNTER] = 0;
        state->regs[REG_CLK_OLD] = clk;
        *outputs = 0;
        return;
    }

    /* Deteccao de borda de subida */
    if (clk && !state->regs[REG_CLK_OLD]) {
        state->regs[REG_COUNTER]++;
        if (state->regs[REG_COUNTER] >= 50000) {
            state->regs[REG_COUNTER] = 0;
            state->regs[REG_EDGE] ^= 1u;
        }
    }
    state->regs[REG_CLK_OLD] = clk;

    *outputs = state->regs[REG_EDGE];
}
