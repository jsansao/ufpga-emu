import re
from enum import Enum, auto


class TokenType(Enum):
    MODULE = auto()
    ENDMODULE = auto()
    INPUT = auto()
    OUTPUT = auto()
    INOUT = auto()
    WIRE = auto()
    REG = auto()
    ALWAYS = auto()
    POSEDGE = auto()
    NEGEDGE = auto()
    OR = auto()
    BEGIN = auto()
    END = auto()
    IF = auto()
    ELSE = auto()
    CASE = auto()
    ENDCASE = auto()
    DEFAULT = auto()
    ASSIGN = auto()
    PARAMETER = auto()
    LOCALPARAM = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COLON = auto()
    SEMICOLON = auto()
    COMMA = auto()
    AT = auto()
    HASH = auto()
    BLOCKING_ASSIGN = auto()
    NONBLOCKING_ASSIGN = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    AMPERSAND = auto()
    PIPE = auto()
    CARET = auto()
    TILDE = auto()
    LSHIFT = auto()
    RSHIFT = auto()
    NOT = auto()
    LOGICAL_AND = auto()
    LOGICAL_OR = auto()
    LOGICAL_NOT = auto()
    EQ = auto()
    NEQ = auto()
    TRIPLE_EQ = auto()
    TRIPLE_NEQ = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    QUESTION = auto()
    FOR = auto()
    REPEAT = auto()
    INTEGER = auto()
    GENERATE = auto()
    ENDGENERATE = auto()
    GENVAR = auto()
    TASK = auto()
    ENDTASK = auto()
    FUNCTION = auto()
    ENDFUNCTION = auto()
    AUTOMATIC = auto()
    NUMBER = auto()
    IDENTIFIER = auto()
    DOT = auto()
    LBRACE = auto()
    RBRACE = auto()
    EOF = auto()


TOKEN_PATTERNS = [
    (r'module\b',       TokenType.MODULE),
    (r'endmodule\b',    TokenType.ENDMODULE),
    (r'input\b',        TokenType.INPUT),
    (r'output\b',       TokenType.OUTPUT),
    (r'inout\b',        TokenType.INOUT),
    (r'wire\b',         TokenType.WIRE),
    (r'reg\b',          TokenType.REG),
    (r'always\b',       TokenType.ALWAYS),
    (r'posedge\b',      TokenType.POSEDGE),
    (r'negedge\b',      TokenType.NEGEDGE),
    (r'or\b',           TokenType.OR),
    (r'begin\b',        TokenType.BEGIN),
    (r'end\b',          TokenType.END),
    (r'if\b',           TokenType.IF),
    (r'else\b',         TokenType.ELSE),
    (r'case\b',         TokenType.CASE),
    (r'endcase\b',      TokenType.ENDCASE),
    (r'default\b',      TokenType.DEFAULT),
    (r'assign\b',       TokenType.ASSIGN),
    (r'for\b',          TokenType.FOR),
    (r'repeat\b',       TokenType.REPEAT),
    (r'integer\b',      TokenType.INTEGER),
    (r'generate\b',     TokenType.GENERATE),
    (r'endgenerate\b',  TokenType.ENDGENERATE),
    (r'genvar\b',       TokenType.GENVAR),
    (r'task\b',         TokenType.TASK),
    (r'endtask\b',      TokenType.ENDTASK),
    (r'function\b',     TokenType.FUNCTION),
    (r'endfunction\b',  TokenType.ENDFUNCTION),
    (r'automatic\b',    TokenType.AUTOMATIC),
    (r'not\b',          TokenType.LOGICAL_NOT),
    (r'parameter\b',    TokenType.PARAMETER),
    (r'localparam\b',   TokenType.LOCALPARAM),
    (r'===',            TokenType.TRIPLE_EQ),
    (r'!==',            TokenType.TRIPLE_NEQ),
    (r'<=',             TokenType.NONBLOCKING_ASSIGN),
    (r'>=',             TokenType.GE),
    (r'==',             TokenType.EQ),
    (r'!=',             TokenType.NEQ),
    (r'<<',             TokenType.LSHIFT),
    (r'>>',             TokenType.RSHIFT),
    (r'&&',             TokenType.LOGICAL_AND),
    (r'\|\|',           TokenType.LOGICAL_OR),
    (r'=',               TokenType.BLOCKING_ASSIGN),
    (r'\+',              TokenType.PLUS),
    (r'-',               TokenType.MINUS),
    (r'\*',              TokenType.STAR),
    (r'/',               TokenType.SLASH),
    (r'%',               TokenType.PERCENT),
    (r'&',               TokenType.AMPERSAND),
    (r'\|',              TokenType.PIPE),
    (r'\^',              TokenType.CARET),
    (r'~',               TokenType.TILDE),
    (r'!',               TokenType.LOGICAL_NOT),
    (r'\(',              TokenType.LPAREN),
    (r'\)',              TokenType.RPAREN),
    (r'\[',              TokenType.LBRACKET),
    (r'\]',              TokenType.RBRACKET),
    (r':',               TokenType.COLON),
    (r';',               TokenType.SEMICOLON),
    (r',',               TokenType.COMMA),
    (r'@',               TokenType.AT),
    (r'#',               TokenType.HASH),
    (r'\?',              TokenType.QUESTION),
    (r'\.',              TokenType.DOT),
    (r'\{',              TokenType.LBRACE),
    (r'\}',              TokenType.RBRACE),
    (r'<',               TokenType.LT),
    (r'>',               TokenType.GT),
    (r"'",               TokenType.NOT),  # temp, will handle in numbers
]


class Token:
    __slots__ = ('type', 'value', 'line', 'col')
    def __init__(self, type_: TokenType, value: str = '', line: int = 0, col: int = 0):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f'Token({self.type.name}, {self.value!r})'


NUMBER_RE = re.compile(r"(\d+)'([bBdDhH])([0-9a-fA-FzZxX_]+)|(\d(?:[\d_]*)\d|\d)")


def tokenize(text: str) -> list[Token]:
    # Remove comments first
    text = re.sub(r'//.*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

    tokens = []
    i = 0
    line = 1
    col = 1
    text_len = len(text)

    while i < text_len:
        ch = text[i]

        # Skip whitespace
        if ch in ' \t\n\r':
            if ch == '\n':
                line += 1
                col = 1
            else:
                col += 1
            i += 1
            continue

        # Try to match a token
        matched = False
        for pattern, tok_type in TOKEN_PATTERNS:
            m = re.match(pattern, text[i:])
            if m:
                val = m.group(0)
                tokens.append(Token(tok_type, val, line, col))
                i += len(val)
                col += len(val)
                matched = True
                break

        if matched:
            continue

        # Handle identifiers and numbers
        if ch.isalpha() or ch == '_':
            m = re.match(r'[a-zA-Z_][a-zA-Z0-9_]*', text[i:])
            if m:
                val = m.group(0)
                tokens.append(Token(TokenType.IDENTIFIER, val, line, col))
                i += len(val)
                col += len(val)
                continue

        # Handle Verilog numbers: <size>'<radix><value> or plain decimal
        num_m = NUMBER_RE.match(text[i:])
        if num_m:
            val = num_m.group(0)
            tokens.append(Token(TokenType.NUMBER, val, line, col))
            i += len(val)
            col += len(val)
            continue

        # Unknown character
        i += 1
        col += 1

    tokens.append(Token(TokenType.EOF, '', line, col))
    return tokens
