#!/usr/bin/env python3
"""Testes unitarios para o parser e codegen do uFPGA-Emu."""

import sys
import os
import glob
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pc_tool.parser.parser import parse, ParseError, Parser
from pc_tool.parser.lexer import tokenize
from pc_tool.parser.ast import RepeatStatement
from pc_tool.codegen.c_generator import CGenerator


EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', 'examples')
GENERATED_DIR = os.path.join(os.path.dirname(__file__), '..', 'generated')


def test_parse_all_examples():
    """Testa que todos os exemplos .v compilam sem erro."""
    v_files = glob.glob(os.path.join(EXAMPLES_DIR, '*.v'))
    assert len(v_files) > 0, 'Nenhum arquivo .v encontrado em examples/'

    for v_path in v_files:
        name = os.path.basename(v_path)
        print(f'  Parsing: {name}...', end=' ')
        with open(v_path) as f:
            source = f.read()
        module = parse(source)
        assert module.name, f'{name}: modulo sem nome'
        print(f'OK (modulo={module.name}, ports={len(module.ports)}, '
              f'always={len(module.always_blocks)})')


def test_codegen_all_examples():
    """Testa que todos os exemplos geram C valido."""
    v_files = glob.glob(os.path.join(EXAMPLES_DIR, '*.v'))

    for v_path in v_files:
        name = os.path.basename(v_path)
        print(f'  Codegen: {name}...', end=' ')
        with open(v_path) as f:
            source = f.read()
        module = parse(source)
        gen = CGenerator(module)
        code = gen.generate()

        assert '#include "model.h"' in code, f'{name}: falta include model.h'
        assert 'circuit_init' in code, f'{name}: falta circuit_init'
        assert 'circuit_eval' in code, f'{name}: falta circuit_eval'
        assert 'REG_COUNT' in code, f'{name}: falta REG_COUNT'
        print('OK')


def test_blinky_generated_code():
    """Verifica a corretude do codigo gerado para blinky.v."""
    with open(os.path.join(EXAMPLES_DIR, 'blinky.v')) as f:
        source = f.read()
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()

    assert 'GET_BIT(inputs, 0)' in code  # clk
    assert 'GET_BIT(inputs, 1)' in code  # rst
    assert 'clk_rise' in code
    assert 'state->regs' in code
    assert '0x1' in code or '& 0x1' in code  # width masking


def test_counter_generated_code():
    """Verifica a corretude do codigo gerado para counter.v."""
    with open(os.path.join(EXAMPLES_DIR, 'counter.v')) as f:
        source = f.read()
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()

    assert '& 0xF' in code  # counter width masking (4 bits)
    assert 'state->regs[0]' in code  # count register


def test_generate_main_all_examples():
    """Testa generate_main() produz C valido com pin map JSON para todos os exemplos."""
    v_files = glob.glob(os.path.join(EXAMPLES_DIR, '*.v'))

    for v_path in v_files:
        name = os.path.basename(v_path)
        print(f'  Main gen: {name}...', end=' ')
        with open(v_path) as f:
            source = f.read()
        module = parse(source)
        gen = CGenerator(module)
        code = gen.generate_main()

        assert '#include <stdio.h>' in code, f'{name}: falta stdio'
        assert '#include <pthread.h>' in code, f'{name}: falta pthread'
        assert 'pin_map_load' in code, f'{name}: falta pin_map_load'
        assert 'pthread_create' in code, f'{name}: falta pthread_create'
        assert 'emulator_run_core1' in code, f'{name}: falta emulator_run_core1'
        assert 'telemetry_run_core0' in code, f'{name}: falta telemetry_run_core0'
        # Se o modulo tem clock, verifica hal_gpio_set_clk
        has_clk = any(item.edge for b in module.always_blocks for item in b.sensitivity)
        if has_clk:
            assert 'hal_gpio_set_clk' in code, f'{name}: falta hal_gpio_set_clk'

        # Verifica que o pin map JSON contem todos os ports
        for p in module.ports:
            w = 1 if p.msb is None else p.msb - p.lsb + 1
            for bit in range(w):
                sig = p.name if w == 1 else f'{p.name}[{bit}]'
                assert sig in code, f'{name}: falta {sig} no pin map'

        print('OK')


def test_fsm_generated_code():
    """Verifica a corretude do codigo gerado para fsm_101.v."""
    with open(os.path.join(EXAMPLES_DIR, 'fsm_101.v')) as f:
        source = f.read()
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()

    assert 'switch' in code  # case statement
    assert 'data_in' in code
    assert '& 0x1' in code  # output width (1 bit)


def test_always_star():
    """Verifica que always @(*) gera codigo sem deteccao de borda."""
    source = '''
    module mux(input a, input b, input sel, output reg y);
        always @(*) begin
            if (sel) y = a;
            else     y = b;
        end
    endmodule
    '''
    module = parse(source)
    assert len(module.always_blocks) == 1
    assert module.always_blocks[0].is_auto == True

    gen = CGenerator(module)
    code = gen.generate()

    assert 'clk_rise' not in code
    assert 'state->regs[0]' in code
    # blocking assignment should be direct, no if(edge)
    assert 'if (clk_rise)' not in code
    assert 'REG_COUNT 1' in code

    # test always @* (without parens)
    source2 = '''
    module inv(input a, output reg y);
        always @* y = ~a;
    endmodule
    '''
    module2 = parse(source2)
    assert len(module2.always_blocks) == 1
    assert module2.always_blocks[0].is_auto == True


def test_always_star_mixed():
    """Verifica that @(*) e @(posedge) convivem no mesmo modulo."""
    source = '''
    module mixed(
        input clk, input rst, input a, input b,
        output reg [1:0] count, output reg y
    );
        always @(posedge clk or posedge rst) begin
            if (rst) count <= 2'b0;
            else     count <= count + 1'b1;
        end
        always @(*) begin
            y = a & b;
        end
    endmodule
    '''
    module = parse(source)
    assert len(module.always_blocks) == 2
    auto_blocks = [b for b in module.always_blocks if b.is_auto]
    edge_blocks = [b for b in module.always_blocks if not b.is_auto]
    assert len(auto_blocks) == 1
    assert len(edge_blocks) == 1

    gen = CGenerator(module)
    code = gen.generate()

    assert 'clk_rise' in code  # sequential block has edge detection
    assert 'clk_rise || rst_rise' in code or 'clk_rise || rst_rise' in code
    # combinational block should have direct assignment without edge guard
    assert 'state->regs[1] =' in code  # y assignment
    # verify the code compiles to valid C structure
    assert 'REG_COUNT' in code


