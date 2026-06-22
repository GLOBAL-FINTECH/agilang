"""Single-command blockchain app generator and runtime gateway for AGILANG.

This module turns the AGILANG blockchain framework into an out-of-the-box
chain starter experience. It intentionally keeps the user workflow simple while
keeping the generated app modular inside:

    agi chain init my-chain
    cd my-chain
    agi run
    agi chain rpc

The generated project includes chain config, validator config, genesis config,
JSON-RPC config, staking config, Ethereum external-client config, runbooks and
safe wallet placeholders. Private keys are never generated into committed files.
"""
from __future__ import annotations

import json
import re
import textwrap
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List

from . import __version__
from .blockchain import blockchain_config, blockchain_node, blockchain_transaction


DEFAULT_VALIDATORS: Dict[str, int] = {
    "0x04aac0173878aee604c1eaec3455ca8b5719f39b": 40,
    "0x95e3673f703cb53b3c1848cd3def70a64c59fb08": 35,
    "0x42753c26f7ef0deedcd27967b34ed48b294e1443": 25,
}

DEFAULT_BALANCES: Dict[str, str] = {
    "0x04aac0173878aee604c1eaec3455ca8b5719f39b": "400000000000000000000000",
    "0x95e3673f703cb53b3c1848cd3def70a64c59fb08": "300000000000000000000000",
    "0x42753c26f7ef0deedcd27967b34ed48b294e1443": "200000000000000000000000",
    "0x7bfaa76280ab8607ed3efb1184dca1c89e6a5565": "25000000000000000000000",
    "0x91a51c376404b14c51e91536494944d3976a8bed": "75000000000000000000000",
}


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    return value or "my-chain"


