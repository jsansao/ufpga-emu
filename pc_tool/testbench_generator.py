#!/usr/bin/env python3
"""Gerador automatico de testbenches C com estímulo CSV.

Uso:
    python3 -m pc_tool.testbench_generator <circuit> --verilog <file.v> \
        --csv <stim.csv> -o firmware/src/stim_test_<circuit>.c
"""

import argparse
import os
import re
import sys


def discover_signals(csv_path: str) -> dict[str, int]:
    """Parse CSV and return dict mapping base_signal -> max_bit.

    Simple signals (no [N] suffix) get max_bit=0.
    Bit-sliced signals get max_bit = highest index found.
    Special signals 'inputs' is ignored (handled separately as direct inputs mode).
    """
    signals: dict[str, int] = {}
    with open(csv_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('time_us'):
                continue
            parts = line.split(',')
            if len(parts) < 2:
                continue
            sig = parts[1].strip()
            if sig == 'inputs':
                continue  # handled separately as direct inputs mode
            m = re.match(r'^(\w+)\[(\d+)\]$', sig)
            if m:
                base = m.group(1)
                bit = int(m.group(2))
                if base not in signals or bit > signals[base]:
                    signals[base] = bit
            else:
                m2 = re.match(r'^(\w+)$', sig)
                if m2:
                    base = m2.group(1)
                    if base not in signals:
                        signals[base] = 0
    return signals


def load_port_widths(verilog_path: str) -> dict[str, int]:
    """Simple regex-based port width extraction from Verilog."""
    widths: dict[str, int] = {}
    with open(verilog_path) as f:
        text = f.read()
    for _dir, msb_s, lsb_s, names in _iter_port_decls(text):
        if msb_s is not None and lsb_s is not None:
            msb, lsb = int(msb_s), int(lsb_s)
            width = abs(msb - lsb) + 1
        else:
            width = 1
        for name in names:
            widths[name] = width
    return widths


def load_port_order(verilog_path: str) -> list[str]:
    """Return port names in declaration order from Verilog file."""
    order: list[str] = []
    with open(verilog_path) as f:
        text = f.read()
    for _dir, _msb_s, _lsb_s, names in _iter_port_decls(text):
        for name in names:
            if name and name not in order:
                order.append(name)
    return order


def _iter_port_decls(text: str):
    """Yield (direction, msb, lsb, names) for ANSI-style port declarations."""
    pat = re.compile(r'\b(input|output|inout)\b(.*?)(?=\binput\b|\boutput\b|\binout\b|;)', re.DOTALL)
    name_re = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s*\)?$')
    for m in pat.finditer(text):
        direction = m.group(1)
        chunk = m.group(2)
        width_m = re.search(r'\[(\d+)\s*:\s*(\d+)\]', chunk)
        msb_s = width_m.group(1) if width_m else None
        lsb_s = width_m.group(2) if width_m else None
        names_part = chunk[width_m.end():] if width_m else chunk
        names = []
        for decl in names_part.split(','):
            mname = name_re.search(decl.strip())
            if mname:
                names.append(mname.group(1))
        if names:
            yield direction, msb_s, lsb_s, names


