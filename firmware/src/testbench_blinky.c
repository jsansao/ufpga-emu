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
        printf("FAIL %s step %d: inputs=0x%X expected=%u got=%u\n",
               label, step, (unsigned)inp, (unsigned)exp, (unsigned)out);
        failures++;
    }
    step++;
}

int main(void)
{
    /* Blinky: LED toggles every 50000 rising edges */
    /* Inputs: bit1=rst, bit0=clk */
    /* Outputs: bit0=led */

    circuit_init(&state);

    /* Reset */
    check("rst",  0b10, 0);  /* clk=0, rst=1 */
    check("rst2", 0b11, 0);  /* clk=1, rst=1 */
    check("rel",  0b00, 0);  /* release */

    /* 49999 edges should keep output=0 */
    for (int i = 1; i <= 49999; i++) {
        check("up",  0b01, 0);  /* rising edge */
        check("hld", 0b00, 0);  /* hold */
    }
    /* After our loop, last eval was clk=0 (the "hld" step).
     * regs[REG_COUNTER]=49999, regs[REG_CLK_OLD]=0
     * Counter hasn't reached 50000 yet. */

    /* 50000th edge: toggle to 1 */
    check("edge50000", 0b01, 1);  /* counter=50000 → toggle! output=1 */
    check("hold1",     0b00, 1);  /* holds 1 */

    /* 49999 more edges should keep output=1 */
    for (int i = 1; i <= 49999; i++) {
        check("up2",  0b01, 1);
        check("hld2", 0b00, 1);
    }

    /* 100000th edge: toggle back to 0 */
    check("edge100k", 0b01, 0);  /* toggle! output=0 */
    check("hold2",    0b00, 0);

    /* Reset should set output=0 */
    check("rst3", 0b10, 0);
    check("rst4", 0b11, 0);
    check("rel2", 0b00, 0);
    check("post", 0b01, 0);  /* 1 edge apos reset → counter=1, output=0 */

    printf("%s: %d steps, %d failures\n",
           failures ? "FAIL" : "PASS", step, failures);
    return failures ? 1 : 0;
}
