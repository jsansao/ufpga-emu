"""Module registry for multi-file Verilog projects."""

from .ast import Module
from .lexer import tokenize
from .parser import Parser


class ModuleRegistry:
    """Stores parsed modules by name for resolution during inlining."""

    def __init__(self):
        self._modules: dict[str, Module] = {}

    def register(self, mod: Module):
        self._modules[mod.name] = mod

    def get(self, name: str) -> Module | None:
        return self._modules.get(name)

    def has(self, name: str) -> bool:
        return name in self._modules

    def all_modules(self) -> list[Module]:
        return list(self._modules.values())

    def parse_file(self, path: str) -> list[Module]:
        """Parse all modules from a .v file and register them."""
        with open(path) as f:
            source = f.read()
        return self.parse_source(source)

    def parse_source(self, source: str) -> list[Module]:
        """Parse all modules from a Verilog source string and register them."""
        tokens = tokenize(source)
        parser = Parser(tokens)
        modules = []
        while parser.has_more():
            mod = parser.parse_module()
            self.register(mod)
            modules.append(mod)
        return modules
