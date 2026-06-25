"""Vendored runtime packaging for generated AGILANG projects.

Generated blockchain projects can include a copy of the AGILANG runtime under
``vendor/agilang``. This keeps the generated project portable on a Python host
without requiring the AGILANG package to be installed globally.

The project-facing entrypoints are AGILANG files, not Python files:
``run.agi``, ``chain.agi`` and ``rpc.agi``.
"""
from __future__ import annotations

import shutil
import textwrap
from pathlib import Path
from typing import Any


def copy_runtime_vendor(project_root: str | Path, *, force: bool = False) -> dict[str, Any]:
    """Copy the installed AGILANG runtime package into a generated project."""
    root = Path(project_root).resolve()
    source = Path(__file__).resolve().parent
    vendor_root = root / "vendor"
    destination = vendor_root / "agilang"

    if destination.exists():
        if not force:
            _write_agi_entrypoints(root)
            return {"ok": True, "vendored": False, "path": str(destination), "reason": "already_exists"}
        shutil.rmtree(destination)

    vendor_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "*.sqlite", "*.db", "*.log"),
    )
    _write_agi_entrypoints(root)
    _write_vendor_readme(vendor_root / "README.md")
    return {"ok": True, "vendored": True, "path": str(destination)}


def _write_agi_entrypoints(root: Path) -> None:
    """Write root-level AGILANG entrypoints for the generated chain."""
    _write_text(root / "run.agi", '''
        fn main() -> i32:
            print("AGILANG standalone blockchain runtime")
            print("entry", "src/main.agi")
            print("next", "run chain.agi for status or rpc.agi for RPC profile")
            return include("src/main.agi")
        ''')
    _write_text(root / "chain.agi", '''
        fn main() -> i32:
            print("AGILANG standalone chain status")
            return include("src/chain.agi")
        ''')
    _write_text(root / "rpc.agi", '''
        fn main() -> i32:
            print("AGILANG standalone RPC profile")
            print("RPC config", "config/rpc.json")
            print("start RPC with the vendored AGILANG runtime command for this host")
            return include("src/rpc.agi")
        ''')


def _write_vendor_readme(path: Path) -> None:
    _write_text(path, '''
# Vendored AGILANG Runtime

This generated project includes the AGILANG runtime under `vendor/agilang`.
The blockchain app entrypoints are AGILANG source files at the project root:

```bash
agi run run.agi
agi run chain.agi
agi run rpc.agi
```

On a clean server, point your AGILANG runner to the local `vendor/` folder or
install the AGILANG command from the vendored runtime. The app-facing files are
`.agi` and `.ags`; Python remains the current runtime backend internally.
''')


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


__all__ = ["copy_runtime_vendor"]
