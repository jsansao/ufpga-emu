/*
 * circuit_template.c
 * Template gerado pelo pc_tool (uFPGA-Emu).
 * O codegen deve preencher circuit_init() e circuit_eval()
 * com base no HDL de entrada.
 */
#include "model.h"
#include "emulator.h"

/* Numero de registradores/variaveis internas */
#define REG_COUNT 1

void circuit_init(model_state_t *state)
{
    for (int i = 0; i < REG_COUNT; i++) {
        state->regs[i] = 0;
    }
    state->inputs  = 0;
    state->outputs = 0;
    state->clock_count = 0;
}

/*
 * Avaliacao ciclo-a-ciclo.
 * inputs:  word de 32 bits com os sinais de entrada mapeados
 * outputs: word de 32 bits com os sinais de saida
 */
void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs)
{
    (void)state;
    (void)inputs;
    *outputs = 0;
}
