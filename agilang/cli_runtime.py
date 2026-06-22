"""Extended AGILANG CLI router.

This wrapper keeps the existing AGILANG CLI intact, but intercepts the new
first-class blockchain generator/runtime commands so users can create and run a
complete chain with one command.
"""
from __future__ import annotations

import json
import sys
from typing import List

from .blockchain_runtime_gateway import generate_blockchain_app, print_project_status, serve_project_rpc


def _value(args: List[str], name: str, default: str | None = None) -> str | None:
    if name not in args:
        return default
    idx = args.index(name)
    if idx + 1 >= len(args):
        return default
    return args[idx + 1]


def _flag(args: List[str], name: str) -> bool:
    return name in args


def _positional(args: List[str]) -> List[str]:
    values: List[str] = []
    takes_value = {
        "--template", "--dir", "--chain-id", "--symbol", "--mode", "--root",
        "--host", "--port", "--config", "--jwt-secret", "--execution-rpc", "--beacon-api",
    }
    skip = False
    for item in args:
        if skip:
            skip = False
            continue
        if item in takes_value:
            skip = True
            continue
        if item.startswith("--"):
            continue
        values.append(item)
    return values


def _new_blockchain(argv: List[str], name_args: List[str]) -> int:
    name = " ".join(_positional(name_args)) or "my-chain"
    result = generate_blockchain_app(
        name,
        _value(argv, "--dir"),
        force=_flag(argv, "--force"),
        chain_id=int(_value(argv, "--chain-id", "1900") or "1900"),
        symbol=_value(argv, "--symbol", "SBQ") or "SBQ",
        mode=_value(argv, "--mode", "validator") or "validator",
    )
    print(json.dumps(result, indent=2))
    return 0


def _intercept(argv: List[str]) -> int | None:
    if not argv:
        return None

    # agi new my-chain --template blockchain
    if argv[0] == "new" and "--template" in argv and _value(argv, "--template") == "blockchain":
        return _new_blockchain(argv, argv[1:])

    # agi blockchain new my-chain
    if argv[0] == "blockchain" and len(argv) >= 2 and argv[1] in {"new", "init", "create"}:
        return _new_blockchain(argv, argv[2:])

    # agi chain init my-chain
    if argv[0] == "chain" and len(argv) >= 2 and argv[1] in {"init", "new", "create"}:
        return _new_blockchain(argv, argv[2:])

    # Project-local runtime commands: agi chain rpc/status/head/finalized/validators
    if argv[0] == "chain" and len(argv) >= 2 and argv[1] in {"rpc", "status", "head", "finalized", "validators"}:
        root = _value(argv, "--root", ".") or "."
        if argv[1] == "rpc":
            host = _value(argv, "--host")
            port_raw = _value(argv, "--port")
            serve_project_rpc(root, host=host, port=int(port_raw) if port_raw else None)
            return 0
        print_project_status(root)
        return 0

    # Ethereum external-client commands provided by agilang.ethereum_clients.
    if argv[0] == "chain" and len(argv) >= 2 and argv[1].startswith("ethereum-"):
        from .ethereum_clients import (
            default_ethereum_client_config,
            detect_installed_ethereum_clients,
            ensure_jwt_secret,
            ethereum_client_capabilities,
            ethereum_connectivity_smoke,
            ethereum_stack_check,
            ethereum_stack_plan,
            start_ethereum_stack,
            write_ethereum_client_config,
        )
        cmd = argv[1]
        if cmd == "ethereum-clients":
            print(json.dumps(ethereum_client_capabilities(), indent=2))
        elif cmd == "ethereum-detect":
            print(json.dumps(detect_installed_ethereum_clients(), indent=2))
        elif cmd == "ethereum-jwt":
            print(json.dumps(ensure_jwt_secret(_value(argv, "--jwt-secret", "ethereum-data/jwt.hex") or "ethereum-data/jwt.hex"), indent=2))
        elif cmd == "ethereum-write-config":
            cfg = default_ethereum_client_config(mode=_value(argv, "--mode", "full") or "full")
            print(json.dumps(write_ethereum_client_config(_value(argv, "--config", "config/ethereum-clients.json") or "config/ethereum-clients.json", cfg), indent=2))
        elif cmd == "ethereum-plan":
            cfg = default_ethereum_client_config(mode=_value(argv, "--mode", "full") or "full")
            print(json.dumps(ethereum_stack_plan(cfg, mode=_value(argv, "--mode", "full") or "full"), indent=2))
        elif cmd == "ethereum-check":
            print(json.dumps(ethereum_stack_check(_value(argv, "--config", "config/ethereum-clients.json") or "config/ethereum-clients.json", require_installed=_flag(argv, "--require-installed")), indent=2))
        elif cmd == "ethereum-connectivity":
            print(json.dumps(ethereum_connectivity_smoke(_value(argv, "--execution-rpc", "http://127.0.0.1:8545") or "http://127.0.0.1:8545", _value(argv, "--beacon-api", "http://127.0.0.1:5052") or "http://127.0.0.1:5052"), indent=2))
        elif cmd == "ethereum-start":
            print(json.dumps(start_ethereum_stack(_value(argv, "--config", "config/ethereum-clients.json") or "config/ethereum-clients.json", mode=_value(argv, "--mode", "full") or "full", dry_run=_flag(argv, "--dry-run")), indent=2))
        else:
            return None
        return 0

    return None


def main(argv: List[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    intercepted = _intercept(args)
    if intercepted is not None:
        raise SystemExit(intercepted)
    from .cli import main as legacy_main
    legacy_main()


if __name__ == "__main__":
    main()
