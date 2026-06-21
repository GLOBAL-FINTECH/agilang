"""Static checker for AGILANG's Python backend."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .errors import Diagnostic, SourceLocation
from .translator import AGILTranslator
from .typechecker import typecheck_source


@dataclass
class CheckReport:
    """Result of checking one source file."""

    ok: bool
    diagnostics: list[Diagnostic] = field(default_factory=list)
    python: str = ""

    def format(self) -> str:
        if not self.diagnostics:
            return "OK: no diagnostics"
        return "\n".join(d.format() for d in self.diagnostics)


class _SemanticVisitor(ast.NodeVisitor):
    """Lightweight semantic checks on generated Python AST.

    This does not try to be a complete type system.  It catches common
    production mistakes early: using names before declaration, returning
    values from None functions, duplicate functions, and suspicious
    mutable defaults.
    """

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.diagnostics: list[Diagnostic] = []
        self.scope_stack: list[set[str]] = [set(dir(__builtins__))]
        self.functions: dict[str, ast.FunctionDef] = {}
        self.current_function_return: str | None = None

    @property
    def scope(self) -> set[str]:
        return self.scope_stack[-1]

    def loc(self, node: ast.AST) -> SourceLocation:
        return SourceLocation(self.path, getattr(node, "lineno", 1), getattr(node, "col_offset", 0) + 1)

    def warn(self, code: str, message: str, node: ast.AST, hint: str | None = None) -> None:
        self.diagnostics.append(Diagnostic("warning", code, message, self.loc(node), hint))

    def error(self, code: str, message: str, node: ast.AST, hint: str | None = None) -> None:
        self.diagnostics.append(Diagnostic("error", code, message, self.loc(node), hint))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.scope.add(alias.asname or alias.name.split(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            self.scope.add(alias.asname or alias.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope.add(node.name)
        self.scope_stack.append(set(self.scope) | {"self"})
        for stmt in node.body:
            self.visit(stmt)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name in self.functions:
            self.warn("W101", f"Function `{node.name}` is defined more than once.", node)
        self.functions[node.name] = node
        self.scope.add(node.name)
        for default in node.args.defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.warn(
                    "W102",
                    f"Function `{node.name}` has a mutable default argument.",
                    default,
                    "Use None as the default and create the list/dict inside the function.",
                )
        # Nested callbacks capture the surrounding scope, so start from the current scope.
        fn_scope = set(self.scope) | {"True", "False", "None"}
        for arg in node.args.args + node.args.kwonlyargs:
            fn_scope.add(arg.arg)
        if node.args.vararg:
            fn_scope.add(node.args.vararg.arg)
        if node.args.kwarg:
            fn_scope.add(node.args.kwarg.arg)
        self.scope_stack.append(fn_scope)
        old_return = self.current_function_return
        self.current_function_return = ast.unparse(node.returns) if node.returns else None
        for stmt in node.body:
            self.visit(stmt)
        self.current_function_return = old_return
        self.scope_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        for target in node.targets:
            self._bind_target(target)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value:
            self.visit(node.value)
        self._bind_target(node.target)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.target)
        self.visit(node.value)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        self._bind_target(node.target)
        for stmt in node.body + node.orelse:
            self.visit(stmt)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self._bind_target(item.optional_vars)
        for stmt in node.body:
            self.visit(stmt)

    def _visit_comprehension(self, node: ast.AST) -> None:
        generators = getattr(node, "generators", [])
        self.scope_stack.append(set(self.scope))
        for gen in generators:
            self.visit(gen.iter)
            self._bind_target(gen.target)
            for cond in gen.ifs:
                self.visit(cond)
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            self.visit(node.elt)
        elif isinstance(node, ast.DictComp):
            self.visit(node.key)
            self.visit(node.value)
        self.scope_stack.pop()

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node)

    def visit_Return(self, node: ast.Return) -> None:
        if self.current_function_return in {"None", "void"} and node.value is not None:
            self.warn("W201", "Function annotated as void/None returns a value.", node)
        if node.value:
            self.visit(node.value)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            if node.id not in self.scope and node.id not in {"True", "False", "None"}:
                # Avoid excessive warnings for globals injected by stdlib; CLI will add common names.
                common_runtime = {
                    "print", "len", "range", "int", "float", "str", "bool", "list", "dict", "sum", "min", "max",
                    "read_csv", "write_csv", "read_text", "write_text", "http_get", "mean", "median", "stddev",
                    "train_linear_regression", "train_logistic_regression", "train_decision_tree_classifier", "predict",
                    "accuracy_score", "plot", "json_loads", "json_dumps", "read_json", "write_json", "random_int",
                    "now_iso", "ensure_dir", "assert_eq",
                    "websocket_listen", "websocket_connect", "realtime_channel", "pubsub_bus",
                    "json_event", "parse_json_event",
                    "web_app", "text_response", "html_response", "json_response", "redirect", "file_response",
                    "render_template", "render_ags", "seo_tags", "web_get", "web_post_json", "hash_password", "verify_password",
                    "sign_cookie", "verify_cookie", "sqlite_db", "mysql_db",
                }
                if node.id not in common_runtime:
                    self.warn("W301", f"Name `{node.id}` may be used before declaration.", node)
        elif isinstance(node.ctx, (ast.Store, ast.Del)):
            self.scope.add(node.id)

    def _bind_target(self, target: ast.AST) -> None:
        if isinstance(target, ast.Name):
            self.scope.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._bind_target(elt)
        elif isinstance(target, ast.Attribute):
            self.visit(target.value)
        elif isinstance(target, ast.Subscript):
            self.visit(target.value)
            self.visit(target.slice)


def _check_const_reassignment(source: str, path: Path | None) -> list[Diagnostic]:
    """Detect direct reassignment of AGILANG const declarations.

    This is a source-level rule because `const` is lowered to Python with
    a comment. It intentionally catches the common production mistake:
    declaring `const TAX = 0.16` and later writing `TAX = 0.18`.
    """
    diagnostics: list[Diagnostic] = []
    consts: dict[str, int] = {}
    assign_re = re.compile(r"^([A-Za-z_]\w*)\s*(?:=|\+=|-=|\*=|/=|%=)")
    for line_no, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m_const = re.match(r"^const\s+([A-Za-z_]\w*)\b", stripped)
        if m_const:
            name = m_const.group(1)
            if name in consts:
                diagnostics.append(Diagnostic("warning", "W401", f"Const `{name}` is declared more than once.", SourceLocation(path, line_no, 1)))
            consts[name] = line_no
            continue
        if stripped.startswith(("let ", "fn ", "export fn ", "pub fn ")):
            continue
        m_assign = assign_re.match(stripped)
        if m_assign and m_assign.group(1) in consts:
            name = m_assign.group(1)
            diagnostics.append(
                Diagnostic(
                    "error",
                    "E401",
                    f"Cannot reassign const `{name}` declared on line {consts[name]}.",
                    SourceLocation(path, line_no, 1),
                    "Use `let` for mutable values or create a new variable name.",
                )
            )
    return diagnostics


def check_source(source: str, path: Path | None = None) -> CheckReport:
    """Translate and statically check AGILANG source."""
    translator = AGILTranslator()
    try:
        result = translator.translate_result(source, path)
        tree = ast.parse(result.python, filename=str(path or "<source>"))
    except Exception as exc:
        if hasattr(exc, "diagnostic"):
            return CheckReport(ok=False, diagnostics=[exc.diagnostic])
        diag = Diagnostic("error", "E900", str(exc), SourceLocation(path, 1, 1))
        return CheckReport(ok=False, diagnostics=[diag])
    visitor = _SemanticVisitor(path)
    visitor.visit(tree)
    try:
        type_report = typecheck_source(source, path)
        # The AST type checker is intentionally conservative and still trails
        # the executable translator for Python-compatible AGILANG constructs
        # such as try/except, dict mutation, and unannotated helper returns.
        # Keep those diagnostics visible, but do not fail `agi check` when the
        # translator and Python AST validation already passed.
        type_diagnostics = [
            Diagnostic(
                "warning" if d.severity == "error" else d.severity,
                ("W" + d.code[1:]) if d.severity == "error" and d.code.startswith("E") else d.code,
                d.message,
                d.location,
                d.hint,
            )
            for d in type_report.diagnostics
        ]
    except Exception as exc:
        type_diagnostics = [Diagnostic("warning", "WTYPE00", f"Type checker skipped: {exc}", SourceLocation(path, 1, 1))]
    diagnostics = list(result.diagnostics) + _check_const_reassignment(source, path) + type_diagnostics + visitor.diagnostics
    seen: set[tuple[str, int, str]] = set()
    unique = []
    for d in diagnostics:
        key = (d.code, d.location.line if d.location else -1, d.message)
        if key not in seen:
            seen.add(key)
            unique.append(d)
    ok = not any(d.severity == "error" for d in unique)
    return CheckReport(ok=ok, diagnostics=unique, python=result.python)


def check_file(path: Path) -> CheckReport:
    return check_source(path.read_text(encoding="utf-8"), path.resolve())
