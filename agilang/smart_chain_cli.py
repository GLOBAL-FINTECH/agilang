"""AGILANG CLI entrypoint with the complete Smart Chain as the default chain scaffold."""
from __future__ import annotations

from . import scaffold
from .smart_chain_scaffold import create_project


def main() -> None:
    # cli_runtime imports create_project from agilang.scaffold. Replace it before
    # loading cli_runtime so `agi new ... --template blockchain` and equivalent
    # EVM/chain aliases generate the complete Smart Chain application.
    scaffold.create_project = create_project
    from .cli_runtime import main as runtime_main

    runtime_main()


if __name__ == "__main__":
    main()
