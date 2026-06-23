"""Diagnostics and exceptions for AGILANG."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class SourceLocation:
    """A location inside a source file."""

    path: Optional[Path]
    line: int
    column: int = 1

    def display(self) -> str:
        file_name = str(self.path) if self.path else "<source>"
        return f"{file_name}:{self.line}:{self.column}"


@dataclass(frozen=True)
class Diagnostic:
    """A compiler diagnostic emitted by translation or checking."""

    severity: str
    code: str
    message: str
    location: Optional[SourceLocation] = None
    hint: Optional[str] = None

    def format(self) -> str:
        prefix = f"{self.severity.upper()}[{self.code}]"
        if self.location:
            prefix += f" at {self.location.display()}"
        output = f"{prefix}: {self.message}"
        if self.hint:
            output += f"\n  hint: {self.hint}"
        return output


class AGILangError(Exception):
    """Base class for AGILANG compiler/runtime-facing errors."""

    def __init__(self, diagnostic: Diagnostic):
        self.diagnostic = diagnostic
        super().__init__(diagnostic.format())


class TranslationError(AGILangError):
    """Raised when source cannot be translated."""


class CheckError(AGILangError):
    """Raised when static checking fails."""
