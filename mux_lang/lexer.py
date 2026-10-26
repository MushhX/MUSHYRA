"""Lexer and source-aware errors for the Mux language."""

import re
from typing import List, Optional


class Token(tuple):
    """A token retaining the legacy three-tuple API plus source coordinates."""

    def __new__(cls, token_type, value, line, column=1, offset=0):
        instance = super().__new__(cls, (token_type, value, line))
        instance.column = column
        instance.offset = offset
        return instance

    @property
    def type(self):
        return self[0]

    @property
    def value(self):
        return self[1]

    @property
    def line(self):
        return self[2]


class MuxError(Exception):
    """An error that can be rendered with the source location that caused it."""

    def __init__(self, message: str, path: Optional[str] = None,
                 line: Optional[int] = None, column: Optional[int] = None,
                 cause: Optional[BaseException] = None):
        self.message = message
        self.path = path
        self.line = line
        self.column = column
        self.cause = cause
        self.contexts = []
        super().__init__(self.format())

    def add_context(self, description: str) -> "MuxError":
        self.contexts.append(description)
        self.args = (self.format(),)
        return self

    def set_location(self, path: Optional[str], line: Optional[int],
                     column: Optional[int]) -> "MuxError":
        if self.path is None:
            self.path, self.line, self.column = path, line, column
            self.args = (self.format(),)
        elif self.line is None and self.path == path:
            self.line, self.column = line, column
            self.args = (self.format(),)
        return self

    def format(self) -> str:
        location = self.path or ""
        if self.line is not None:
            separator = ":" if location else ""
            location = f"{location}{separator}{self.line}"
            if self.column is not None:
                location += f":{self.column}"
        prefix = f"{location}: " if location else ""
        result = f"{prefix}{self.message}"
        if self.contexts:
            result += "\n" + "\n".join(f"  en {item}" for item in reversed(self.contexts))
        return result


class Lexer:
    """Tokenize Mux source while retaining exact source positions."""

    # A single compiled scanner avoids recompiling a large list of expressions
    # at every character. Keywords are ordered before identifiers and use word
    # boundaries, so e.g. `ifx` remains an identifier.
    TOKEN_PATTERNS = [
        ("NUMBER", r"\d+(?:\.\d+)?(?![A-Za-z_\d.])"),
        ("STRING", r'"(?:[^"\\\r\n]|\\(?:["\\bnrtf]|u[0-9a-fA-F]{4}))*"'),
        ("BOOL", r"\b(?:true|false)\b"),
        ("NULL", r"\bnull\b"),
        ("IMPORT", r"\bimport\b"),
        ("FROM", r"\bfrom\b"),
        ("AS", r"\bas\b"),
        ("IF", r"\bif\b"),
        ("ELSE", r"\belse\b"),
        ("ELIF", r"\belif\b"),
        ("REPEAT", r"\brepeat\b"),
        ("WHILE", r"\bwhile\b"),
        ("FOR", r"\bfor\b"),
        ("IN", r"\bin\b"),
        ("FUNC", r"\bfunc\b"),
        ("RETURN", r"\breturn\b"),
        ("BREAK", r"\bbreak\b"),
        ("CONTINUE", r"\bcontinue\b"),
        ("END", r"\bend\b"),
        ("LET", r"\blet\b"),
        ("PRINT", r"\bprint\b"),
        ("INPUT", r"\binput\b"),
        ("LEN", r"\blen\b"),
        ("TYPE", r"\btype\b"),
        ("STR", r"\bstr\b"),
        ("INT", r"\bint\b"),
        ("FLOAT", r"\bfloat\b"),
        ("RANGE", r"\brange\b"),
        ("ASSERT", r"\bassert\b"),
        ("EACH", r"\beach\b"),
        ("TIMES", r"\btimes\b"),
        ("UNTIL", r"\buntil\b"),
        ("UNLESS", r"\bunless\b"),
        ("LOOP", r"\bloop\b"),
        ("EXIT", r"\bexit\b"),
        ("PASS", r"\bpass\b"),
        ("SHOW", r"\bshow\b"),
        ("ASK", r"\bask\b"),
        ("SAY", r"\bsay\b"),
        ("WAIT", r"\bwait\b"),
        ("DO", r"\bdo\b"),
        ("GLOBAL", r"\bglobal\b"),
        ("NONLOCAL", r"\bnonlocal\b"),
        ("EQ", r"=="),
        ("NEQ", r"!="),
        ("LTE", r"<="),
        ("GTE", r">="),
        ("AND", r"&&"),
        ("OR", r"\|\|"),
        ("LT", r"<"),
        ("GT", r">"),
        ("NOT", r"!"),
        ("ASSIGN", r"="),
        ("PLUS", r"\+"),
        ("MINUS", r"-"),
        ("MULT", r"\*"),
        ("DIV", r"/"),
        ("MOD", r"%"),
        ("LPAREN", r"\("),
        ("RPAREN", r"\)"),
        ("LBRACKET", r"\["),
        ("RBRACKET", r"\]"),
        ("LBRACE", r"\{"),
        ("RBRACE", r"\}"),
        ("COMMA", r","),
        ("DOT", r"\."),
        ("COLON", r":"),
        ("ID", r"(?:[^\W\d]|_)(?:\w|_)*"),
        ("NEWLINE", r"\n"),
        ("SKIP", r"[ \t\f]+"),
        ("COMMENT", r"\#[^\r\n]*"),
    ]
    TOKEN_RE = re.compile(
        "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_PATTERNS)
    )

    def __init__(self, code: str, path: Optional[str] = None):
        self.code = code.replace("\r\n", "\n").replace("\r", "\n")
        self.path = path

    def tokenize(self) -> List[Token]:
        tokens = []
        line, column, pos = 1, 1, 0
        while pos < len(self.code):
            match = self.TOKEN_RE.match(self.code, pos)
            if match is None:
                char = self.code[pos]
                if char == '"':
                    line_end = self.code.find("\n", pos)
                    if line_end < 0:
                        line_end = len(self.code)
                    closing_quote = self.code.find('"', pos + 1, line_end)
                    message = "Cadena sin cerrar" if closing_quote < 0 else "Escape no válido en una cadena"
                    raise MuxError(message, self.path, line, column)
                raise MuxError(
                    f"Carácter inesperado {char!r}", self.path, line, column
                )
            token_type = match.lastgroup
            value = match.group(token_type)
            start_line, start_column = line, column
            if token_type not in ("SKIP", "COMMENT"):
                tokens.append(Token(token_type, value, start_line, start_column, pos))
            consumed = self.code[pos:match.end()]
            if token_type == "NEWLINE":
                line += 1
                column = 1
            else:
                column += len(consumed)
            pos = match.end()
        return tokens
