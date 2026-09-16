#!/usr/bin/env python3
"""
uFPGA-Emu PC Tool
Traduz codigo Verilog/SystemVerilog para C ANSI para execucao
em microcontroladores ESP32, RP2040 e simulacao PC.

Suporta multi-arquivos: instancias de submodulos sao resolvidas
e inlinadas automaticamente.

Uso:
    python -m pc_tool.cli entrada.v -o saida.c [--gen-main]
    python -m pc_tool.cli top.v sub.v -o saida.c --top TopModule
"""

import argparse
import sys
import os

from pc_tool.parser.parser import ParseError
from pc_tool.parser.registry import ModuleRegistry
from pc_tool.parser.inliner import flatten_module
from pc_tool.codegen.c_generator import CGenerator


def main():
    parser = argparse.ArgumentParser(
        description='uFPGA-Emu PC Tool - Verilog para C ANSI')
    parser.add_argument('input', nargs='+',
                        help='Arquivo(s) Verilog/SystemVerilog de entrada')
    parser.add_argument('-o', '--output', default=None,
                        help='Arquivo C de saida (stdout se omitido)')
    parser.add_argument('--top', default=None,
                        help='Nome do modulo top-level (auto-detect se unico)')
    parser.add_argument('--gen-main', action='store_true',
                        help='Gera tambem <output>_main.c para simulacao PC')

    args = parser.parse_args()

    registry = ModuleRegistry()
    for path in args.input:
        if not os.path.exists(path):
            print('Erro: arquivo nao encontrado:', path, file=sys.stderr)
            sys.exit(1)
        try:
            registry.parse_file(path)
        except ParseError as e:
            print('Erro de parsing em', path + ':', e, file=sys.stderr)
            sys.exit(1)

    all_mods = registry.all_modules()
    if not all_mods:
        print('Erro: nenhum modulo encontrado nos arquivos de entrada',
              file=sys.stderr)
        sys.exit(1)

    top_name = args.top
    if top_name is None:
        if len(all_mods) == 1:
            top_name = all_mods[0].name
        else:
            names = [m.name for m in all_mods]
            print('Erro: multiplos modulos encontrados:',
                  ', '.join(names), file=sys.stderr)
            print('Use --top para especificar o modulo top-level.',
                  file=sys.stderr)
            sys.exit(1)

    module = registry.get(top_name)
    if module is None:
        print('Erro: modulo top-level "' + top_name + '" nao encontrado',
              file=sys.stderr)
        sys.exit(1)

    try:
        flat = flatten_module(module, registry) if module.instances else module
    except RuntimeError as e:
        print('Erro ao achatar instancias:', e, file=sys.stderr)
        sys.exit(1)

    generator = CGenerator(flat)
    c_code = generator.generate()

    if args.output:
        with open(args.output, 'w') as f:
            f.write(c_code)
        print('Gerado:', args.output, file=sys.stderr)

        if args.gen_main:
            main_code = generator.generate_main()
            base, ext = os.path.splitext(args.output)
            main_path = base + '_main' + ext
            with open(main_path, 'w') as f:
                f.write(main_code)
            print('Gerado:', main_path, file=sys.stderr)
    else:
        print(c_code)


if __name__ == '__main__':
    main()
