"""Testes dos pinmaps JSON (firmware/pinmaps/) e headers gerados.

Cobre: header embutido == JSON fonte, headers atualizados (staleness),
template a partir do Verilog e o loader C (pin_map_load_circuit).
"""
import json
import os
import re
import subprocess
import sys
import textwrap

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_DIR)

from pc_tool.pinmap_gen import gen_header, make_template, validate  # noqa: E402

PINMAP_DIR = os.path.join(PROJECT_DIR, 'firmware', 'pinmaps')
SRC_DIR = os.path.join(PROJECT_DIR, 'firmware', 'src')
RUNTIME_SRC_DIR = os.path.join(PROJECT_DIR, 'firmware', 'lib', 'runtime', 'src')
RUNTIME_INC_DIR = os.path.join(PROJECT_DIR, 'firmware', 'lib', 'runtime', 'include')
PLATFORMS = sorted(f[:-5] for f in os.listdir(PINMAP_DIR) if f.endswith('.json'))


def _load_pinmap_json(plat):
    with open(os.path.join(PINMAP_DIR, f'{plat}.json')) as f:
        return json.load(f)


def _embedded_json_from_header(plat):
    """Extrai e desescapa PINMAP_JSON do header gerado."""
    with open(os.path.join(SRC_DIR, f'pinmap_{plat}.h')) as f:
        text = f.read()
    m = re.search(r'PINMAP_JSON\[\] =\n(.*?);\n', text, re.DOTALL)
    assert m, f'pinmap_{plat}.h sem PINMAP_JSON'
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
    s = ''.join(parts)
    assert '\\\\' not in s, 'escape inesperado no header'
    return json.loads(s.replace('\\"', '"'))


def test_platforms_present():
    assert set(PLATFORMS) == {'due', 'esp32', 'esp8266', 'rp2040', 'rpi'}


def test_json_schema_and_sources():
    for plat in PLATFORMS:
        validate(plat, _load_pinmap_json(plat))


def test_embedded_json_matches_file():
    for plat in PLATFORMS:
        assert _embedded_json_from_header(plat) == _load_pinmap_json(plat), plat


def test_headers_up_to_date():
    for plat in PLATFORMS:
        data = _load_pinmap_json(plat)
        validate(plat, data)
        expected = gen_header(plat, data)
        with open(os.path.join(SRC_DIR, f'pinmap_{plat}.h')) as f:
            assert f.read() == expected, \
                f'pinmap_{plat}.h desatualizado — rode: python3 -m pc_tool.pinmap_gen'


def test_tiny_cpu_run_init():
    # esp32/due/esp8266 setavam run=1 no main; rpi/rp2040 nao setavam (vazio)
    expected_init = {'esp32': {'run': 1}, 'due': {'run': 1},
                     'esp8266': {'run': 1}, 'rpi': {}, 'rp2040': {}}
    run_pin = {'esp32': 34, 'due': 34, 'esp8266': 34, 'rpi': 27, 'rp2040': 4}
    for plat in PLATFORMS:
        data = _load_pinmap_json(plat)
        assert data['tiny_cpu']['virtual_init'] == expected_init[plat], plat
        run = [b for b in data['tiny_cpu']['pins'] if b['name'] == 'run']
        assert run and run[0]['pin'] == run_pin[plat], plat


def test_template_matches_counter():
    name, entry = make_template(os.path.join(PROJECT_DIR, 'examples', 'counter.v'), None)
    assert name == 'counter'
    ref = _load_pinmap_json('esp32')['counter']
    got = [(p['name'], p['bit'], p['dir']) for p in entry['pins']]
    exp = [(p['name'], p['bit'], p['dir']) for p in ref['pins']]
    assert got == exp
    assert all(p['pin'] is None for p in entry['pins'])


LOADER_C = textwrap.dedent(r'''
    #include <assert.h>
    #include <stdio.h>
    #include <string.h>
    #include "pin_map.h"
    #include "pinmap_esp32.h"

    int main(void)
    {
        pin_map_t map;
        pin_init_t inits[MAX_PIN_INITS];

        memset(&map, 0, sizeof(map));
        assert(pin_map_load_circuit(&map, PINMAP_JSON, "counter", inits, 8) == 0);
        assert(map.count == 6);
        assert(pin_map_get_physical(&map, "count[3]") == 17);
        assert(pin_map_get_bit(&map, "count[3]") == 3);

        memset(&map, 0, sizeof(map));
        int n = pin_map_load_circuit(&map, PINMAP_JSON, "tiny_cpu", inits, 8);
        assert(n == 1);
        assert(strcmp(inits[0].name, "run") == 0 && inits[0].value == 1);
        assert(pin_map_get_physical(&map, "run") == 34);
        assert(pin_map_get_physical(&map, "instr[15]") == 23);
        assert(pin_map_get_bit(&map, "halted") == 16);

        memset(&map, 0, sizeof(map));
        assert(pin_map_load_circuit(&map, PINMAP_JSON, "nope", inits, 8) == -1);

        memset(&map, 0, sizeof(map));
        assert(pin_map_load_circuit(&map, PINMAP_JSON, "blinky", inits, 8) == 0);
        assert(pin_map_get_physical(&map, "led") == 2);

        puts("loader OK");
        return 0;
    }
''')


def test_loader_c():
    harness = '/tmp/opencode/test_pinmap_loader.c'
    os.makedirs(os.path.dirname(harness), exist_ok=True)
    with open(harness, 'w') as f:
        f.write(LOADER_C)
    r = subprocess.run(
        ['gcc', '-I' + RUNTIME_INC_DIR, '-I' + SRC_DIR,
         harness, os.path.join(RUNTIME_SRC_DIR, 'pin_map.c'),
         '-o', '/tmp/opencode/test_pinmap_loader'],
        capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode()
    r = subprocess.run(['/tmp/opencode/test_pinmap_loader'],
                       capture_output=True, timeout=10)
    assert r.returncode == 0, r.stdout.decode()
