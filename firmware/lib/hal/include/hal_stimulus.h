#ifndef HAL_STIMULUS_H
#define HAL_STIMULUS_H

#include <stdint.h>
#include "pin_map.h"

#if defined(__linux__)

int hal_stimulus_load(const char *csv_path, const pin_map_t *pin_map);
int hal_stimulus_get(uint8_t physical_pin, uint64_t now_us);

#endif

#endif
