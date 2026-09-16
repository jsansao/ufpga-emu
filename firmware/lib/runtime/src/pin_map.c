#include "pin_map.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

static int pin_map_parse_json(pin_map_t *map, const char *json)
{
    const char *p = json;
    map->count = 0;

    while (*p && *p != '[') p++;
    if (!*p) return -1;
    p++;

    while (*p && *p != ']') {
        while (*p && *p != '{') p++;
        if (!*p || *p == ']') break;

        pin_binding_t *b = &map->bindings[map->count];
        memset(b, 0, sizeof(pin_binding_t));

        while (*p && *p != '}') {
            if (strncmp(p, "\"name\"", 6) == 0) {
                p = strchr(p, ':') + 1;
                while (*p && *p != '\"') p++;
                p++;
                int i = 0;
                while (*p && *p != '\"' && i < MAX_PIN_NAME_LEN - 1) {
                    b->name[i++] = *p++;
                }
                b->name[i] = '\0';
                p++;
            } else if (strncmp(p, "\"pin\"", 5) == 0) {
                p = strchr(p, ':') + 1;
                b->physical_pin = (uint8_t)strtol(p, (char**)&p, 10);
            } else if (strncmp(p, "\"bit\"", 4) == 0) {
                p = strchr(p, ':') + 1;
                b->bit_pos = (uint8_t)strtol(p, (char**)&p, 10);
            } else if (strncmp(p, "\"dir\"", 4) == 0) {
                p = strchr(p, ':') + 1;
                while (*p && *p != '\"') p++;
                p++;
                b->direction = (*p == 'o') ? PIN_DIR_OUTPUT : PIN_DIR_INPUT;
                p = strchr(p, '\"') + 1;
            } else {
                p++;
            }
        }
        map->count++;
        p++;
    }
    return 0;
}

int pin_map_load(pin_map_t *map, const char *json_str)
{
    return pin_map_parse_json(map, json_str);
}

int pin_map_load_file(pin_map_t *map, const char *filepath)
{
    FILE *f = fopen(filepath, "r");
    if (!f) return -1;

    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    fseek(f, 0, SEEK_SET);

    char *buf = (char*)malloc(len + 1);
    if (!buf) { fclose(f); return -1; }

    fread(buf, 1, len, f);
    buf[len] = '\0';
    fclose(f);

    int ret = pin_map_parse_json(map, buf);
    free(buf);
    return ret;
}

int pin_map_get_bit(const pin_map_t *map, const char *name)
{
    for (int i = 0; i < map->count; i++) {
        if (strcmp(map->bindings[i].name, name) == 0)
            return map->bindings[i].bit_pos;
    }
    return -1;
}

int pin_map_get_physical(const pin_map_t *map, const char *name)
{
    for (int i = 0; i < map->count; i++) {
        if (strcmp(map->bindings[i].name, name) == 0)
            return map->bindings[i].physical_pin;
    }
    return -1;
}
