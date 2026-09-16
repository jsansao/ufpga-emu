#!/usr/bin/env python3
"""
Renderiza um arquivo VCD em forma de onda ASCII estilizada no terminal.
Usa caracteres Unicode para parecer com a saída de simuladores profissionais.
Uso: python3 scripts/vcd_to_ascii.py <vcd_file> [max_time] [signal_filter]
"""

import sys
import re
from collections import defaultdict


def parse_vcd(path):
    """Retorna dict de sinal -> lista de (timestamp, valor)."""
    with open(path) as f:
        content = f.read()

    sig_id_to_name = {}
    sig_id_to_width = {}
    for m in re.finditer(r'\$var\s+(\S+)\s+(\d+)\s+(\S+)\s+(\S+)\s+\$end', content):
        width = int(m.group(2))
        sid = m.group(3)
        name = m.group(4)
        sig_id_to_name[sid] = name
        sig_id_to_width[sid] = width

    data_start = content.index('$enddefinitions $end') + len('$enddefinitions $end')
    data_section = content[data_start:]

    events = []
    current_time = 0
    for line in data_section.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            try:
                current_time = int(line[1:])
            except ValueError:
                pass
        else:
            m = re.match(r'b([01xz]+)\s+(\S+)', line)
            if m:
                events.append((current_time, m.group(2), m.group(1)))
                continue
            m = re.match(r'([01xz])\s*(\S+)', line)
            if m:
                events.append((current_time, m.group(2), m.group(1)))

    return sig_id_to_name, sig_id_to_width, events


def render_ascii(vcd_path, max_time=None, signals_filter=None, width=140):
    sig_id_to_name, sig_id_to_width, events = parse_vcd(vcd_path)

    if not sig_id_to_name:
        print(f"Erro: nenhum sinal encontrado em {vcd_path}")
        return

    if signals_filter:
        keep = {sid for sid, name in sig_id_to_name.items()
                if any(f.lower() in name.lower() for f in signals_filter)}
        sig_id_to_name = {sid: name for sid, name in sig_id_to_name.items() if sid in keep}
        sig_id_to_width = {sid: w for sid, w in sig_id_to_width.items() if sid in keep}

    if not events:
        print("Nenhum evento encontrado no VCD")
        return

    all_times = [t for t, _, _ in events]
    t_min = min(all_times)
    t_max = max(all_times)
    if max_time and t_max > max_time:
        t_max = max_time

    sig_history = defaultdict(list)
    for t, sid, val in sorted(events):
        sig_history[sid].append((t, val))

    def get_value(sid, t):
        if sid not in sig_history:
            return '?'
        val = '?'
        for ts, v in sig_history[sid]:
            if ts <= t:
                val = v
            else:
                break
        return val

    print(f"\n\033[1;36m{'═' * (width + 28)}\033[0m")
    print(f"\033[1;36m  VCD Waveform Visualizer\033[0m")
    print(f"\033[1;36m{'═' * (width + 28)}\033[0m")
    print(f"  \033[1mArquivo:\033[0m    {vcd_path}")
    print(f"  \033[1mSinais:\033[0m     {len(sig_id_to_name)}")
    print(f"  \033[1mRange:\033[0m      t={t_min} a t={t_max} ({t_max - t_min} µs simulados)")
    print(f"  \033[1mTransições:\033[0m {len(events)}")
    print(f"\033[1;36m{'═' * (width + 28)}\033[0m\n")

    header_str = f"{'Signal':<20} {'W':>3} │"
    for i in range(width):
        if i % 20 == 0:
            ts = int(t_min + (t_max - t_min) * i / (width - 1))
            ts_str = str(ts)
            for k, ch in enumerate(ts_str):
                if i + k < width:
                    header_str += ch
                else:
                    break
            i += len(ts_str) - 1
        else:
            header_str += ' '
    header_str += '│'
    print(f"\033[1;33m{header_str}\033[0m")

    sep_str = f"{'─' * 20} {'─' * 3} ┼{'─' * width}┤"
    print(f"\033[1;33m{sep_str}\033[0m")

    for sid in sorted(sig_id_to_name.keys(), key=lambda s: (sig_id_to_width[s] != 1, sig_id_to_name[s])):
        name = sig_id_to_name[sid]
        w = sig_id_to_width[sid]

        line = f"{name:<20} {w:>3} │"
        prev_val = None
        first_in_segment = True
        for i in range(width):
            t = t_min + (t_max - t_min) * i / (width - 1)
            val = get_value(sid, t)

            if w == 1:
                if val in '01':
                    if i == 0 or prev_val != val:
                        char = '█' if val == '1' else ' '
                        line += char
                        first_in_segment = False
                    else:
                        if val == '1':
                            line += '▀' if i % 2 == 0 else '▄'
                        else:
                            line += ' '
                else:
                    line += 'x' if val == 'x' else '?'
                prev_val = val
            else:
                if i == 0 or prev_val != val:
                    short_val = val[:min(len(val), 4)]
                    if len(short_val) > width - i - 2:
                        short_val = short_val[:width - i - 2]
                    line += short_val
                    i += len(short_val) - 1
                else:
                    line += ' '
                prev_val = val

        line += '│'
        print(line)

    print(f"\n\033[1;36m{'═' * (width + 28)}\033[0m")
    print(f"  \033[1;32m█\033[0m = nível alto  │  \033[1;32m▀▄\033[0m = transição  │  \033[1;30m·\033[0m = nível baixo")
    print(f"  Colunas: t={t_min} → t={t_max} µs | Largura: {width} chars")
    print(f"\033[1;36m{'═' * (width + 28)}\033[0m\n")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python3 vcd_to_ascii.py <vcd_file> [max_time_us] [signal_filter]")
        sys.exit(1)

    vcd = sys.argv[1]
    max_t = int(sys.argv[2]) if len(sys.argv) > 2 else None
    flt = sys.argv[3] if len(sys.argv) > 3 else None

    render_ascii(vcd, max_t, [flt] if flt else None)