def load_csv_expected(csv_path: str) -> list[tuple[int, int]]:
    """Parse CSV and return list of (time_us, expected_output) for auto-assertions.

    Looks for rows with a 4th column (expected output value).
    Returns list of (t, expected) tuples.
    """
    expected: list[tuple[int, int]] = []
    with open(csv_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('time_us'):
                continue
            parts = line.split(',')
            if len(parts) >= 4 and parts[3].strip():
                try:
                    t = int(parts[0].strip())
                    exp = int(parts[3].strip(), 0)
                    expected.append((t, exp))
                except (ValueError, IndexError):
                    pass
    return expected


def _discover_has_inputs_direct(csv_path: str) -> bool:
    """Check if CSV uses the 'inputs' direct signal (vs individual signals)."""
    with open(csv_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('time_us'):
                continue
            parts = line.split(',')
            if len(parts) >= 2 and parts[1].strip() == 'inputs':
                return True
    return False


def generate_stim_test(
    name: str,
    signals: dict[str, int],
    port_widths: dict[str, int],
    max_time_us: int = 100,
    half_period_us: int = 5,
    port_order: list[str] = None,
    has_inputs_direct: bool = False,
    expected_list: list[tuple[int, int]] = None,
) -> str:
    """Generate stim_test_<name>.c from signal info.

    Args:
        name: Circuit name (e.g., "alu")
        signals: Map of base_signal -> max_bit (0 for simple 1-bit)
        port_widths: Map of signal_name -> width from Verilog ports
        max_time_us: Total simulation time in microseconds
        half_period_us: Clock half-period (full period = 2 * half_period)
        port_order: Ordered list of port names from Verilog
        has_inputs_direct: If True, CSV uses 'inputs' signal for full input value
        expected_list: List of (time_us, expected_output) for auto-assertions

    Returns:
        Generated C source code
    """
    has_clk = 'clk' in port_widths

    if has_inputs_direct:
        # === Direct inputs mode: CSV has 'inputs' signal for full input value ===
        var_decls = ['    uint32_t inputs_val = 0;']
        dispatch_body = '''            if (strcmp(e->signal, "inputs") == 0) {
                inputs_val = e->value;
            }'''
        packing_expr = 'inputs_val'
    else:
        # === Individual signal mode: CSV has per-signal events ===
        all_simple: set[str] = set()
        bus_list: list[tuple[str, int]] = []
        for sig, max_bit in signals.items():
            if max_bit == 0:
                all_simple.add(sig)
            else:
                w = port_widths.get(sig, max_bit + 1)
                bus_list.append((sig, w))
        bus_names = {s for s, _ in bus_list}

        csv_signal_names = set(signals.keys())
        ordered = []
        if has_clk:
            ordered.append('clk')
        for pref in ('rst',):
            if pref in csv_signal_names:
                ordered.append(pref)
        if port_order:
            remaining_simple = set(all_simple) - {'clk', 'rst'}
            remaining_bus = set(s for s, _ in bus_list)
            for sig in port_order:
                if sig in remaining_simple:
                    ordered.append(sig)
                    remaining_simple.discard(sig)
                elif sig in remaining_bus:
                    ordered.append(sig)
                    remaining_bus.discard(sig)
            ordered.extend(sorted(remaining_simple))
            ordered.extend(sorted(remaining_bus))
        else:
            ordered.extend(sorted(s for s in all_simple if s not in ('clk', 'rst')))
            ordered.extend(s for s, _ in bus_list)

        bit_pos: dict[str, int] = {}
        cur_bit = 0
        for sig in ordered:
            if sig == 'clk':
                w = 1
            else:
                w = 1 if sig in all_simple else dict(bus_list).get(sig, 1)
            bit_pos[sig] = cur_bit
            cur_bit += w

        csv_sigs = [sig for sig in ordered if sig != 'clk']
        parts = []
        for idx, sig in enumerate(csv_sigs):
            is_last = (idx == len(csv_sigs) - 1)
            if sig in all_simple:
                cond = f'strcmp(e->signal, "{sig}") == 0'
                body = f'                {sig}_val = e->value;\n'
                close = '            }' if is_last else '            } else'
            else:
                sig_w = dict(bus_list).get(sig, 1)
                cond = f'strncmp(e->signal, "{sig}[", {len(sig)+1}) == 0'
                body = (
                    f'                int bit;\n'
                    f'                if (sscanf(e->signal + {len(sig)+1}, "%d]", &bit) == 1 && bit >= 0 && bit < {sig_w}) {{\n'
                    f'                    if (e->value) {sig}_val |= (1u << bit);\n'
                    f'                    else {sig}_val &= ~(1u << bit);\n'
                    f'                }}\n')
                close = '            }' if is_last else '            } else'

            if idx == 0:
                parts.append(f'            if ({cond}) {{\n{body}{close}')
            else:
                parts.append(f' if ({cond}) {{\n{body}{close}')
        dispatch_body = ''.join(parts)

        def pack(sig, val):
            pos = bit_pos[sig]
            return f'({val})' if pos == 0 else f'({val} << {pos})'

        packing_parts = []
        for sig in ordered:
            if sig == 'clk':
                packing_parts.append(pack(sig, 'clk'))
            elif sig in all_simple:
                packing_parts.append(pack(sig, f'{sig}_val'))
            else:
                sig_w = dict(bus_list).get(sig, 1)
                mask = (1 << sig_w) - 1
                packing_parts.append(pack(sig, f'({sig}_val & 0x{mask:X})'))
        packing_expr = ' | '.join(packing_parts)

        var_decls = []
        for sig in ordered:
            if sig != 'clk':
                var_decls.append(f'    uint32_t {sig}_val = 0;')

    # === Auto-assertions from expected list ===
    if expected_list:
        assertion_lines = []
        for t, exp in expected_list:
            label = f't={t}'
            assertion_lines.append(
                f'        if (t == {t}) check(t, "{label}", outputs, {exp});')
        assertion_body = '\n'.join(assertion_lines)
    else:
        assertion_body = (
            '        /* TODO: Add time-point assertions here\n'
            '         * Example:\n'
            '         * if (t == 0)   check(t, "init", outputs, <expected>);\n'
            '         * if (t == 10)  check(t, "step1", outputs, <expected>);\n'
            '         */')

    # === Check function ===
    if name == 'tiny_cpu':
        check_fn = '''static void check(uint64_t t, const char *label, uint32_t actual, uint32_t expected)
{
    if (actual != expected) {
        printf("FAIL %s t=%lu: expected=%u (pc=%u out=%u halt=%u) got=%u (pc=%u out=%u halt=%u)\\n",
               label, (unsigned long)t,
               (unsigned)expected, (unsigned)(expected & 0xFF),
               (unsigned)((expected >> 8) & 0xFF), (unsigned)((expected >> 16) & 1),
               (unsigned)actual, (unsigned)(actual & 0xFF),
               (unsigned)((actual >> 8) & 0xFF), (unsigned)((actual >> 16) & 1));
        failures++;
    }
}'''
    else:
        check_fn = '''static void check(uint64_t t, const char *label, uint32_t actual, uint32_t expected)
{
    if (actual != expected) {
        printf("FAIL %s t=%lu: expected=%u got=%u\\n",
               label, (unsigned long)t, (unsigned)expected, (unsigned)actual);
        failures++;
    }
}'''

    clock_gen = (
        '        uint32_t clk = (uint32_t)((t / HALF_PERIOD_US) & 1u);'
        if has_clk else ''
    )

    # Build the complete C source
    code = f'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "model.h"

void circuit_init(model_state_t *state);
void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs);

#define MAX_EVENTS 256
#define SIGNAL_MAX 64
#define HALF_PERIOD_US {half_period_us}
#define MAX_TIME_US {max_time_us}

typedef struct {{
    uint64_t time_us;
    char signal[SIGNAL_MAX];
    uint32_t value;
}} event_t;

static event_t events[MAX_EVENTS];
static int num_events = 0;
static int failures = 0;

static int parse_csv(const char *path)
{{
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    char line[256];
    int lineno = 0;
    while (fgets(line, sizeof(line), f)) {{
        lineno++;
        if (lineno == 1) continue;
        if (line[0] == '#' || line[0] == '\\n') continue;
        unsigned long t;
        char sig[64];
        unsigned int val;
        if (sscanf(line, "%lu,%63[^,],%u", &t, sig, &val) < 3) continue;
        if (num_events >= MAX_EVENTS) break;
        events[num_events].time_us = t;
        strncpy(events[num_events].signal, sig, SIGNAL_MAX - 1);
        events[num_events].signal[SIGNAL_MAX - 1] = '\\0';
        events[num_events].value = val;
        num_events++;
    }}
    fclose(f);
    return 0;
}}

{check_fn}

int main(void)
{{
    const char *csv = getenv("STIMULUS_CSV");
    if (!csv) {{
        fprintf(stderr, "FAIL: STIMULUS_CSV env var not set\\n");
        return 1;
    }}
    if (parse_csv(csv) != 0) {{
        fprintf(stderr, "FAIL: could not open %s\\n", csv);
        return 1;
    }}

    model_state_t state;
    circuit_init(&state);

{chr(10).join(var_decls)}
    int event_idx = 0;
    int steps = 0;

    for (uint64_t t = 0; t <= MAX_TIME_US; t += HALF_PERIOD_US) {{
        while (event_idx < num_events && events[event_idx].time_us <= t) {{
            event_t *e = &events[event_idx];
{dispatch_body}
            event_idx++;
        }}

{clock_gen}
        uint32_t inputs = {packing_expr};

        uint32_t outputs;
        circuit_eval(&state, inputs, &outputs);
        steps++;

{assertion_body}
    }}

    printf("%s: %d steps, %d failures\\n",
           failures ? "FAIL" : "PASS", steps, failures);
    return failures ? 1 : 0;
}}
'''

    return code


def main():
    parser = argparse.ArgumentParser(
        description='Gera testbench C com estímulo CSV para uFPGA-Emu')
    parser.add_argument('circuit', help='Nome do circuito (ex: counter, alu)')
    parser.add_argument('--verilog', '-v', default=None,
                        help='Arquivo Verilog .v para extrair largura das portas')
    parser.add_argument('--csv', '-c', required=True,
                        help='Arquivo CSV de estímulo')
    parser.add_argument('--output', '-o', default=None,
                        help='Arquivo C de saída (stdout se omitido)')
    parser.add_argument('--max-time-us', type=int, default=100,
                        help='Tempo máximo de simulação em microssegundos (default: 100)')
    parser.add_argument('--half-period-us', type=int, default=5,
                        help='Half-period do clock em microssegundos (default: 5)')

    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f'Erro: CSV não encontrado: {args.csv}', file=sys.stderr)
        sys.exit(1)

    signals = discover_signals(args.csv)
    has_inputs_direct = _discover_has_inputs_direct(args.csv)
    expected_list = load_csv_expected(args.csv)

    port_widths: dict[str, int] = {}
    port_order: list[str] = []
    if args.verilog:
        if not os.path.exists(args.verilog):
            print(f'Erro: Verilog não encontrado: {args.verilog}', file=sys.stderr)
            sys.exit(1)
        port_widths = load_port_widths(args.verilog)
        port_order = load_port_order(args.verilog)

    code = generate_stim_test(
        name=args.circuit,
        signals=signals,
        port_widths=port_widths,
        max_time_us=args.max_time_us,
        half_period_us=args.half_period_us,
        port_order=port_order,
        has_inputs_direct=has_inputs_direct,
        expected_list=expected_list,
    )

    if args.output:
        with open(args.output, 'w') as f:
            f.write(code)
        print(f'Gerado: {args.output}', file=sys.stderr)
        # Also print platformio.ini env block
        short = args.circuit.replace('_', '')
        print(file=sys.stderr)
        print(f'Adicione ao platformio.ini:', file=sys.stderr)
        print(f'[env:pc-stim-{short}]', file=sys.stderr)
        print(f'platform = native', file=sys.stderr)
        print(f'build_flags =', file=sys.stderr)
        print(f'    -I${{PROJECT_DIR}}/firmware/lib/hal/include', file=sys.stderr)
        print(f'    -I${{PROJECT_DIR}}/firmware/lib/runtime/include', file=sys.stderr)
        print(f'build_src_filter = +<*> -<*esp32*> -<*rp2040*> -<main_rpi*/> -<circuit_*/>', file=sys.stderr)
        print(f'    -<main_pc*/> -<testbench_*/> -<stim_test_*/> -<examples/>', file=sys.stderr)
        print(f'    +<circuit_{args.circuit}*/> +<stim_test_{args.circuit}*/>', file=sys.stderr)
    else:
        print(code)


if __name__ == '__main__':
    main()
