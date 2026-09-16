import json
import re
from collections import deque
from pc_tool.parser.ast import (
    Module, Port, Signal, AlwaysBlock, AssignStatement,
    IfStatement, CaseItem, CaseStatement, ForStatement, RepeatStatement,
    SensitivityItem, TaskDecl, FunctionDecl, TaskEnableStatement,
    FuncCallExpression
)


class CGenerator:
    def __init__(self, module: Module):
        self.module = module
        self.indent = 0
        self.lines = []
        self.inputs: list[Port] = []
        self.outputs: list[Port] = []
        self.regs: list[Signal] = []
        self._reg_mask: dict[int, str] = {}
        self._classify()
        self._assign_input_bits()
        self._assign_output_bits()
        self._edge_regs: dict[str, int] = {}
        self._find_edge_regs()
        self._remove_unused_regs()
        self._local_vars: set[str] = set()
        self._local_out_ports: dict[str, str] = {}
        self._func_return_name: str | None = None
        self._func_return_mask: str | None = None
        self._check_function_recursion()
        self._check_task_recursion()

    def _reg_names(self) -> set[str]:
        return {r.name for r in self.regs}

    def _block_io(self, block: AlwaysBlock) -> tuple[set[str], set[str]]:
        """Return (reads, writes) for register signals in an always block."""
        reads: set[str] = set()
        writes: set[str] = set()
        regs = self._reg_names()
        for stmt in block.statements:
            self._stmt_io(stmt, reads, writes, regs)
        return reads, writes

    def _stmt_io(self, stmt, reads: set[str], writes: set[str], regs: set[str]):
        if isinstance(stmt, AssignStatement):
            if stmt.lhs in regs:
                writes.add(stmt.lhs)
            for name in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', stmt.rhs):
                if name in regs:
                    reads.add(name)
        elif isinstance(stmt, IfStatement):
            for name in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', stmt.condition):
                if name in regs:
                    reads.add(name)
            for s in stmt.if_branch:
                self._stmt_io(s, reads, writes, regs)
            if stmt.else_branch:
                for s in stmt.else_branch:
                    self._stmt_io(s, reads, writes, regs)
        elif isinstance(stmt, CaseStatement):
            for name in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', stmt.expression):
                if name in regs:
                    reads.add(name)
            for item in stmt.items:
                for s in item.statements:
                    self._stmt_io(s, reads, writes, regs)
        elif isinstance(stmt, ForStatement):
            for name in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', stmt.start):
                if name in regs:
                    reads.add(name)
            for name in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', stmt.condition):
                if name in regs:
                    reads.add(name)
            for name in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', stmt.step):
                if name in regs:
                    reads.add(name)
            for s in stmt.statements:
                self._stmt_io(s, reads, writes, regs)
        elif isinstance(stmt, RepeatStatement):
            for name in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', stmt.count):
                if name in regs:
                    reads.add(name)
            for s in stmt.statements:
                self._stmt_io(s, reads, writes, regs)
        elif isinstance(stmt, TaskEnableStatement):
            for arg in stmt.args:
                for name in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', arg):
                    if name in regs:
                        reads.add(name)
                        writes.add(name)

    def _topological_sort(self) -> list[AlwaysBlock]:
        """Return always blocks: combinational blocks first (topologically sorted),
        then sequential blocks in original order."""
        combos = []
        sequential = []
        for b in self.module.always_blocks:
            if b.is_auto:
                combos.append(b)
            else:
                sequential.append(b)

        n = len(combos)
        if n > 1:
            ios = [self._block_io(b) for b in combos]
            adj = [[] for _ in range(n)]
            in_deg = [0] * n
            for i in range(n):
                for j in range(n):
                    if i != j and ios[i][1] & ios[j][0]:
                        adj[i].append(j)
                        in_deg[j] += 1

            q = deque([i for i in range(n) if in_deg[i] == 0])
            sorted_idx = []
            while q:
                i = q.popleft()
                sorted_idx.append(i)
                for j in adj[i]:
                    in_deg[j] -= 1
                    if in_deg[j] == 0:
                        q.append(j)

            remaining = set(range(n)) - set(sorted_idx)
            sorted_idx.extend(remaining)
            result = [combos[i] for i in sorted_idx]
        else:
            result = list(combos)

        result.extend(sequential)
        return result

    def _stmt_usage(self, stmt, reads: set[str], writes: set[str]):
        def extract(txt):
            return set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', txt))
        if isinstance(stmt, AssignStatement):
            writes.add(stmt.lhs)
            reads.update(extract(stmt.rhs))
        elif isinstance(stmt, IfStatement):
            reads.update(extract(stmt.condition))
            for s in stmt.if_branch:
                self._stmt_usage(s, reads, writes)
            if stmt.else_branch:
                for s in stmt.else_branch:
                    self._stmt_usage(s, reads, writes)
        elif isinstance(stmt, CaseStatement):
            reads.update(extract(stmt.expression))
            for item in stmt.items:
                for s in item.statements:
                    self._stmt_usage(s, reads, writes)
        elif isinstance(stmt, ForStatement):
            reads.update(extract(stmt.start))
            reads.update(extract(stmt.condition))
            reads.update(extract(stmt.step))
            for s in stmt.statements:
                self._stmt_usage(s, reads, writes)
        elif isinstance(stmt, RepeatStatement):
            reads.update(extract(stmt.count))
            for s in stmt.statements:
                self._stmt_usage(s, reads, writes)
        elif isinstance(stmt, TaskEnableStatement):
            for arg in stmt.args:
                reads.update(extract(arg))

    def _stmt_function_calls(self, stmt, fn_names: set[str], calls: set[str]):
        def extract_calls(txt):
            for name in fn_names:
                if re.search(r'\b%s\s*\(' % re.escape(name), txt):
                    calls.add(name)

        if isinstance(stmt, AssignStatement):
            extract_calls(stmt.rhs)
            if stmt.lhs_msb is not None:
                extract_calls(stmt.lhs_msb)
            if stmt.lhs_lsb is not None:
                extract_calls(stmt.lhs_lsb)
        elif isinstance(stmt, IfStatement):
            extract_calls(stmt.condition)
            for s in stmt.if_branch:
                self._stmt_function_calls(s, fn_names, calls)
            if stmt.else_branch:
                for s in stmt.else_branch:
                    self._stmt_function_calls(s, fn_names, calls)
        elif isinstance(stmt, CaseStatement):
            extract_calls(stmt.expression)
            for item in stmt.items:
                for s in item.statements:
                    self._stmt_function_calls(s, fn_names, calls)
        elif isinstance(stmt, ForStatement):
            extract_calls(stmt.start)
            extract_calls(stmt.condition)
            extract_calls(stmt.step)
            for s in stmt.statements:
                self._stmt_function_calls(s, fn_names, calls)
        elif isinstance(stmt, RepeatStatement):
            extract_calls(stmt.count)
            for s in stmt.statements:
                self._stmt_function_calls(s, fn_names, calls)
        elif isinstance(stmt, TaskEnableStatement):
            for arg in stmt.args:
                extract_calls(arg)

    def _stmt_task_calls(self, stmt, task_names: set[str], calls: set[str]):
        def extract_calls(txt):
            for name in task_names:
                if re.search(r'\b%s\s*\(' % re.escape(name), txt):
                    calls.add(name)

        if isinstance(stmt, AssignStatement):
            extract_calls(stmt.rhs)
            if stmt.lhs_msb is not None:
                extract_calls(stmt.lhs_msb)
            if stmt.lhs_lsb is not None:
                extract_calls(stmt.lhs_lsb)
        elif isinstance(stmt, IfStatement):
            extract_calls(stmt.condition)
            for s in stmt.if_branch:
                self._stmt_task_calls(s, task_names, calls)
            if stmt.else_branch:
                for s in stmt.else_branch:
                    self._stmt_task_calls(s, task_names, calls)
        elif isinstance(stmt, CaseStatement):
            extract_calls(stmt.expression)
            for item in stmt.items:
                for s in item.statements:
                    self._stmt_task_calls(s, task_names, calls)
        elif isinstance(stmt, ForStatement):
            extract_calls(stmt.start)
            extract_calls(stmt.condition)
            extract_calls(stmt.step)
            for s in stmt.statements:
                self._stmt_task_calls(s, task_names, calls)
        elif isinstance(stmt, RepeatStatement):
            extract_calls(stmt.count)
            for s in stmt.statements:
                self._stmt_task_calls(s, task_names, calls)
        elif isinstance(stmt, TaskEnableStatement):
            if stmt.name in task_names:
                calls.add(stmt.name)
            for arg in stmt.args:
                extract_calls(arg)

    def _check_function_recursion(self):
        fn_names = {f.name for f in self.module.functions}
        graph: dict[str, set[str]] = {name: set() for name in fn_names}
        for func in self.module.functions:
            calls: set[str] = set()
            for stmt in func.statements:
                self._stmt_function_calls(stmt, fn_names, calls)
            graph[func.name] = calls

        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(node: str):
            if node in visiting:
                raise RuntimeError(f'Function recursion detected: {node}')
            if node in visited:
                return
            visiting.add(node)
            for nxt in graph.get(node, set()):
                dfs(nxt)
            visiting.remove(node)
            visited.add(node)

        for name in fn_names:
            dfs(name)

    def _check_task_recursion(self):
        task_names = {t.name for t in self.module.tasks}
        graph: dict[str, set[str]] = {name: set() for name in task_names}
        for task in self.module.tasks:
            calls: set[str] = set()
            for stmt in task.statements:
                self._stmt_task_calls(stmt, task_names, calls)
            graph[task.name] = calls

        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(node: str):
            if node in visiting:
                raise RuntimeError(f'Task recursion detected: {node}')
            if node in visited:
                return
            visiting.add(node)
            for nxt in graph.get(node, set()):
                dfs(nxt)
            visiting.remove(node)
            visited.add(node)

        for name in task_names:
            dfs(name)

    def _remove_unused_regs(self):
        if not self.regs:
            return
        reads: set[str] = set()
        writes: set[str] = set()
        def extract(txt):
            return set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', txt))
        for b in self.module.always_blocks:
            for stmt in b.statements:
                self._stmt_usage(stmt, reads, writes)
        for ca in self.module.continuous_assigns:
            reads.update(extract(ca.rhs))
            if re.match(r'^\w+$', ca.lhs):
                writes.add(ca.lhs)
        output_reg_names = {p.name for p in self.outputs if p.name in self._reg_names()}
        dead = set()
        for r in self.regs:
            if r.name in output_reg_names:
                continue
            if r.name in reads:
                continue
            dead.add(r.name)
        if not dead:
            return
        new_regs = [r for r in self.regs if r.name not in dead]
        new_masks = {}
        for i, r in enumerate(new_regs):
            if r.width < 32:
                new_masks[i] = '0x%X' % ((1 << r.width) - 1)
        new_edge = {}
        edge_names = sorted(self._edge_regs.keys())
        for j, name in enumerate(edge_names):
            new_edge[name] = len(new_regs) + j
            new_masks[new_edge[name]] = '0x1'
        self.regs = new_regs
        self._reg_mask = new_masks
        self._edge_regs = new_edge

    def _classify(self):
        self.inputs.clear()
        self.outputs.clear()
        self.regs.clear()
        self._reg_mask.clear()
        for p in self.module.ports:
            if p.direction == 'input':
                self.inputs.append(p)
            elif p.direction == 'output':
                self.outputs.append(p)
        for s in self.module.signals:
            if s.sig_type == 'reg':
                idx = len(self.regs)
                self.regs.append(s)
                if s.width < 32:
                    self._reg_mask[idx] = '0x%X' % ((1 << s.width) - 1)

    def _assign_input_bits(self):
        bit = 0
        for p in self.inputs:
            if p.msb is None:
                p.lsb = bit
                p.msb = bit
                bit += 1
            else:
                w = p.msb - p.lsb + 1
                p.lsb = bit
                p.msb = bit + w - 1
                bit = p.msb + 1

    def _assign_output_bits(self):
        bit = 0
        for p in self.outputs:
            w = p.width
            p.lsb = bit
            p.msb = bit + w - 1
            bit += w

    def _find_edge_regs(self):
        idx = len(self.regs)
        for block in self.module.always_blocks:
            if block.is_auto:
                continue
            for item in block.sensitivity:
                if item.edge:
                    name = item.signal + '_old'
                    if name not in self._edge_regs:
                        self._edge_regs[name] = idx
                        self._reg_mask[idx] = '0x1'
                        idx += 1

    def _find_clk_signal(self) -> str | None:
        """Return the first signal with posedge across all always blocks."""
        for b in self.module.always_blocks:
            if b.is_auto:
                continue
            for item in b.sensitivity:
                if item.edge == 'posedge':
                    return item.signal
        return None

    def _reg_idx(self, name: str) -> int:
        for i, r in enumerate(self.regs):
            if r.name == name:
                return i
        if name in self._edge_regs:
            return self._edge_regs[name]
        return -1

    def _signal_width(self, name: str) -> int | None:
        for s in self.inputs + self.outputs:
            if s.name == name:
                return s.width
        for s in self.regs:
            if s.name == name:
                return s.width
        for s in self.module.signals:
            if s.name == name:
                return s.width
        return None

    def _expand_and_reduce(self, inner: str) -> str:
        w = self._signal_width(inner)
        if w is None or w >= 32:
            return f'({inner} == 0xFFFFFFFFu)'
        if w == 1:
            return f'({inner})'
        mask = (1 << w) - 1
        return f'({inner} == 0x{mask:X}u)'

    def _fold_constants(self, expr: str) -> str:
        def fold_repl(m):
            inner = m.group(1)
            mask_str = m.group(2)
            suffix = m.group(3) or ''
            n = int(inner, 0)
            mask = int(mask_str, 0)
            return str(n & mask) + suffix
        # Pattern 1: (NUMBER) & MASK[u] — from _gen_assign mask wrapping
        expr = re.sub(r'\((\d+|0x[0-9a-fA-F]+)\)\s*&\s*(0x[0-9a-fA-F]+|\d+)(u?)', fold_repl, expr)
        # Pattern 2: NUMBER & MASK[u] (not preceded by word char) — from continuous assigns
        expr = re.sub(r'(?<!\w)(\d+|0x[0-9a-fA-F]+)\s*&\s*(0x[0-9a-fA-F]+|\d+)(u?)', fold_repl, expr)
        return expr

    def _expand_reductions(self, expr: str) -> str:
        result = []
        i = 0
        while i < len(expr):
            for prefix, func_name in (
                ('emu_and_reduce(', 'and'),
                ('emu_or_reduce(', 'or'),
                ('emu_xor_reduce(', 'xor'),
            ):
                if expr[i:].startswith(prefix):
                    start = i + len(prefix)
                    depth = 1
                    j = start
                    while j < len(expr) and depth > 0:
                        if expr[j] == '(':
                            depth += 1
                        elif expr[j] == ')':
                            depth -= 1
                        j += 1
                    inner = expr[start:j-1]
                    if func_name == 'and':
                        result.append(self._expand_and_reduce(inner))
                    elif func_name == 'or':
                        result.append(f'({inner} != 0u)')
                    elif func_name == 'xor':
                        result.append(f'(__builtin_popcount({inner}) & 1)')
                    i = j
                    break
            else:
                result.append(expr[i])
                i += 1
        return ''.join(result)

    def _rewrite(self, expr: str, local_vars: set[str] = None) -> str:
        expr = self._expand_reductions(expr)
        expr = expr.replace('===', '==')
        expr = expr.replace('!==', '!=')
        lv = local_vars or self._local_vars
        def repl(m):
            name = m.group(1)
            if name in self._local_out_ports:
                return self._local_out_ports[name]
            if name in lv:
                return name
            idx = self._reg_idx(name)
            if idx >= 0:
                return 'state->regs[%d]' % idx
            return name
        return re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', repl, expr)

    def _emit(self, line: str = ''):
        self.lines.append('    ' * self.indent + line)

    def generate(self) -> str:
        self._emit('/*')
        self._emit(' * Gerado pelo pc_tool uFPGA-Emu')
        self._emit(' * Modulo: %s' % self.module.name)
        self._emit(' */')
        self._emit('#include "model.h"')
        self._emit()
        self._emit('#define GET_BIT(w, b)  (((w) >> (b)) & 1u)')
        self._emit('#define GET_BITS(w, h, l) (((w) >> (l)) & ((1u << ((h)-(l)+1)) - 1u))')
        self._emit()

        for p in self.module.parameters:
            self._emit('#define %s %d' % (p.name, p.value))
        if self.module.parameters:
            self._emit()

        reg_count = len(self.regs) + len(self._edge_regs)
        self._emit('#define REG_COUNT %d' % reg_count)
        self._emit()

        self._gen_function_prototypes()
        self._gen_functions()
        self._gen_tasks()
        self._gen_init()
        self._gen_eval()

        return '\n'.join(self.lines)

    def generate_main(self) -> str:
        entries = []
        pin = 1
        clk_pin = 0
        clk_signal = self._find_clk_signal()
        for p in self.inputs:
            for bit_offset in range(p.width):
                name = p.name if p.width == 1 else '%s[%d]' % (p.name, bit_offset)
                entries.append('  {"name":"%s","pin":%d,"bit":%d,"dir":"input"}'
                               % (name, pin, p.lsb + bit_offset))
                if clk_signal and p.name == clk_signal and clk_pin == 0:
                    clk_pin = pin
                pin += 1
        for p in self.outputs:
            for bit_offset in range(p.width):
                name = p.name if p.width == 1 else '%s[%d]' % (p.name, bit_offset)
                entries.append('  {"name":"%s","pin":%d,"bit":%d,"dir":"output"}'
                               % (name, pin, p.lsb + bit_offset))
                pin += 1
        raw_json = '[\n' + ',\n'.join(entries) + '\n]'

        c_json = []
        for line in raw_json.split('\n'):
            escaped = line.replace('\\', '\\\\').replace('"', '\\"')
            c_json.append('    "%s\\n"' % escaped)
        pinmap_literal = '\n'.join(c_json)

        lines = []
        lines.append('#include <stdio.h>')
        lines.append('#include <pthread.h>')
        lines.append('#include <signal.h>')
        lines.append('')
        lines.append('#include <stdlib.h>')
        lines.append('#include "hal_gpio.h"')
        lines.append('#include "hal_timer.h"')
        lines.append('#include "hal_stimulus.h"')
        lines.append('#include "emulator.h"')
        lines.append('#include "telemetry.h"')
        lines.append('#include "vcd_writer.h"')
        lines.append('')
        lines.append('void circuit_init(model_state_t *state);')
        lines.append('void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs);')
        lines.append('')
        lines.append('#define VCD_REG_COUNT %d' % (len(self.regs) + len(self._edge_regs)))
        lines.append('')
        lines.append('static const char *pinmap_json =')
        lines.append(pinmap_literal + ';')
        lines.append('')
        lines.append('static emulator_config_t emu_cfg;')
        lines.append('static vcd_writer_t vcd;')
        lines.append('static void _vcd_atexit(void) { vcd_close(&vcd); }')
        lines.append('static void _sig_handler(int sig) { (void)sig; exit(0); }')
        lines.append('')
        lines.append('int main(void)')
        lines.append('{')
        lines.append('    hal_gpio_init();')
        if clk_pin > 0:
            lines.append('    hal_gpio_set_clk(%d, 100000);' % clk_pin)
        lines.append('    hal_timer_init();')
        lines.append('    signal(SIGINT, _sig_handler);')
        lines.append('    signal(SIGTERM, _sig_handler);')
        lines.append('    telemetry_init(115200);')
        lines.append('')
        lines.append('    telemetry_send_string("uFPGA-Emu v1.0 - PC Simulation (%s)\\n");'
                      % self.module.name)
        lines.append('')
        lines.append('    pin_map_load(&emu_cfg.pin_map, pinmap_json);')
        lines.append('    {')
        lines.append('        const char *csv = getenv("STIMULUS_CSV");')
        lines.append('        if (csv) hal_stimulus_load(csv, &emu_cfg.pin_map);')
        lines.append('    }')
        lines.append('    {')
        lines.append('        const char *vcd_path = getenv("VCD_OUT");')
        lines.append('        if (vcd_path && vcd_init(&vcd, vcd_path, &emu_cfg.pin_map, VCD_REG_COUNT, 0) == 0) {')
        lines.append('            emu_cfg.vcd = &vcd;')
        lines.append('            atexit(_vcd_atexit);')
        lines.append('        }')
        lines.append('    }')
        lines.append('    emu_cfg.init_fn  = circuit_init;')
        lines.append('    emu_cfg.eval_fn  = circuit_eval;')
        lines.append('    emu_cfg.target_freq_hz = 100000;')
        lines.append('')
        lines.append('    emulator_init(&emu_cfg);')
        lines.append('')
        lines.append('    pthread_t emu_thread;')
        lines.append('    pthread_create(&emu_thread, NULL, (void *(*)(void *))emulator_run_core1, &emu_cfg);')
        lines.append('')
        lines.append('    telemetry_run_core0(&emu_cfg);')
        lines.append('')
        lines.append('    pthread_join(emu_thread, NULL);')
        lines.append('    vcd_close(&vcd);')
        lines.append('    return 0;')
        lines.append('}')
        return '\n'.join(lines) + '\n'

    def _gen_functions(self):
        for func in self.module.functions:
            params = []
            local_vars: set[str] = set()
            for p in func.ports:
                params.append('uint32_t %s' % p.name)
                local_vars.add(p.name)
            for s in func.locals:
                local_vars.add(s.name)
            ret_type = 'uint32_t'
            self._emit('static inline %s %s(%s)' %
                       (ret_type, func.name, ', '.join(params)))
            self._emit('{')
            self.indent += 1
            old_local = self._local_vars
            old_return = self._func_return_name
            old_return_mask = self._func_return_mask
            self._local_vars = local_vars
            self._func_return_name = func.name
            if func.return_msb is not None and func.return_lsb is not None:
                width = func.return_msb - func.return_lsb + 1
                self._func_return_mask = '0x%X' % ((1 << width) - 1) if width < 32 else None
            else:
                self._func_return_mask = None
            for s in func.locals:
                self._emit('uint32_t %s = 0;' % s.name)
            self._gen_stmts(func.statements, clocked=False, guarded=False)
            self._func_return_name = old_return
            self._func_return_mask = old_return_mask
            self._local_vars = old_local
            self.indent -= 1
            self._emit('}')
            self._emit()

    def _gen_function_prototypes(self):
        for func in self.module.functions:
            params = ['uint32_t %s' % p.name for p in func.ports]
            self._emit('static inline uint32_t %s(%s);' % (func.name, ', '.join(params)))
        if self.module.functions:
            self._emit()

    def _gen_tasks(self):
        for task in self.module.tasks:
            params = ['model_state_t *state']
            local_vars: set[str] = set()
            local_out_ports: dict[str, str] = {}
            for p in task.ports:
                if p.direction == 'input':
                    params.append('uint32_t %s' % p.name)
                    local_vars.add(p.name)
                else:
                    params.append('uint32_t *%s' % p.name)
                    local_vars.add(p.name)
                    local_out_ports[p.name] = '*%s' % p.name
            for s in task.locals:
                local_vars.add(s.name)
            self._emit('static void %s(%s)' %
                       (task.name, ', '.join(params)))
            self._emit('{')
            self.indent += 1
            old_local = self._local_vars
            old_out = self._local_out_ports
            self._local_vars = local_vars
            self._local_out_ports = local_out_ports
            for s in task.locals:
                self._emit('uint32_t %s = 0;' % s.name)
            self._gen_stmts(task.statements, clocked=False, guarded=False)
            self._local_out_ports = old_out
            self._local_vars = old_local
            self.indent -= 1
            self._emit('}')
            self._emit()

    def _gen_task_enable(self, stmt: TaskEnableStatement):
        task = None
        for t in self.module.tasks:
            if t.name == stmt.name:
                task = t
                break
        if task is None:
            self._emit('%s(%s);' % (stmt.name, ', '.join(stmt.args)))
            return
        args = ['state']
        for i, p in enumerate(task.ports):
            arg = self._rewrite(stmt.args[i]) if i < len(stmt.args) else '0'
            if p.direction == 'input':
                args.append(arg)
            else:
                args.append('&' + arg)
        self._emit('%s(%s);' % (stmt.name, ', '.join(args)))

    def _gen_init(self):
        self._emit('void circuit_init(model_state_t *state)')
        self._emit('{')
        self.indent += 1
        for i in range(len(self.regs) + len(self._edge_regs)):
            self._emit('state->regs[%d] = 0;' % i)
        self._emit('state->outputs = 0;')
        self._emit('state->clock_count = 0;')
        self.indent -= 1
        self._emit('}')
        self._emit()

    def _gen_eval(self):
        self._emit('void circuit_eval(model_state_t *state, uint32_t inputs, uint32_t *outputs)')
        self._emit('{')
        self.indent += 1

        for p in self.inputs:
            if p.width == 1:
                self._emit('uint32_t %s = GET_BIT(inputs, %d);' % (p.name, p.lsb))
            else:
                mask = (1 << p.width) - 1
                self._emit('uint32_t %s = ((inputs >> %d) & 0x%Xu);' % (p.name, p.lsb, mask))

        # Initialize outputs to 0 before any continuous assign or reg packing
        self._emit('*outputs = 0;')

        # Generate edge detection for ALL signals before any always block
        # so multiple blocks sharing the same clock get consistent edge values
        edge_vars_global: list[str] = []
        edge_updates: list[tuple[str, str, int]] = []  # (var_name, rhs, old_idx)
        for block in self.module.always_blocks:
            if block.is_auto:
                continue
            for item in block.sensitivity:
                if item.edge not in ('posedge', 'negedge'):
                    continue
                var_name = '%s_%s' % (item.signal,
                                      'rise' if item.edge == 'posedge' else 'fall')
                if var_name in edge_vars_global:
                    continue
                edge_val = '1' if item.edge == 'posedge' else '0'
                old_idx = self._reg_idx(item.signal + '_old')
                edge_rhs = item.signal
                emask = self._reg_mask.get(old_idx)
                if emask:
                    edge_rhs = '(%s) & %s' % (edge_rhs, emask)
                edge_rhs = self._fold_constants(edge_rhs)
                self._emit('uint8_t %s = (%s == %s) && (state->regs[%d] != %s);' %
                          (var_name, item.signal, edge_val, old_idx, edge_val))
                edge_vars_global.append(var_name)
                edge_updates.append((var_name, edge_rhs, old_idx))

        sorted_blocks = self._topological_sort()
        for block in sorted_blocks:
            self._gen_always(block, edge_vars_global)

        # Declare local variables for wire signals
        wire_regs = {r.name for r in self.regs}
        wire_names = set()
        for s in self.module.signals:
            if s.sig_type == 'wire' and s.name not in wire_regs:
                wire_names.add(s.name)
        for name in sorted(wire_names):
            self._emit('uint32_t %s;' % name)

        # Generate continuous assigns (from wire assignments and inlined connections)
        # Emit simple wire assigns first (plain identifier LHS), then output bit assigns
        wire_assigns = []
        bit_assigns = []
        for ca in self.module.continuous_assigns:
            idx = self._reg_idx(ca.lhs)
            if idx >= 0 or (not ca.lhs.startswith('GET_BIT') and not ca.lhs.startswith('GET_BITS')):
                wire_assigns.append(ca)
            else:
                bit_assigns.append(ca)
        for ca in wire_assigns + bit_assigns:
            lhs = ca.lhs
            rhs = self._rewrite(ca.rhs)
            # If lhs is a reg, rewrite to its register
            idx = self._reg_idx(lhs)
            if idx >= 0:
                self._emit('state->regs[%d] = %s;' % (idx, rhs))
                continue
            # Handle GET_BIT(port, bit) = expr  → write to output bit
            m = re.match(r'GET_BIT\((\w+),\s*(\d+)\)', lhs)
            if m:
                port_name = m.group(1)
                bit = int(m.group(2))
                for p in self.outputs:
                    if p.name == port_name:
                        out_bit = p.lsb + bit
                        rhs = self._fold_constants(rhs)
                        if out_bit == 0:
                            self._emit('*outputs |= (%s & 1u);' % rhs)
                        else:
                            self._emit('*outputs |= ((%s & 1u) << %d);' %
                                      (rhs, out_bit))
                        break
                continue
            # Handle GET_BITS(port, msb, lsb) = expr → write to output bits
            m = re.match(r'GET_BITS\((\w+),\s*(\d+),\s*(\d+)\)', lhs)
            if m:
                port_name = m.group(1)
                msb = int(m.group(2))
                lsb = int(m.group(3))
                w = msb - lsb + 1
                for p in self.outputs:
                    if p.name == port_name:
                        out_lsb = p.lsb + lsb
                        mask = ((1 << w) - 1)
                        rhs = self._fold_constants(rhs)
                        if out_lsb == 0:
                            self._emit('*outputs |= (%s & %du);' %
                                      (rhs, mask))
                        else:
                            self._emit('*outputs |= ((%s & %du) << %d);' %
                                      (rhs, mask, out_lsb))
                        break
                continue
            # Fallback: just emit the assignment (may not be valid C)
            self._emit('%s = %s;' % (lhs, rhs))

        # Update old registers after all blocks have used them
        for _var_name, edge_rhs, old_idx in edge_updates:
            self._emit('state->regs[%d] = %s;' % (old_idx, edge_rhs))

        # Reg-based output packing (wire outputs set via *outputs |= in CAs above)
        for p in self.outputs:
            idx = self._reg_idx(p.name)
            if idx >= 0:
                val = 'state->regs[%d]' % idx
                mask = self._reg_mask.get(idx)
                if mask:
                    val = '(%s & %s)' % (val, mask)
                if p.lsb == 0:
                    self._emit('*outputs |= %s;' % val)
                else:
                    self._emit('*outputs |= ((%s) << %d);' % (val, p.lsb))

        self.indent -= 1
        self._emit('}')
        self._emit()

    def _gen_always(self, block: AlwaysBlock, global_edge_vars: list[str] = None):
        if block.is_auto:
            self._gen_stmts(block.statements, clocked=False, guarded=False)
            return

        # Look up edge vars from the global set computed in _gen_eval
        edge_vars = []
        for item in block.sensitivity:
            if item.edge not in ('posedge', 'negedge'):
                continue
            var_name = '%s_%s' % (item.signal,
                                  'rise' if item.edge == 'posedge' else 'fall')
            if global_edge_vars is None or var_name in global_edge_vars:
                edge_vars.append(var_name)

        if edge_vars:
            combined = ' || '.join(edge_vars)
            self._emit('if (%s) {' % combined)
            self.indent += 1
            self._gen_stmts(block.statements, clocked=True, guarded=True)
            self.indent -= 1
            self._emit('}')
        else:
            self._gen_stmts(block.statements, clocked=False, guarded=False)

    def _gen_stmts(self, stmts: list, clocked: bool, guarded: bool):
        for stmt in stmts:
            if isinstance(stmt, AssignStatement):
                self._gen_assign(stmt, clocked, guarded)
            elif isinstance(stmt, IfStatement):
                self._gen_if(stmt, clocked, guarded)
            elif isinstance(stmt, CaseStatement):
                self._gen_case(stmt, clocked, guarded)
            elif isinstance(stmt, ForStatement):
                self._gen_for(stmt, clocked, guarded)
            elif isinstance(stmt, RepeatStatement):
                self._gen_repeat(stmt, clocked, guarded)
            elif isinstance(stmt, TaskEnableStatement):
                self._gen_task_enable(stmt)

    def _gen_assign(self, stmt: AssignStatement, clocked: bool, guarded: bool):
        rhs = self._rewrite(stmt.rhs)

        # Function return: assign to function name → emit return
        if self._func_return_name and stmt.lhs == self._func_return_name:
            if self._func_return_mask:
                rhs = self._fold_constants(f'({rhs}) & {self._func_return_mask}u')
            self._emit('return %s;' % rhs)
            return

        # Task output port: dereference pointer
        if stmt.lhs in self._local_out_ports:
            self._emit('%s = %s;' % (self._local_out_ports[stmt.lhs], rhs))
            return

        # Part-select on LHS: extended[7:4] = expr → read-modify-write
        if stmt.lhs_msb is not None:
            idx = self._reg_idx(stmt.lhs)
            if idx >= 0:
                msb_str = self._rewrite(stmt.lhs_msb)
                lsb_str = self._rewrite(stmt.lhs_lsb) if stmt.lhs_lsb is not None else msb_str
                try:
                    msb = int(msb_str, 0)
                    lsb = int(lsb_str, 0)
                except (ValueError, TypeError):
                    pass
                else:
                    width = msb - lsb + 1
                    rhs_part = f'({rhs} & 0x{(1<<width)-1:X}u)'
                    if lsb > 0:
                        rhs_part = f'({rhs_part} << {lsb})'
                    rhs_part = self._fold_constants(rhs_part)
                    full = f'(state->regs[{idx}] & ~0x{((1<<width)-1) << lsb:X}u) | {rhs_part}'
                    if stmt.is_nonblocking and clocked and not guarded:
                        self._emit('if (clk_edge)')
                        self._emit('    state->regs[%d] = %s;' % (idx, full))
                    else:
                        self._emit('state->regs[%d] = %s;' % (idx, full))
                    return

        idx = self._reg_idx(stmt.lhs)
        mask = self._reg_mask.get(idx)
        if mask:
            rhs = '(%s) & %s' % (rhs, mask)
        rhs = self._fold_constants(rhs)

        if stmt.is_nonblocking and clocked and not guarded:
            self._emit('if (clk_edge)')
            self._emit('    state->regs[%d] = %s;' % (idx, rhs))
        else:
            self._emit('state->regs[%d] = %s;' % (idx, rhs))

    def _gen_if(self, stmt: IfStatement, clocked: bool, guarded: bool):
        cond = self._rewrite(stmt.condition)
        self._emit('if (%s) {' % cond)
        self.indent += 1
        self._gen_stmts(stmt.if_branch, clocked, guarded)
        self.indent -= 1
        if stmt.else_branch:
            self._emit('} else {')
            self.indent += 1
            self._gen_stmts(stmt.else_branch, clocked, guarded)
            self.indent -= 1
        self._emit('}')

    def _gen_case(self, stmt: CaseStatement, clocked: bool, guarded: bool):
        expr = self._rewrite(stmt.expression)
        opened = False
        if clocked and not guarded:
            self._emit('if (clk_edge) {')
            self.indent += 1
            opened = True
        self._emit('switch (%s) {' % expr)
        self.indent += 1
        for item in stmt.items:
            for val in item.values:
                if val == 'default':
                    self._emit('default:')
                else:
                    self._emit('case %s:' % self._rewrite(val))
            self.indent += 1
            self._gen_stmts(item.statements, clocked, guarded or opened)
            self._emit('break;')
            self.indent -= 1
        self.indent -= 1
        self._emit('}')
        if opened:
            self.indent -= 1
            self._emit('}')

    def _gen_for(self, stmt: ForStatement, clocked: bool, guarded: bool):
        opened = False
        if clocked and not guarded:
            self._emit('if (clk_edge) {')
            self.indent += 1
            opened = True
        cond = self._rewrite(stmt.condition)
        step = self._rewrite(stmt.step)
        self._emit('for (int %s = %s; %s; %s = %s) {' %
                   (stmt.var, stmt.start, cond, stmt.var, step))
        self.indent += 1
        self._gen_stmts(stmt.statements, clocked, guarded or opened)
        self.indent -= 1
        self._emit('}')
        if opened:
            self.indent -= 1
            self._emit('}')

    def _gen_repeat(self, stmt: RepeatStatement, clocked: bool, guarded: bool):
        opened = False
        if clocked and not guarded:
            self._emit('if (clk_edge) {')
            self.indent += 1
            opened = True
        count = self._rewrite(stmt.count)
        self._emit('for (int __repeat_i = 0; __repeat_i < %s; __repeat_i++) {' % count)
        self.indent += 1
        self._gen_stmts(stmt.statements, clocked, guarded or opened)
        self.indent -= 1
        self._emit('}')
        if opened:
            self.indent -= 1
            self._emit('}')
