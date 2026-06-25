"""Vendored runtime packaging for generated AGILANG projects.

Generated blockchain projects can include a copy of the AGILANG runtime under
``vendor/agilang``. This keeps the generated project portable on a Python host
without requiring the AGILANG package to be installed globally.
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
            _write_launchers(root)
            return {"ok": True, "vendored": False, "path": str(destination), "reason": "already_exists"}
        shutil.rmtree(destination)

    vendor_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "*.sqlite", "*.db", "*.log"),
    )
    _write_launchers(root)
    _write_vendor_readme(vendor_root / "README.md")
    return {"ok": True, "vendored": True, "path": str(destination)}


def _write_launchers(root: Path) -> None:
    _write_text(root / "run.py", _launcher("run"))
    _write_text(root / "chain.py", _launcher("chain"))
    _write_text(root / "rpc.py", _launcher("rpc"))


def _launcher(kind: str) -> str:
    return f'''
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "vendor"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

if __name__ == "__main__":
    if "{kind}" == "run":
        from agilang.cli_runtime import main
        raise SystemExit(main(["run", "src/main.agi"]))
    if "{kind}" == "chain":
        from agilang.cli_runtime import main
        raise SystemExit(main(["chain", "status"]))
    if "{kind}" == "rpc":
        from agilang.blockchain_runtime_gateway import serve_project_rpc
        serve_project_rpc(ROOT)
'''


def _write_vendor_readme(path: Path) -> None:
    _write_text(path, '''
# Vendored AGILANG Runtime

This generated project includes the AGILANG runtime under `vendor/agilang`.
The project can be copied to a Python-capable server and started with:

```bash
python run.py
python chain.py
python rpc.py
```

The current backend is Python-hosted. The application code remains `.agi` and
`.ags`, and the vendored runtime provides the local compiler/runtime layer.
''')


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


__all__ = ["copy_runtime_vendor"]
