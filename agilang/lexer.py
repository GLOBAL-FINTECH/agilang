"""AGILANG lexical scanner.

This lexer is intentionally small but production-useful: it gives the
compiler and tools stable token positions for diagnostics, formatting,
syntax highlighting, and future parser work. The Python backend still
handles expressions, but AGILANG-owned syntax now has a real token layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .errors import Diagnostic, SourceLocation, TranslationError

KEYWORDS = {
    "fn", "export", "pub", "let", "const", "struct", "enum", "type",
    "import", "from", "as", "return", "if", "elif", "else", "for", "while",
    "in", "match", "case", "break", "continue", "and", "or", "not",
    "True", "False", "None",
}

MULTI_CHAR_SYMBOLS = {
    "->", "==", "!=", "<=", ">=", "//", "**", "+=", "-=", "*=", "/=", "%=", ":=",
}

SINGLE_CHAR_SYMBOLS = set("()[]{}:,.=+-*/%<>!&|;@")


@dataclass(frozen=True)
class Token:
    """A lexical token with source location."""

    kind: str
    value: str
    line: int
    column: int

    def display(self) -> str:
        return f"{self.kind}({self.value!r})@{self.line}:{self.column}"


def tokenize(source: str, path: Path | None = None) -> list[Token]:
    """Tokenize AGILANG source.

    The scanner is expression-tolerant because AGILANG currently reuses
    Python expression syntax. It still rejects unterminated strings and
    unknown characters with source locations.
    """
    tokens: list[Token] = []
    line = 1
    col = 1
    i = 0
    n = len(source)

    def add(kind: str, value: str, start_line: int, start_col: int) -> None:
        tokens.append(Token(kind, value, start_line, start_col))

    while i < n:
        ch = source[i]
        start_line, start_col = line, col

        if ch in " \t\r":
            i += 1
            col += 1
            continue
        if ch == "\n":
            add("NEWLINE", "\\n", start_line, start_col)
            i += 1
            line += 1
            col = 1
            continue
        if ch == "#":
            start = i
            while i < n and source[i] != "\n":
                i += 1
                col += 1
            add("COMMENT", source[start:i], start_line, start_col)
            continue
        if ch.isalpha() or ch == "_":
            start = i
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i += 1
                col += 1
            value = source[start:i]
            add("KEYWORD" if value in KEYWORDS else "IDENT", value, start_line, start_col)
            continue
        if ch.isdigit():
            start = i
            seen_dot = False
            while i < n and (source[i].isdigit() or (source[i] == "." and not seen_dot)):
                if source[i] == ".":
                    seen_dot = True
                i += 1
                col += 1
            add("NUMBER", source[start:i], start_line, start_col)
            continue
        if ch in ('"', "'"):
            quote = ch
            start = i
            i += 1
            col += 1
            escaped = False
            closed = False
            while i < n:
                c = source[i]
                if c == "\n" and not escaped:
                    break
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == quote:
                    i += 1
                    col += 1
                    closed = True
                    break
                i += 1
                col += 1
            if not closed:
                raise TranslationError(
                    Diagnostic(
                        "error",
                        "ELEX01",
                        "Unterminated string literal.",
                        SourceLocation(path, start_line, start_col),
                    )
                )
            add("STRING", source[start:i], start_line, start_col)
            continue
        two = source[i : i + 2]
        if two in MULTI_CHAR_SYMBOLS:
            add("SYMBOL", two, start_line, start_col)
            i += 2
            col += 2
            continue
        if ch in SINGLE_CHAR_SYMBOLS:
            add("SYMBOL", ch, start_line, start_col)
            i += 1
            col += 1
            continue
        raise TranslationError(
            Diagnostic(
                "error",
                "ELEX02",
                f"Unexpected character: {ch!r}",
                SourceLocation(path, start_line, start_col),
            )
        )

    tokens.append(Token("EOF", "", line, col))
    return tokens


def tokens_as_table(tokens: Iterable[Token]) -> str:
    rows = ["KIND       LINE COL  VALUE", "---------- ---- ---- ----------------"]
    for t in tokens:
        rows.append(f"{t.kind:<10} {t.line:>4} {t.column:>4} {t.value!r}")
    return "\n".join(rows)
