"""Recursive-line parser for AGILANG source.

AGILANG v0.6 owns its top-level grammar and statement grammar. Python-like
expressions are parsed by Python's expression parser in later semantic and
backend passes until the expression grammar is replaced by a dedicated Pratt
parser.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .ast_nodes import (
    AssignStmt,
    EnumDecl,
    ExprStmt,
    Field,
    FunctionDecl,
    ImportDecl,
    LetStmt,
    Param,
    Program,
    RawBlockStmt,
    ReturnStmt,
    Span,
    StructDecl,
    TypeAlias,
)
from .errors import Diagnostic, SourceLocation, TranslationError
from .translator import _split_params

_IDENT = r"[A-Za-z_]\w*"
_ASSIGN_RE = re.compile(rf"^({_IDENT})\s*(=|\+=|-=|\*=|/=|%=)\s*(.+)$")
_DECL_RE = re.compile(rf"^({_IDENT})\s*(?::\s*([^=]+))?\s*=\s*(.+)$")
_FIELD_RE = re.compile(rf"^({_IDENT})\s*:\s*([^=]+?)(?:\s*=\s*(.+))?$")
_FN_RE = re.compile(rf"^fn\s+({_IDENT})\s*\((.*)\)\s*(?:->\s*([^:]+))?\s*:\s*$")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _clean(line: str) -> str:
    return line.strip()


class AGILParser:
    """Parse AGILANG source into a serializable AST."""

    def __init__(self, source: str, path: Path | None = None) -> None:
        self.source = source
        self.path = path
        self.lines = self._logical_lines(source)
        self.index = 0
        self.diagnostics: list[Diagnostic] = []

    def _logical_lines(self, source: str) -> list[str]:
        """Join bracket-continued physical lines into parser lines."""
        result: list[str] = []
        buffer: list[str] = []
        depth = 0
        quote: str | None = None
        escaped = False
        for raw in source.splitlines():
            scan = raw
            for ch in scan:
                if quote:
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == quote:
                        quote = None
                    continue
                if ch == "#":
                    break
                if ch in {"'", '"'}:
                    quote = ch
                elif ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    depth = max(0, depth - 1)
            if buffer:
                buffer.append(raw.strip())
            else:
                buffer.append(raw)
            if depth == 0 and quote is None:
                result.append(" ".join(buffer) if len(buffer) > 1 else buffer[0])
                buffer = []
        if buffer:
            result.append(" ".join(buffer))
        return result

    def parse(self) -> Program:
        body = self._parse_block(base_indent=0, top_level=True)
        return Program(span=Span.from_path(self.path, 1, 1), body=body)

    def _span(self, line_no: int, col: int = 1) -> Span:
        return Span.from_path(self.path, line_no, col)

    def _diag(self, code: str, message: str, line_no: int, col: int = 1, hint: str | None = None) -> TranslationError:
        return TranslationError(Diagnostic("error", code, message, SourceLocation(self.path, line_no, col), hint))

    def _parse_block(self, base_indent: int, top_level: bool = False) -> list:
        nodes = []
        while self.index < len(self.lines):
            raw = self.lines[self.index]
            line_no = self.index + 1
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                self.index += 1
                continue
            indent = _indent(raw)
            if indent < base_indent:
                break
            if not top_level and indent == 0 and base_indent > 0:
                break
            if indent > base_indent:
                raise self._diag("EPARSE01", f"Unexpected indentation at line {line_no}.", line_no, indent + 1)
            nodes.append(self._parse_decl_or_stmt(raw, line_no, indent, top_level))
        return nodes

    def _parse_decl_or_stmt(self, raw: str, line_no: int, indent: int, top_level: bool):
        stripped = _clean(raw)
        public = False
        if stripped.startswith("pub "):
            public = True
            stripped = stripped[4:].strip()
        elif stripped.startswith("export "):
            public = True
            stripped = stripped[7:].strip()

        if top_level and stripped.startswith("import "):
            self.index += 1
            spec = stripped[len("import "):].strip()
            alias = None
            if " as " in spec:
                spec, alias = [part.strip() for part in spec.split(" as ", 1)]
            if spec.startswith(("'", '"')) and spec.endswith(("'", '"')):
                spec = spec[1:-1]
            return ImportDecl(self._span(line_no, indent + 1), module=spec, alias=alias, is_agilang=spec.endswith(".agi"))

        if top_level and stripped.startswith("type "):
            m = re.match(rf"^type\s+({_IDENT})\s*=\s*(.+)$", stripped)
            if not m:
                raise self._diag("EPARSE02", "Invalid type alias syntax.", line_no, indent + 1, "Use: type Name = ExistingType")
            self.index += 1
            return TypeAlias(self._span(line_no, indent + 1), name=m.group(1), target=m.group(2).strip())

        if top_level and stripped.startswith("struct "):
            m = re.match(rf"^struct\s+({_IDENT})\s*:\s*$", stripped)
            if not m:
                raise self._diag("EPARSE03", "Invalid struct syntax.", line_no, indent + 1, "Use: struct Name:")
            self.index += 1
            fields: list[Field] = []
            while self.index < len(self.lines):
                child_raw = self.lines[self.index]
                child_no = self.index + 1
                child_stripped = child_raw.strip()
                if not child_stripped or child_stripped.startswith("#"):
                    self.index += 1
                    continue
                child_indent = _indent(child_raw)
                if child_indent <= indent:
                    break
                fm = _FIELD_RE.match(child_stripped)
                if not fm:
                    raise self._diag("EPARSE04", "Invalid struct field syntax.", child_no, child_indent + 1, "Use: field_name: type")
                fields.append(Field(self._span(child_no, child_indent + 1), name=fm.group(1), type_name=fm.group(2).strip(), default=fm.group(3)))
                self.index += 1
            return StructDecl(self._span(line_no, indent + 1), name=m.group(1), fields=fields, public=public)

        if top_level and stripped.startswith("enum "):
            m = re.match(rf"^enum\s+({_IDENT})\s*:\s*$", stripped)
            if not m:
                raise self._diag("EPARSE05", "Invalid enum syntax.", line_no, indent + 1, "Use: enum Name:")
            self.index += 1
            variants: list[str] = []
            while self.index < len(self.lines):
                child_raw = self.lines[self.index]
                child_no = self.index + 1
                child_stripped = child_raw.strip()
                if not child_stripped or child_stripped.startswith("#"):
                    self.index += 1
                    continue
                child_indent = _indent(child_raw)
                if child_indent <= indent:
                    break
                if not re.match(r"^[A-Z][A-Z0-9_]*$", child_stripped):
                    raise self._diag("EPARSE06", "Invalid enum variant syntax.", child_no, child_indent + 1, "Use upper-case variant names such as ACTIVE")
                variants.append(child_stripped)
                self.index += 1
            return EnumDecl(self._span(line_no, indent + 1), name=m.group(1), variants=variants, public=public)

        if stripped.startswith("fn "):
            m = _FN_RE.match(stripped)
            if not m:
                raise self._diag("EPARSE07", "Invalid function definition syntax.", line_no, indent + 1, "Use: fn name(arg: type) -> type:")
            self.index += 1
            body = self._parse_block(base_indent=indent + 4, top_level=False)
            return FunctionDecl(
                self._span(line_no, indent + 1),
                name=m.group(1),
                params=self._parse_params(m.group(2), line_no),
                return_type=(m.group(3) or "void").strip(),
                body=body,
                public=public,
            )

        node = self._parse_statement(stripped, line_no, indent)
        self.index += 1
        return node

    def _parse_params(self, params: str, line_no: int) -> list[Param]:
        result: list[Param] = []
        for raw in _split_params(params):
            if not raw:
                continue
            default = None
            if "=" in raw:
                raw, default = raw.split("=", 1)
                raw = raw.strip()
                default = default.strip()
            if ":" in raw:
                name, type_name = raw.split(":", 1)
                name = name.strip()
                type_name = type_name.strip()
            else:
                name, type_name = raw.strip(), "any"
            if not re.match(rf"^{_IDENT}$", name):
                raise self._diag("EPARSE08", f"Invalid parameter name `{name}`.", line_no)
            result.append(Param(self._span(line_no), name=name, type_name=type_name, default=default))
        return result

    def _parse_statement(self, stripped: str, line_no: int, indent: int):
        if stripped.startswith("let ") or stripped.startswith("const "):
            mutable = stripped.startswith("let ")
            keyword = "let" if mutable else "const"
            decl = stripped[len(keyword):].strip()
            m = _DECL_RE.match(decl)
            if not m:
                raise self._diag("EPARSE09", f"Invalid {keyword} declaration.", line_no, indent + 1, f"Use: {keyword} name: type = expression")
            return LetStmt(self._span(line_no, indent + 1), name=m.group(1), type_name=(m.group(2).strip() if m.group(2) else None), expr=m.group(3).strip(), mutable=mutable)
        if stripped.startswith("return"):
            expr = stripped[len("return"):].strip()
            return ReturnStmt(self._span(line_no, indent + 1), expr=expr or None)
        raw_block_prefixes = ("if ", "elif ", "else:", "while ", "for ", "try:", "except ", "except:", "finally:", "with ")
        if any(stripped.startswith(prefix) for prefix in raw_block_prefixes):
            head = "else" if stripped.startswith("else") else stripped.split()[0].rstrip(":")
            kind = head if head in {"if", "elif", "else", "while", "for", "try", "except", "finally", "with"} else "raw"
            self.index += 1
            body = self._parse_block(base_indent=indent + 4, top_level=False)
            self.index -= 1
            return RawBlockStmt(self._span(line_no, indent + 1), header=stripped, body=body, kind=kind)
        m = _ASSIGN_RE.match(stripped)
        if m:
            return AssignStmt(self._span(line_no, indent + 1), target=m.group(1), op=m.group(2), expr=m.group(3).strip())
        return ExprStmt(self._span(line_no, indent + 1), expr=stripped)


def parse_source(source: str, path: Path | None = None) -> Program:
    return AGILParser(source, path).parse()


def parse_file(path: Path) -> Program:
    return parse_source(path.read_text(encoding="utf-8"), path.resolve())