def _title(value: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[-_\s]+", value.strip()) if part) or "AGILANG Chain"


def _write(path: Path, content: str, files: List[str], *, force: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    files.append(str(path))


def generate_blockchain_app(
    name: str,
    parent_dir: str | Path | None = None,
    *,
    force: bool = False,
    chain_id: int = 1900,
    symbol: str = "SBQ",
    decimals: int = 18,
    mode: str = "validator",
) -> Dict[str, Any]:
    """Generate a complete AGILANG/SBQ blockchain starter app."""
    slug = _slug(name)
    title = _title(name)
    parent = Path(parent_dir or ".").resolve()
    root = parent / slug
    if root.exists() and any(root.iterdir()) and not force:
        raise FileExistsError(f"Project already exists and is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    files: List[str] = []

    validators = json.dumps(DEFAULT_VALIDATORS, indent=2)
    balances = json.dumps(DEFAULT_BALANCES, indent=2)
    validator_keys = {addr: f"dev-signing-key-{i+1}" for i, addr in enumerate(DEFAULT_VALIDATORS)}

    _write(root / "agilang.toml", f'''
        [project]
        name = "{slug}"
        version = "0.1.0"
        entry = "src/main.agi"

        [runtime]
        kind = "blockchain"
        chain_id = {chain_id}
        symbol = "{symbol}"
        decimals = {decimals}
        default_mode = "{mode}"
        ''', files, force=force)

    _write(root / ".env.example", f'''
        APP_NAME="{title}"
        APP_ENV=local
        APP_DEBUG=true

        CHAIN_ID={chain_id}
        CHAIN_NAME="{title}"
        CHAIN_SYMBOL={symbol}
        CHAIN_DECIMALS={decimals}
        CHAIN_DB=storage/chain.sqlite

        RPC_HOST=127.0.0.1
        RPC_PORT=8545
        P2P_HOST=0.0.0.0
        P2P_PORT=30333
        VALIDATOR_ENABLED=true
        VALIDATOR_ADDRESS=0x04aac0173878aee604c1eaec3455ca8b5719f39b
        VALIDATOR_KEY_FILE=config/wallets/validator.key

        ETHEREUM_CLIENT_CONFIG=config/ethereum-clients.json
        ETHEREUM_JWT_SECRET=ethereum-data/jwt.hex
        ''', files, force=force)

    _write(root / ".gitignore", '''
        __pycache__/
        .pytest_cache/
        .agilang/
        storage/*.sqlite
        storage/*.db
        storage/logs/*.log
        .env
        config/wallets/*.json
        config/wallets/*.key
        config/wallets/*.pem
        config/wallets/*.private
        ethereum-data/
        node_modules/
        dist/
        build/
        ''', files, force=force)

    _write(root / "src/main.agi", f'''
        fn main() -> i32:
            print("{title} blockchain starter")
            print("capabilities", blockchain_capabilities())
            let cfg = blockchain_config(chain_id={chain_id}, name="{title}", validators={validators}, validator_signing_keys={json.dumps(validator_keys)}, genesis_state={{"balances": {balances}}}, consensus_mode="pos", mainnet_profile=True, require_block_signatures=True, slot_seconds=1, mempool_min_gas_price=1, block_gas_limit=30000000, finality_depth=8)
            let node = blockchain_node(cfg, "../storage/chain.sqlite", "validator-node")
            let tx = blockchain_transaction("0x04aac0173878aee604c1eaec3455ca8b5719f39b", "0x95e3673f703cb53b3c1848cd3def70a64c59fb08", 25000000000000000, nonce=node.height() + 1, gas_price=1)
            print("mempool add", node.submit_tx(tx))
            let parent = node.head()
            let slot = parent["slot"] + 1
            let proposer = node.consensus.select_proposer(parent["hash"], slot)
            let produced = node.produce_and_import_block(proposer, slot)
            print("block", produced["block"]["height"], produced["block"]["hash"])
            print("status", node.status())
            return 0
        ''', files, force=force)

    _write(root / "src/chain.agi", f'''
        fn main() -> i32:
            let cfg = blockchain_config(chain_id={chain_id}, name="{title}", validators={validators}, validator_signing_keys={json.dumps(validator_keys)}, genesis_state={{"balances": {balances}}}, consensus_mode="pos", mainnet_profile=True, require_block_signatures=True, slot_seconds=1, finality_depth=8)
            let node = blockchain_node(cfg, "../storage/chain.sqlite", "status-node")
            print("head", node.head())
            print("finalized", node.finalized_head())
            print("status", node.status())
            return 0
        ''', files, force=force)

    _write(root / "src/devnet.agi", f'''
        fn main() -> i32:
            let cfg = blockchain_config(chain_id={chain_id}, name="{title}-devnet", validators={validators}, genesis_state={{"balances": {balances}}}, consensus_mode="pos", slot_seconds=1)
            let net = blockchain_devnet(cfg, ["0x04aac0173878aee604c1eaec3455ca8b5719f39b", "0x95e3673f703cb53b3c1848cd3def70a64c59fb08"])
            let tx = blockchain_transaction("0x04aac0173878aee604c1eaec3455ca8b5719f39b", "0x95e3673f703cb53b3c1848cd3def70a64c59fb08", 10, nonce=1, gas_price=1)
            print("submit", net.submit_tx(tx))
            print("step", net.step())
            print("sync", net.sync_all())
            return 0
        ''', files, force=force)

    _write(root / "src/staking.agi", f'''
        fn main() -> i32:
            let cfg = blockchain_config(chain_id={chain_id}, name="{title}", validators={{"0x04aac0173878aee604c1eaec3455ca8b5719f39b": 100000}}, validator_signing_keys={{"0x04aac0173878aee604c1eaec3455ca8b5719f39b": "dev-signing-key-1"}}, genesis_state={{"balances": {balances}}}, consensus_mode="pos", mainnet_profile=True, require_block_signatures=True, staking_enabled=True, validator_join_enabled=True, min_validator_stake=1000, slashing_enabled=True, slot_seconds=1)
            let node = blockchain_node(cfg, ":memory:", "staking-node")
            print("dashboard", node.validator_dashboard())
            print("join", node.join_validator("0x95e3673f703cb53b3c1848cd3def70a64c59fb08", 50000, signing_key="dev-signing-key-2", commission_bps=500))
            print("after", node.validator_dashboard())
            return 0
        ''', files, force=force)

    _write(root / "scripts/start_rpc_server.py", '''
        from agilang.blockchain_runtime_gateway import serve_project_rpc

        if __name__ == "__main__":
            serve_project_rpc(".")
        ''', files, force=force)

    _write(root / "scripts/chain_status.py", '''
        from agilang.blockchain_runtime_gateway import print_project_status

        if __name__ == "__main__":
            print_project_status(".")
        ''', files, force=force)

    _write(root / "config/genesis.json", json.dumps({
        "chain_id": chain_id,
        "name": title,
        "symbol": symbol,
        "decimals": decimals,
        "balances": DEFAULT_BALANCES,
        "validators": DEFAULT_VALIDATORS,
    }, indent=2), files, force=force)

    _write(root / "config/validators.json", json.dumps({
        "chain_id": chain_id,
        "consensus": "pos",
        "validators": DEFAULT_VALIDATORS,
        "validator_signing_keys": validator_keys,
        "slot_seconds": 1,
        "finality_depth": 8,
        "require_block_signatures": True,
    }, indent=2), files, force=force)

    _write(root / "config/rpc.json", json.dumps({
        "host": "127.0.0.1",
        "port": 8545,
        "node_id": "rpc-node",
        "db_path": "storage/chain.sqlite",
        "auto_mine": True,
        "dev_send": True,
        "chain": {
            "chain_id": chain_id,
            "name": title,
            "symbol": symbol,
            "decimals": decimals,
            "consensus": "pos",
            "mainnet_profile": True,
            "require_block_signatures": True,
            "mempool_min_gas_price": 1,
            "validators": DEFAULT_VALIDATORS,
            "validator_signing_keys": validator_keys,
            "genesis_state": {"balances": DEFAULT_BALANCES},
        },
    }, indent=2), files, force=force)

    _write(root / "config/network.json", json.dumps({
        "network_name": slug,
        "chain_id": chain_id,
        "symbol": symbol,
        "mode": mode,
        "db_path": "storage/chain.sqlite",
        "services": {
            "public_rpc": {"host": "127.0.0.1", "port": 8545, "public": True},
            "p2p": {"host": "0.0.0.0", "port": 30333, "public": True},
            "validator_api": {"host": "127.0.0.1", "port": 8651, "public": False},
            "metrics": {"host": "127.0.0.1", "port": 9100, "public": False},
        },
    }, indent=2), files, force=force)

    _write(root / "config/staking.json", json.dumps({
        "staking_enabled": True,
        "validator_join_enabled": True,
        "min_validator_stake": 1000,
        "slashing_enabled": True,
        "validator_commission_bps": 0,
    }, indent=2), files, force=force)

    _write(root / "config/ethereum-clients.json", json.dumps({
        "network": "mainnet",
        "mode": "full",
        "data_dir": "ethereum-data",
        "jwt_secret_path": "ethereum-data/jwt.hex",
        "execution_client": "geth",
        "consensus_client": "lighthouse",
        "validator_client": "lighthouse",
        "validator_enabled": False,
        "archive": False,
        "checkpoint_sync_url": "",
        "fee_recipient": "",
        "graffiti": "AGILANG-SBQ",
    }, indent=2), files, force=force)

    _write(root / "config/wallets/wallets.example.json", json.dumps({
        "warning": "Example only. Do not commit real private keys.",
        "accounts": [
            {"name": "validator-1", "address": addr, "private_key_file": "config/wallets/validator-1.key"}
            for addr in DEFAULT_VALIDATORS
        ],
    }, indent=2), files, force=force)

    (root / "storage" / "logs").mkdir(parents=True, exist_ok=True)
    _write(root / "storage/.gitkeep", "", files, force=True)
    _write(root / "storage/logs/.gitkeep", "", files, force=True)

    _write(root / "docs/BLOCKCHAIN_RUNBOOK.md", f'''
        # {title} Blockchain Runbook

        This project was generated by the AGILANG blockchain runtime generator.
        It is designed as a single-command starter with modular internal services.

        ## Quick start

        ```bash
        agi run
        agi run src/chain.agi
        agi chain rpc
        ```

        ## One-command runtime philosophy

        The user runs one command, but the app is modular inside:

        - chain database
        - mempool
        - proof-of-stake consensus
        - validator signing profile
        - block production
        - JSON-RPC
        - staking configuration
        - Ethereum external-client configuration

        ## Recommended node modes

        ```bash
        agi chain start --mode validator
        agi chain start --mode full
        agi chain start --mode archive
        agi chain start --mode rpc
        ```

        ## Production boundary

        This starter can run a local/staging SBQ chain profile. Before public
        real-value operation, add hardened networking, validator key isolation,
        slashing economics review, DoS protection, monitoring, backups and an
        independent security audit.
        ''', files, force=force)

    _write(root / "docs/METAMASK_SETUP.md", f'''
        # MetaMask Setup

        Add a custom network:

        - Network name: `{title}`
        - RPC URL: `http://127.0.0.1:8545`
        - Chain ID: `{chain_id}`
        - Currency symbol: `{symbol}`
        - Decimals: `{decimals}`

        Start RPC:

        ```bash
        agi chain rpc
        ```

        Never commit real private keys. Use `config/wallets/wallets.example.json`
        only as a placeholder format.
        ''', files, force=force)

    _write(root / "README.md", f'''
        # {title}

        A complete AGILANG/SBQ blockchain starter generated from the AGILANG runtime.

        ## Start the chain

        ```bash
        agi run
        ```

        ## Check chain status

        ```bash
        agi run src/chain.agi
        agi chain status
        ```

        ## Start JSON-RPC for MetaMask

        ```bash
        agi chain rpc
        ```

        RPC URL: `http://127.0.0.1:8545`  
        Chain ID: `{chain_id}`  
        Symbol: `{symbol}`

        ## Generated runtime files

        - `src/main.agi` - one-shot validator/block-production starter
        - `src/chain.agi` - chain status/head/finality view
        - `src/devnet.agi` - local devnet demo
        - `src/staking.agi` - staking/validator join demo
        - `config/rpc.json` - JSON-RPC configuration
        - `config/network.json` - node service configuration
        - `config/validators.json` - validator set and signing-key profile
        - `config/genesis.json` - genesis balances and validator allocation
        - `config/ethereum-clients.json` - external Ethereum client stack config
        ''', files, force=force)

    return {"ok": True, "root": str(root), "files": files, "chain_id": chain_id, "symbol": symbol}


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _project_root(root: str | Path | None = None) -> Path:
    return Path(root or ".").resolve()


def load_project_chain(root: str | Path | None = None):
    project = _project_root(root)
    rpc_cfg = _load_json(project / "config" / "rpc.json")
    chain_cfg = dict(rpc_cfg.get("chain") or {})
    for meta_key in ("symbol", "decimals"):
        chain_cfg.pop(meta_key, None)
    if "consensus" in chain_cfg and "consensus_mode" not in chain_cfg:
        chain_cfg["consensus_mode"] = chain_cfg.pop("consensus")
    db_path = project / str(rpc_cfg.get("db_path") or "storage/chain.sqlite")
    cfg = blockchain_config(**chain_cfg)
    return blockchain_node(cfg, str(db_path), rpc_cfg.get("node_id") or "rpc-node"), rpc_cfg


def chain_status(root: str | Path | None = None) -> Dict[str, Any]:
    node, cfg = load_project_chain(root)
    return {
        "ok": True,
        "status": node.status(),
        "head": node.head(),
        "finalized": node.finalized_head(),
        "rpc": {"host": cfg.get("host", "127.0.0.1"), "port": cfg.get("port", 8545)},
    }


def print_project_status(root: str | Path | None = None) -> None:
    print(json.dumps(chain_status(root), indent=2))


def _hex(value: int) -> str:
    return hex(max(0, int(value)))


def _parse_block_number(value: Any, node: Any) -> int:
    if value in (None, "latest"):
        return int(node.height())
    if value in ("earliest", "genesis"):
        return 0
    if isinstance(value, str) and value.startswith("0x"):
        return int(value, 16)
    return int(value)


def _block_to_rpc(block: Dict[str, Any], full: bool = False) -> Dict[str, Any]:
    txs = block.get("transactions") or []
    return {
        "number": _hex(block.get("height", 0)),
        "hash": block.get("hash"),
        "parentHash": block.get("parent_hash"),
        "nonce": "0x0000000000000000",
        "sha3Uncles": "0x" + "0" * 64,
        "logsBloom": "0x" + "0" * 512,
        "transactionsRoot": block.get("tx_root"),
        "stateRoot": block.get("state_root"),
        "receiptsRoot": block.get("receipts_root"),
        "miner": block.get("proposer"),
        "difficulty": "0x0",
        "totalDifficulty": _hex(block.get("score", 0)),
        "extraData": "0x",
        "size": "0x0",
        "gasLimit": _hex(30000000),
        "gasUsed": _hex(block.get("gas_used", 0)),
        "timestamp": _hex(int(block.get("timestamp_ms", 0)) // 1000),
        "transactions": txs if full else [tx.get("hash") for tx in txs],
        "uncles": [],
    }


def _get_balance(node: Any, address: str) -> int:
    head = node.head()
    state = head.get("state_updates") or {}
    balances = state.get("balances") or {}
    raw = balances.get(address) or balances.get(address.lower()) or 0
    return int(raw)


def serve_project_rpc(root: str | Path | None = None, host: str | None = None, port: int | None = None) -> None:
    node, cfg = load_project_chain(root)
    host = host or str(cfg.get("host") or "127.0.0.1")
    port = int(port or cfg.get("port") or 8545)
    chain_id = int((cfg.get("chain") or {}).get("chain_id") or node.status().get("chain_id") or 1900)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "content-type")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._send({"ok": True})

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0") or 0)
            try:
                request = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception as exc:
                self._send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}})
                return
            self._send(self._handle(request))

        def _result(self, request_id: Any, result: Any) -> Dict[str, Any]:
            return {"jsonrpc": "2.0", "id": request_id, "result": result}

        def _error(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

        def _handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
            request_id = request.get("id")
            method = request.get("method")
            params = request.get("params") or []
            try:
                if method == "eth_chainId":
                    return self._result(request_id, hex(chain_id))
                if method == "net_version":
                    return self._result(request_id, str(chain_id))
                if method == "web3_clientVersion":
                    return self._result(request_id, f"AGILANG-SBQ/{__version__}")
                if method == "eth_blockNumber":
                    return self._result(request_id, _hex(node.height()))
                if method == "eth_getBalance":
                    return self._result(request_id, _hex(_get_balance(node, str(params[0]).lower())))
                if method == "eth_getTransactionCount":
                    head = node.head()
                    nonces = ((head.get("state_updates") or {}).get("nonces") or {})
                    return self._result(request_id, _hex(int(nonces.get(str(params[0]).lower(), 0))))
                if method == "eth_getBlockByNumber":
                    num = _parse_block_number(params[0] if params else "latest", node)
                    full = bool(params[1]) if len(params) > 1 else False
                    block = node.get_block_by_height(num) if hasattr(node, "get_block_by_height") else node.head()
                    return self._result(request_id, _block_to_rpc(block or node.head(), full=full))
                if method == "eth_accounts":
                    return self._result(request_id, list(DEFAULT_BALANCES.keys()))
                if method == "eth_sendRawTransaction":
                    return self._error(request_id, -32000, "signed raw transaction decoding requires the hardened rpc.py runtime; use dev_sendTransaction locally or import the v2 RPC module")
                if method in ("sbq_sendTransaction", "dev_sendTransaction", "eth_sendTransaction"):
                    txp = dict(params[0] if params else {})
                    tx = blockchain_transaction(
                        str(txp.get("from", "")).lower(),
                        str(txp.get("to", "")).lower(),
                        int(txp.get("value", 0)),
                        nonce=node.height() + 1,
                        gas_price=int(txp.get("gasPrice", 1)),
                    )
                    added = node.submit_tx(tx)
                    parent = node.head()
                    slot = parent.get("slot", node.height()) + 1
                    proposer = node.consensus.select_proposer(parent["hash"], slot)
                    node.produce_and_import_block(proposer, slot)
                    return self._result(request_id, added.get("hash"))
                return self._error(request_id, -32601, f"Method not found: {method}")
            except Exception as exc:
                return self._error(request_id, -32000, str(exc))

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"AGILANG/SBQ JSON-RPC running at http://{host}:{port}")
    print(f"chain_id={chain_id} height={node.height()} head={node.head().get('hash')}")
    server.serve_forever()


__all__ = [
    "generate_blockchain_app",
    "serve_project_rpc",
    "print_project_status",
    "chain_status",
    "load_project_chain",
]
