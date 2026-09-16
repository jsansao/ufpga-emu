#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "model.h"

void circuit_init(model_state_t *state);
void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs);

#define MAX_EVENTS 256
#define SIGNAL_MAX 64
#define HALF_PERIOD_US 5
#define MAX_TIME_US 100

typedef struct {
    uint64_t time_us;
    char signal[SIGNAL_MAX];
    uint8_t value;
} event_t;

static event_t events[MAX_EVENTS];
static int num_events = 0;
static int failures = 0;

static int parse_csv(const char *path)
{
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    char line[256];
    int lineno = 0;
    while (fgets(line, sizeof(line), f)) {
        lineno++;
        if (lineno == 1) continue;
        if (line[0] == '#' || line[0] == '\n') continue;
        unsigned long t;
        char sig[64];
        int val;
        if (sscanf(line, "%lu,%63[^,],%d", &t, sig, &val) < 3) continue;
        if (num_events >= MAX_EVENTS) break;
        events[num_events].time_us = t;
        strncpy(events[num_events].signal, sig, SIGNAL_MAX - 1);
        events[num_events].signal[SIGNAL_MAX - 1] = '\0';
        events[num_events].value = (uint8_t)(val ? 1 : 0);
        num_events++;
    }
    fclose(f);
    return 0;
}

static void check(uint64_t t, const char *label, uint32_t actual, uint32_t expected)
{
    if (actual != expected) {
        printf("FAIL %s t=%lu: expected=%u got=%u\n",
               label, (unsigned long)t, (unsigned)expected, (unsigned)actual);
        failures++;
    }
}

int main(void)
{
    const char *csv = getenv("STIMULUS_CSV");
    if (!csv) {
        fprintf(stderr, "FAIL: STIMULUS_CSV env var not set\n");
        return 1;
    }
    if (parse_csv(csv) != 0) {
        fprintf(stderr, "FAIL: could not open %s\n", csv);
        return 1;
    }

    model_state_t state;
    circuit_init(&state);

    uint32_t rst_val = 0;
    int event_idx = 0;
    int steps = 0;

    for (uint64_t t = 0; t <= MAX_TIME_US; t += HALF_PERIOD_US) {
        while (event_idx < num_events && events[event_idx].time_us <= t) {
            event_t *e = &events[event_idx];
            if (strcmp(e->signal, "rst") == 0) {
                rst_val = e->value;
            }
            event_idx++;
        }

        uint32_t clk = (uint32_t)((t / HALF_PERIOD_US) & 1u);
        uint32_t inputs = (clk) | (rst_val << 1);

        uint32_t outputs;
        circuit_eval(&state, inputs, &outputs);
        steps++;

        if (t == 10)  check(t, "count1", outputs, 1);
        if (t == 20)  check(t, "count2", outputs, 2);
        if (t == 30)  check(t, "count3", outputs, 3);
        if (t == 40)  check(t, "count4", outputs, 4);
        if (t == 50)  check(t, "count5", outputs, 5);
        if (t == 60)  check(t, "count6", outputs, 6);
        if (t == 70)  check(t, "count7", outputs, 7);
        if (t == 80)  check(t, "rst_clear", outputs, 0);
        if (t == 90)  check(t, "count1_again", outputs, 1);
    }

    printf("%s: %d steps, %d failures\n",
           failures ? "FAIL" : "PASS", steps, failures);
    return failures ? 1 : 0;
}
