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

/* Localiza a chave '"<circuit>":' e retorna ponteiro para o '{' do objeto. */
static const char *find_circuit(const char *json, const char *circuit)
{
    char key[MAX_PIN_NAME_LEN + 4];
    snprintf(key, sizeof(key), "\"%s\"", circuit);

    const char *p = json;
    while ((p = strstr(p, key)) != NULL) {
        const char *q = p + strlen(key);
        while (*q == ' ' || *q == '\t' || *q == '\n' || *q == '\r') q++;
        if (*q == ':') {
            q++;
            while (*q == ' ' || *q == '\t' || *q == '\n' || *q == '\r') q++;
            if (*q == '{') return q;
        }
        p += strlen(key);
    }
    return NULL;
}

/* Retorna ponteiro para o '}' que fecha o objeto iniciado em p ('{'). */
static const char *object_end(const char *p)
{
    int depth = 0;
    while (*p) {
        if (*p == '{') depth++;
        else if (*p == '}') { if (--depth == 0) return p; }
        else if (*p == '\"') {
            p++;
            while (*p && *p != '\"') {
                if (*p == '\\' && p[1]) p++;
                p++;
            }
        }
        p++;
    }
    return NULL;
}

int pin_map_load_circuit(pin_map_t *map, const char *json_str,
                         const char *circuit,
                         pin_init_t *inits, uint8_t max_inits)
{
    const char *obj = find_circuit(json_str, circuit);
    if (!obj) return -1;

    /* "pins" e o primeiro array do objeto — o parser existente pula ate '['. */
    if (pin_map_parse_json(map, obj) != 0) return -1;

    int total = 0;
    const char *end = object_end(obj);
    if (!end) return -1;

    /* "virtual_init": busca a chave dentro do objeto do circuito. */
    const char *p = obj;
    const char *vi = NULL;
    while (p < end) {
        if (strncmp(p, "\"virtual_init\"", 14) == 0) { vi = p; break; }
        p++;
    }
    if (!vi) return 0;

    p = strchr(vi, ':') + 1;
    while (*p && *p != '{') p++;
    if (*p != '{') return 0;

    p++;
    while (*p && *p != '}') {
        if (*p == '\"') {
            p++;
            pin_init_t tmp;
            int i = 0;
            while (*p && *p != '\"' && i < MAX_PIN_NAME_LEN - 1)
                tmp.name[i++] = *p++;
            tmp.name[i] = '\0';
            const char *colon = strchr(p, ':');
            if (!colon || colon > end) break;
            tmp.value = (uint8_t)strtol(colon + 1, (char**)&p, 10);
            if (inits && total < max_inits)
                inits[total] = tmp;
            total++;
        } else {
            p++;
        }
    }
    return total;
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
