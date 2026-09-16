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
        printf("FAIL %s step %d: inputs=0x%04X expected=0x%04X got=0x%04X\n",
               label, step, (unsigned)inp, (unsigned)exp, (unsigned)out);
        failures++;
    }
    step++;
}

int main(void)
{
    /* FSM 101: Moore machine - detected only asserted on rising edge */
    /* Inputs: bit2=data_in, bit1=rst, bit0=clk */
    /* Outputs: bit0=detected */

    /* Helper macros for readability */
    /* clk=0, rst, data_in */
    #define CL0(r,d)  (((uint32_t)(r) << 1) | ((uint32_t)(d) << 2))
    /* clk=1, rst, data_in */
    #define CL1(r,d)  (1u | ((uint32_t)(r) << 1) | ((uint32_t)(d) << 2))

    circuit_init(&state);

    /* Reset sequence */
    check("reset", CL0(1,0), 0);  /* clk=0, rst=1 */
    check("reset", CL1(1,0), 0);  /* clk=1, rst=1 → reset (detected=0) */
    check("hold1", CL0(0,0), 0);  /* clk=0, rst=0, no edge, detected holds 0 */
    check("idle",  CL1(0,0), 0);  /* edge, data=0 → IDLE, detected=0 */
    check("hold2", CL0(0,0), 0);
    check("idle2", CL1(0,0), 0);  /* edge, data=0 → IDLE */

    /* S1: data=1 */
    check("hold3", CL0(0,1), 0);  /* setup data=1, no edge */
    check("toS1",  CL1(0,1), 0);  /* edge, data=1 → S1, detected=0 */

    /* Stay in S1 */
    check("hold4", CL0(0,1), 0);
    check("stayS1",CL1(0,1), 0);  /* edge, data=1 → stay S1, detected=0 */

    /* S2: data=0 */
    check("hold5", CL0(0,0), 0);  /* setup data=0 */
    check("toS2",  CL1(0,0), 0);  /* edge, data=0 → S2, detected=0 */

    /* Detection: data=1 in S2 */
    check("hold6", CL0(0,1), 0);  /* setup data=1 */
    check("detect",CL1(0,1), 1);  /* edge, data=1 → S1, detected=1!!! */
    check("hold7", CL0(0,0), 1);  /* detected holds 1 between edges */
    check("toS2b", CL1(0,0), 0);  /* edge, S1+data=0 → S2, detected=0 */

    /* Reset stops detection */
    check("hold8", CL0(0,1), 0);  /* no effect yet */
    check("reset2",CL1(1,0), 0);  /* edge, rst=1 → reset, detected=0 */
    check("hold9", CL0(0,0), 0);
    check("idle3", CL1(0,0), 0);  /* edge, data=0 → IDLE */

    /* Re-test detection quickly */
    check("h10", CL0(0,1), 0);
    check("e10", CL1(0,1), 0);  /* S1 */
    check("h11", CL0(0,0), 0);
    check("e11", CL1(0,0), 0);  /* S2 */
    check("h12", CL0(0,1), 0);
    check("e12", CL1(0,1), 1);  /* S1 + detected=1 */
    check("h13", CL0(0,0), 1);  /* holds */
    check("e13", CL1(0,0), 0);  /* S2 + detected=0 */

    printf("%s: %d steps, %d failures\n",
           failures ? "FAIL" : "PASS", step, failures);
    return failures ? 1 : 0;
}
