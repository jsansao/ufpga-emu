#include <stdio.h>
#include <stdint.h>
#include "model.h"

void circuit_init(model_state_t *state);
void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs);

static int step = 0;
static int failures = 0;
static uint32_t out;
static model_state_t state;

static void check(const char *label, uint32_t inp, uint32_t exp)
{
    circuit_eval(&state, inp, &out);
    if (out != exp) {
        printf("FAIL %s step %d: inputs=0x%04X expected=0x%02X got=0x%02X\n",
               label, step, (unsigned)inp, (unsigned)exp, (unsigned)out);
        failures++;
    }
    step++;
}

/* Input word: bit0=clk, bit1=rst, bit2=load, bit3=data_in, bits11..4=parallel_load */
static uint32_t inp(uint8_t clk, uint8_t rst, uint8_t load, uint8_t data_in, uint8_t pload)
{
    return (uint32_t)clk | ((uint32_t)rst << 1) | ((uint32_t)load << 2)
         | ((uint32_t)data_in << 3) | ((uint32_t)(pload & 0xFF) << 4);
}

int main(void)
{
    circuit_init(&state);

    /* === Reset === */
    check("rst",  inp(0,1,0,0,0), 0);
    check("rst+", inp(1,1,0,0,0), 0);
    check("rel",  inp(0,0,0,0,0), 0);

    /* === Shift serial: 8 bits of 1 (LSB first) === */
    /* data_out = {data_out[6:0], data_in} = (data_out << 1) | data_in */
    uint8_t exp = 0;
    for (int i = 0; i < 8; i++) {
        exp = (uint8_t)((exp << 1) | 1u);
        check("sh1", inp(1,0,0,1,0), (uint32_t)exp);
        check("h1",  inp(0,0,0,1,0), (uint32_t)exp);
    }
    /* exp = 0xFF */

    /* === Shift serial: 8 bits of 0 (LSB first) === */
    for (int i = 0; i < 8; i++) {
        exp = (uint8_t)(exp << 1);
        check("sh0", inp(1,0,0,0,0), (uint32_t)exp);
        check("h0",  inp(0,0,0,0,0), (uint32_t)exp);
    }
    /* exp = 0x00 */

    /* === Parallel load 0xA5 === */
    check("pl0", inp(0,0,0,0,0), 0);    /* hold */
    check("pl1", inp(1,0,1,0,0xA5), 0xA5);  /* load=1, pload=0xA5 */
    check("pl2", inp(0,0,0,0,0), 0xA5);  /* hold */

    /* Shift: {0xA5[6:0], data_in=1} = (0xA5 << 1) | 1 = 0x14B & 0xFF = 0x4B */
    check("hld1", inp(0,0,0,1,0), 0xA5);  /* clk=0, no edge yet */
    check("sh1x", inp(1,0,0,1,0), 0x4B);  /* rising edge */

    /* === Parallel load 0xFF === */
    check("hld2", inp(0,0,0,0,0), 0x4B);  /* hold, clk=0 */
    check("pl3",  inp(1,0,1,0,0xFF), 0xFF);  /* load=1, pload=0xFF */

    /* Shift: {0xFF[6:0], data_in=0} = 0xFE */
    check("hld3", inp(0,0,0,0,0), 0xFF);  /* clk=0 first */
    check("shf",  inp(1,0,0,0,0), 0xFE);  /* rising edge, shift 0 */

    /* Shift again: {0xFE[6:0], data_in=0} = 0xFC */
    check("hld4", inp(0,0,0,0,0), 0xFE);
    check("shf2", inp(1,0,0,0,0), 0xFC);

    printf("%s: %d steps, %d failures\n",
           failures ? "FAIL" : "PASS", step, failures);
    return failures ? 1 : 0;
}
