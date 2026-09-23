#!/usr/bin/env python3
"""Gera os headers de pinmap embutidos a partir de firmware/pinmaps/<plat>.json.

Uso:
    python3 -m pc_tool.pinmap_gen
        Regenera firmware/src/pinmap_<plat>.h para todo .json em firmware/pinmaps/.

    python3 -m pc_tool.pinmap_gen --template -v examples/novo.v -p esp32 [-p due ...]
        Imprime a entrada JSON do circuito (pins com "pin": null) para colar
        em firmware/pinmaps/<plat>.json. Atribua os pinos fisicos e rode
        o modo default para regenerar os headers.

Fluxo "novo circuito -> novo alvo":
    1. python3 -m pc_tool.cli novo.v -o firmware/src/circuit_novo.c
    2. python3 -m pc_tool.pinmap_gen --template -v novo.v -p esp32
       -> colar entrada em firmware/pinmaps/esp32.json e atribuir os pinos
    3. python3 -m pc_tool.pinmap_gen
    4. Adicionar env no platformio.ini
    Nenhum main_*.c precisa ser editado.
"""

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PINMAP_DIR = os.path.join(ROOT, 'firmware', 'pinmaps')
SRC_DIR = os.path.join(ROOT, 'firmware', 'src')

PIN_KEYS = {'name', 'pin', 'bit', 'dir'}


def validate(plat, data):
    assert isinstance(data, dict) and data, f'{plat}: vazio'
    assert 'blinky' in data, f'{plat}: blinky ausente (fallback do #else)'
    for name, entry in data.items():
        ctx = f'{plat}/{name}'
        assert re.match(r'^\w+$', name), f'{ctx}: nome invalido'
        assert isinstance(entry, dict), f'{ctx}: entrada nao e objeto'
        pins = entry.get('pins')
        assert isinstance(pins, list) and pins, f'{ctx}: pins vazio'
        for p in pins:
            assert isinstance(p, dict), f'{ctx}: binding nao e objeto'
            missing = PIN_KEYS - set(p)
            assert not missing, f'{ctx}: faltam chaves {missing} em {p}'
            assert isinstance(p['pin'], int) and 0 <= p['pin'] <= 255, \
                f'{ctx}: "pin" invalido ({p["pin"]}) — preencha o template'
            assert isinstance(p['bit'], int) and 0 <= p['bit'] < 64, \
                f'{ctx}: "bit" invalido ({p["bit"]})'
            assert p['dir'] in ('input', 'output'), f'{ctx}: "dir" invalida'
            assert p['name'] and len(p['name']) < 32, f'{ctx}: nome longo'
        vi = entry.get('virtual_init', {})
        assert isinstance(vi, dict), f'{ctx}: virtual_init nao e objeto'
        for k, v in vi.items():
            assert re.match(r'^\w+(\[\d+\])?$', k), f'{ctx}: nome init invalido {k!r}'
            assert isinstance(v, int) and 0 <= v <= 255, f'{ctx}: valor init invalido'
        src = os.path.join(SRC_DIR, f'circuit_{name}.c')
        assert os.path.exists(src), f'{ctx}: {src} ausente'


def gen_header(plat, data):
    guard = f'PINMAP_{plat.upper()}_H'
    lines = [
        f'/* Gerado por pc_tool/pinmap_gen.py - NAO EDITAR.',
        f' * Fonte: firmware/pinmaps/{plat}.json */',
        f'#ifndef {guard}',
        f'#define {guard}',
        '',
    ]
    first = True
    for name in data:
        kw = '#if' if first else '#elif'
        first = False
        lines += [
            f'{kw} defined(EMU_CIRCUIT_{name.upper()})',
            f'#include "circuit_{name}.c"',
            f'#define CIRCUIT_NAME "{name}"',
        ]
    lines += [
        '#else',
        '#include "circuit_blinky.c"',
        '#define CIRCUIT_NAME "blinky"',
        '#endif',
        '',
    ]

    segs = [json.dumps(n) + ':' + json.dumps(e, separators=(',', ':'))
            for n, e in data.items()]
    lines.append('static const char PINMAP_JSON[] =')
    lines.append('    "{"')
    for i, seg in enumerate(segs):
        tail = ',' if i < len(segs) - 1 else ''
        esc = (seg + tail).replace('\\', '\\\\').replace('"', '\\"')
        lines.append(f'    "{esc}"')
    lines.append('    "}";')
    lines.append('')
    lines.append(f'#endif /* {guard} */')
    return '\n'.join(lines) + '\n'


def regen():
    names = sorted(f for f in os.listdir(PINMAP_DIR) if f.endswith('.json'))
    assert names, f'nenhum .json em {PINMAP_DIR}'
    for fn in names:
        plat = fn[:-5]
        with open(os.path.join(PINMAP_DIR, fn)) as f:
            data = json.load(f)
        validate(plat, data)
        out = os.path.join(SRC_DIR, f'pinmap_{plat}.h')
        with open(out, 'w') as f:
            f.write(gen_header(plat, data))
        print(f'{out} ({len(data)} circuitos)')


def make_template(verilog_path, top_name):
    from pc_tool.parser.parser import ParseError
    from pc_tool.parser.registry import ModuleRegistry

    registry = ModuleRegistry()
    registry.parse_file(verilog_path)
    mods = registry.all_modules()
    if top_name is None:
        if len(mods) != 1:
            names = ', '.join(m.name for m in mods)
            raise SystemExit(f'Erro: multiplos modulos ({names}); use --top')
        top_name = mods[0].name
    module = registry.get(top_name)
    if module is None:
        raise SystemExit(f'Erro: modulo "{top_name}" nao encontrado')

    entry = {'pins': [], 'virtual_init': {}}
    bit = {'input': 0, 'output': 0}
    for p in module.ports:
        if p.direction not in bit:
            raise SystemExit(f'Erro: porta "{p.name}" com direcao "{p.direction}" nao suportada')
        width = p.width if (p.msb is not None and p.lsb is not None and p.msb >= p.lsb) \
            else (abs(p.msb - p.lsb) + 1 if p.msb is not None and p.lsb is not None else 1)
        for i in range(width):
            nm = p.name if width == 1 else f'{p.name}[{i}]'
            entry['pins'].append({'name': nm, 'pin': None,
                                  'bit': bit[p.direction], 'dir': p.direction})
            bit[p.direction] += 1
    return module.name, entry


def template(args):
    name, entry = make_template(args.verilog, args.top)
    for plat in args.platform:
        path = os.path.join(PINMAP_DIR, f'{plat}.json')
        if os.path.exists(path):
            with open(path) as f:
                if name in json.load(f):
                    print(f'Aviso: "{name}" ja existe em {plat}.json', file=sys.stderr)
        print(f'# Cole em firmware/pinmaps/{plat}.json e preencha os "pin": null:')
        print(f'  "{name}": {json.dumps(entry, indent=2)},')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--template', action='store_true',
                    help='Imprime entrada JSON do circuito a partir do Verilog')
    ap.add_argument('-v', '--verilog', help='Arquivo Verilog (modo --template)')
    ap.add_argument('--top', default=None, help='Modulo top-level (auto se unico)')
    ap.add_argument('-p', '--platform', action='append',
                    help='Plataforma alvo (modo --template; repetivel)')
    args = ap.parse_args()

    if args.template:
        if not args.verilog or not args.platform:
            ap.error('--template exige -v <file.v> e -p <plat>')
        template(args)
    else:
        regen()


if __name__ == '__main__':
    main()