def test_arithmetic_operators():
    """Verifica operadores *, /, % no parser e codegen."""
    source = '''
    module alu(
        input [3:0] a, input [3:0] b, input [1:0] op,
        output reg [3:0] y
    );
        always @(*) begin
            case (op)
                2'b00:   y = a + b;
                2'b01:   y = a * b;
                2'b10:   y = a / b;
                2'b11:   y = a % b;
                default: y = 4'b0;
            endcase
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()

    assert '(a * b)' in code
    assert '(a / b)' in code
    assert '(a % b)' in code
    assert '(a + b)' in code


def test_relational_operators():
    """Verifica operadores <, >, <=, >= no parser e codegen."""
    source = '''
    module cmp(
        input [3:0] a, input [3:0] b,
        output reg lt, output reg gt, output reg le, output reg ge
    );
        always @(*) begin
            lt = (a < b);
            gt = (a > b);
            le = (a <= b);
            ge = (a >= b);
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()

    assert '(a < b)' in code
    assert '(a > b)' in code
    assert '(a <= b)' in code
    assert '(a >= b)' in code


def test_operator_precedence():
    """Verifica precedencia: * tem prioridade sobre +, e + sobre <."""
    source = '''
    module prec(
        input [3:0] a, input [3:0] b, input [3:0] c,
        input [3:0] d, output reg y
    );
        always @(*) begin
            y = a + b < c * d;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()

    # (a + b) < (c * d) — addition and multiply bind tighter than relational
    assert '((a + b) < (c * d))' in code


def test_parameter_hash_list():
    """Verifica parameter no #(parameter ...) antes dos ports."""
    source = '''
    module param_counter #(parameter WIDTH = 8) (
        input clk, input rst,
        output reg [WIDTH-1:0] count
    );
        always @(posedge clk or posedge rst) begin
            if (rst) count <= 0;
            else     count <= count + 1;
        end
    endmodule
    '''
    module = parse(source)
    assert len(module.parameters) == 1
    assert module.parameters[0].name == 'WIDTH'
    assert module.parameters[0].value == 8

    gen = CGenerator(module)
    code = gen.generate()

    assert '#define WIDTH 8' in code
    # WIDTH=8 → mask 0xFF
    assert '& 0xFF' in code


def test_parameter_multiple_and_references():
    """Verifica multiplos parametros e referencia entre eles (B = A * 2)."""
    source = '''
    module multi #(
        parameter A = 4,
        parameter B = A * 2
    ) (
        input clk,
        output reg [A-1:0] data,
        output reg [B-1:0] data2
    );
        always @(posedge clk) begin
            data  <= data + 1;
            data2 <= data2 + 2;
        end
    endmodule
    '''
    module = parse(source)
    assert len(module.parameters) == 2
    assert module.parameters[0].name == 'A'
    assert module.parameters[0].value == 4
    assert module.parameters[1].name == 'B'
    assert module.parameters[1].value == 8

    gen = CGenerator(module)
    code = gen.generate()

    assert '#define A 4' in code
    assert '#define B 8' in code
    # A=4 → mask 0xF, B=8 → mask 0xFF
    assert '& 0xF' in code
    assert '& 0xFF' in code
    # Outputs should be packed sequentially: data at bit 0, data2 at bit 4
    assert '<< 4' in code
    # << 0 is suppressed (optimization), data at bit 0 uses direct or
    assert 'state->regs[0] & 0xF' in code


def test_localparam_in_body():
    """Verifica localparam declarado no body do modulo."""
    source = '''
    module lp(
        input clk, input rst,
        output reg [3:0] count
    );
        localparam MAX = 15;
        always @(posedge clk or posedge rst) begin
            if (rst)
                count <= 0;
            else if (count == MAX)
                count <= 0;
            else
                count <= count + 1;
        end
    endmodule
    '''
    module = parse(source)
    assert len(module.parameters) == 1
    assert module.parameters[0].name == 'MAX'
    assert module.parameters[0].value == 15
    assert module.parameters[0].is_local == True

    gen = CGenerator(module)
    code = gen.generate()

    assert '#define MAX 15' in code
    # MAX should be used in the comparison (not replaced by value)
    assert '(count == MAX)' in code or 'MAX' in code


def test_number_underscores():
    """Numeros com underscores são aceitos no lexer/parser."""
    source = '''
    module test(output reg [15:0] y);
        always @(*) begin
            y = 1_000 + 8'b10_10_10_10;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()
    assert '1000' in code
    assert '0xAA' in code or '170' in code


def test_pwm_example():
    """Verifica geracao do exemplo PWM."""
    with open(os.path.join(EXAMPLES_DIR, 'pwm.v')) as f:
        source = f.read()
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()

    assert '#define WIDTH 8' in code
    assert 'clk_rise' in code
    assert '>=' in code
    assert 'duty' in code
    assert 'period' in code
    assert '& 0xFF' in code


def test_uart_tx_example():
    """Verifica geracao do exemplo UART TX."""
    with open(os.path.join(EXAMPLES_DIR, 'uart_tx.v')) as f:
        source = f.read()
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()

    assert '#define CLK_DIV 8' in code
    assert 'clk_rise' in code
    assert 'CLK_DIV' in code
    assert 'GET_BIT' in code
    assert 'GET_BITS' in code
    assert '& 0xFF' in code
    # shift concat pattern: {shift[6:0], 1'b0}
    assert 'GET_BITS(state->regs[4], 6, 0)' in code


def test_tiny_cpu_example():
    """Verifica geracao do exemplo Tiny CPU."""
    with open(os.path.join(EXAMPLES_DIR, 'tiny_cpu.v')) as f:
        source = f.read()
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()

    assert 'switch' in code
    assert 'GET_BITS(instr' in code
    assert 'case 0' in code
    assert 'case 1' in code
    assert 'case 6' in code
    assert 'halted' in code or 'regs[2]' in code
    assert 'REG_COUNT' in code
    # All 4 GP registers should be 8-bit masked
    assert code.count('& 0xFF') >= 8


