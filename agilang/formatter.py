"""Small AGILANG formatter.

The formatter is deliberately safe and minimal.  It normalizes trailing
spaces and common keyword spacing without reflowing user expressions.
"""

from __future__ import annotations

import re
from pathlib import Path


def format_source(source: str) -> str:
    lines: list[str] = []
    for line in source.splitlines():
        stripped_right = line.rstrip()
        stripped_left = stripped_right.lstrip()
        leading = stripped_right[: len(stripped_right) - len(stripped_left)]
        # Normalize fn spacing: fn  main (x : i32)->i32: -> fn main(x: i32) -> i32:
        if stripped_left.startswith("fn ") or stripped_left.startswith("export fn "):
            stripped_left = re.sub(r"\s+", " ", stripped_left)
            stripped_left = re.sub(r"\s*\(\s*", "(", stripped_left)
            stripped_left = re.sub(r"\s*\)\s*", ") ", stripped_left)
            stripped_left = re.sub(r"\s*->\s*", " -> ", stripped_left)
            stripped_left = stripped_left.replace(" :", ":")
            stripped_left = re.sub(r"\s+:\s*$", ":", stripped_left)
        if stripped_left.startswith(("let ", "const ")):
            stripped_left = re.sub(r"\s*=\s*", " = ", stripped_left, count=1)
            stripped_left = stripped_left.replace(" :", ":")
        lines.append(leading + stripped_left)
    return "\n".join(lines) + "\n"


def format_file(path: Path, write: bool = False) -> str:
    original = path.read_text(encoding="utf-8")
    formatted = format_source(original)
    if write and formatted != original:
        path.write_text(formatted, encoding="utf-8")
    return formatted
