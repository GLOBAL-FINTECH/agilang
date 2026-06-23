"""AGILANG abstract syntax tree nodes.

The AST is deliberately explicit and serializable so compiler passes,
formatters, language-server features, and native backends can share the
same source model instead of scraping translated Python.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class Span:
    path: str | None
    line: int
    column: int = 1

    @classmethod
    def from_path(cls, path: Path | None, line: int, column: int = 1) -> "Span":
        return cls(str(path) if path else None, line, column)


@dataclass
class Node:
    span: Span

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["node"] = self.__class__.__name__
        return data


@dataclass
class Program(Node):
    body: list[Node] = field(default_factory=list)


@dataclass
class ImportDecl(Node):
    module: str = ""
    alias: str | None = None
    is_agilang: bool = False


@dataclass
class TypeAlias(Node):
    name: str = ""
    target: str = "any"


@dataclass
class Field(Node):
    name: str = ""
    type_name: str = "any"
    default: str | None = None


@dataclass
class StructDecl(Node):
    name: str = ""
    fields: list[Field] = field(default_factory=list)
    public: bool = False


@dataclass
class EnumDecl(Node):
    name: str = ""
    variants: list[str] = field(default_factory=list)
    public: bool = False


@dataclass
class Param(Node):
    name: str = ""
    type_name: str = "any"
    default: str | None = None


@dataclass
class FunctionDecl(Node):
    name: str = ""
    params: list[Param] = field(default_factory=list)
    return_type: str = "void"
    body: list[Node] = field(default_factory=list)
    public: bool = False


@dataclass
class LetStmt(Node):
    name: str = ""
    type_name: str | None = None
    expr: str = ""
    mutable: bool = True


@dataclass
class AssignStmt(Node):
    target: str = ""
    op: str = "="
    expr: str = ""


@dataclass
class ReturnStmt(Node):
    expr: str | None = None


@dataclass
class ExprStmt(Node):
    expr: str = ""


@dataclass
class RawBlockStmt(Node):
    """A statement the parser preserves for Python compatibility.

    The native C backend supports a defined subset. Unsupported raw block
    statements produce clear backend diagnostics instead of silent output.
    """

    header: str = ""
    body: list[Node] = field(default_factory=list)
    kind: Literal["if", "elif", "else", "while", "for", "raw"] = "raw"


@dataclass
class ParseResult:
    program: Program
    diagnostics: list[Any] = field(default_factory=list)


def ast_to_dict(program: Program) -> dict[str, Any]:
    return program.to_dict()
