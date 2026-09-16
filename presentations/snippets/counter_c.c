void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs)
{
    uint32_t clk = GET_BIT(inputs, 0);
    uint32_t rst = GET_BIT(inputs, 1);
    uint8_t clk_edge = (clk == 1) && (state->regs[1] != 1);
    state->regs[1] = (clk) & 0x1;
    if (rst) {
        state->regs[0] = (0) & 0xF;
    } else if (clk_edge) {
        state->regs[0] = ((state->regs[0] + 1)) & 0xF;
    }
    *outputs = ((state->regs[0] & 0xF) << 0);
}
