/*
 * Gerado pelo pc_tool uFPGA-Emu
 * Modulo: task_func
 */
#include "model.h"

#define GET_BIT(w, b)  (((w) >> (b)) & 1u)
#define GET_BITS(w, h, l) (((w) >> (l)) & ((1u << ((h)-(l)+1)) - 1u))

#define REG_COUNT 3

static inline uint32_t add_func(uint32_t x, uint32_t y)
{
    return (x + y);
}

static void mult_task(model_state_t *state, uint32_t x, uint32_t y, uint32_t *z)
{
    *z = 0;
    for (int i = 0; (i < 4); i = (i + 1)) {
        if (GET_BIT(y, i)) {
            *z = (*z + ((x << i)));
        }
    }
}

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
    uint32_t a = GET_BITS(inputs, 5, 2);
    uint32_t b = GET_BITS(inputs, 9, 6);
    *outputs = 0;
    uint8_t clk_rise = (clk == 1) && (state->regs[1] != 1);
    uint8_t rst_rise = (rst == 1) && (state->regs[2] != 1);
    if (clk_rise || rst_rise) {
        if (rst) {
            state->regs[0] = (0) & 0xFF;
        } else {
            mult_task(state, a, b, &state->regs[0]);
            if ((state->regs[0] == 0)) {
                state->regs[0] = (add_func(a, b)) & 0xFF;
            }
        }
    }
    state->regs[1] = (clk) & 0x1;
    state->regs[2] = (rst) & 0x1;
    *outputs |= (((state->regs[0] & 0xFF)) << 0);
}