def test_topological_sort_mixed():
    """Verifica que a ordenacao topologica coloca blocos @(*) antes dos sequenciais."""
    source = '''
    module mixed(
        input clk, input rst, input a, input b,
        output reg [1:0] count, output reg y
    );
        always @(posedge clk or posedge rst) begin
            if (rst) count <= 2'b0;
            else     count <= count + 1'b1;
        end
        always @(*) begin
            if (a & b) y = 1'b1;
            else       y = 1'b0;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    sorted_blocks = gen._topological_sort()

    assert len(sorted_blocks) == 2
    assert sorted_blocks[0].is_auto == True   # @(*) first
    assert sorted_blocks[1].is_auto == False  # sequential second

    code = gen.generate()
    # combinational block body should appear BEFORE the sequential clock guard
    eval_start = code.index('circuit_eval')
    auto_pos = code.index('a & b', eval_start)
    # The sequential guard is now 'if (clk_rise || rst_rise)'
    # (edge detection is global, above both blocks)
    for guard in ('if (clk_rise || rst_rise)', 'if (clk_rise)'):
        try:
            seq_start = code.index(guard, eval_start)
            break
        except ValueError:
            continue
    else:
        raise AssertionError('sequential guard not found')
    assert auto_pos < seq_start, \
        "bloco @(*) deve vir antes do bloco sequencial em circuit_eval()"


def test_edge_detection_all_signals():
    """Verifica que todos os sinais da sensitivity list tem deteccao de borda."""
    source = '''
    module test(input clk, input rst, output reg [1:0] count);
        always @(posedge clk or posedge rst) begin
            if (rst) count <= 2'b0;
            else     count <= count + 1'b1;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()

    assert 'clk_rise' in code, 'clk_rise ausente'
    assert 'rst_rise' in code, 'rst_rise ausente'
    assert 'clk_rise || rst_rise' in code, 'guard combinado ausente'
    # rst_old register deve existir (nao apenas clk_old)
    assert 'state->regs[2]' in code, 'rst_old register ausente'
    # REG_COUNT deve incluir clk_old e rst_old: 1 (count) + 1 + 1 = 3
    assert 'REG_COUNT 3' in code, 'REG_COUNT esperado=3'


def test_edge_detection_reversed_order():
    """Verifica que ordem invertida (rst antes de clk) nao quebra."""
    source = '''
    module test(input clk, input rst, output reg [1:0] count);
        always @(posedge rst or posedge clk) begin
            if (rst) count <= 2'b0;
            else     count <= count + 1'b1;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()

    assert 'clk_rise' in code, 'clk_rise ausente (ordem invertida)'
    assert 'rst_rise' in code, 'rst_rise ausente (ordem invertida)'
    assert 'clk_rise || rst_rise' in code or 'rst_rise || clk_rise' in code


def test_edge_detection_negedge():
    """Verifica que negedge funciona corretamente."""
    source = '''
    module test(input clk, input rst, output reg [1:0] count);
        always @(negedge clk or posedge rst) begin
            if (rst) count <= 2'b0;
            else     count <= count + 1'b1;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()

    assert 'clk_fall' in code, 'clk_fall ausente (negedge)'
    assert 'rst_rise' in code, 'rst_rise ausente'
    assert ' || ' in code, 'guard combinado ausente'


def test_edge_detection_single_signal():
    """Verifica que always @(posedge clk) sem rst funciona."""
    source = '''
    module test(input clk, output reg [1:0] count);
        always @(posedge clk) begin
            count <= count + 1'b1;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()

    assert 'clk_rise' in code, 'clk_rise ausente'
    assert 'rst_rise' not in code, 'rst_rise nao deveria existir'
    assert "if (clk_rise) {" in code, 'guard simples ausente'


def test_topological_sort_cross_dep():
    """Verifica ordenacao topologica: writer antes de reader entre @(*) blocks."""
    source = '''
    module cross(
        input a, input b, input c,
        output reg x, output reg y
    );
        always @(*) begin
            y = x | c;
        end
        always @(*) begin
            x = a & b;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    sorted_blocks = gen._topological_sort()

    assert len(sorted_blocks) == 2
    r0, w0 = gen._block_io(sorted_blocks[0])
    r1, w1 = gen._block_io(sorted_blocks[1])

    # Block 0 must write x (which block 1 reads)
    # Block 1 must write y and read x
    assert 'x' in w0, "bloco 0 deveria escrever x"
    assert 'x' in r1, "bloco 1 deveria ler x"
    assert 'y' in w1, "bloco 1 deveria escrever y"

    code = gen.generate()
    eval_start = code.index('circuit_eval')
    # x = a & b → state->regs[0] = ((a & b))
    # y = x | c → state->regs[1] = ((state->regs[0] | c))
    reg0_assign = code.index('state->regs[0]', eval_start)
    reg1_assign = code.index('state->regs[1]', eval_start)
    assert reg0_assign < reg1_assign, \
        "escritor de x (regs[0]) deve vir antes do leitor de x"

def test_case_equality():
    """=== e !== sao parseados como == e != (case equality em sintetizavel)."""
    source = '''
    module test(input clk, input [3:0] a, input [3:0] b, output reg y);
        always @(posedge clk) begin
            if (a === b) y <= 1'b1;
            else if (a !== b) y <= 1'b0;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()
    assert '==' in code
    assert '!=' in code
    assert 'TRIPLE_EQ' not in code  # macros nao geradas


def test_reduction_operators():
    """&a, |a, ^a geram expressoes C corretas."""
    source = '''
    module test(input clk, input [7:0] a, output reg all_set, any_set, parity);
        always @(posedge clk) begin
            all_set <= &a;
            any_set <= |a;
            parity <= ^a;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()
    assert 'a == 0xFFu' in code   # AND_reduce: a == 0xFF
    assert 'a != 0u' in code     # OR_reduce: a != 0
    assert '!= 0u' in code   # OR_reduce: a != 0
    assert '__builtin_popcount' in code  # XOR_reduce


def test_ternary_operator():
    """Operador ternario ?: gera expressao C correta."""
    source = '''
    module test(input clk, input sel, input a, input b, output reg y);
        always @(posedge clk) begin
            y <= sel ? a : b;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()
    assert '?' in code
    assert ':' in code
    assert 'sel ? a : b' in code or 'sel ?' in code


def test_ternary_nested():
    """Operador ternario aninhado."""
    source = '''
    module test(input clk, input [1:0] sel, input a, input b, input c, output reg y);
        always @(posedge clk) begin
            y <= sel[0] ? (sel[1] ? a : b) : c;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()
    assert code.count('?') == 2
    assert code.count(':') >= 2


def test_for_loop():
    """For loop gera C for loop no codigo gerado."""
    source = '''
    module test(input clk, input rst, output reg [7:0] shift_reg);
        integer i;
        always @(posedge clk or posedge rst) begin
            if (rst)
                shift_reg <= 8'b0;
            else
                for (i = 0; i < 8; i = i + 1)
                    shift_reg[i] <= shift_reg[i+1];
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()
    assert 'for (int i = 0;' in code
    assert 'i < 8' in code
    assert 'i + 1' in code
    assert 'state->regs[' in code


def test_repeat_loop_parse():
    """repeat loop e parseado corretamente."""
    source = '''
    module test(input [3:0] count, output reg [7:0] out);
        reg [7:0] acc;
        always @(*) begin
            acc = 0;
            repeat (count) begin
                acc = acc + 1;
            end
            out = acc;
        end
    endmodule
    '''
    mod = parse(source)
    assert len(mod.always_blocks) == 1
    stmts = mod.always_blocks[0].statements
    assert len(stmts) == 3
    assert isinstance(stmts[1], RepeatStatement)
    assert stmts[1].count == 'count'
    assert len(stmts[1].statements) == 1


def test_repeat_loop_codegen():
    """repeat loop gera for loop C com __repeat_i."""
    source = '''
    module test(input [3:0] count, output reg [7:0] out);
        reg [7:0] acc;
        always @(*) begin
            acc = 0;
            repeat (count) begin
                acc = acc + 1;
            end
            out = acc;
        end
    endmodule
    '''
    mod = parse(source)
    gen = CGenerator(mod)
    code = gen.generate()
    assert '__repeat_i = 0' in code or '__repeat_i <' in code
    assert '__repeat_i < count' in code or '__repeat_i < (count)' in code or '__repeat_i < ((inputs >>' in code
    assert '__repeat_i++' in code
    assert 'state->regs[' in code


def test_not_keyword():
    """not keyword funciona como ! (LOGICAL_NOT)."""
    source = '''
    module test(input clk, input a, output reg y);
        always @(posedge clk) begin
            if (not a) y <= 1'b1;
            else       y <= 1'b0;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()
    assert '!a' in code or '!(a)' in code


