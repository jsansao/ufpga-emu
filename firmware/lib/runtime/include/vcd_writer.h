#ifndef VCD_WRITER_H
#define VCD_WRITER_H

#include <stdint.h>
#include "pin_map.h"

#define VCD_MAX_SIGNALS 128

typedef struct {
    char    name[32];
    int     width;
    int     is_reg;
    int     bit_offset;
    int     is_input;
} vcd_signal_entry_t;

typedef struct vcd_writer_s {
    void   *file;
    int     initialized;
    vcd_signal_entry_t signals[VCD_MAX_SIGNALS];
    int     signal_count;
    uint32_t prev_inputs;
    uint32_t prev_outputs;
    uint32_t prev_regs[64];
    uint32_t prev_wires[64];
    const pin_map_t *pin_map;
    int     has_state;
    uint32_t record_count;
} vcd_writer_t;

int vcd_init(vcd_writer_t *vcd, const char *path,
             const pin_map_t *pin_map, int reg_count, int wire_count);
void vcd_record(vcd_writer_t *vcd,
                uint32_t inputs, uint32_t outputs,
                const uint32_t *regs, const uint32_t *wires,
                uint32_t clock_count);
void vcd_close(vcd_writer_t *vcd);

#endif
