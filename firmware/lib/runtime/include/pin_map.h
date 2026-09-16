#ifndef PIN_MAP_H
#define PIN_MAP_H

#include <stdint.h>

#define MAX_PIN_BINDINGS 64
#define MAX_PIN_NAME_LEN 32

typedef enum {
    PIN_DIR_INPUT,
    PIN_DIR_OUTPUT
} pin_direction_t;

typedef struct {
    uint8_t physical_pin;
    uint8_t bit_pos;
    pin_direction_t direction;
    char name[MAX_PIN_NAME_LEN];
} pin_binding_t;

typedef struct {
    pin_binding_t bindings[MAX_PIN_BINDINGS];
    uint8_t count;
} pin_map_t;

int  pin_map_load(pin_map_t *map, const char *json_str);
int  pin_map_load_file(pin_map_t *map, const char *filepath);
int  pin_map_get_bit(const pin_map_t *map, const char *name);
int  pin_map_get_physical(const pin_map_t *map, const char *name);

#endif
