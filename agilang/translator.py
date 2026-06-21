"""
AGILANG source translator.

AGILANG v0.5 targets Python as its first production backend.  The
translator is intentionally conservative: it lowers AGILANG syntax to
valid Python while preserving line structure where possible so errors are
understandable.  It supports a practical language surface:

* fn / export fn function declarations
* let / const declarations with optional type annotations
* struct declarations lowered to dataclasses
* enum declarations lowered to Enum classes
* import "file.agi" or import module.agi for AGILANG modules
* normal Python-style control flow and expressions

The goal is not to pretend this is LLVM-grade yet.  The goal is to make
AGILANG installable, checkable, testable, and usable for real project
prototypes while the compiler evolves.
"""

from __future__ import annotations

import ast
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from .errors import Diagnostic, SourceLocation, TranslationError
from .lexer import tokenize


TYPE_MAP: dict[str, str] = {
    "i8": "int",
    "i16": "int",
    "i32": "int",
    "i64": "int",
    "u8": "int",
    "u16": "int",
    "u32": "int",
    "u64": "int",
    "int": "int",
    "f32": "float",
    "f64": "float",
    "float": "float",
    "str": "str",
    "string": "str",
    "bool": "bool",
    "any": "Any",
    "void": "None",
    "none": "None",
    "list": "list",
    "dict": "dict",
}


@dataclass
class TranslationResult:
    """A translated source unit."""

    python: str
    diagnostics: list[Diagnostic] = field(default_factory=list)
    imports_runtime: bool = False


def _split_params(params: str) -> list[str]:
    """Split function params while respecting nested brackets."""
    result: list[str] = []
    current: list[str] = []
    depth = 0
    quote: str | None = None
    for ch in params:
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            current.append(ch)
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            result.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        result.append(tail)
    return result


def normalize_type(type_name: str) -> str:
    """Map AGILANG aliases into Python annotations."""
    t = type_name.strip()
    if not t:
        return "Any"
    lower = t.lower()
    if lower in TYPE_MAP:
        return TYPE_MAP[lower]
    # Basic generics: list[i32] -> list[int], dict[str, i64] -> dict[str, int]
    for agi, py in sorted(TYPE_MAP.items(), key=lambda kv: -len(kv[0])):
        t = re.sub(rf"\b{re.escape(agi)}\b", py, t, flags=re.IGNORECASE)
    return t


def _convert_params(params: str) -> str:
    if not params.strip():
        return ""
    out: list[str] = []
    for raw in _split_params(params):
        if not raw:
            continue
        # Preserve *args / **kwargs simply.
        prefix = ""
        name_part = raw
        if raw.startswith("**"):
            prefix, name_part = "**", raw[2:].strip()
        elif raw.startswith("*"):
            prefix, name_part = "*", raw[1:].strip()
        default = ""
        if "=" in name_part:
            before, after = name_part.split("=", 1)
            name_part = before.strip()
            default = " = " + after.strip()
        if ":" in name_part:
            name, type_name = name_part.split(":", 1)
            out.append(f"{prefix}{name.strip()}: {normalize_type(type_name)}{default}")
        else:
            out.append(f"{prefix}{name_part.strip()}{default}")
    return ", ".join(out)


