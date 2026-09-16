#!/usr/bin/env python3
"""Testes de integracao: compila e executa testbenches C com stimuli CSV."""

import re
import shutil
import subprocess
import os
import sys
import signal
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

PIO = (os.environ.get("PIO")
       or shutil.which("pio")
       or os.path.expanduser('~/.venvs/pio/bin/pio'))
PIO_BUILD = os.path.join(os.path.dirname(__file__), '..', '.pio', 'build')
EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', 'examples')
PROJECT_DIR = os.path.join(os.path.dirname(__file__), '..')


def _run_tb(env, csv=None):
    """Compila e executa um testbench. Retorna (stdout, returncode)."""
    r = subprocess.run([PIO, 'run', '-e', env], cwd=PROJECT_DIR,
                       capture_output=True, timeout=60)
    if r.returncode != 0:
        print(f'BUILD FAILED for {env}:')
        print(r.stdout.decode())
        print(r.stderr.decode())
        return '', 1
    prog = os.path.join(PIO_BUILD, env, 'program')
    env_vars = os.environ.copy()
    if csv:
        env_vars['STIMULUS_CSV'] = csv
    r = subprocess.run([prog], env=env_vars, capture_output=True, timeout=30)
    return r.stdout.decode(), r.returncode


def test_tb_fsm101():
    out, rc = _run_tb('pc-test-fsm101')
    print(out, end='')
    assert rc == 0, f'pc-test-fsm101 falhou (rc={rc})'


def test_tb_counter():
    out, rc = _run_tb('pc-test-counter')
    print(out, end='')
    assert rc == 0, f'pc-test-counter falhou (rc={rc})'


def test_tb_blinky():
    out, rc = _run_tb('pc-test-blinky')
    print(out, end='')
    assert rc == 0, f'pc-test-blinky falhou (rc={rc})'


def test_tb_shiftreg():
    out, rc = _run_tb('pc-test-shiftreg')
    print(out, end='')
    assert rc == 0, f'pc-test-shiftreg falhou (rc={rc})'


STIM_CSV_MAP = {
    'pc-stim-counter': 'stim_counter.csv',
    'pc-stim-paramcounter': 'stim_param_counter.csv',
    'pc-stim-alu': 'stim_alu.csv',
    'pc-stim-pwm': 'stim_pwm.csv',
    'pc-stim-fsm101': 'fsm_detect.csv',
    'pc-stim-shiftreg': 'shift_full.csv',
    'pc-stim-tinycpu': 'stim_tiny_cpu.csv',
    'pc-stim-reduction': 'stim_reduction.csv',
    'pc-stim-priorityencoder': 'stim_priority_encoder.csv',
    'pc-stim-negedgecounter': 'stim_negedge_counter.csv',
    'pc-stim-signextend': 'stim_sign_extend.csv',
    'pc-stim-addern': 'stim_adder_n.csv',
    'pc-stim-concatmulti': 'stim_concat_multi.csv',
    'pc-stim-partselectlhs': 'stim_part_select_lhs.csv',
    'pc-stim-caseequality': 'stim_case_equality.csv',
    'pc-stim-notkeyword': 'stim_not_keyword.csv',
    'pc-stim-localparamexample': 'stim_localparam_example.csv',
    'pc-stim-moduleinst': 'stim_module_inst.csv',
    'pc-stim-repeatexample': 'stim_repeat_example.csv',
}


def _discover_stim_envs():
    """Discover pc-stim-* envs from platformio.ini and match to CSVs."""
    pio_ini = os.path.join(PROJECT_DIR, 'platformio.ini')
    envs = []
    with open(pio_ini) as f:
        for line in f:
            m = re.match(r'^\[env:pc-stim-(\w+)]', line)
            if m:
                envs.append(f'pc-stim-{m.group(1)}')
    result = []
    for env in sorted(envs):
        if env in STIM_CSV_MAP:
            csv = os.path.join(EXAMPLES_DIR, STIM_CSV_MAP[env])
            result.append((env, csv))
    return result


@pytest.mark.parametrize('env,csv', _discover_stim_envs())
def test_stim(env, csv):
    out, rc = _run_tb(env, csv)
    print(out, end='')
    assert rc == 0, f'{env} falhou (rc={rc})'


EXAMPLES_SRC = os.path.join(PROJECT_DIR, 'firmware', 'src', 'examples')
HAL_SRC_DIR = os.path.join(PROJECT_DIR, 'firmware', 'lib', 'hal', 'src')
RUNTIME_SRC_DIR = os.path.join(PROJECT_DIR, 'firmware', 'lib', 'runtime', 'src')


