#ifndef PIN_MAP_H
#define PIN_MAP_H

#include <stdint.h>

#define MAX_PIN_BINDINGS 64
#define MAX_PIN_NAME_LEN 32
#define MAX_PIN_INITS 8

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

typedef struct {
    char name[MAX_PIN_NAME_LEN];
    uint8_t value;
} pin_init_t;

int  pin_map_load(pin_map_t *map, const char *json_str);
int  pin_map_load_file(pin_map_t *map, const char *filepath);
/* Carrega o circuito do JSON multi-circuito (chave "circuit").
 * Preenche map com "pins" e inits (ate max_inits) com "virtual_init".
 * Retorna o total de entradas virtual_init, ou -1 se circuito ausente. */
int  pin_map_load_circuit(pin_map_t *map, const char *json_str,
                          const char *circuit,
                          pin_init_t *inits, uint8_t max_inits);
int  pin_map_get_bit(const pin_map_t *map, const char *name);
int  pin_map_get_physical(const pin_map_t *map, const char *name);

#endif
