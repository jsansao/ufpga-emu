#include "vcd_writer.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#if defined(__linux__)

static char id_from_idx(int idx)
{
    return (char)('!' + idx);
}

static void vcd_write_value(FILE *f, uint32_t val, int width, char id)
{
    if (width == 1) {
        fprintf(f, "%u%c\n", val & 1u, id);
    } else {
        fprintf(f, "b");
        for (int b = width - 1; b >= 0; b--)
            fputc((val >> b) & 1u ? '1' : '0', f);
        fprintf(f, " %c\n", id);
    }
}

int vcd_init(vcd_writer_t *vcd, const char *path,
             const pin_map_t *pin_map, int reg_count, int wire_count)
{
    FILE *f = fopen(path, "w");
    if (!f) return -1;

    memset(vcd, 0, sizeof(*vcd));
    vcd->file = f;
    vcd->pin_map = pin_map;
    vcd->signal_count = 0;

    fprintf(f, "$timescale 1 us $end\n");
    fprintf(f, "$scope module top $end\n");

    for (int i = 0; i < pin_map->count && vcd->signal_count < VCD_MAX_SIGNALS; i++) {
        vcd_signal_entry_t *s = &vcd->signals[vcd->signal_count];
        strncpy(s->name, pin_map->bindings[i].name, sizeof(s->name) - 1);
        s->width = 1;
        s->bit_offset = pin_map->bindings[i].bit_pos;
        s->is_input = (pin_map->bindings[i].direction == PIN_DIR_INPUT);
        s->is_reg = 0;
        char id = id_from_idx(vcd->signal_count);
        fprintf(f, "$var wire 1 %c %s $end\n", id, s->name);
        vcd->signal_count++;
    }

    for (int i = 0; i < reg_count && vcd->signal_count < VCD_MAX_SIGNALS; i++) {
        vcd_signal_entry_t *s = &vcd->signals[vcd->signal_count];
        snprintf(s->name, sizeof(s->name), "reg%d", i);
        s->width = 32;
        s->is_reg = 1;
        s->is_input = 0;
        s->bit_offset = 0;
        char id = id_from_idx(vcd->signal_count);
        fprintf(f, "$var reg 32 %c %s $end\n", id, s->name);
        vcd->signal_count++;
    }

    for (int i = 0; i < wire_count && vcd->signal_count < VCD_MAX_SIGNALS; i++) {
        vcd_signal_entry_t *s = &vcd->signals[vcd->signal_count];
        snprintf(s->name, sizeof(s->name), "wire%d", i);
        s->width = 32;
        s->is_reg = 0;
        s->is_input = 0;
        s->bit_offset = 0;
        char id = id_from_idx(vcd->signal_count);
        fprintf(f, "$var wire 32 %c %s $end\n", id, s->name);
        vcd->signal_count++;
    }

    fprintf(f, "$upscope $end\n");
    fprintf(f, "$enddefinitions $end\n");

    vcd->initialized = 1;
    vcd->has_state = 0;
    return 0;
}

void vcd_record(vcd_writer_t *vcd,
                uint32_t inputs, uint32_t outputs,
                const uint32_t *regs, const uint32_t *wires,
                uint32_t clock_count)
{
    if (!vcd || !vcd->initialized) return;
    FILE *f = (FILE *)vcd->file;

    int changed = 0;

    if (!vcd->has_state) {
        changed = 1;
    } else {
        if (inputs != vcd->prev_inputs) changed = 1;
        if (outputs != vcd->prev_outputs) changed = 1;
        if (!changed) {
            for (int i = 0; i < vcd->signal_count; i++) {
                vcd_signal_entry_t *s = &vcd->signals[i];
                if (s->is_reg) {
                    int idx = atoi(s->name + 3);
                    if (regs[idx] != vcd->prev_regs[idx]) { changed = 1; break; }
                }
            }
        }
    }

    if (!changed) return;

    fprintf(f, "#%u\n", clock_count);

    for (int i = 0; i < vcd->signal_count; i++) {
        vcd_signal_entry_t *s = &vcd->signals[i];
        char id = id_from_idx(i);

        if (s->is_reg) {
            int idx = atoi(s->name + 3);
            uint32_t val = regs[idx];
            uint32_t prev = vcd->prev_regs[idx];
            if (!vcd->has_state || val != prev) {
                vcd_write_value(f, val, s->width, id);
                vcd->prev_regs[idx] = val;
            }
        } else if (s->is_input) {
            uint32_t val = (inputs >> s->bit_offset) & 1u;
            uint32_t prev = (vcd->prev_inputs >> s->bit_offset) & 1u;
            if (!vcd->has_state || val != prev) {
                vcd_write_value(f, val, 1, id);
            }
        } else {
            uint32_t val = (outputs >> s->bit_offset) & 1u;
            uint32_t prev = (vcd->prev_outputs >> s->bit_offset) & 1u;
            if (!vcd->has_state || val != prev) {
                vcd_write_value(f, val, 1, id);
            }
        }
    }

    vcd->prev_inputs = inputs;
    vcd->prev_outputs = outputs;
    vcd->has_state = 1;
    vcd->record_count++;
    if ((vcd->record_count & 0x3FF) == 0)
        fflush(f);
}

void vcd_close(vcd_writer_t *vcd)
{
    if (!vcd || !vcd->initialized) return;
    FILE *f = (FILE *)vcd->file;
    if (f) fclose(f);
    vcd->initialized = 0;
}

#else

int vcd_init(vcd_writer_t *vcd, const char *path,
             const pin_map_t *pin_map, int reg_count, int wire_count)
{
    (void)vcd; (void)path; (void)pin_map; (void)reg_count; (void)wire_count;
    return -1;
}

void vcd_record(vcd_writer_t *vcd,
                uint32_t inputs, uint32_t outputs,
                const uint32_t *regs, const uint32_t *wires,
                uint32_t clock_count)
{
    (void)vcd; (void)inputs; (void)outputs;
    (void)regs; (void)wires; (void)clock_count;
}

void vcd_close(vcd_writer_t *vcd)
{
    (void)vcd;
}

#endif
