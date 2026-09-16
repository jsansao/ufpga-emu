"""Module inliner: flattens hierarchy by inlining submodule instances."""

import copy
import re

from .ast import Module, Instance, ContinuousAssign, Signal, Parameter


def _substitute_strs(obj, old: str, new: str):
    """Recursively substitute `old` with `new` in all string/dataclass fields."""
    pat = re.compile(r'\b' + re.escape(old) + r'\b')
    if isinstance(obj, str):
        return pat.sub(new, obj)
    if isinstance(obj, list):
        for i, item in enumerate(obj):
            obj[i] = _substitute_strs(item, old, new)
        return obj
    if hasattr(obj, '__dataclass_fields__'):
        for field_name in obj.__dataclass_fields__:
            old_val = getattr(obj, field_name)
            new_val = _substitute_strs(old_val, old, new)
            if new_val is not old_val:
                setattr(obj, field_name, new_val)
        return obj
    return obj


def _rename_signal(mod: Module, prefix: str):
    """Rename all signals/ports in a module with a prefix to avoid conflicts.

    Also substitutes old names for new names in all always blocks and assigns.
    """
    if not prefix:
        return
    renames: list[tuple[str, str]] = []
    for sig in mod.signals:
        old = sig.name
        sig.name = prefix + old
        renames.append((old, sig.name))
    for p in mod.ports:
        old = p.name
        p.name = prefix + old
        renames.append((old, p.name))
    for old, new in renames:
        for ab in mod.always_blocks:
            _substitute_strs(ab, old, new)
        for ca in mod.continuous_assigns:
            ca.lhs = _substitute_strs(ca.lhs, old, new)
            ca.rhs = _substitute_strs(ca.rhs, old, new)


def _substitute_body(mod: Module, old_name: str, new_expr: str):
    """Replace all references to a port name in always blocks and assigns only."""
    for ab in mod.always_blocks:
        _substitute_strs(ab, old_name, new_expr)
    for ca in mod.continuous_assigns:
        ca.lhs = _substitute_strs(ca.lhs, old_name, new_expr)
        ca.rhs = _substitute_strs(ca.rhs, old_name, new_expr)


def _apply_param_overrides(mod: Module, overrides: dict[str, str], registry) -> Module:
    """Apply parameter overrides to a module (deep copies if needed)."""
    for param in mod.parameters:
        if param.name in overrides:
            expr = overrides[param.name]
            # Try to evaluate the expression
            ns = {p.name: p.value for p in mod.parameters}
            try:
                param.value = int(eval(expr, {"__builtins__": {}}, ns))
            except Exception:
                param.value = 0
    return mod


def flatten_module(top: Module, registry, _expanding: set | None = None) -> Module:
    """Inline all instances in a module, returning a flat module.

    Processes instances depth-first: submodules are inlined before their parent.
    """
    if _expanding is None:
        _expanding = set()
        top = copy.deepcopy(top)

    if top.name in _expanding:
        raise RuntimeError(f"Circular module dependency: {top.name}")

    # Process instances recursively (depth-first)
    for inst in list(top.instances):
        sub = registry.get(inst.module_name)
        if sub is None:
            raise RuntimeError(
                f"Module '{inst.module_name}' instantiated as '{inst.instance_name}' "
                f"not found in registry"
            )

        # Deep copy submodule for this instance
        sub_copy = copy.deepcopy(sub)

        # Apply parameter overrides (skip localparam — cannot be overridden)
        for param in sub_copy.parameters:
            if param.is_local:
                continue
            if param.name in inst.param_overrides:
                expr = inst.param_overrides[param.name]
                ns = {p.name: p.value for p in sub_copy.parameters}
                try:
                    param.value = int(eval(expr, {"__builtins__": {}}, ns))
                except Exception:
                    param.value = 0

        # Recursively flatten submodule's own instances
        if sub_copy.instances:
            _expanding.add(top.name)
            sub_copy = flatten_module(sub_copy, registry, _expanding)
            _expanding.discard(top.name)

        # Build port name maps: input ports and output ports
        input_ports = {p.name: p for p in sub_copy.ports if p.direction == 'input'}
        output_ports = {p.name: p for p in sub_copy.ports if p.direction == 'output'}
        inout_ports = {p.name: p for p in sub_copy.ports if p.direction == 'inout'}

        prefix = inst.instance_name + '_'

        # First, rename all internal signals with prefix to avoid conflicts
        _rename_signal(sub_copy, prefix)

        # Now map connections: replace port references in body with connected expr
        for port_name, conn_expr in inst.port_connections.items():
            if port_name.isdigit():
                idx = int(port_name)
                if idx < len(sub_copy.ports):
                    port_name = sub_copy.ports[idx].name
                    if port_name.startswith(prefix):
                        port_name_orig = port_name[len(prefix):]
                    else:
                        continue
                else:
                    continue
            else:
                port_name_orig = port_name

            port_name_prefixed = prefix + port_name_orig

            if port_name_orig in input_ports or port_name_orig in inout_ports:
                # Input: replace prefixed name with connected expr in body
                _substitute_body(sub_copy, port_name_prefixed, conn_expr)
            elif port_name_orig in output_ports:
                # Output: keep prefixed name in body, add assign connecting
                # to the parent's signal
                top.continuous_assigns.append(
                    ContinuousAssign(lhs=conn_expr, rhs=port_name_prefixed)
                )

        # Add remaining signals (skip original output port signals that are
        # now unused — the output port name was renamed and will be kept)
        sigs_seen = set()
        for sig in sub_copy.signals:
            if sig.name not in sigs_seen:
                top.signals.append(sig)
                sigs_seen.add(sig.name)

        # Add all always blocks and continuous assigns from the inlined module
        top.always_blocks.extend(sub_copy.always_blocks)
        top.continuous_assigns.extend(sub_copy.continuous_assigns)

    # Clear instances since they've been inlined
    top.instances.clear()

    return top
