"""Complete production-oriented AGILANG Smart Chain project generator.

This replaces the historical toy blockchain scaffold with a deployable project
layout backed by AGILANG's real in-house execution, RPC, beacon, validator,
P2P, slashing-protection, monitoring, and EVM runtime modules.
"""
from __future__ import annotations

import json
import os
import stat
import textwrap
from pathlib import Path
from typing import Any

from . import scaffold as _legacy


DEFAULT_CHAIN_ID = 1990
DEFAULT_CHAIN_ID_HEX = "0x7c6"


def _write(path: Path, content: str, files: list[Path], *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    if executable and os.name != "nt":
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    files.append(path)


def _write_json(path: Path, value: Any, files: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    files.append(path)


def _chain_configs(slug: str, title: str) -> dict[str, Any]:
    funded = "0x1000000000000000000000000000000000000001"
    validator = "0x2000000000000000000000000000000000000002"
    return {
        "genesis.json": {
            "config": {
                "chainId": DEFAULT_CHAIN_ID,
                "homesteadBlock": 0,
                "eip150Block": 0,
                "eip155Block": 0,
                "eip158Block": 0,
                "byzantiumBlock": 0,
                "constantinopleBlock": 0,
                "petersburgBlock": 0,
                "istanbulBlock": 0,
                "berlinBlock": 0,
                "londonBlock": 0,
                "shanghaiTime": 0,
            },
            "nonce": "0x0",
            "timestamp": "0x0",
            "extraData": "0x",
            "gasLimit": "0x1c9c380",
            "difficulty": "0x1",
            "alloc": {funded: {"balance": "100000000000000000000000000"}},
        },
        "network.json": {
            "name": slug,
            "display_name": title,
            "chain_id": DEFAULT_CHAIN_ID,
            "network_id": DEFAULT_CHAIN_ID,
            "native_currency": {"name": "Smart Chain Token", "symbol": "SBQ", "decimals": 18},
            "rpc_http": "http://127.0.0.1:8545",
            "engine_http": "http://127.0.0.1:8551",
            "p2p_host": "0.0.0.0",
            "p2p_port": 30333,
        },
        "rpc.json": {
            "host": "127.0.0.1",
            "port": 8545,
            "chain_id": DEFAULT_CHAIN_ID,
            "client_version": f"AGILANG-{slug}/1.0.0",
            "cors_origins": ["http://localhost", "http://127.0.0.1"],
            "modules": ["web3", "net", "eth", "txpool", "debug"],
            "request_body_limit": 1048576,
            "rate_limit_per_minute": 1200,
        },
        "beacon.json": {
            "enabled": True,
            "slot_seconds": 12,
            "slots_per_epoch": 32,
            "finality_depth": 8,
            "database": "storage/beacon.sqlite",
            "empty_block_production": True,
        },
        "validators.json": {
            "chain_id": DEFAULT_CHAIN_ID,
            "consensus": "pos-beacon",
            "validator_address": validator,
            "validators": [{"address": validator, "weight": 100, "enabled": True}],
            "slot_seconds": 12,
            "block_gas_limit": 30000000,
        },
        "p2p.json": {
            "enabled": True,
            "listen_host": "0.0.0.0",
            "listen_port": 30333,
            "max_peers": 50,
            "min_peers": 1,
            "bootnodes": [],
            "discovery": True,
            "peer_scoring": True,
        },
        "security.json": {
            "public_rpc": False,
            "engine_api_requires_jwt": True,
            "jwt_secret_file": "config/jwt.hex",
            "reject_replays": True,
            "max_clock_skew_seconds": 30,
            "max_request_bytes": 1048576,
            "production_secrets_required": True,
        },
        "slashing.json": {
            "enabled": True,
            "database": "storage/slashing.sqlite",
            "reject_double_proposals": True,
            "reject_double_votes": True,
            "reject_surround_votes": True,
        },
        "performance.json": {
            "worker_threads": 2,
            "max_pending_transactions": 10000,
            "block_batch_size": 500,
            "state_cache_mb": 256,
            "historical_scan_enabled": False,
            "resource_monitor_interval_seconds": 15,
        },
        "readiness.json": {
            "required_checks": ["chain", "rpc", "engine", "beacon", "validator", "p2p", "slashing"],
            "minimum_peer_count": 0,
            "maximum_slot_lag": 2,
            "maximum_disk_usage_percent": 85,
            "maximum_memory_pressure_percent": 80,
        },
        "chain-services.json": {
            "profile": "local",
            "chain_id": DEFAULT_CHAIN_ID,
            "database": "storage/chain.sqlite",
            "genesis": "config/genesis.json",
            "rpc": "config/rpc.json",
            "beacon": "config/beacon.json",
            "validators": "config/validators.json",
            "p2p": "config/p2p.json",
            "security": "config/security.json",
            "slashing": "config/slashing.json",
            "performance": "config/performance.json",
            "start": {"execution": True, "rpc": True, "engine": True, "beacon": True, "validator": True, "p2p": True},
        },
        "metamask.json": {
            "chainId": DEFAULT_CHAIN_ID_HEX,
            "chainName": title,
            "nativeCurrency": {"name": "Smart Chain Token", "symbol": "SBQ", "decimals": 18},
            "rpcUrls": ["http://127.0.0.1:8545"],
            "blockExplorerUrls": ["http://127.0.0.1:8545/explorer"],
        },
    }


def create_smart_chain_project(
    name: str,
    *,
    directory: str | Path | None = None,
    force: bool = False,
) -> _legacy.ScaffoldResult:
    slug = _legacy.slugify_project_name(name)
    title = _legacy.titleize(slug)
    parent = Path(directory).expanduser().resolve() if directory else Path.cwd().resolve()
    root = parent / slug
    if root.exists() and any(root.iterdir()) and not force:
        raise FileExistsError(f"Directory exists and is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []

    _write(root / "agilang.toml", f'''
        [project]
        name = "{slug}"
        version = "1.0.0"
        entry = "src/main.agi"
        template = "blockchain"

        [blockchain]
        implementation = "smart-chain"
        chain_id = {DEFAULT_CHAIN_ID}
        execution = "native-evm"
        consensus = "pos-beacon"
        rpc = "http://127.0.0.1:8545"
        engine = "http://127.0.0.1:8551"
        p2p_port = 30333
        slot_seconds = 12

        [runtime]
        mode = "production"
        bundled = true
        ''', files)
    _write(root / ".gitignore", '''
        __pycache__/
        .pytest_cache/
        .env
        storage/*.sqlite
        storage/*.sqlite-*
        storage/*.log
        config/jwt.hex
        config/validator-keys.json
        build/
        dist/
        ''', files)
    _write(root / ".env.example", f'''
        AGILANG_CHAIN_ID={DEFAULT_CHAIN_ID}
        AGILANG_CHAIN_CONFIG=config/chain-services.json
        AGILANG_RPC_HOST=127.0.0.1
        AGILANG_RPC_PORT=8545
        AGILANG_ENGINE_HOST=127.0.0.1
        AGILANG_ENGINE_PORT=8551
        AGILANG_P2P_PORT=30333
        AGILANG_PROFILE=local
        ''', files)
    _write(root / ".env.production.example", '''
        AGILANG_PROFILE=production
        AGILANG_RPC_HOST=127.0.0.1
        AGILANG_ENGINE_HOST=127.0.0.1
        AGILANG_PUBLIC_RPC=false
        AGILANG_VALIDATOR_KEY_FILE=/secure/path/validator-keys.json
        AGILANG_JWT_SECRET_FILE=/secure/path/jwt.hex
        ''', files)

    for filename, value in _chain_configs(slug, title).items():
        _write_json(root / "config" / filename, value, files)
    _write_json(root / "config/profiles/local.json", {"name": "local", "public_rpc": False, "p2p_discovery": True, "empty_blocks": True}, files)
    _write_json(root / "config/profiles/production.json", {"name": "production", "public_rpc": False, "require_external_signer": True, "require_jwt": True, "minimum_peers": 1}, files)
    _write(root / "config/jwt.hex.example", "REPLACE_WITH_32_BYTE_HEX_SECRET\n", files)

    _write(root / "src/main.agi", '''
        fn main() -> i32:
            print("AGILANG Smart Chain project")
            print("Start: agi blockchain start --config config/chain-services.json")
            print("RPC: http://127.0.0.1:8545")
            print("Chain ID: 1990")
            return 0
        ''', files)
    _write(root / "src/chain.agi", f'''
        fn main() -> i32:
            let cfg = blockchain_config(chain_id={DEFAULT_CHAIN_ID}, name="{slug}", validators={{"validator-1": 100}}, slot_seconds=12)
            let node = blockchain_node(cfg, "../storage/chain.sqlite", "validator-1")
            print("head", node.head())
            print("finalized", node.finalized_head())
            return 0
        ''', files)
    _write(root / "src/rpc.agi", '''
        fn main() -> i32:
            print("Use the complete native RPC service:")
            print("agi blockchain start --config ../config/chain-services.json")
            return 0
        ''', files)
    _write(root / "src/devnet.agi", f'''
        fn main() -> i32:
            let cfg = blockchain_config(chain_id={DEFAULT_CHAIN_ID}, name="{slug}-devnet", validators={{"validator-1": 100}}, slot_seconds=12)
            let net = blockchain_devnet(cfg, ["validator-1"])
            print("step", net.step())
            print("sync", net.sync_all())
            return 0
        ''', files)

    _write(root / "scripts/run_chain.py", '''
        from agilang.inhouse_chain import main
        if __name__ == "__main__":
            raise SystemExit(main())
        ''', files)
    _write(root / "scripts/run_validator.py", '''
        from agilang.inhouse_chain import main
        if __name__ == "__main__":
            raise SystemExit(main())
        ''', files)
    _write(root / "scripts/run_p2p_node.py", '''
        from agilang.p2p_node import main
        if __name__ == "__main__":
            raise SystemExit(main())
        ''', files)
    _write(root / "scripts/rpc_gate.py", '''
        import json
        import urllib.request
        def rpc(method, params=None):
            body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
            req = urllib.request.Request("http://127.0.0.1:8545", data=body, headers={"Content-Type":"application/json"})
            return json.load(urllib.request.urlopen(req, timeout=5))
        if __name__ == "__main__":
            for method in ("web3_clientVersion", "eth_chainId", "eth_blockNumber"):
                print(method, rpc(method))
        ''', files)
    _write(root / "scripts/readiness.py", '''
        import json
        from pathlib import Path
        required = ["genesis.json", "network.json", "rpc.json", "beacon.json", "validators.json", "p2p.json", "security.json", "slashing.json", "chain-services.json"]
        missing = [name for name in required if not (Path("config") / name).exists()]
        print(json.dumps({"ready": not missing, "missing": missing}, indent=2))
        raise SystemExit(1 if missing else 0)
        ''', files)
    _write(root / "scripts/monitor_resources.py", '''
        from agilang.resource_monitor import main
        if __name__ == "__main__":
            raise SystemExit(main())
        ''', files)

    _write(root / "start-chain.ps1", '''
        $ErrorActionPreference = "Stop"
        python -m agilang.inhouse_chain --config config/chain-services.json
        ''', files)
    _write(root / "start-chain.cmd", '''
        @echo off
        python -m agilang.inhouse_chain --config config\chain-services.json
        ''', files)
    _write(root / "start-chain.sh", '''
        #!/usr/bin/env sh
        set -eu
        python -m agilang.inhouse_chain --config config/chain-services.json
        ''', files, executable=True)

    _write(root / "README.md", f'''
        # {title} — AGILANG Smart Chain

        Generated by AGILANG as the **complete default blockchain application**.
        This is not the former boilerplate SQLite blockchain starter.

        Included architecture:

        - native EVM execution client and persistent state
        - Ethereum-compatible JSON-RPC on `127.0.0.1:8545`
        - authenticated Engine API on `127.0.0.1:8551`
        - PoS beacon slots, validator production, fork choice and finality
        - mempool admission and block production
        - P2P node configuration and peer controls
        - slashing protection
        - local and production profiles
        - MetaMask network configuration
        - readiness, RPC compatibility and resource-monitoring scripts
        - bundled AGILANG runtime for self-contained execution

        ## Run

        ```bash
        ./start-chain.sh
        ```

        Windows PowerShell:

        ```powershell
        .\\start-chain.ps1
        ```

        Direct command:

        ```bash
        agi blockchain start --config config/chain-services.json
        ```

        ## Verify

        ```bash
        python scripts/readiness.py
        python scripts/rpc_gate.py
        ```

        Chain ID: `{DEFAULT_CHAIN_ID}` (`{DEFAULT_CHAIN_ID_HEX}`).

        Before public production deployment, replace the example validator identity,
        create a strong Engine API JWT secret, use an external signer or protected key
        file, configure bootnodes, restrict RPC exposure, and run an independent audit.
        ''', files)
    _write(root / "storage/.gitkeep", "\n", files)
    _write(root / "tests/test_smart_chain_scaffold.py", f'''
        import json
        from pathlib import Path
        ROOT = Path(__file__).resolve().parents[1]
        assert json.loads((ROOT / "config/network.json").read_text())["chain_id"] == {DEFAULT_CHAIN_ID}
        assert (ROOT / "config/chain-services.json").exists()
        assert (ROOT / "vendor/agilang/inhouse_chain.py").exists()
        ''', files)

    _legacy._copy_vendor_runtime(root, files)
    return _legacy.ScaffoldResult(root=root, files=files, template="blockchain")


def create_project(
    name: str,
    *,
    directory: str | Path | None = None,
    template: str = "web",
    force: bool = False,
) -> _legacy.ScaffoldResult:
    normalized = (template or "web").lower()
    if normalized in {"blockchain", "evm", "smart-chain", "smart_chain", "chain"}:
        return create_smart_chain_project(name, directory=directory, force=force)
    return _legacy.create_project(name, directory=directory, template=template, force=force)
