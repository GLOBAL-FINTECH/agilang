"""AGILANG CLI entrypoint with the complete Smart Chain as the default chain scaffold."""
from __future__ import annotations

from pathlib import Path

from . import scaffold
from .frontend_compat import write_frontend
from .smart_chain_scaffold import create_project as _create_project


_CHAIN_TEMPLATES = {"blockchain", "evm", "smart-chain", "smart_chain", "chain"}


def create_project(
    name: str,
    *,
    directory: str | Path | None = None,
    template: str = "web",
    force: bool = False,
):
    """Create a project and include the uploaded-ZIP-compatible chain frontend."""
    result = _create_project(name, directory=directory, template=template, force=force)
    if (template or "").lower() in _CHAIN_TEMPLATES:
        config = result.root / "frontend" / "api-contract.json"
        if not config.exists():
            title = " ".join(part.capitalize() for part in result.root.name.replace("_", "-").split("-") if part)
            write_frontend(result.root, result.files, title=title or "AGILANG Smart Chain", chain_id=1990)
    return result


def main() -> None:
    # cli_runtime imports create_project from agilang.scaffold. Replace it before
    # loading cli_runtime so all blockchain/EVM aliases generate the complete
    # Smart Chain backend and its same-origin observability frontend together.
    scaffold.create_project = create_project
    from .cli_runtime import main as runtime_main

    runtime_main()


if __name__ == "__main__":
    main()