def _compile_example(name):
    """Compila um exemplo gerado pelo pc_tool como programa PC."""
    hal_src = [os.path.join(HAL_SRC_DIR, f)
               for f in ('hal_gpio.c', 'hal_timer.c', 'hal_stimulus.c',
                         'hal_mutex.c', 'hal_serial.c')]
    runtime_src = [os.path.join(RUNTIME_SRC_DIR, f)
                   for f in ('emulator.c', 'pin_map.c', 'telemetry.c', 'vcd_writer.c')]
    flags = ['-I' + os.path.join(PROJECT_DIR, 'firmware', 'lib', 'hal', 'include'),
             '-I' + os.path.join(PROJECT_DIR, 'firmware', 'lib', 'runtime', 'include'),
             '-I' + os.path.join(PROJECT_DIR, 'firmware', 'src'),
             '-lpthread']
    src = [os.path.join(EXAMPLES_SRC, f'{name}.c'),
           os.path.join(EXAMPLES_SRC, f'{name}_main.c')]
    r = subprocess.run(['gcc'] + flags + src + hal_src + runtime_src +
                       ['-o', f'/tmp/example_{name}'],
                       capture_output=True, timeout=60)
    if r.returncode != 0:
        print(r.stderr.decode())
    return r.returncode


def test_compile_all_examples():
    """Verifica que todos os exemplos gerados compilam para PC."""
    examples = ['alu', 'blinky', 'counter', 'decoder', 'fsm_101', 'mixed',
                'mux', 'mux2', 'param_counter', 'pwm', 'shift_register',
                'tiny_cpu', 'uart_tx', 'reduction', 'priority_encoder',
                'negedge_counter', 'sign_extend', 'adder_n',
                'concat_multi', 'part_select_lhs',
                'case_equality', 'not_keyword', 'localparam_example',
                'module_inst', 'repeat_example']
    failures = []
    for name in examples:
        rc = _compile_example(name)
        if rc != 0:
            failures.append(name)
        print(f'  {name}: {"OK" if rc == 0 else "FAIL"}')
    assert not failures, f'Falhou ao compilar: {failures}'


def _run_vcd(example, duration=3):
    """Executa um exemplo com VCD_OUT e retorna o caminho do .vcd."""
    prog = f'/tmp/example_{example}'
    vcd_path = f'/tmp/traces_{example}.vcd'
    env = os.environ.copy()
    env['VCD_OUT'] = vcd_path
    proc = subprocess.Popen([prog], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        proc.wait(timeout=duration + 1)
    except subprocess.TimeoutExpired:
        os.kill(proc.pid, signal.SIGTERM)
        proc.wait(timeout=2)
    return vcd_path


def _validate_vcd(vcd_path, expected_signals, expected_regs):
    """Valida um arquivo VCD."""
    with open(vcd_path) as f:
        content = f.read()
    lines = content.split('\n')

    assert '$timescale 1 us $end' in content, 'timescale ausente'
    assert '$scope module top $end' in content, 'scope ausente'
    assert '$enddefinitions $end' in content, 'enddefinitions ausente'

    for sig in expected_signals:
        assert f' {sig} $end' in content, f'sinal ausente: {sig}'
    for i in range(expected_regs):
        assert f' reg{i} $end' in content, f'reg{i} ausente'

    data_start = content.index('$enddefinitions $end') + len('$enddefinitions $end')
    data = content[data_start:].strip()
    data_lines = data.split('\n')

    timestamps = [l for l in data_lines if l.startswith('#')]
    assert len(timestamps) > 100, f'poucos timestamps: {len(timestamps)}'

    for t in timestamps[:10]:
        num = t[1:]
        assert num.isdigit(), f'timestamp invalido: {t}'

    assert len(content) > 1024, f'arquivo muito pequeno: {len(content)} bytes'
    assert len(data_lines) > len(timestamps), 'sem registros de mudanca'

    change_lines = [l for l in data_lines if l and not l.startswith('#')]
    for cl in change_lines[:100]:
        if ' ' in cl:
            parts = cl.split(' ', 1)
            assert len(parts) == 2, f'registro invalido: {cl}'
            assert len(parts[1]) == 1, f'id invalido: {parts[1]}'
        else:
            assert 'b' in cl or len(cl) >= 2, f'registro invalido: {cl}'


def test_vcd_counter():
    name = 'counter'
    rc = _compile_example(name)
    assert rc == 0, f'Falha ao compilar {name}'
    vcd = _run_vcd(name, duration=2)
    _validate_vcd(vcd,
                  expected_signals=['clk', 'rst', 'count[0]', 'count[1]',
                                    'count[2]', 'count[3]'],
                  expected_regs=3)


def test_vcd_pwm():
    name = 'pwm'
    rc = _compile_example(name)
    assert rc == 0, f'Falha ao compilar {name}'
    vcd = _run_vcd(name, duration=2)
    _validate_vcd(vcd,
                  expected_signals=['clk', 'rst', 'enable', 'pwm_out',
                                    'duty[0]', 'period[0]', 'period[7]'],
                  expected_regs=4)


def test_load_port_order_and_widths_multiple_names(tmp_path):
    from pc_tool.testbench_generator import load_port_order, load_port_widths

    verilog = tmp_path / 'multi.v'
    verilog.write_text('''
module test(input clk, rst, input [7:0] a, b, output reg y, z);
endmodule
''')

    assert load_port_order(str(verilog)) == ['clk', 'rst', 'a', 'b', 'y', 'z']
    widths = load_port_widths(str(verilog))
    assert widths['clk'] == 1
    assert widths['rst'] == 1
    assert widths['a'] == 8
    assert widths['b'] == 8
    assert widths['y'] == 1
    assert widths['z'] == 1