def test_repeat_concat():
    """Repeticao {N{expr}} expande para N copias."""
    source = '''
    module test(input clk, output reg [7:0] val);
        always @(posedge clk) begin
            val <= {4{2'b01}};
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()
    assert '<< 2)' in code  # repeat spacing: 2 bits per copy
    assert '<< 4)' in code
    assert '<< 6)' in code


def test_shift_assign_not_broken():
    """<<= e >>= NAO devem ser tokenizados como LE/GE."""
    source = '''
    module test(input clk, input [7:0] a, output reg [7:0] y);
        always @(posedge clk) begin
            y <= a << 1;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()
    assert '<<' in code
    assert 'LE' not in code
    # Previously <<= was mapped to LE, which would corrupt parsing of <<


def test_multi_signal_range_propagation():
    """Verifica que reg [7:0] a, b, c propaga largura para todos."""
    source = '''
    module test(input clk, output reg [7:0] a, b, c);
        always @(posedge clk) begin
            a <= 0; b <= 0; c <= 0;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()

    # All three should have 8-bit mask
    assert code.count('& 0xFF') >= 3


def test_generate_if():
    """generate if seleciona branch correto baseado em parametro."""
    src_true = '''
    module mux #(parameter W = 1)(
        input a, b, sel, output y
    );
        generate
            if (W == 1) begin
                assign y = sel ? a : b;
            end else begin
                assign y = b;
            end
        endgenerate
    endmodule
    '''
    mod = parse(src_true)
    assert len(mod.continuous_assigns) == 1
    assert '?' in mod.continuous_assigns[0].rhs  # if-branch: ternary

    src_false = '''
    module mux2 #(parameter W = 8)(
        input [7:0] a, b,
        input sel,
        output y
    );
        generate
            if (W == 1) begin
                assign y = sel ? a : b;
            end else begin
                assign y = b;
            end
        endgenerate
    endmodule
    '''
    mod2 = parse(src_false)
    assert len(mod2.continuous_assigns) == 1
    assert '?' not in mod2.continuous_assigns[0].rhs  # else-branch: just b


def test_generate_for():
    """generate for desenrola loop com genvar substitution."""
    src = '''
    module adder #(parameter N = 4)(
        input [N-1:0] a, b,
        input cin,
        output [N-1:0] sum,
        output cout
    );
        wire [N:0] c;
        assign c[0] = cin;
        generate
            genvar i;
            for (i = 0; i < N; i = i + 1) begin
                assign sum[i] = a[i] ^ b[i] ^ c[i];
            end
        endgenerate
        assign cout = c[N];
    endmodule
    '''
    mod = parse(src)
    # N=4 => 4 unrolled assigns + c[0] + cout = 6
    assert len(mod.continuous_assigns) == 6

    # Verifica que cada iteracao tem indices diferentes
    rhss = [ca.rhs for ca in mod.continuous_assigns]
    assert any('GET_BIT(a, 0)' in r for r in rhss)
    assert any('GET_BIT(a, 1)' in r for r in rhss)
    assert any('GET_BIT(a, 2)' in r for r in rhss)
    assert any('GET_BIT(a, 3)' in r for r in rhss)


def test_generate_for_different_n():
    """generate for com N=8 produz o dobro de assigns."""
    src4 = '''
    module adder #(parameter N = 4)(
        input [N-1:0] a, b,
        input cin,
        output [N-1:0] sum,
        output cout
    );
        wire [N:0] c;
        assign c[0] = cin;
        generate
            genvar i;
            for (i = 0; i < N; i = i + 1) begin
                assign sum[i] = a[i] ^ b[i] ^ c[i];
            end
        endgenerate
        assign cout = c[N];
    endmodule
    '''
    mod4 = parse(src4)
    src8 = src4.replace('#(parameter N = 4)', '#(parameter N = 8)')
    mod8 = parse(src8)
    # N=4 => 6, N=8 => 10
    assert len(mod8.continuous_assigns) - len(mod4.continuous_assigns) == 4


def test_generate_for_with_parameters():
    """generate for com step = i + STEP (parametro) funciona."""
    src = '''
    module gen #(parameter STEP = 2, N = 8)(
        input clk,
        output reg [7:0] val
    );
        integer i;
        generate
            for (i = 0; i < N; i = i + STEP) begin
                always @(posedge clk) val[i] <= ~val[i];
            end
        endgenerate
    endmodule
    '''
    mod = parse(src)
    # N=8, STEP=2: i = 0, 2, 4, 6 => 4 always blocks
    assert len(mod.always_blocks) == 4


def test_generate_case():
    """generate case seleciona branch correta."""
    src = '''
    module gen_case #(parameter MODE = 2)(
        input a, b,
        output y
    );
        generate
            case (MODE)
                0: assign y = a & b;
                1: assign y = a | b;
                2: assign y = a ^ b;
                default: assign y = 1'b0;
            endcase
        endgenerate
    endmodule
    '''
    mod = parse(src)
    assert len(mod.continuous_assigns) == 1
    assert '^' in mod.continuous_assigns[0].rhs  # MODE=2 => XOR


def test_generate_case_nested_if():
    """generate case com nested generate if dentro de um branch."""
    src = '''
    module nested_gen_if #(parameter CFG = 0, parameter WIDTH = 4)(
        input [WIDTH-1:0] a, b,
        output [WIDTH-1:0] y
    );
        generate
            case (CFG)
                0: begin
                    if (WIDTH > 4) begin
                        assign y = a + b;
                    end else begin
                        assign y = a & b;
                    end
                end
                1: assign y = a | b;
                default: assign y = a ^ b;
            endcase
        endgenerate
    endmodule
    '''
    mod = parse(src)
    # CFG=0, WIDTH=4 => nested if (4 > 4 = false) => a & b
    assert len(mod.continuous_assigns) == 1
    assert '&' in mod.continuous_assigns[0].rhs


def test_generate_case_nested_for():
    """generate case com nested generate for dentro de um branch."""
    src = '''
    module nested_gen_for #(parameter CFG = 0)(
        input [7:0] in,
        output [7:0] out
    );
        generate
            case (CFG)
                0: begin
                    for (genvar i = 0; i < 8; i = i + 1) begin
                        assign out[i] = ~in[i];
                    end
                end
                default: begin
                    assign out = in;
                end
            endcase
        endgenerate
    endmodule
    '''
    mod = parse(src)
    # CFG=0 => for loop with 8 iterations => 8 assigns com ~
    assert len(mod.continuous_assigns) == 8
    for assign in mod.continuous_assigns:
        assert '~' in assign.rhs


def test_generate_case_inactive_skip_nested():
    """Skip (inactive branch) com nested generate for não quebra parser."""
    src = '''
    module nested_inactive_skip #(parameter CFG = 1)(
        input [7:0] in,
        output [7:0] out
    );
        generate
            case (CFG)
                0: begin
                    for (genvar i = 0; i < 8; i = i + 1) begin
                        assign out[i] = ~in[i];
                    end
                end
                default: assign out = in;
            endcase
        endgenerate
    endmodule
    '''
    mod = parse(src)
    # CFG=1 => branch 0 inactive, default active => out = in
    assert len(mod.continuous_assigns) == 1
    assert '~' not in mod.continuous_assigns[0].rhs


def test_generate_nested_generate_block():
    """generate aninhado é expandido corretamente dentro de outro generate."""
    src = '''
    module nested_gen #(parameter CFG = 0, parameter WIDTH = 4)(
        input [WIDTH-1:0] a, b,
        output [WIDTH-1:0] y
    );
        generate
            if (CFG == 0) begin
                generate
                    case (WIDTH)
                        4: assign y = a & b;
                        default: assign y = a | b;
                    endcase
                endgenerate
            end else begin
                assign y = a ^ b;
            end
        endgenerate
    endmodule
    '''
    mod = parse(src)
    assert len(mod.continuous_assigns) == 1
    assert '&' in mod.continuous_assigns[0].rhs


def test_generate_case_with_always():
    """generate case com always blocks dentro de begin...end."""
    src = '''
    module gen_case_always #(parameter CFG = 0)(
        input clk, rst,
        input a, b,
        output reg y
    );
        generate
            case (CFG)
                0: begin
                    always @(posedge clk) begin
                        if (rst)
                            y <= 0;
                        else
                            y <= a & b;
                    end
                end
                default: begin
                    always @(posedge clk) begin
                        y <= a | b;
                    end
                end
            endcase
        endgenerate
    endmodule
    '''
    mod = parse(src)
    assert len(mod.always_blocks) == 1  # CFG=0 => only first always


def test_generate_case_inactive_skip_always():
    """Skip (inactive branch) com always blocks dentro de generate case."""
    src = '''
    module gen_case_skip_always #(parameter CFG = 1)(
        input clk, rst,
        input a, b,
        output reg y
    );
        generate
            case (CFG)
                0: begin
                    always @(posedge clk) begin
                        y <= a & b;
                    end
                end
                default: begin
                    always @(posedge clk) begin
                        y <= a | b;
                    end
                end
            endcase
        endgenerate
    endmodule
    '''
    mod = parse(src)
    assert len(mod.always_blocks) == 1  # CFG=1 => default active
    # Output should be a | b (from default branch)
    code = CGenerator(mod).generate()
    assert '|' in code


def test_generate_case_nested_case():
    """generate case aninhado dentro de outro generate case."""
    src = '''
    module nested_gen_case #(parameter OUTER = 0, parameter INNER = 1)(
        input [3:0] a, b,
        output [3:0] y
    );
        generate
            case (OUTER)
                0: begin
                    case (INNER)
                        0: assign y = a & b;
                        1: assign y = a | b;
                        default: assign y = a ^ b;
                    endcase
                end
                default: assign y = a + b;
            endcase
        endgenerate
    endmodule
    '''
    mod = parse(src)
    # OUTER=0, INNER=1 => a | b
    assert len(mod.continuous_assigns) == 1
    assert '|' in mod.continuous_assigns[0].rhs


def test_codegen_case_statement():
    """Case dentro de always block gera switch em C."""
    source = '''
    module mux_case(
        input [1:0] sel,
        input [3:0] a, b, c, d,
        output reg [3:0] y
    );
        always @(*) begin
            case (sel)
                0: y = a;
                1: y = b;
                2: y = c;
                default: y = d;
            endcase
        end
    endmodule
    '''
    mod = parse(source)
    gen = CGenerator(mod)
    code = gen.generate()
    assert 'switch' in code and 'sel' in code
    assert 'case 0:' in code
    assert 'case 1:' in code
    assert 'case 2:' in code
    assert 'default:' in code
    assert 'break;' in code
    # Verify it generates valid C (includes model.h, etc.)
    assert '#include "model.h"' in code
    assert 'circuit_eval' in code


def test_comb_block_dependency_with_repeat():
    """repeat dentro de bloco combinacional não quebra a ordenacao topologica."""
    source = '''
    module test(input [3:0] n, input a, output reg x, y);
        always @(*) begin
            x = a;
            repeat (n) begin
                x = x ^ 1'b1;
            end
        end
        always @(*) begin
            y = x;
        end
    endmodule
    '''
    module = parse(source)
    gen = CGenerator(module)
    code = gen.generate()
    assert code.index('state->regs[0]') < code.index('state->regs[1]')


def test_parse_instantiation():
    """Module instantiation syntax é parseada corretamente."""
    source = '''
    module inner(input clk, input [3:0] d, output reg [3:0] q);
        always @(posedge clk) q <= d;
    endmodule
    module top(input clk, input [3:0] d, output [3:0] q);
        wire [3:0] w;
        inner #(.WIDTH(4)) u1 (.clk(clk), .d(d), .q(w));
        assign q = w;
    endmodule
    '''
    from pc_tool.parser.registry import ModuleRegistry
    reg = ModuleRegistry()
    reg.parse_source(source)
    top = reg.get('top')
    assert top is not None
    assert len(top.instances) == 1
    inst = top.instances[0]
    assert inst.module_name == 'inner'
    assert inst.instance_name == 'u1'
    assert inst.param_overrides == {'WIDTH': '4'}
    assert inst.port_connections == {'clk': 'clk', 'd': 'd', 'q': 'w'}


def test_inline_single_instance():
    """Inlining de uma instância produz módulo flat correto."""
    source = '''
    module dff(input clk, input d, output reg q);
        always @(posedge clk) q <= d;
    endmodule
    module top(input clk, input d, output q);
        wire w;
        dff u1 (.clk(clk), .d(d), .q(w));
        assign q = w;
    endmodule
    '''
    from pc_tool.parser.registry import ModuleRegistry
    from pc_tool.parser.inliner import flatten_module
    reg = ModuleRegistry()
    reg.parse_source(source)
    flat = flatten_module(reg.get('top'), reg)
    # After flattening: no instances, proper always blocks and assigns
    assert len(flat.instances) == 0
    # Should have 1 always block (from dff), 1 assign (from top)
    assert len(flat.always_blocks) >= 1
    # Wire variable w should exist, plus submodule's reg u1_q
    wire_names = {s.name for s in flat.signals}
    assert 'w' in wire_names or 'u1_q' in wire_names


def test_inline_multiple_instances():
    """Múltiplas instâncias do mesmo módulo têm nomes únicos prefixados."""
    source = '''
    module dff(input clk, input d, output reg q);
        always @(posedge clk) q <= d;
    endmodule
    module top(input clk, input [1:0] d, output [1:0] q);
        wire a, b;
        dff u0 (.clk(clk), .d(d[0]), .q(a));
        dff u1 (.clk(clk), .d(d[1]), .q(b));
        assign q[0] = a;
        assign q[1] = b;
    endmodule
    '''
    from pc_tool.parser.registry import ModuleRegistry
    from pc_tool.parser.inliner import flatten_module
    reg = ModuleRegistry()
    reg.parse_source(source)
    flat = flatten_module(reg.get('top'), reg)
    assert len(flat.instances) == 0
    # Should have 2 always blocks (one per instance)
    assert len(flat.always_blocks) == 2
    signal_names = {s.name for s in flat.signals}
    assert 'u0_q' in signal_names, 'u0_q prefix missing'
    assert 'u1_q' in signal_names, 'u1_q prefix missing'


def test_inline_nested_hierarchy():
    """Hierarquia aninhada é totalmente achatada sem perder prefixos."""
    source = '''
    module leaf(input a, output reg y);
        always @(*) y = a;
    endmodule
    module mid(input a, output y);
        wire w;
        leaf u1(.a(a), .y(w));
        assign y = w;
    endmodule
    module top(input a, output y);
        mid u2(.a(a), .y(y));
    endmodule
    '''
    from pc_tool.parser.registry import ModuleRegistry
    from pc_tool.parser.inliner import flatten_module
    reg = ModuleRegistry()
    reg.parse_source(source)
    flat = flatten_module(reg.get('top'), reg)
    assert len(flat.instances) == 0
    signal_names = {s.name for s in flat.signals}
    assert 'u2_w' in signal_names
    assert 'u2_u1_y' in signal_names


def test_codegen_inlined():
    """Código gerado para módulo com instâncias inline é válido."""
    source = '''
    module dff(input clk, input d, output reg q);
        always @(posedge clk) q <= d;
    endmodule
    module top(input clk, input d, output q);
        wire w;
        dff u1 (.clk(clk), .d(d), .q(w));
        assign q = w;
    endmodule
    '''
    from pc_tool.parser.registry import ModuleRegistry
    from pc_tool.parser.inliner import flatten_module
    reg = ModuleRegistry()
    reg.parse_source(source)
    flat = flatten_module(reg.get('top'), reg)
    gen = CGenerator(flat)
    code = gen.generate()
    assert '#include "model.h"' in code
    assert 'circuit_init' in code
    assert 'circuit_eval' in code
    assert 'REG_COUNT' in code
    assert '*outputs |= ' in code
    # Edge detection should be global (before the if guard)
    assert 'uint8_t clk_rise' in code


def test_parse_task():
    """Parse uma task dentro de um modulo."""
    source = '''
    module test_task(input clk, input [3:0] a, output reg [3:0] out);
        task my_task;
            input [3:0] x;
            output [3:0] y;
            reg [3:0] t;
            begin
                t = x + 1;
                y = t;
            end
        endtask
        always @(posedge clk) begin
            my_task(a, out);
        end
    endmodule
    '''
    tokens = tokenize(source)
    parser = Parser(tokens)
    mod = parser.parse_module()
    assert len(mod.tasks) == 1
    assert mod.tasks[0].name == 'my_task'
    assert len(mod.tasks[0].ports) == 2
    assert mod.tasks[0].ports[0].name == 'x'
    assert mod.tasks[0].ports[0].direction == 'input'
    assert mod.tasks[0].ports[1].name == 'y'
    assert mod.tasks[0].ports[1].direction == 'output'
    assert len(mod.tasks[0].statements) == 2


def test_parse_function():
    """Parse uma funcao dentro de um modulo."""
    source = '''
    module test_func(input clk, input [3:0] a, input [3:0] b, output reg [7:0] out);
        function [7:0] my_func;
            input [3:0] x;
            input [3:0] y;
            begin
                my_func = x + y;
            end
        endfunction
        always @(posedge clk) begin
            out <= my_func(a, b);
        end
    endmodule
    '''
    tokens = tokenize(source)
    parser = Parser(tokens)
    mod = parser.parse_module()
    assert len(mod.functions) == 1
    assert mod.functions[0].name == 'my_func'
    assert mod.functions[0].return_msb == 7
    assert mod.functions[0].return_lsb == 0
    assert len(mod.functions[0].ports) == 2
    assert mod.functions[0].ports[0].name == 'x'
    assert mod.functions[0].ports[1].name == 'y'


def test_codegen_task():
    """Codigo gerado para modulo com task tem funcao C auxiliar."""
    source = '''
    module test_task(input clk, input [3:0] a, output reg [3:0] out);
        task my_task;
            input [3:0] x;
            output [3:0] y;
            begin
                y = x + 1;
            end
        endtask
        always @(posedge clk) begin
            my_task(a, out);
        end
    endmodule
    '''
    tokens = tokenize(source)
    parser = Parser(tokens)
    mod = parser.parse_module()
    gen = CGenerator(mod)
    code = gen.generate()
    assert 'static void my_task(model_state_t *state' in code
    assert 'uint32_t *y' in code
    assert '*y = ' in code
    assert 'my_task(state' in code


def test_codegen_function():
    """Codigo gerado para modulo com funcao tem funcao inline C."""
    source = '''
    module test_func(input clk, input [3:0] a, input [3:0] b, output reg [7:0] out);
        function [7:0] my_func;
            input [3:0] x;
            input [3:0] y;
            begin
                my_func = x + y;
            end
        endfunction
        always @(posedge clk) begin
            out <= my_func(a, b);
        end
    endmodule
    '''
    tokens = tokenize(source)
    parser = Parser(tokens)
    mod = parser.parse_module()
    gen = CGenerator(mod)
    code = gen.generate()
    assert 'static inline uint32_t my_func(uint32_t x, uint32_t y)' in code
    assert 'return' in code
    assert 'my_func(a, b)' in code


def test_codegen_function_return_mask():
    """Function com largura declarada deve mascarar o retorno."""
    source = '''
    module test(input [7:0] a, input [7:0] b, output reg [7:0] out);
        function [7:0] f1;
            input [7:0] x;
            input [7:0] y;
            begin
                f1 = x + y + 8'hff;
            end
        endfunction
        always @(*) begin
            out = f1(a, b);
        end
    endmodule
    '''
    mod = parse(source)
    gen = CGenerator(mod)
    code = gen.generate()
    assert 'static inline uint32_t f1(uint32_t x, uint32_t y)' in code
    assert 'return' in code
    assert '& 0xFFu' in code or '& 0xFF' in code


def test_codegen_function_in_expression():
    """Chamadas de function dentro de expressões maiores continuam corretas."""
    source = '''
    module test(input [3:0] a, input [3:0] b, input sel, output reg [7:0] out);
        function [7:0] add8;
            input [3:0] x;
            input [3:0] y;
            begin
                add8 = x + y;
            end
        endfunction
        always @(*) begin
            out = sel ? {add8(a, b)[3:0], 4'b0000} : add8(a, b);
        end
    endmodule
    '''
    mod = parse(source)
    gen = CGenerator(mod)
    code = gen.generate()
    assert 'static inline uint32_t add8(uint32_t x, uint32_t y)' in code
    assert 'add8(a, b)' in code
    assert '?' in code


def test_codegen_nested_functions():
    """Functions podem se chamar mesmo quando a outra é declarada depois."""
    source = '''
    module test(input [3:0] a, output reg [7:0] out);
        function [7:0] outer;
            input [3:0] x;
            begin
                outer = inner(x);
            end
        endfunction
        function [7:0] inner;
            input [3:0] x;
            begin
                inner = {4'b0000, x};
            end
        endfunction
        always @(*) begin
            out = outer(a);
        end
    endmodule
    '''
    mod = parse(source)
    gen = CGenerator(mod)
    code = gen.generate()
    assert 'static inline uint32_t outer(uint32_t x);' in code
    assert 'static inline uint32_t inner(uint32_t x);' in code
    assert 'outer(a)' in code
    assert 'inner(x)' in code


def test_function_direct_recursion_rejected():
    """Recursao direta em function deve ser rejeitada explicitamente."""
    source = '''
    module test(input [3:0] a, output reg [7:0] out);
        function [7:0] f1;
            input [3:0] x;
            begin
                f1 = f1(x);
            end
        endfunction
        always @(*) out = f1(a);
    endmodule
    '''
    mod = parse(source)
    with pytest.raises(RuntimeError, match='Function recursion detected'):
        CGenerator(mod).generate()


def test_function_indirect_recursion_rejected():
    """Recursao indireta em functions deve ser rejeitada."""
    source = '''
    module test(input [3:0] a, output reg [7:0] out);
        function [7:0] f1;
            input [3:0] x;
            begin
                f1 = f2(x);
            end
        endfunction
        function [7:0] f2;
            input [3:0] x;
            begin
                f2 = f1(x);
            end
        endfunction
        always @(*) out = f1(a);
    endmodule
    '''
    mod = parse(source)
    with pytest.raises(RuntimeError, match='Function recursion detected'):
        CGenerator(mod).generate()


def test_task_direct_recursion_rejected():
    """Recursao direta em task deve ser rejeitada."""
    source = '''
    module test(input clk);
        task t1;
            input x;
            begin
                t1(x);
            end
        endtask
        always @(posedge clk) t1(1'b0);
    endmodule
    '''
    mod = parse(source)
    with pytest.raises(RuntimeError, match='Task recursion detected'):
        CGenerator(mod).generate()


def test_task_indirect_recursion_rejected():
    """Recursao indireta em tasks deve ser rejeitada."""
    source = '''
    module test(input clk);
        task t1;
            input x;
            begin
                t2(x);
            end
        endtask
        task t2;
            input x;
            begin
                t1(x);
            end
        endtask
        always @(posedge clk) t1(1'b0);
    endmodule
    '''
    mod = parse(source)
    with pytest.raises(RuntimeError, match='Task recursion detected'):
        CGenerator(mod).generate()


def test_function_calling_task_rejected():
    """Function não deve chamar task diretamente."""
    source = '''
    module test(input [3:0] a, output reg [3:0] out);
        task t1;
            input [3:0] x;
            begin
                out = x;
            end
        endtask
        function [3:0] f1;
            input [3:0] x;
            begin
                t1(x);
                f1 = x;
            end
        endfunction
        always @(*) out = f1(a);
    endmodule
    '''
    with pytest.raises(Exception, match='cross-call'):
        parse(source)


def test_task_calling_function_allowed():
    """Task pode chamar function diretamente."""
    source = '''
    module test(input clk, input [3:0] a, input [3:0] b, output reg [7:0] out);
        function [7:0] f1;
            input [3:0] x;
            input [3:0] y;
            begin
                f1 = x + y;
            end
        endfunction
        task t1;
            input [3:0] x;
            input [3:0] y;
            output [7:0] z;
            begin
                z = f1(x, y);
            end
        endtask
        always @(posedge clk) begin
            t1(a, b, out);
        end
    endmodule
    '''
    mod = parse(source)
    gen = CGenerator(mod)
    code = gen.generate()
    assert 'static inline uint32_t f1(uint32_t x, uint32_t y)' in code
    assert 'static void t1(model_state_t *state' in code
    assert 'f1(x, y)' in code


def test_task_function_nested_chain_allowed():
    """Task pode chamar function que chama outra function definida depois."""
    source = '''
    module test(input clk, input [3:0] a, input [3:0] b, output reg [7:0] out);
        function [7:0] f2;
            input [3:0] x;
            begin
                f2 = {4'b0000, x};
            end
        endfunction
        function [7:0] f1;
            input [3:0] x;
            input [3:0] y;
            begin
                f1 = f2(x) + y;
            end
        endfunction
        task t1;
            input [3:0] x;
            input [3:0] y;
            output [7:0] z;
            begin
                z = f1(x, y);
            end
        endtask
        always @(posedge clk) begin
            t1(a, b, out);
        end
    endmodule
    '''
    mod = parse(source)
    gen = CGenerator(mod)
    code = gen.generate()
    assert 'static inline uint32_t f1(uint32_t x, uint32_t y);' in code
    assert 'static inline uint32_t f2(uint32_t x);' in code
    assert 'f1(x, y)' in code
    assert 'f2(x)' in code


def test_task_function_local_regs():
    """Task e function preservam regs locais declarados no corpo."""
    source = '''
    module test(input clk, input [3:0] a, input [3:0] b, output reg [7:0] out);
        task t1;
            input [3:0] x;
            output [3:0] y;
            reg [3:0] tmp;
            begin
                tmp = x + 1;
                y = tmp;
            end
        endtask
        function [7:0] f1;
            input [3:0] x;
            input [3:0] y;
            reg [7:0] acc;
            begin
                acc = x + y;
                f1 = acc;
            end
        endfunction
        always @(posedge clk) begin
            t1(a, out[3:0]);
            out <= f1(a, b);
        end
    endmodule
    '''
    mod = parse(source)
    assert mod.tasks[0].locals[0].name == 'tmp'
    assert mod.functions[0].locals[0].name == 'acc'
    gen = CGenerator(mod)
    code = gen.generate()
    assert 'uint32_t tmp = 0;' in code
    assert 'uint32_t acc = 0;' in code
    assert 'return' in code
    assert '& 0xFFu' in code or '& 0xFF' in code


def test_codegen_task_func_example():
    """Codigo gerado para o exemplo task_func.v e valido."""
    import os
    path = os.path.join(os.path.dirname(__file__), '..', 'examples', 'task_func.v')
    with open(path) as f:
        source = f.read()
    tokens = tokenize(source)
    parser = Parser(tokens)
    mod = parser.parse_module()
    gen = CGenerator(mod)
    code = gen.generate()
    assert '#include "model.h"' in code
    assert 'static void mult_task(model_state_t *state' in code
    assert 'static inline uint32_t add_func(uint32_t x, uint32_t y)' in code
    assert 'circuit_init' in code
    assert 'circuit_eval' in code


def test_concat_multi_bit_width():
    """Concat {4b1111, 4-bit-signal} must use <<4 and &0xF, not <<1 and &0x1."""
    source = '''
    module test (
        input wire [3:0] value,
        output reg [7:0] out
    );
        always @(*) begin
            out = {4'b1111, value};
        end
    endmodule
    '''
    mod = parse(source)
    gen = CGenerator(mod)
    code = gen.generate()
    # The expr for value must be value & 0xF (not & 0x1),
    # and shifted by 4 (not by 1)
    assert 'value & 0xF' in code, 'Should mask value with 0xF (4 bits), not 0x1'
    assert '<< 4)' in code or '<< 4,' in code, 'Should shift 4b1111 by 4, not by 1'
    # Should NOT have << 1 anywhere in the concat area
    out_assign = [l for l in code.splitlines() if 'state->regs' in l and 'out' not in l]
    if out_assign:
        assert '<< 1' not in out_assign[0], 'Should not shift by 1'


def test_concat_multi_bit_width_repeat():
    """Repeat concat {N{expr}} with multi-bit signal must infer correct width."""
    source = '''
    module test (
        input wire [3:0] value,
        output reg [7:0] out
    );
        always @(*) begin
            out = {4{value}};
        end
    endmodule
    '''
    mod = parse(source)
    gen = CGenerator(mod)
    code = gen.generate()
    # Each copy of value is 4 bits, total 16 bits, but out is 8 bits
    assert 'value & 0xF' in code, 'Each copy of value should be & 0xF, not & 0x1'


def test_part_select_lhs():
    """LHS part-select must generate read-modify-write, not full overwrite."""
    source = '''
    module test (
        input wire [3:0] value,
        output reg [7:0] out
    );
        always @(*) begin
            out[7:4] = value;
        end
    endmodule
    '''
    mod = parse(source)
    gen = CGenerator(mod)
    code = gen.generate()
    # Must have read-modify-write pattern: & ~mask | ...shifted
    assert 'state->regs[0] & ~0xF0u' in code, (
        'Should mask out bits 7:4 before OR')
    assert 'value & 0xFu' in code, (
        'Should mask value to 4 bits')
    assert '<< 4' in code, (
        'Should shift value to bits 7:4')


def test_part_select_lhs_single_bit():
    """Single-bit LHS select must generate read-modify-write."""
    source = '''
    module test (
        input wire       set,
        output reg [7:0] out
    );
        always @(*) begin
            out[3] = set;
        end
    endmodule
    '''
    mod = parse(source)
    gen = CGenerator(mod)
    code = gen.generate()
    assert 'state->regs[0] & ~0x8u' in code, (
        'Should mask out bit 3 before OR')
    assert 'set' in code, 'Should read set input'


def test_part_select_nonblocking():
    """Non-blocking assign with LHS part-select must wrap in if(clk_edge)."""
    source = '''
    module test (
        input wire       clk,
        input wire [3:0] value,
        output reg [7:0] out
    );
        always @(posedge clk) begin
            out[7:4] <= value;
        end
    endmodule
    '''
    mod = parse(source)
    gen = CGenerator(mod)
    code = gen.generate()
    assert 'clk_rise' in code, 'Needs edge detection'
    assert '& ~0xF0u' in code, 'Should have read-modify-write mask'
    assert '<< 4' in code, 'Should shift value to upper nibble'


if __name__ == '__main__':
    print('Testes do Parser:')
    test_parse_all_examples()
    print()
    print('Testes do Codegen:')
    test_codegen_all_examples()
    print()
    print('Testes de Corretude:')
    test_blinky_generated_code()
    print('  blinky: OK')
    test_counter_generated_code()
    print('  counter: OK')
    test_fsm_generated_code()
    print('  fsm_101: OK')
    print()
    print('Testes de always @(*):')
    test_always_star()
    print('  always_star: OK')
    test_always_star_mixed()
    print('  always_star_mixed: OK')
    print()
    print('Testes de Operadores:')
    test_arithmetic_operators()
    print('  arithmetic: OK')
    test_relational_operators()
    print('  relational: OK')
    test_operator_precedence()
    print('  precedence: OK')
    print()
    print('Testes de Parameter:')
    test_parameter_hash_list()
    print('  parameter_hash: OK')
    test_parameter_multiple_and_references()
    print('  parameter_multiple: OK')
    test_localparam_in_body()
    print('  localparam: OK')
    print()
    print('Testes de Exemplos Avancados:')
    test_pwm_example()
    print('  pwm: OK')
    test_uart_tx_example()
    print('  uart_tx: OK')
    test_tiny_cpu_example()
    print('  tiny_cpu: OK')
    test_multi_signal_range_propagation()
    print('  range_propagation: OK')
    print()
    print('Testes de Generate:')
    test_generate_case()
    print('  generate_case: OK')
    test_generate_if()
    print('  generate_if: OK')
    test_generate_for()
    print('  generate_for: OK')
    test_generate_for_different_n()
    print('  generate_for_different_n: OK')
    test_generate_for_with_parameters()
    print('  generate_for_with_params: OK')
    test_generate_case_nested_if()
    print('  generate_case_nested_if: OK')
    test_generate_case_nested_for()
    print('  generate_case_nested_for: OK')
    test_generate_case_inactive_skip_nested()
    print('  generate_case_inactive_skip_nested: OK')
    print()
    print('Testes de Main Generation:')
    test_generate_main_all_examples()
    print()
    print('Todos os testes passaram!')
