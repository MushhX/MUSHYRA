"""Typed, source-aware AST nodes with tuple compatibility for older clients."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SourceSpan:
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    start_offset: int
    end_offset: int

    @property
    def line(self):
        return self.start_line

    @property
    def column(self):
        return self.start_column

    def to_dict(self):
        return {
            "start": {"line": self.start_line, "column": self.start_column, "offset": self.start_offset},
            "end": {"line": self.end_line, "column": self.end_column, "offset": self.end_offset},
        }


class ASTNode(tuple):
    """Tuple-shaped AST node that adds a stable kind and source span."""

    def __new__(cls, values, span: Optional[SourceSpan] = None):
        node = super().__new__(cls, values)
        node.span = span
        return node

    @property
    def kind(self):
        return self[0]