class AGILTranslator:
    """Translate AGILANG source into Python source."""

    def __init__(self) -> None:
        self._module_cache: Dict[Path, str] = {}
        self.diagnostics: list[Diagnostic] = []
        self._dataclass_needed = False
        self._enum_needed = False
        self._typing_needed = False

    def translate_file(self, path: Path) -> str:
        """Translate a `.agi` file into Python source."""
        path = path.resolve()
        if path in self._module_cache:
            return self._module_cache[path]
        if not path.exists():
            raise TranslationError(
                Diagnostic(
                    "error",
                    "E001",
                    f"Cannot find AGILANG module: {path}",
                    SourceLocation(path, 1, 1),
                )
            )
        source = path.read_text(encoding="utf-8")
        code = self.translate(source, path)
        self._module_cache[path] = code
        return code

    def translate(self, source: str, path: Optional[Path] = None) -> str:
        """Translate AGILANG source text into Python code."""
        self.diagnostics.clear()
        self._dataclass_needed = False
        self._enum_needed = False
        self._typing_needed = False
        result = self.translate_result(source, path)
        return result.python

    def translate_result(self, source: str, path: Optional[Path] = None) -> TranslationResult:
        # Lex first so obvious source-level mistakes get AGILANG diagnostics.
        tokenize(source, path)
        lines = source.splitlines()
        python_lines: List[str] = []
        preamble_lines: List[str] = []
        imported_files: Set[Path] = set()

        for idx, line in enumerate(lines, start=1):
            translated = self._translate_line(line, idx, path, imported_files, preamble_lines)
            if translated is None:
                continue
            python_lines.append(translated)

        header: list[str] = []
        if self._dataclass_needed:
            header.append("from dataclasses import dataclass")
        if self._enum_needed:
            header.append("from enum import Enum, auto")
        if self._typing_needed:
            header.append("from typing import Any")
        if header:
            header.append("")

        full_code_lines: list[str] = []
        full_code_lines.extend(header)
        full_code_lines.extend(preamble_lines)
        full_code_lines.extend(python_lines)
        python = "\n".join(full_code_lines) + "\n"

        # Validate emitted Python early; this is a production guardrail.
        try:
            ast.parse(python, filename=str(path or "<source>"))
        except SyntaxError as exc:
            loc = SourceLocation(path, exc.lineno or 1, exc.offset or 1)
            raise TranslationError(
                Diagnostic(
                    "error",
                    "E099",
                    f"Generated Python is invalid: {exc.msg}",
                    loc,
                    "Run `agilang to-py --line-map` to inspect generated output.",
                )
            ) from exc

        return TranslationResult(python=python, diagnostics=list(self.diagnostics))

    def _translate_line(
        self,
        line: str,
        line_no: int,
        path: Optional[Path],
        imported_files: Set[Path],
        preamble_lines: List[str],
    ) -> Optional[str]:
        stripped = line.lstrip()
        leading_ws = line[: len(line) - len(stripped)]
        location = SourceLocation(path, line_no, len(leading_ws) + 1)

        if not stripped or stripped.startswith("#"):
            return line

        # AGILANG module imports.
        if stripped.startswith("import "):
            module_spec = stripped[len("import "):].strip()
            if module_spec.startswith(('"', "'")) and module_spec.endswith(('"', "'")):
                module_name = module_spec[1:-1]
            else:
                module_name = module_spec.split()[0].rstrip(",")
            if module_name.endswith(".agi"):
                if path is None:
                    raise TranslationError(
                        Diagnostic(
                            "error",
                            "E010",
                            "Relative AGILANG import requires a source file path.",
                            location,
                        )
                    )
                module_path = (path.parent / module_name).resolve()
                if module_path not in imported_files:
                    imported_files.add(module_path)
                    module_code = self.translate_file(module_path)
                    preamble_lines.append(f"# BEGIN imported from {module_name}")
                    preamble_lines.append(textwrap.dedent(module_code).rstrip())
                    preamble_lines.append(f"# END imported from {module_name}\n")
                return f"{leading_ws}# import {module_name}"
            return line

        # export fn / pub fn are accepted for package/module compatibility.
        exported = False
        if stripped.startswith("export fn "):
            exported = True
            stripped = stripped[len("export "):]
        elif stripped.startswith("pub fn "):
            exported = True
            stripped = stripped[len("pub "):]

        if stripped.startswith("fn "):
            fn_pattern = re.compile(
                r"^fn\s+([A-Za-z_]\w*)\s*\((.*)\)\s*(?:->\s*([^:]+))?\s*:\s*$"
            )
            match = fn_pattern.match(stripped)
            if not match:
                raise TranslationError(
                    Diagnostic(
                        "error",
                        "E020",
                        f"Invalid function definition: {stripped}",
                        location,
                        "Use: fn name(arg: type = value) -> type:",
                    )
                )
            name, params, ret = match.group(1), match.group(2), match.group(3)
            py_params = _convert_params(params)
            py_ret = f" -> {normalize_type(ret)}" if ret else ""
            if ret and normalize_type(ret) == "Any":
                self._typing_needed = True
            if "Any" in py_params:
                self._typing_needed = True
            suffix = "  # exported" if exported else ""
            return f"{leading_ws}def {name}({py_params}){py_ret}:{suffix}"

        if stripped.startswith("let ") or stripped.startswith("const "):
            is_const = stripped.startswith("const ")
            keyword = "const" if is_const else "let"
            decl = stripped[len(keyword) :].strip()
            decl_pattern = re.compile(r"^([A-Za-z_]\w*)\s*(?::\s*([^=]+))?\s*=\s*(.+)$")
            match = decl_pattern.match(decl)
            if not match:
                raise TranslationError(
                    Diagnostic(
                        "error",
                        "E030",
                        f"Invalid {keyword} declaration: {stripped}",
                        location,
                        f"Use: {keyword} name: type = expression",
                    )
                )
            name, annotation, expr = match.group(1), match.group(2), match.group(3)
            suffix = "  # const" if is_const else ""
            if annotation:
                py_type = normalize_type(annotation)
                if py_type == "Any":
                    self._typing_needed = True
                return f"{leading_ws}{name}: {py_type} = {expr}{suffix}"
            return f"{leading_ws}{name} = {expr}{suffix}"

        if stripped.startswith("type "):
            match = re.match(r"^type\s+([A-Za-z_]\w*)\s*=\s*(.+)$", stripped)
            if not match:
                raise TranslationError(
                    Diagnostic(
                        "error",
                        "E035",
                        f"Invalid type alias: {stripped}",
                        location,
                        "Use: type Name = ExistingType",
                    )
                )
            alias, target = match.group(1), normalize_type(match.group(2))
            if "Any" in target:
                self._typing_needed = True
            return f"{leading_ws}{alias} = {target}  # type alias"

        if stripped.startswith("struct "):
            match = re.match(r"^struct\s+([A-Za-z_]\w*)\s*:\s*$", stripped)
            if not match:
                raise TranslationError(
                    Diagnostic(
                        "error",
                        "E040",
                        f"Invalid struct declaration: {stripped}",
                        location,
                        "Use: struct Name:",
                    )
                )
            self._dataclass_needed = True
            return f"{leading_ws}@dataclass\n{leading_ws}class {match.group(1)}:"

        if stripped.startswith("enum "):
            match = re.match(r"^enum\s+([A-Za-z_]\w*)\s*:\s*$", stripped)
            if not match:
                raise TranslationError(
                    Diagnostic(
                        "error",
                        "E050",
                        f"Invalid enum declaration: {stripped}",
                        location,
                        "Use: enum Name:",
                    )
                )
            self._enum_needed = True
            return f"{leading_ws}class {match.group(1)}(Enum):"

        # Inside enum blocks, allow bare identifiers: PENDING -> PENDING = auto()
        if re.match(r"^[A-Z][A-Z0-9_]*\s*$", stripped):
            self._enum_needed = True
            return f"{leading_ws}{stripped.strip()} = auto()"

        # Struct fields and normal annotations: name: i32 -> name: int
        annotation_match = re.match(r"^([A-Za-z_]\w*)\s*:\s*([^=#]+)(.*)$", stripped)
        if annotation_match and not stripped.startswith(("if ", "elif ", "while ", "for ", "case ")):
            name, type_name, tail = annotation_match.groups()
            py_type = normalize_type(type_name)
            if py_type == "Any":
                self._typing_needed = True
            return f"{leading_ws}{name}: {py_type}{tail}"

        return line
