from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Port:
    name: str
    direction: str  # input, output, inout
    msb: Optional[int] = None
    lsb: Optional[int] = None

    @property
    def width(self) -> int:
        if self.msb is not None and self.lsb is not None:
            return self.msb - self.lsb + 1
        return 1


@dataclass
class Signal:
    name: str
    sig_type: str  # wire, reg
    msb: Optional[int] = None
    lsb: Optional[int] = None

    @property
    def width(self) -> int:
        if self.msb is not None and self.lsb is not None:
            return self.msb - self.lsb + 1
        return 1


@dataclass
class SensitivityItem:
    edge: Optional[str]  # posedge, negedge, or None
    signal: str


@dataclass
class AssignStatement:
    lhs: str
    rhs: str
    is_nonblocking: bool = False
    lhs_msb: Optional[str] = None
    lhs_lsb: Optional[str] = None
    rhs_msb: Optional[str] = None
    rhs_lsb: Optional[str] = None


@dataclass
class IfStatement:
    condition: str
    if_branch: list = field(default_factory=list)
    else_branch: Optional[list] = None


@dataclass
class CaseItem:
    values: list[str]
    statements: list


@dataclass
class CaseStatement:
    expression: str
    items: list[CaseItem] = field(default_factory=list)


@dataclass
class AlwaysBlock:
    sensitivity: list[SensitivityItem] = field(default_factory=list)
    statements: list = field(default_factory=list)  # mixed: Assign | IfStatement | CaseStatement
    is_auto: bool = False  # True for always @(*) / @*


@dataclass
class ForStatement:
    var: str
    start: str
    condition: str
    step: str
    statements: list = field(default_factory=list)


@dataclass
class RepeatStatement:
    count: str
    statements: list = field(default_factory=list)


@dataclass
class Instance:
    module_name: str
    instance_name: str
    param_overrides: dict[str, str] = field(default_factory=dict)
    port_connections: dict[str, str] = field(default_factory=dict)


@dataclass
class ContinuousAssign:
    lhs: str
    rhs: str


@dataclass
class Parameter:
    name: str
    value: int
    is_local: bool = False


@dataclass
class TaskDecl:
    name: str
    ports: list[Port] = field(default_factory=list)
    locals: list[Signal] = field(default_factory=list)
    statements: list = field(default_factory=list)
    is_automatic: bool = False


@dataclass
class FunctionDecl:
    name: str
    ports: list[Port] = field(default_factory=list)
    locals: list[Signal] = field(default_factory=list)
    statements: list = field(default_factory=list)
    return_msb: Optional[int] = None
    return_lsb: Optional[int] = None
    is_automatic: bool = False


@dataclass
class TaskEnableStatement:
    name: str
    args: list[str] = field(default_factory=list)


@dataclass
class FuncCallExpression:
    name: str
    args: list[str] = field(default_factory=list)


@dataclass
class Module:
    name: str
    ports: list[Port] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    always_blocks: list[AlwaysBlock] = field(default_factory=list)
    continuous_assigns: list[ContinuousAssign] = field(default_factory=list)
    parameters: list[Parameter] = field(default_factory=list)
    instances: list[Instance] = field(default_factory=list)
    tasks: list[TaskDecl] = field(default_factory=list)
    functions: list[FunctionDecl] = field(default_factory=list)

    def get_port(self, name: str) -> Optional[Port]:
        for p in self.ports:
            if p.name == name:
                return p
        return None

    def get_signal(self, name: str) -> Optional[Signal]:
        for s in self.signals:
            if s.name == name:
                return s
        return None
