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
        printf("FAIL %s step %d: inputs=0x%04X expected=0x%X got=0x%X\n",
               label, step, (unsigned)inp, (unsigned)exp, (unsigned)out);
        failures++;
    }
    step++;
}

int main(void)
{
    #define CL0(r) ((uint32_t)(r) << 1)
    #define CL1(r) (1u | ((uint32_t)(r) << 1))

    circuit_init(&state);

    /* Reset */
    check("rst0", CL0(1), 0);
    check("rst1", CL1(1), 0);
    check("rel0", CL0(0), 0);

    /* Count up to 20, wrap to 0 at 16 */
    for (int i = 1; i <= 20; i++) {
        check("cnt", CL1(0), (uint32_t)(i & 0xF));
        check("hld", CL0(0), (uint32_t)(i & 0xF));
    }
    /* Count=20 → output = 20 & 0xF = 4 */

    /* Reset should force output to 0 */
    check("r2_0", CL0(1), 0);  /* rst=1 → regs[0]=0, output=0 */
    check("r2_1", CL1(1), 0);
    check("r2_2", CL0(0), 0);
    check("r2_3", CL1(0), 1);  /* count=1 */

    printf("%s: %d steps, %d failures\n",
           failures ? "FAIL" : "PASS", step, failures);
    return failures ? 1 : 0;
}
