"""AGILANG AST-level static type checker.

This checker is intentionally deterministic and conservative. It checks the
AGILANG AST before backend generation and reports actionable diagnostics.
It supports numeric, string, bool, void, any, aliases, structs, enums, and
function signatures.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .ast_nodes import AssignStmt, EnumDecl, ExprStmt, FunctionDecl, LetStmt, Program, RawBlockStmt, ReturnStmt, StructDecl, TypeAlias
from .errors import Diagnostic, SourceLocation
from .parser import parse_source

NUMERIC = {"i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "int", "f32", "f64", "float"}
INTEGER = {"i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "int"}
FLOATING = {"f32", "f64", "float"}
BUILTINS: dict[str, tuple[list[str], str]] = {
    "print": (["any"], "void"),
    "len": (["any"], "i32"),
    "range": (["i32"], "any"),
    "int": (["any"], "i32"),
    "float": (["any"], "f64"),
    "str": (["any"], "str"),
    "bool": (["any"], "bool"),
    "sum": (["any"], "any"),
    "min": (["any"], "any"),
    "max": (["any"], "any"),
    "assert_eq": (["any", "any"], "void"),
    "websocket_listen": (["str", "i32", "str"], "any"),
    "websocket_connect": (["str"], "any"),
    "realtime_channel": (["str"], "any"),
    "pubsub_bus": ([], "any"),
    "json_event": (["str", "any", "str"], "str"),
    "parse_json_event": (["str"], "any"),
    "web_app": (["str", "bool"], "any"),
    "text_response": (["str"], "any"),
    "html_response": (["str"], "any"),
    "json_response": (["any"], "any"),
    "redirect": (["str"], "any"),
    "file_response": (["str"], "any"),
    "render_template": (["str", "any"], "str"),
    "render_ags": (["str", "any"], "any"),
    "seo_tags": (["any"], "str"),
    "web_get": (["str"], "str"),
    "web_post_json": (["str", "any"], "str"),
    "hash_password": (["str"], "str"),
    "verify_password": (["str", "str"], "bool"),
    "sign_cookie": (["any", "str"], "str"),
    "verify_cookie": (["str", "str"], "any"),
    "sqlite_db": (["str"], "any"),
    "mysql_db": (["str"], "any"),
}


@dataclass
class Symbol:
    name: str
    type_name: str
    mutable: bool = True
    span_line: int = 1


@dataclass
class FunctionSig:
    name: str
    params: dict[str, str]
    return_type: str


@dataclass
class TypeCheckReport:
    ok: bool
    diagnostics: list[Diagnostic] = field(default_factory=list)
    symbols: dict[str, str] = field(default_factory=dict)

    def format(self) -> str:
        if not self.diagnostics:
            return "OK: no type diagnostics"
        return "\n".join(d.format() for d in self.diagnostics)


class TypeEnvironment:
    def __init__(self) -> None:
        self.aliases: dict[str, str] = {
            "string": "str",
            "none": "void",
            "None": "void",
            "float": "f64",
            "int": "i32",
        }
        self.structs: set[str] = set()
        self.enums: set[str] = set()
        self.functions: dict[str, FunctionSig] = {}

    def normalize(self, type_name: str | None) -> str:
        if not type_name:
            return "any"
        t = type_name.strip()
        seen = set()
        while t in self.aliases and t not in seen:
            seen.add(t)
            t = self.aliases[t]
        return t

    def compatible(self, expected: str, actual: str) -> bool:
        expected = self.normalize(expected)
        actual = self.normalize(actual)
        if expected == "any" or actual == "any":
            return True
        if expected == actual:
            return True
        if expected in FLOATING and actual in NUMERIC:
            return True
        if expected in NUMERIC and actual in INTEGER:
            return True
        return False


class TypeChecker:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.env = TypeEnvironment()
        self.diagnostics: list[Diagnostic] = []

    def check(self, program: Program) -> TypeCheckReport:
        self._collect_declarations(program)
        global_scope: dict[str, Symbol] = {}
        for node in program.body:
            if isinstance(node, FunctionDecl):
                self._check_function(node, global_scope)
            elif isinstance(node, LetStmt):
                self._check_let(node, global_scope)
        ok = not any(d.severity == "error" for d in self.diagnostics)
        return TypeCheckReport(ok=ok, diagnostics=self.diagnostics, symbols={k: v.type_name for k, v in global_scope.items()})

    def _loc(self, line: int, col: int = 1) -> SourceLocation:
        return SourceLocation(self.path, line, col)

    def _error(self, code: str, message: str, line: int, col: int = 1, hint: str | None = None) -> None:
        self.diagnostics.append(Diagnostic("error", code, message, self._loc(line, col), hint))

    def _warn(self, code: str, message: str, line: int, col: int = 1, hint: str | None = None) -> None:
        self.diagnostics.append(Diagnostic("warning", code, message, self._loc(line, col), hint))

    def _collect_declarations(self, program: Program) -> None:
        for node in program.body:
            if isinstance(node, TypeAlias):
                self.env.aliases[node.name] = self.env.normalize(node.target)
            elif isinstance(node, StructDecl):
                if node.name in self.env.structs:
                    self._error("ETYPE01", f"Struct `{node.name}` is declared more than once.", node.span.line)
                self.env.structs.add(node.name)
            elif isinstance(node, EnumDecl):
                if node.name in self.env.enums:
                    self._error("ETYPE02", f"Enum `{node.name}` is declared more than once.", node.span.line)
                self.env.enums.add(node.name)
            elif isinstance(node, FunctionDecl):
                if node.name in self.env.functions:
                    self._error("ETYPE03", f"Function `{node.name}` is declared more than once.", node.span.line)
                self.env.functions[node.name] = FunctionSig(
                    node.name,
                    {p.name: self.env.normalize(p.type_name) for p in node.params},
                    self.env.normalize(node.return_type),
                )

    def _check_function(self, fn: FunctionDecl, outer: dict[str, Symbol]) -> None:
        scope = dict(outer)
        for param in fn.params:
            scope[param.name] = Symbol(param.name, self.env.normalize(param.type_name), mutable=True, span_line=param.span.line)
        return_seen = False
        for stmt in fn.body:
            if isinstance(stmt, ReturnStmt):
                return_seen = True
                actual = "void" if stmt.expr is None else self._infer_expr(stmt.expr, scope, stmt.span.line)
                if not self.env.compatible(fn.return_type, actual):
                    self._error("ETYPE10", f"Return type mismatch in `{fn.name}`: expected `{self.env.normalize(fn.return_type)}`, got `{actual}`.", stmt.span.line)
            else:
                self._check_stmt(stmt, scope, fn.return_type)
        if self.env.normalize(fn.return_type) != "void" and not return_seen:
            self._warn("WTYPE11", f"Function `{fn.name}` declares return type `{fn.return_type}` but has no explicit return.", fn.span.line)

    def _check_stmt(self, stmt, scope: dict[str, Symbol], fn_return: str = "void") -> None:
        if isinstance(stmt, LetStmt):
            self._check_let(stmt, scope)
        elif isinstance(stmt, AssignStmt):
            if stmt.target not in scope:
                self._error("ETYPE20", f"Assignment to undeclared name `{stmt.target}`.", stmt.span.line, hint="Declare it first with `let` or `const`.")
                return
            sym = scope[stmt.target]
            if not sym.mutable:
                self._error("ETYPE21", f"Cannot assign to const `{stmt.target}` declared on line {sym.span_line}.", stmt.span.line)
            actual = self._infer_expr(stmt.expr, scope, stmt.span.line)
            if not self.env.compatible(sym.type_name, actual):
                self._error("ETYPE22", f"Assignment type mismatch for `{stmt.target}`: expected `{sym.type_name}`, got `{actual}`.", stmt.span.line)
        elif isinstance(stmt, FunctionDecl):
            # Nested functions are valid AGILANG callback declarations. Treat them as
            # local callable values and check their bodies with closure access.
            scope[stmt.name] = Symbol(stmt.name, "any", mutable=False, span_line=stmt.span.line)
            nested_scope = dict(scope)
            for param in stmt.params:
                nested_scope[param.name] = Symbol(param.name, self.env.normalize(param.type_name), mutable=True, span_line=param.span.line)
            for child in stmt.body:
                if isinstance(child, ReturnStmt):
                    actual = "void" if child.expr is None else self._infer_expr(child.expr, nested_scope, child.span.line)
                    if not self.env.compatible(stmt.return_type, actual):
                        self._error("ETYPE10", f"Return type mismatch in `{stmt.name}`: expected `{self.env.normalize(stmt.return_type)}`, got `{actual}`.", child.span.line)
                else:
                    self._check_stmt(child, nested_scope, stmt.return_type)
        elif isinstance(stmt, ExprStmt):
            self._infer_expr(stmt.expr, scope, stmt.span.line)
        elif isinstance(stmt, RawBlockStmt):
            # Check condition/expression when possible, then descend into block with copied scope.
            block_scope = dict(scope)
            if stmt.kind in {"if", "elif", "while"}:
                cond = stmt.header.split(None, 1)[1].rstrip(":")
                self._infer_expr(cond, scope, stmt.span.line)
            elif stmt.kind == "for":
                header = stmt.header.rstrip(":")
                if " in " in header:
                    _, rest = header.split(" ", 1)
                    name, iterable = rest.split(" in ", 1)
                    name = name.strip()
                    self._infer_expr(iterable.strip(), scope, stmt.span.line)
                    if name.isidentifier():
                        block_scope[name] = Symbol(name, "any", mutable=True, span_line=stmt.span.line)
            for child in stmt.body:
                if isinstance(child, ReturnStmt):
                    actual = "void" if child.expr is None else self._infer_expr(child.expr, block_scope, child.span.line)
                    if not self.env.compatible(fn_return, actual):
                        self._error("ETYPE10", f"Return type mismatch: expected `{self.env.normalize(fn_return)}`, got `{actual}`.", child.span.line)
                else:
                    self._check_stmt(child, block_scope, fn_return)

    def _check_let(self, stmt: LetStmt, scope: dict[str, Symbol]) -> None:
        if stmt.name in scope:
            self._warn("WTYPE30", f"Name `{stmt.name}` shadows an existing declaration.", stmt.span.line)
        actual = self._infer_expr(stmt.expr, scope, stmt.span.line)
        declared = self.env.normalize(stmt.type_name or actual)
        if stmt.type_name and not self.env.compatible(declared, actual):
            self._error("ETYPE31", f"Declaration type mismatch for `{stmt.name}`: expected `{declared}`, got `{actual}`.", stmt.span.line)
        scope[stmt.name] = Symbol(stmt.name, declared, mutable=stmt.mutable, span_line=stmt.span.line)

    def _infer_expr(self, expr: str, scope: dict[str, Symbol], line: int) -> str:
        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as exc:
            self._error("ETYPE40", f"Invalid expression `{expr}`: {exc.msg}.", line)
            return "any"
        return self._infer_node(tree.body, scope, line)

    def _infer_node(self, node: ast.AST, scope: dict[str, Symbol], line: int) -> str:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "bool"
            if isinstance(node.value, int):
                return "i32"
            if isinstance(node.value, float):
                return "f64"
            if isinstance(node.value, str):
                return "str"
            if node.value is None:
                return "void"
            return "any"
        if isinstance(node, ast.Name):
            if node.id in scope:
                return self.env.normalize(scope[node.id].type_name)
            if node.id in {"True", "False"}:
                return "bool"
            if node.id == "None":
                return "void"
            if node.id in BUILTINS or node.id in self.env.functions:
                return "any"
            self._error("ETYPE41", f"Name `{node.id}` is not declared.", line, hint="Declare it with `let`, `const`, or as a function parameter.")
            return "any"
        if isinstance(node, ast.UnaryOp):
            return self._infer_node(node.operand, scope, line)
        if isinstance(node, ast.BinOp):
            left = self._infer_node(node.left, scope, line)
            right = self._infer_node(node.right, scope, line)
            if left == "any" or right == "any":
                return "any"
            if left == "str" or right == "str":
                if isinstance(node.op, ast.Add) and left == right == "str":
                    return "str"
                self._error("ETYPE42", f"Invalid string operation between `{left}` and `{right}`.", line)
                return "any"
            if left in NUMERIC and right in NUMERIC:
                return "f64" if left in FLOATING or right in FLOATING or isinstance(node.op, ast.Div) else "i32"
            self._error("ETYPE43", f"Unsupported binary operation between `{left}` and `{right}`.", line)
            return "any"
        if isinstance(node, ast.Compare):
            self._infer_node(node.left, scope, line)
            for comp in node.comparators:
                self._infer_node(comp, scope, line)
            return "bool"
        if isinstance(node, ast.BoolOp):
            for value in node.values:
                self._infer_node(value, scope, line)
            return "bool"
        if isinstance(node, ast.Call):
            fn_name = self._call_name(node.func)
            for arg in node.args:
                self._infer_node(arg, scope, line)
            if fn_name in self.env.functions:
                sig = self.env.functions[fn_name]
                if len(node.args) > len(sig.params):
                    self._error("ETYPE44", f"Function `{fn_name}` expects {len(sig.params)} args but got {len(node.args)}.", line)
                return self.env.normalize(sig.return_type)
            if fn_name in BUILTINS:
                return BUILTINS[fn_name][1]
            if fn_name in self.env.structs:
                return fn_name
            return "any"
        if isinstance(node, (ast.List, ast.Dict, ast.Tuple, ast.Subscript, ast.Attribute, ast.IfExp)):
            return "any"
        return "any"

    def _call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return "<call>"


def typecheck_source(source: str, path: Path | None = None) -> TypeCheckReport:
    program = parse_source(source, path)
    return TypeChecker(path).check(program)


def typecheck_file(path: Path) -> TypeCheckReport:
    return typecheck_source(path.read_text(encoding="utf-8"), path.resolve())
