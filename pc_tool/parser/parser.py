from .lexer import Token, TokenType, tokenize
from .ast import (Module, Port, Signal, AlwaysBlock, SensitivityItem,
                  AssignStatement, IfStatement, CaseItem, CaseStatement,
                  ForStatement, RepeatStatement, ContinuousAssign, Parameter,
                  Instance, TaskDecl, FunctionDecl, TaskEnableStatement,
                  FuncCallExpression)


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self._number_widths: dict[str, int] = {}
        self._genvar_values: dict[str, int] = {}
        self._routine_kind: str | None = None

    def peek(self) -> TokenType:
        return self.tokens[self.pos].type

    def peek_value(self) -> str:
        return self.tokens[self.pos].value

    def advance(self) -> Token:
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def expect(self, *types: TokenType) -> Token:
        if self.peek() not in types:
            got = self.peek().name if self.pos < len(self.tokens) else 'EOF'
            expected = ', '.join(t.name for t in types)
            tok = self.tokens[self.pos]
            raise ParseError(f'Line {tok.line}: Expected {expected}, got {got} ({tok.value!r})')
        return self.advance()

    def skip_semicolon(self):
        self.expect(TokenType.SEMICOLON)

    def parse_module(self) -> Module:
        self.expect(TokenType.MODULE)
        name = self.expect(TokenType.IDENTIFIER).value
        mod = Module(name=name)
        self._current_mod = mod

        # Optional parameter list: #(parameter NAME = expr, ...)
        if self.peek() == TokenType.HASH:
            self.advance()
            self.expect(TokenType.LPAREN)
            while self.peek() not in (TokenType.RPAREN, TokenType.EOF):
                if self.peek() in (TokenType.PARAMETER, TokenType.LOCALPARAM):
                    self.advance()
                # Optional [msb:lsb] range — skip
                if self.peek() == TokenType.LBRACKET:
                    self.advance()
                    self._parse_expression()
                    self.expect(TokenType.COLON)
                    self._parse_expression()
                    self.expect(TokenType.RBRACKET)
                pname = self.expect(TokenType.IDENTIFIER).value
                self.expect(TokenType.BLOCKING_ASSIGN)
                pexpr = self._parse_expression()
                pval = self._eval_expr(mod, pexpr)
                mod.parameters.append(Parameter(name=pname, value=pval))
                if self.peek() == TokenType.COMMA:
                    self.advance()
            self.expect(TokenType.RPAREN)

        # Port list (ANSI-style: input wire clk, output reg led, ...)
        self.expect(TokenType.LPAREN)
        cur_direction = None
        cur_msb = None
        cur_lsb = None
        while self.peek() not in (TokenType.RPAREN, TokenType.EOF):
            if self.peek() == TokenType.COMMA:
                self.advance()
                continue

            if self.peek() in (TokenType.INPUT, TokenType.OUTPUT, TokenType.INOUT):
                cur_direction = self.advance().value
                if self.peek() in (TokenType.WIRE, TokenType.REG):
                    self.advance()
                # Parse a single name with optional range
                p = self._parse_one_signal(mod, cur_direction)
                cur_msb = p.msb
                cur_lsb = p.lsb
            else:
                port_name = self.expect(TokenType.IDENTIFIER).value
                p = Port(name=port_name, direction=cur_direction or 'inout',
                         msb=cur_msb, lsb=cur_lsb)

            found = False
            for existing in mod.ports:
                if existing.name == p.name:
                    existing.direction = p.direction
                    existing.msb = p.msb
                    existing.lsb = p.lsb
                    found = True
                    break
            if not found:
                mod.ports.append(p)
            if p.direction == 'output':
                mod.signals.append(Signal(name=p.name, sig_type='reg',
                                          msb=p.msb, lsb=p.lsb))
        self.expect(TokenType.RPAREN)
        if self.peek() == TokenType.SEMICOLON:
            self.advance()

        # Parse body
        while self.peek() not in (TokenType.ENDMODULE, TokenType.EOF):
            self._parse_declaration(mod)

        self.expect(TokenType.ENDMODULE)
        return mod

    def _parse_one_signal(self, mod: Module, direction: str | None = None) -> Port:
        """Parse [msb:lsb]? name and return a single Port."""
        msb = None
        lsb = None
        if self.peek() == TokenType.LBRACKET:
            self.advance()
            msb_expr = self._parse_expression()
            self.expect(TokenType.COLON)
            lsb_expr = self._parse_expression()
            self.expect(TokenType.RBRACKET)
            msb = self._eval_expr(mod, msb_expr)
            lsb = self._eval_expr(mod, lsb_expr)
        name = self.expect(TokenType.IDENTIFIER).value
        return Port(name=name, direction=direction or 'inout', msb=msb, lsb=lsb)

    def _parse_signal_decls(self, mod: Module, direction: str | None = None) -> list[Port]:
        """Parse [msb:lsb]? name (, name)* and consume semicolon."""
        items = []
        first = self._parse_one_signal(mod, direction)
        items.append(first)
        msb = first.msb
        lsb = first.lsb
        while self.peek() == TokenType.COMMA and self._peek_is_next_ident():
            self.advance()
            sig = self._parse_one_signal(mod, direction)
            if sig.msb is None and msb is not None:
                sig.msb = msb
                sig.lsb = lsb
            items.append(sig)
        return items

    def _peek_is_next_ident(self) -> bool:
        saved = self.pos
        if self.peek() != TokenType.COMMA:
            return False
        self.advance()
        is_ident = self.peek() == TokenType.IDENTIFIER
        self.pos = saved
        return is_ident

    def _parse_declaration(self, mod: Module):
        tok_type = self.peek()

        if tok_type == TokenType.INPUT:
            self.advance()
            if self.peek() in (TokenType.WIRE, TokenType.REG):
                self.advance()
            ports = self._parse_port_or_signal_list(mod, 'input')

        elif tok_type == TokenType.OUTPUT:
            self.advance()
            has_reg = self.peek() == TokenType.REG
            if has_reg:
                self.advance()
            elif self.peek() == TokenType.WIRE:
                self.advance()
            ports = self._parse_port_or_signal_list(mod, 'output')
            for p in ports:
                p.direction = 'output'
                if has_reg:
                    mod.signals.append(Signal(name=p.name, sig_type='reg',
                                              msb=p.msb, lsb=p.lsb))

        elif tok_type == TokenType.INOUT:
            self.advance()
            ports = self._parse_port_or_signal_list(mod, 'inout')

        elif tok_type == TokenType.WIRE:
            self.advance()
            sigs = self._parse_port_or_signal_list(mod, None)
            for s in sigs:
                mod.signals.append(Signal(name=s.name, sig_type='wire',
                                          msb=s.msb, lsb=s.lsb))

        elif tok_type == TokenType.REG:
            self.advance()
            sigs = self._parse_port_or_signal_list(mod, None)
            for s in sigs:
                mod.signals.append(Signal(name=s.name, sig_type='reg',
                                          msb=s.msb, lsb=s.lsb))

        elif tok_type == TokenType.GENERATE:
            self.advance()
            self._parse_generate_block(mod)

        elif tok_type == TokenType.GENVAR:
            self._parse_genvar_decl(mod)

        elif tok_type == TokenType.INTEGER:
            self.advance()
            # integer vars are local loop variables, not state registers
            while True:
                self.expect(TokenType.IDENTIFIER)
                if self.peek() != TokenType.COMMA:
                    break
                self.advance()
            self.skip_semicolon()

        elif tok_type == TokenType.ALWAYS:
            self._parse_always(mod)

        elif tok_type == TokenType.ASSIGN:
            self.advance()
            lhs = self.expect(TokenType.IDENTIFIER).value
            # check for part select: [idx] or [msb:lsb]
            if self.peek() == TokenType.LBRACKET:
                self.advance()
                idx = self._parse_expression()
                if self.peek() == TokenType.COLON:
                    self.advance()
                    lsb = self._parse_expression()
                    self.expect(TokenType.RBRACKET)
                    lhs = f'GET_BITS({lhs}, {idx}, {lsb})'
                else:
                    self.expect(TokenType.RBRACKET)
                    lhs = f'GET_BIT({lhs}, {idx})'
            self.expect(TokenType.BLOCKING_ASSIGN)
            rhs = self._parse_expression()
            self.skip_semicolon()
            mod.continuous_assigns.append(ContinuousAssign(lhs, rhs))

        elif tok_type in (TokenType.PARAMETER, TokenType.LOCALPARAM):
            is_local = tok_type == TokenType.LOCALPARAM
            self.advance()
            # Optional [msb:lsb] range — skip
            if self.peek() == TokenType.LBRACKET:
                self.advance()
                self._parse_expression()
                self.expect(TokenType.COLON)
                self._parse_expression()
                self.expect(TokenType.RBRACKET)
            while True:
                pname = self.expect(TokenType.IDENTIFIER).value
                self.expect(TokenType.BLOCKING_ASSIGN)
                pexpr = self._parse_expression()
                pval = self._eval_expr(mod, pexpr)
                mod.parameters.append(Parameter(name=pname, value=pval, is_local=is_local))
                if self.peek() == TokenType.COMMA:
                    self.advance()
                    continue
                break
            self.skip_semicolon()

        elif tok_type == TokenType.TASK:
            self._parse_task(mod)

        elif tok_type == TokenType.FUNCTION:
            self._parse_function(mod)

        elif tok_type == TokenType.IDENTIFIER:
            self._parse_instantiation(mod)

        else:
            raise ParseError(f'Line {self.tokens[self.pos].line}: Unexpected token '
                              f'{tok_type.name} ({self.tokens[self.pos].value!r})')

    def _parse_task(self, mod: Module):
        """Parse task [automatic] name; [port_decls] [reg_decls] begin...end endtask"""
        self.advance()  # task
        is_automatic = False
        if self.peek() == TokenType.AUTOMATIC:
            self.advance()
            is_automatic = True
        name = self.expect(TokenType.IDENTIFIER).value
        task_decl = TaskDecl(name=name, is_automatic=is_automatic)
        self.skip_semicolon()
        # Parse port declarations (input/output/inout) and reg declarations
        while self.peek() not in (TokenType.BEGIN, TokenType.ENDTASK, TokenType.EOF):
            if self.peek() == TokenType.INPUT:
                self.advance()
                sigs = self._parse_signal_decls(mod, 'input')
                self.skip_semicolon()
                for s in sigs:
                    s.direction = 'input'
                task_decl.ports.extend(sigs)
            elif self.peek() == TokenType.OUTPUT:
                self.advance()
                sigs = self._parse_signal_decls(mod, 'output')
                self.skip_semicolon()
                for s in sigs:
                    s.direction = 'output'
                task_decl.ports.extend(sigs)
            elif self.peek() == TokenType.INOUT:
                self.advance()
                sigs = self._parse_signal_decls(mod, 'inout')
                self.skip_semicolon()
                for s in sigs:
                    s.direction = 'inout'
                task_decl.ports.extend(sigs)
            elif self.peek() == TokenType.REG:
                self.advance()
                sigs = self._parse_signal_decls(mod, None)
                self.skip_semicolon()
                for s in sigs:
                    task_decl.locals.append(Signal(name=s.name, sig_type='reg', msb=s.msb, lsb=s.lsb))
            elif self.peek() == TokenType.INTEGER:
                self.advance()
                self.expect(TokenType.IDENTIFIER)
                self.skip_semicolon()
            else:
                raise ParseError(f'Line {self.tokens[self.pos].line}: '
                                f'Unexpected token in task body: {self.peek().name}')
        # Parse body statements
        if self.peek() == TokenType.BEGIN:
            old_kind = self._routine_kind
            self._routine_kind = 'task'
            self._parse_statement_block(task_decl.statements, mod)
            self._routine_kind = old_kind
        self.expect(TokenType.ENDTASK)
        mod.tasks.append(task_decl)

    def _parse_function(self, mod: Module):
        """Parse function [automatic] [range] name; [input_decls] [reg_decls] begin...end endfunction"""
        self.advance()  # function
        is_automatic = False
        if self.peek() == TokenType.AUTOMATIC:
            self.advance()
            is_automatic = True
        # Optional range: [msb:lsb]
        return_msb = None
        return_lsb = None
        if self.peek() == TokenType.LBRACKET:
            self.advance()
            return_msb_expr = self._parse_expression()
            self.expect(TokenType.COLON)
            return_lsb_expr = self._parse_expression()
            self.expect(TokenType.RBRACKET)
            try:
                return_msb = int(return_msb_expr)
                return_lsb = int(return_lsb_expr)
            except ValueError:
                pass
        name = self.expect(TokenType.IDENTIFIER).value
        func_decl = FunctionDecl(name=name, return_msb=return_msb, return_lsb=return_lsb,
                                 is_automatic=is_automatic)
        self.skip_semicolon()
        # Parse input declarations and reg declarations
        while self.peek() not in (TokenType.BEGIN, TokenType.ENDFUNCTION, TokenType.EOF):
            if self.peek() == TokenType.INPUT:
                self.advance()
                sigs = self._parse_signal_decls(mod, 'input')
                self.skip_semicolon()
                for s in sigs:
                    s.direction = 'input'
                func_decl.ports.extend(sigs)
            elif self.peek() == TokenType.REG:
                self.advance()
                sigs = self._parse_signal_decls(mod, None)
                self.skip_semicolon()
                for s in sigs:
                    func_decl.locals.append(Signal(name=s.name, sig_type='reg', msb=s.msb, lsb=s.lsb))
            elif self.peek() == TokenType.INTEGER:
                self.advance()
                self.expect(TokenType.IDENTIFIER)
                self.skip_semicolon()
            else:
                raise ParseError(f'Line {self.tokens[self.pos].line}: '
                                f'Unexpected token in function body: {self.peek().name}')
        # Parse body statements
        if self.peek() == TokenType.BEGIN:
            old_kind = self._routine_kind
            self._routine_kind = 'function'
            self._parse_statement_block(func_decl.statements, mod)
            self._routine_kind = old_kind
        self.expect(TokenType.ENDFUNCTION)
        mod.functions.append(func_decl)

    def _parse_genvar_decl(self, mod: Module):
        """Parse genvar name (, name)* ;"""
        self.advance()  # genvar
        while True:
            self.expect(TokenType.IDENTIFIER)  # name
            if self.peek() != TokenType.COMMA:
                break
            self.advance()
        self.skip_semicolon()

    def _parse_generate_block(self, mod: Module):
        """Parse items inside a generate block until endgenerate."""
        while self.peek() not in (TokenType.ENDGENERATE, TokenType.EOF):
            self._parse_generate_item_sub(mod)
        self.expect(TokenType.ENDGENERATE)

    def _parse_generate_if(self, mod: Module):
        """Parse generate if(cond) ... else ... and include only active branch."""
        self.expect(TokenType.IF)
        self.expect(TokenType.LPAREN)
        cond_str = self._parse_expression()
        self.expect(TokenType.RPAREN)

        cond_true = bool(self._eval_expr(mod, cond_str))

        # Parse if-branch
        self._parse_generate_item(mod, cond_true)

        # Parse optional else-branch
        if self.peek() == TokenType.ELSE:
            self.advance()
            self._parse_generate_item(mod, not cond_true)

    def _parse_generate_item(self, mod: Module, active: bool):
        """Parse a single generate item (begin...end block or single decl)."""
        if active:
            if self.peek() == TokenType.BEGIN:
                self.advance()
                while self.peek() not in (TokenType.END, TokenType.ENDGENERATE, TokenType.EOF):
                    self._parse_generate_item_sub(mod)
                self.expect(TokenType.END)
            elif self.peek() == TokenType.GENERATE:
                self.advance()
                self._parse_generate_block(mod)
            else:
                self._parse_generate_item_sub(mod)
        else:
            self._skip_generate_item()

    def _parse_generate_item_sub(self, mod: Module):
        """Parse one item inside a generate block, dispatching nested generates."""
        tok = self.peek()
        if tok == TokenType.GENERATE:
            self.advance()
            self._parse_generate_block(mod)
            return
        if tok == TokenType.IF:
            self._parse_generate_if(mod)
        elif tok == TokenType.FOR:
            self._parse_generate_for(mod)
        elif tok == TokenType.CASE:
            self._parse_generate_case(mod)
        elif tok == TokenType.GENVAR:
            self._parse_genvar_decl(mod)
        else:
            self._parse_declaration(mod)

    def _skip_generate_item(self):
        """Skip one generate item without parsing it."""
        if self.peek() == TokenType.BEGIN:
            depth = 1
            self.advance()
            while depth > 0 and self.peek() != TokenType.EOF:
                t = self.advance()
                if t.type == TokenType.BEGIN:
                    depth += 1
                elif t.type == TokenType.END:
                    depth -= 1
        elif self.peek() == TokenType.GENERATE:
            self.advance()
            depth = 1
            while depth > 0 and self.peek() != TokenType.EOF:
                if self.peek() == TokenType.GENERATE:
                    self.advance()
                    depth += 1
                elif self.peek() == TokenType.ENDGENERATE:
                    self.advance()
                    depth -= 1
                else:
                    self._skip_generate_item()
        elif self.peek() == TokenType.IF:
            self.advance()
            self._skip_to_rparen()
            self._skip_generate_item()
            if self.peek() == TokenType.ELSE:
                self.advance()
                self._skip_generate_item()
        elif self.peek() == TokenType.FOR:
            self.advance()
            self._skip_to_rparen()
            self._skip_generate_item()
        elif self.peek() == TokenType.ALWAYS:
            self.advance()
            if self.peek() == TokenType.AT:
                self.advance()
                if self.peek() == TokenType.LPAREN:
                    self._skip_to_rparen()
                elif self.peek() == TokenType.MUL:
                    self.advance()
            if self.peek() == TokenType.BEGIN:
                depth = 1
                self.advance()
                while depth > 0 and self.peek() != TokenType.EOF:
                    t = self.advance()
                    if t.type == TokenType.BEGIN:
                        depth += 1
                    elif t.type == TokenType.END:
                        depth -= 1
            else:
                self._skip_to_semicolon()
        elif self.peek() == TokenType.CASE:
            self.advance()
            self._skip_to_rparen()
            while self.peek() not in (TokenType.ENDCASE, TokenType.ENDGENERATE, TokenType.EOF):
                self._skip_generate_item()
            if self.peek() == TokenType.ENDCASE:
                self.advance()
        elif self.peek() == TokenType.ENDGENERATE:
            pass
        else:
            self._skip_to_semicolon()

    def _skip_to_rparen(self):
        """Skip tokens until matching )."""
        depth = 1
        self.expect(TokenType.LPAREN)
        while depth > 0 and self.peek() != TokenType.EOF:
            t = self.advance()
            if t.type == TokenType.LPAREN:
                depth += 1
            elif t.type == TokenType.RPAREN:
                depth -= 1

    def _skip_to_semicolon(self):
        """Skip tokens until ; handling nested begin/end."""
        depth = 0
        while self.peek() not in (TokenType.SEMICOLON, TokenType.ENDGENERATE, TokenType.EOF):
            if self.peek() == TokenType.BEGIN:
                self.advance()
                depth += 1
            elif self.peek() == TokenType.END:
                self.advance()
                if depth > 0:
                    depth -= 1
                else:
                    break
            else:
                self.advance()
        if self.peek() == TokenType.SEMICOLON and depth == 0:
            self.advance()

    def _skip_to_semicolon_or_end(self):
        """Skip tokens until ; or end/endgenerate."""
        while self.peek() not in (TokenType.SEMICOLON, TokenType.END, TokenType.ENDCASE,
                                   TokenType.ENDGENERATE, TokenType.EOF):
            self.advance()
        if self.peek() == TokenType.SEMICOLON:
            self.advance()

    def _parse_generate_for(self, mod: Module):
        """Parse generate for(genvar i = start; cond; i = step) and unroll."""
        self.expect(TokenType.FOR)
        self.expect(TokenType.LPAREN)
        if self.peek() == TokenType.GENVAR:
            self.advance()
        var_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.BLOCKING_ASSIGN)
        start_str = self._parse_expression()
        self.expect(TokenType.SEMICOLON)
        cond_str = self._parse_expression()
        self.expect(TokenType.SEMICOLON)
        self.expect(TokenType.IDENTIFIER)  # var name again
        self.expect(TokenType.BLOCKING_ASSIGN)
        step_str = self._parse_expression()
        self.expect(TokenType.RPAREN)

        self._genvar_values[var_name] = 0
        start = self._eval_expr(mod, start_str)
        step = self._eval_expr(mod, step_str)
        del self._genvar_values[var_name]

        # Parse body once into a temp module (for structure), then unroll
        self.expect(TokenType.BEGIN)

        temp_mod = Module(name='__gen_body__')
        while self.peek() not in (TokenType.END, TokenType.ENDGENERATE, TokenType.EOF):
            self._parse_generate_item_sub(temp_mod)
        self.expect(TokenType.END)

        # Unroll: clone temp items with genvar substituted for each iteration
        import copy
        val = start
        max_iter = 1000
        iter_count = 0
        while iter_count < max_iter:
            cond_val = self._eval_expr(mod, cond_str.replace(var_name, str(val)))
            if not cond_val:
                break

            for item_list in ('signals', 'parameters', 'always_blocks', 'continuous_assigns'):
                for item in getattr(temp_mod, item_list):
                    cloned = copy.deepcopy(item)
                    self._substitute_genvar_strs(cloned, var_name, str(val))
                    getattr(mod, item_list).append(cloned)

            val += step
            iter_count += 1

    def _parse_generate_case(self, mod: Module):
        """Parse generate case(expr) ... endcase (simple: parse all branches)."""
        self.expect(TokenType.CASE)
        # Evaluate expression
        expr = self._parse_expression()
        case_val = self._eval_expr(mod, expr)

        matched = False
        while self.peek() not in (TokenType.ENDCASE, TokenType.ENDGENERATE, TokenType.EOF):
            if self.peek() == TokenType.DEFAULT:
                self.advance()
                self.expect(TokenType.COLON)
                if not matched:
                    self._parse_generate_item(mod, True)
                    matched = True
                else:
                    self._skip_generate_item()
            else:
                vals = []
                v = self._parse_expression()
                vals.append(v)
                while self.peek() == TokenType.COMMA:
                    self.advance()
                    vals.append(self._parse_expression())
                self.expect(TokenType.COLON)
                item_match = any(self._eval_expr(mod, vv) == case_val for vv in vals)
                if item_match and not matched:
                    self._parse_generate_item(mod, True)
                    matched = True
                else:
                    self._skip_generate_item()
        self.expect(TokenType.ENDCASE)

    def _substitute_genvar_strs(self, obj, var_name: str, val_str: str):
        """Recursively substitute genvar references in string fields."""
        import re
        pat = re.compile(r'\b' + re.escape(var_name) + r'\b')
        if isinstance(obj, str):
            return pat.sub(val_str, obj)
        if isinstance(obj, list):
            for i, item in enumerate(obj):
                obj[i] = self._substitute_genvar_strs(item, var_name, val_str)
            return obj
        if hasattr(obj, '__dataclass_fields__'):
            for field_name in obj.__dataclass_fields__:
                old = getattr(obj, field_name)
                new = self._substitute_genvar_strs(old, var_name, val_str)
                if new is not old:
                    setattr(obj, field_name, new)
            return obj
        return obj

    def _parse_instantiation(self, mod: Module):
        """Parse module instantiation: mod_name [#(...)] inst_name (.port(expr), ...);"""
        module_name = self.expect(TokenType.IDENTIFIER).value
        param_overrides: dict[str, str] = {}

        if self.peek() == TokenType.HASH:
            self.advance()
            self.expect(TokenType.LPAREN)
            while self.peek() not in (TokenType.RPAREN, TokenType.EOF):
                if self.peek() == TokenType.DOT:
                    self.advance()  # .param_name(expr)
                    pname = self.expect(TokenType.IDENTIFIER).value
                    self.expect(TokenType.LPAREN)
                    pexpr = self._parse_expression()
                    self.expect(TokenType.RPAREN)
                    param_overrides[pname] = pexpr
                elif self.peek() == TokenType.COMMA:
                    self.advance()
                    continue
                else:
                    break
            self.expect(TokenType.RPAREN)

        instance_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LPAREN)

        port_connections: dict[str, str] = {}
        param_idx = 0
        while self.peek() not in (TokenType.RPAREN, TokenType.EOF):
            if self.peek() == TokenType.COMMA:
                self.advance()
                continue
            if self.peek() == TokenType.DOT:
                self.advance()
                port_name = self.expect(TokenType.IDENTIFIER).value
                self.expect(TokenType.LPAREN)
                expr = self._parse_expression()
                self.expect(TokenType.RPAREN)
                port_connections[port_name] = expr
            else:
                # Positional connection
                expr = self._parse_expression()
                port_connections[str(param_idx)] = expr
                param_idx += 1
        self.expect(TokenType.RPAREN)
        self.skip_semicolon()

        mod.instances.append(Instance(
            module_name=module_name,
            instance_name=instance_name,
            param_overrides=param_overrides,
            port_connections=port_connections,
        ))

    def _parse_port_or_signal_list(self, mod: Module, direction: str | None):
        """Parse [msb:lsb]? name (, name)* ; (body-style declaration)."""
        items = self._parse_signal_decls(mod, direction)
        self.skip_semicolon()

        if direction:
            for item in items:
                for p in mod.ports:
                    if p.name == item.name:
                        p.direction = direction
                        p.msb = item.msb
                        p.lsb = item.lsb
                        break

        return items

    def _parse_always(self, mod: Module):
        self.expect(TokenType.ALWAYS)
        self.expect(TokenType.AT)

        block = AlwaysBlock()

        if self.peek() == TokenType.STAR:
            self.advance()
            block.is_auto = True
            self._parse_statement_block(block.statements, mod)
            mod.always_blocks.append(block)
            return

        self.expect(TokenType.LPAREN)

        if self.peek() == TokenType.STAR:
            self.advance()
            self.expect(TokenType.RPAREN)
            block.is_auto = True
            self._parse_statement_block(block.statements, mod)
            mod.always_blocks.append(block)
            return

        self._parse_sensitivity_list(block)

        self.expect(TokenType.RPAREN)
        self._parse_statement_block(block.statements, mod)
        mod.always_blocks.append(block)

    def _parse_sensitivity_list(self, block: AlwaysBlock):
        while self.peek() not in (TokenType.RPAREN, TokenType.EOF):
            if self.peek() == TokenType.POSEDGE:
                self.advance()
                sig = self.expect(TokenType.IDENTIFIER).value
                block.sensitivity.append(SensitivityItem(edge='posedge', signal=sig))
            elif self.peek() == TokenType.NEGEDGE:
                self.advance()
                sig = self.expect(TokenType.IDENTIFIER).value
                block.sensitivity.append(SensitivityItem(edge='negedge', signal=sig))
            elif self.peek() == TokenType.IDENTIFIER:
                sig = self.expect(TokenType.IDENTIFIER).value
                block.sensitivity.append(SensitivityItem(edge=None, signal=sig))
            elif self.peek() == TokenType.OR:
                self.advance()
            elif self.peek() == TokenType.COMMA:
                self.advance()
            else:
                break

    def _known_task_names(self, mod: Module) -> set:
        return {t.name for t in mod.tasks}

    def _known_function_names(self, mod: Module) -> set:
        return {f.name for f in mod.functions}

    def _parse_statement_block(self, statements: list, mod: Module = None):
        if self.peek() == TokenType.BEGIN:
            self.advance()
            while self.peek() not in (TokenType.END, TokenType.EOF):
                self._parse_statement(statements, mod)
            self.expect(TokenType.END)
        else:
            self._parse_statement(statements, mod)

    def _parse_statement(self, statements: list, mod: Module = None):
        if self.peek() == TokenType.IF:
            self._parse_if(statements, mod)
        elif self.peek() == TokenType.CASE:
            self._parse_case(statements, mod)
        elif self.peek() == TokenType.FOR:
            self._parse_for(statements, mod)
        elif self.peek() == TokenType.REPEAT:
            self._parse_repeat(statements, mod)
        elif self.peek() == TokenType.IDENTIFIER:
            self._parse_assign_or_expression(statements)
        else:
            raise ParseError(f'Line {self.tokens[self.pos].line}: '
                              f'Unexpected statement token {self.peek().name}')

    def _parse_repeat(self, statements: list, mod: Module = None):
        self.expect(TokenType.REPEAT)
        self.expect(TokenType.LPAREN)
        count = self._parse_expression()
        self.expect(TokenType.RPAREN)
        stmt = RepeatStatement(count=count)
        self._parse_statement_block(stmt.statements, mod)
        statements.append(stmt)

    def _parse_for(self, statements: list, mod: Module = None):
        self.expect(TokenType.FOR)
        self.expect(TokenType.LPAREN)
        var = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.BLOCKING_ASSIGN)
        start = self._parse_expression()
        self.expect(TokenType.SEMICOLON)
        condition = self._parse_expression()
        self.expect(TokenType.SEMICOLON)
        self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.BLOCKING_ASSIGN)
        step = self._parse_expression()
        self.expect(TokenType.RPAREN)
        stmt = ForStatement(var=var, start=start, condition=condition, step=step)
        self._parse_statement_block(stmt.statements, mod)
        statements.append(stmt)

    def _parse_if(self, statements: list, mod: Module = None):
        self.expect(TokenType.IF)
        self.expect(TokenType.LPAREN)
        condition = self._parse_expression()
        self.expect(TokenType.RPAREN)

        if_stmt = IfStatement(condition=condition)
        self._parse_statement_block(if_stmt.if_branch, mod)

        if self.peek() == TokenType.ELSE:
            self.advance()
            if_stmt.else_branch = []
            self._parse_statement_block(if_stmt.else_branch, mod)

        statements.append(if_stmt)

    def _parse_case(self, statements: list, mod: Module = None):
        self.expect(TokenType.CASE)
        expr = self._parse_expression()
        case_stmt = CaseStatement(expression=expr)

        while self.peek() not in (TokenType.ENDCASE, TokenType.EOF):
            if self.peek() == TokenType.DEFAULT:
                self.advance()
                self.expect(TokenType.COLON)
                item = CaseItem(values=['default'], statements=[])
                self._parse_statement_block(item.statements, mod)
                case_stmt.items.append(item)
            else:
                values = []
                val = self._parse_expression()
                values.append(val)
                while self.peek() == TokenType.COMMA:
                    self.advance()
                    values.append(self._parse_expression())
                self.expect(TokenType.COLON)
                item = CaseItem(values=values, statements=[])
                self._parse_statement_block(item.statements, mod)
                case_stmt.items.append(item)

        self.expect(TokenType.ENDCASE)
        statements.append(case_stmt)

    def _parse_assign_or_expression(self, statements: list):
        name = self.expect(TokenType.IDENTIFIER).value
        lhs_msb = None
        lhs_lsb = None

        # Part select on LHS: <name>[msb:lsb] or <name>[bit]
        if self.peek() == TokenType.LBRACKET:
            self.advance()
            lhs_msb = self._parse_expression()
            if self.peek() == TokenType.COLON:
                self.advance()
                lhs_lsb = self._parse_expression()
            self.expect(TokenType.RBRACKET)

        # Statement call: task_name(arg1, arg2, ...);
        if self.peek() == TokenType.LPAREN:
            if self._routine_kind == 'function':
                raise ParseError(f'Line {self.tokens[self.pos].line}: '
                                  f'Task/function cross-call not allowed inside function: {name}')
            self.advance()
            args = []
            while self.peek() != TokenType.RPAREN:
                if args:
                    self.expect(TokenType.COMMA)
                args.append(self._parse_expression())
            self.expect(TokenType.RPAREN)
            self.skip_semicolon()
            statements.append(TaskEnableStatement(name=name, args=args))
        elif self.peek() == TokenType.NONBLOCKING_ASSIGN:
            self.advance()
            rhs = self._parse_expression()
            self.skip_semicolon()
            statements.append(AssignStatement(lhs=name, rhs=rhs, is_nonblocking=True,
                                              lhs_msb=lhs_msb, lhs_lsb=lhs_lsb))
        elif self.peek() == TokenType.BLOCKING_ASSIGN:
            self.advance()
            rhs = self._parse_expression()
            self.skip_semicolon()
            statements.append(AssignStatement(lhs=name, rhs=rhs, is_nonblocking=False,
                                              lhs_msb=lhs_msb, lhs_lsb=lhs_lsb))
        else:
            # Just an expression statement (e.g. task enable with no args)
            self.skip_semicolon()

    def _parse_expression(self) -> str:
        """Parse an expression and return its string representation."""
        return self._parse_conditional()

    def _parse_conditional(self) -> str:
        left = self._parse_logical_or()
        if self.peek() == TokenType.QUESTION:
            self.advance()
            true_expr = self._parse_expression()
            self.expect(TokenType.COLON)
            false_expr = self._parse_conditional()
            left = f'({left} ? {true_expr} : {false_expr})'
        return left

    def _parse_logical_or(self) -> str:
        left = self._parse_logical_and()
        while self.peek() == TokenType.LOGICAL_OR:
            self.advance()
            right = self._parse_logical_and()
            left = f'({left} || {right})'
        return left

    def _parse_logical_and(self) -> str:
        left = self._parse_bitwise_or()
        while self.peek() == TokenType.LOGICAL_AND:
            self.advance()
            right = self._parse_bitwise_or()
            left = f'({left} && {right})'
        return left

    def _parse_bitwise_or(self) -> str:
        left = self._parse_bitwise_xor()
        while self.peek() == TokenType.PIPE:
            self.advance()
            right = self._parse_bitwise_xor()
            left = f'({left} | {right})'
        return left

    def _parse_bitwise_xor(self) -> str:
        left = self._parse_bitwise_and()
        while self.peek() == TokenType.CARET:
            self.advance()
            right = self._parse_bitwise_and()
            left = f'({left} ^ {right})'
        return left

    def _parse_bitwise_and(self) -> str:
        left = self._parse_equality()
        while self.peek() == TokenType.AMPERSAND:
            self.advance()
            right = self._parse_equality()
            left = f'({left} & {right})'
        return left

    def _parse_equality(self) -> str:
        left = self._parse_relational()
        while self.peek() in (TokenType.EQ, TokenType.NEQ, TokenType.TRIPLE_EQ, TokenType.TRIPLE_NEQ):
            op = self.advance().value
            right = self._parse_relational()
            left = f'({left} {op} {right})'
        return left

    def _parse_relational(self) -> str:
        left = self._parse_shift()
        while self.peek() in (TokenType.LT, TokenType.GT, TokenType.GE,
                              TokenType.NONBLOCKING_ASSIGN):
            op = self.advance().value
            right = self._parse_shift()
            left = f'({left} {op} {right})'
        return left

    def _parse_shift(self) -> str:
        left = self._parse_addition()
        while self.peek() in (TokenType.LSHIFT, TokenType.RSHIFT):
            op = self.advance().value
            right = self._parse_addition()
            left = f'({left} {op} {right})'
        return left

    def _parse_addition(self) -> str:
        left = self._parse_multiplicative()
        while self.peek() in (TokenType.PLUS, TokenType.MINUS):
            op = self.advance().value
            right = self._parse_multiplicative()
            left = f'({left} {op} {right})'
        return left

    def _parse_multiplicative(self) -> str:
        left = self._parse_unary()
        while self.peek() in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.advance().value
            right = self._parse_unary()
            left = f'({left} {op} {right})'
        return left

    def _parse_unary(self) -> str:
        if self.peek() in (TokenType.TILDE, TokenType.MINUS, TokenType.LOGICAL_NOT):
            op = self.advance().value
            if op == 'not':
                op = '!'
            right = self._parse_unary()
            return f'{op}{right}'
        if self.peek() == TokenType.AMPERSAND:
            self.advance()
            right = self._parse_unary()
            return f'emu_and_reduce({right})'
        if self.peek() == TokenType.PIPE:
            self.advance()
            right = self._parse_unary()
            return f'emu_or_reduce({right})'
        if self.peek() == TokenType.CARET:
            self.advance()
            right = self._parse_unary()
            return f'emu_xor_reduce({right})'
        return self._parse_primary()

    def _parse_primary(self) -> str:
        if self.peek() == TokenType.LPAREN:
            self.advance()
            expr = self._parse_expression()
            self.expect(TokenType.RPAREN)
            return f'({expr})'

        if self.peek() == TokenType.LBRACE:
            return self._parse_concat()

        if self.peek() == TokenType.NUMBER:
            val = self.advance().value
            return self._parse_number(val)

        if self.peek() == TokenType.IDENTIFIER:
            name = self.advance().value
            expr = name
            # Function call: name(arg1, arg2, ...)
            if self.peek() == TokenType.LPAREN:
                self.advance()
                args = []
                while self.peek() != TokenType.RPAREN:
                    if args:
                        self.expect(TokenType.COMMA)
                    args.append(self._parse_expression())
                self.expect(TokenType.RPAREN)
                expr = f'{name}({", ".join(args)})'
            # Part select: name[expr] or name[msb:lsb]
            if self.peek() == TokenType.LBRACKET:
                self.advance()
                idx = self._parse_expression()
                if self.peek() == TokenType.COLON:
                    self.advance()
                    idx2 = self._parse_expression()
                    self.expect(TokenType.RBRACKET)
                    return f'GET_BITS({expr}, {idx}, {idx2})'
                self.expect(TokenType.RBRACKET)
                return f'GET_BIT({expr}, {idx})'
            return expr

        raise ParseError(f'Line {self.tokens[self.pos].line}: '
                         f'Unexpected token in expression: {self.peek().name}')

    def _parse_concat(self) -> str:
        """Parse {expr, expr, ...} concatenation, expand to shifts and ORs."""
        self.expect(TokenType.LBRACE)
        parts = []
        widths = []
        while self.peek() != TokenType.RBRACE:
            if self.peek() == TokenType.COMMA:
                self.advance()
                continue

            # Repeat: {N{expr}}
            if self.peek() == TokenType.NUMBER:
                saved = self.pos
                count_tok = self.advance()
                if self.peek() == TokenType.LBRACE:
                    self.advance()
                    inner = self._parse_expression()
                    self.expect(TokenType.RBRACE)
                    count = int(count_tok.value)
                    w = self._infer_width(inner)
                    for _ in range(count):
                        parts.append(inner)
                        widths.append(w)
                    continue
                self.pos = saved

            part = self._parse_expression()
            w = self._infer_width(part)
            parts.append(part)
            widths.append(w)
        self.expect(TokenType.RBRACE)

        if len(parts) == 1:
            return parts[0]

        total_w = sum(widths)
        expr_parts = []
        shift = 0
        for i in range(len(parts) - 1, -1, -1):
            part = parts[i]
            w = widths[i]
            if shift == 0:
                if w < 32:
                    expr_parts.append(f'({part} & 0x{(1<<w)-1:X})')
                else:
                    expr_parts.append(f'({part})')
            else:
                if w < 32:
                    expr_parts.append(f'((({part} & 0x{(1<<w)-1:X})) << {shift})')
                else:
                    expr_parts.append(f'(({part}) << {shift})')
            shift += w

        return ' | '.join(expr_parts)

    def _infer_width(self, expr: str) -> int:
        """Guess the width of an expression from its string form."""
        if expr in self._number_widths:
            return self._number_widths[expr]
        m = __import__('re').match(r'GET_BITS\((\w+),\s*(\d+),\s*(\d+)\)', expr)
        if m:
            msb = int(m.group(2))
            lsb = int(m.group(3))
            return msb - lsb + 1
        m = __import__('re').match(r'GET_BIT\((\w+),\s*(\d+)\)', expr)
        if m:
            return 1
        try:
            val = int(expr, 0)
            if val == 0:
                return 1
            bits = val.bit_length()
            return max(bits, 1)
        except (ValueError, TypeError):
            pass
        if self._current_mod:
            for p in self._current_mod.ports:
                if p.name == expr and p.width > 1:
                    return p.width
            for s in self._current_mod.signals:
                if s.name == expr and s.width > 1:
                    return s.width
        return 1

    def _eval_expr(self, mod: Module, expr: str) -> int:
        """Avalia expressao constante usando parametros e genvars."""
        ns = {p.name: p.value for p in mod.parameters}
        ns.update(self._genvar_values)
        try:
            return int(eval(expr, {"__builtins__": {}}, ns))
        except Exception:
            return 0

    def _parse_number(self, val: str) -> str:
        m = __import__('re').match(r"(\d+)'([bBdDhH])([0-9a-fA-FzZxX_]+)", val)
        if m:
            size = int(m.group(1))
            radix_char = m.group(2).lower()
            digits = m.group(3).replace('_', '')
            if radix_char == 'b':
                value = int(digits.replace('z', '0').replace('x', '0'), 2) if digits else 0
            elif radix_char == 'd':
                value = int(digits)
            elif radix_char == 'h':
                value = int(digits, 16) if digits else 0
            result = str(value)
            self._number_widths[result] = size
            return result
        else:
            # plain decimal
            return val.replace('_', '')

    def has_more(self) -> bool:
        return self.peek() != TokenType.EOF


def parse(text: str) -> Module:
    tokens = tokenize(text)
    parser = Parser(tokens)
    return parser.parse_module()
