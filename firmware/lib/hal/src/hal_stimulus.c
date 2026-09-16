#if defined(__linux__)

#include "hal_stimulus.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_EVENTS 512
#define MAX_PINS 64

typedef struct {
    uint64_t time_us;
    uint8_t  pin;
    uint8_t  value;
} event_t;

static event_t events[MAX_EVENTS];
static int event_count = 0;
static int next_idx = 0;
static int pin_values[MAX_PINS];
static uint64_t start_us = 0;
static int loaded = 0;

static int cmp_events(const void *a, const void *b)
{
    const event_t *ea = (const event_t *)a;
    const event_t *eb = (const event_t *)b;
    if (ea->time_us < eb->time_us) return -1;
    if (ea->time_us > eb->time_us) return 1;
    return 0;
}

int hal_stimulus_load(const char *csv_path, const pin_map_t *pin_map)
{
    for (int i = 0; i < MAX_PINS; i++) pin_values[i] = -1;
    event_count = 0;
    next_idx = 0;
    loaded = 0;

    FILE *f = fopen(csv_path, "r");
    if (!f) return -1;

    char line[256];
    int lineno = 0;

    while (fgets(line, sizeof(line), f)) {
        lineno++;
        if (lineno == 1) continue;
        if (line[0] == '#' || line[0] == '\n') continue;

        char sig_name[64];
        unsigned long t;
        int val;
        if (sscanf(line, "%lu,%63[^,],%d", &t, sig_name, &val) < 3) continue;
        if (event_count >= MAX_EVENTS) break;

        int physical_pin = pin_map_get_physical(pin_map, sig_name);
        if (physical_pin < 0) continue;

        events[event_count].time_us = (uint64_t)t;
        events[event_count].pin = (uint8_t)physical_pin;
        events[event_count].value = (uint8_t)(val ? 1 : 0);
        event_count++;
    }
    fclose(f);

    qsort(events, event_count, sizeof(event_t), cmp_events);
    start_us = 0;
    loaded = 1;
    return 0;
}

int hal_stimulus_get(uint8_t physical_pin, uint64_t now_us)
{
    if (!loaded) return -1;
    if (start_us == 0) start_us = now_us;

    uint64_t elapsed = now_us - start_us;

    while (next_idx < event_count && events[next_idx].time_us <= elapsed) {
        pin_values[events[next_idx].pin] = events[next_idx].value;
        next_idx++;
    }

    if (physical_pin < MAX_PINS && pin_values[physical_pin] >= 0) {
        return pin_values[physical_pin];
    }
    return -1;
}

#endif
