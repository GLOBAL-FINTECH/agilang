"""Single-command blockchain app generator and JSON-RPC runtime gateway for AGILANG.

The generated blockchain app is AGILANG-native at the application layer
(`.agi` source and `.ags` views) while the current AGILANG runtime remains the
Python-hosted backend. The generator emits both local/devnet configuration and
production/staging configuration templates.
"""
from __future__ import annotations

import hashlib
import json
import re
import textwrap
import threading
import time
from collections import defaultdict, deque
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
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower() or "my-chain"


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
    root = Path(parent_dir or ".").resolve() / slug
    if root.exists() and any(root.iterdir()) and not force:
        raise FileExistsError(f"Project already exists and is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    files: List[str] = []
    validators = json.dumps(DEFAULT_VALIDATORS, indent=2)
    balances = json.dumps(DEFAULT_BALANCES, indent=2)
    key_ids = {addr: f"REPLACE_WITH_AUDITED_SIGNING_KEY_ID_{i + 1}" for i, addr in enumerate(DEFAULT_VALIDATORS)}

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
        CHAIN_PROFILE=local
        CHAIN_DB=storage/chain.sqlite
        RPC_HOST=127.0.0.1
        RPC_PORT=8545
        RPC_RATE_LIMIT_PER_MINUTE=600
        RPC_MAX_BODY_BYTES=1048576
        P2P_HOST=0.0.0.0
        P2P_PORT=30333
        VALIDATOR_ENABLED=true
        VALIDATOR_MODE=internal
        VALIDATOR_ADDRESS=0x04aac0173878aee604c1eaec3455ca8b5719f39b
        VALIDATOR_KEY_FILE=config/wallets/validator.key
        ''', files, force=force)

    _write(root / ".env.production.example", f'''
        APP_NAME="{title}"
        APP_ENV=production
        APP_DEBUG=false
        CHAIN_ID={chain_id}
        CHAIN_NAME="{title}"
        CHAIN_SYMBOL={symbol}
        CHAIN_DECIMALS={decimals}
        CHAIN_PROFILE=production
        CHAIN_DB=/var/lib/agilang/{slug}/chain.sqlite
        RPC_HOST=127.0.0.1
        RPC_PORT=8545
        RPC_CORS_ORIGIN=https://your-explorer.example
        RPC_RATE_LIMIT_PER_MINUTE=1200
        RPC_MAX_BODY_BYTES=1048576
        P2P_HOST=0.0.0.0
        P2P_PORT=30333
        P2P_BOOTNODES=
        VALIDATOR_ENABLED=false
        VALIDATOR_MODE=external
        VALIDATOR_ADDRESS=
        VALIDATOR_KEY_PROVIDER=file_or_hsm_or_kms
        VALIDATOR_KEY_FILE=/etc/agilang/{slug}/validator.key
        STORAGE_BACKUP_DIR=/var/backups/agilang/{slug}
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
            let cfg = blockchain_config(chain_id={chain_id}, name="{title}", validators={validators}, validator_signing_keys={json.dumps(key_ids)}, genesis_state={{"balances": {balances}}}, consensus_mode="pos", mainnet_profile=True, require_block_signatures=True, slot_seconds=1, mempool_min_gas_price=1, block_gas_limit=30000000, finality_depth=8)
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
            let cfg = blockchain_config(chain_id={chain_id}, name="{title}", validators={validators}, validator_signing_keys={json.dumps(key_ids)}, genesis_state={{"balances": {balances}}}, consensus_mode="pos", mainnet_profile=True, require_block_signatures=True, slot_seconds=1, finality_depth=8)
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
            let cfg = blockchain_config(chain_id={chain_id}, name="{title}", validators={{"0x04aac0173878aee604c1eaec3455ca8b5719f39b": 100000}}, validator_signing_keys={{"0x04aac0173878aee604c1eaec3455ca8b5719f39b": "REPLACE_WITH_AUDITED_SIGNING_KEY_ID_1"}}, genesis_state={{"balances": {balances}}}, consensus_mode="pos", mainnet_profile=True, require_block_signatures=True, min_validator_stake=1000, slot_seconds=1)
            let node = blockchain_node(cfg, ":memory:", "staking-node")
            print("staking validators", node.status()["validators"])
            print("minimum stake", cfg.min_validator_stake)
            print("production key warning", "replace placeholder signing key with audited key management before launch")
            return 0
        ''', files, force=force)

    _write(root / "src/rpc.agi", f'''
        fn main() -> i32:
            print("{title} JSON-RPC profile")
            print("start command: agi chain rpc --host 127.0.0.1 --port 8545")
            print("supported methods are exposed by sbq_supportedMethods")
            return 0
        ''', files, force=force)

    _write(root / "src/explorer.agi", '''
        fn main() -> i32:
            let view = render_ags("resources/views/explorer.ags", {"chain_name": "AGILANG Chain", "height": 0, "status": "ready"})
            print(view["body"])
            return 0
        ''', files, force=force)

    _write(root / "resources/views/layout.ags", '''
        <html>
          <head><title>{{ title }}</title></head>
          <body><main>{{ body }}</main></body>
        </html>
        ''', files, force=force)
    _write(root / "resources/views/explorer.ags", '''
        <section class="chain-explorer">
          <h1>{{ chain_name }}</h1>
          <p>Height: {{ height }}</p>
          <p>Status: {{ status }}</p>
        </section>
        ''', files, force=force)
    _write(root / "resources/views/validator.ags", '''
        <section class="validator-dashboard">
          <h1>Validator Dashboard</h1>
          <p>Mode: {{ mode }}</p>
        </section>
        ''', files, force=force)

    _write(root / "config/genesis.json", json.dumps({"chain_id": chain_id, "name": title, "symbol": symbol, "decimals": decimals, "balances": DEFAULT_BALANCES, "validators": DEFAULT_VALIDATORS}, indent=2), files, force=force)
    _write(root / "config/validators.json", json.dumps({"chain_id": chain_id, "consensus": "pos", "validators": DEFAULT_VALIDATORS, "validator_signing_keys": key_ids, "slot_seconds": 1, "finality_depth": 8, "require_block_signatures": True}, indent=2), files, force=force)
    _write(root / "config/rpc.json", json.dumps({"host": "127.0.0.1", "port": 8545, "node_id": "rpc-node", "db_path": "storage/chain.sqlite", "auto_mine": True, "dev_send": True, "rate_limit_per_minute": 600, "max_body_bytes": 1048576, "cors_origin": "*", "chain": {"chain_id": chain_id, "name": title, "symbol": symbol, "decimals": decimals, "consensus": "pos", "mainnet_profile": True, "require_block_signatures": True, "mempool_min_gas_price": 1, "validators": DEFAULT_VALIDATORS, "validator_signing_keys": key_ids, "genesis_state": {"balances": DEFAULT_BALANCES}}}, indent=2), files, force=force)
    _write(root / "config/network.json", json.dumps({"network_name": slug, "chain_id": chain_id, "symbol": symbol, "mode": mode, "db_path": "storage/chain.sqlite", "services": {"public_rpc": {"host": "127.0.0.1", "port": 8545, "public": True}, "p2p": {"host": "0.0.0.0", "port": 30333, "public": True}, "validator_api": {"host": "127.0.0.1", "port": 8651, "public": False}, "metrics": {"host": "127.0.0.1", "port": 9100, "public": False}}}, indent=2), files, force=force)
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
    _write(root / "config/profiles/local.json", json.dumps({"profile": "local", "purpose": "developer testing and CI", "rpc": {"host": "127.0.0.1", "tls_required_at_proxy": False}, "validator": {"mode": "internal", "dev_signing_keys_allowed": True}, "storage": {"backup_required": False}}, indent=2), files, force=force)
    _write(root / "config/profiles/production.json", json.dumps({"profile": "production", "purpose": "private-chain or staging baseline", "rpc": {"host": "127.0.0.1", "tls_required_at_proxy": True, "rate_limit_per_minute": 1200}, "validator": {"mode": "external", "dev_signing_keys_allowed": False, "key_provider_required": True}, "storage": {"backup_required": True, "sqlite_integrity_check_required": True}}, indent=2), files, force=force)
    _write(root / "config/validators.internal.json", json.dumps({"mode": "internal", "warning": "Use for local/devnet only.", "validators": DEFAULT_VALIDATORS}, indent=2), files, force=force)
    _write(root / "config/validators.external.example.json", json.dumps({"mode": "external", "beacon_nodes": [{"name": "validator-a", "rpc": "https://validator-a.example", "p2p": "enode-or-libp2p-address"}], "key_management": "file_or_hsm_or_kms", "dev_signing_keys_allowed": False}, indent=2), files, force=force)
    _write(root / "config/metamask.json", json.dumps({"local": {"networkName": title, "rpcUrl": "http://127.0.0.1:8545", "chainId": chain_id, "symbol": symbol}, "production": {"networkName": title, "rpcUrl": "https://rpc.your-chain.example", "chainId": chain_id, "symbol": symbol}}, indent=2), files, force=force)
    _write(root / "config/contracts.example.json", json.dumps({"deployments": [], "receipt_acceptance": {"require_status_success": True, "require_block_hash": True, "require_confirmations": 8}}, indent=2), files, force=force)
    _write(root / "config/wallets/wallets.example.json", json.dumps({"warning": "Example only. Never commit real private keys.", "accounts": []}, indent=2), files, force=force)

    _write(root / "docs/PRODUCTION_ARCHITECTURE.md", f'''
        # {title} Production Architecture

        ## Local/devnet profile
        Local/devnet profile is for developer testing, CI, MetaMask local RPC, and controlled private-chain experiments.

        ## Production/staging profile
        Production/staging profile is for hardened private-chain or staging deployments behind TLS, reverse proxy, monitoring, backups, and rate limits.

        ## External validator beacon node
        External validator beacon node topology is configured through `config/validators.external.example.json` and must use audited key management before public value operation.
        ''', files, force=force)
    _write(root / "docs/VALIDATOR_WORKFLOW.md", """
        # Validator Workflow

        Use internal validators for local/devnet. Use external validators and audited key management for production/staging. Do not use generated placeholder key IDs as real signing keys.
        """, files, force=force)
    _write(root / "docs/METAMASK_CONTRACTS_RECEIPTS.md", """
        # MetaMask, Contracts and Receipts

        Add the local or production RPC endpoint from `config/metamask.json`. Contract deployments should be recorded in `config/contracts.example.json` and accepted only after receipt status is successful and enough confirmations are reached.
        """, files, force=force)
    _write(root / "docs/METAMASK_SETUP.md", f'''
        # MetaMask Setup

        Add a custom network:

        - Network name: `{title}`
        - RPC URL: `http://127.0.0.1:8545`
        - Chain ID: `{chain_id}`
        - Currency symbol: `{symbol}`
        - Decimals: `{decimals}`

        Start the local RPC server with:

        ```bash
        agi chain rpc
        ```

        For standalone vendored deployments, use the project launcher:

        ```bash
        python run.py chain rpc
        ```
        ''', files, force=force)
    _write(root / "docs/STORAGE_DURABILITY.md", """
        # Storage Durability

        Production storage requires SQLite integrity checks, backups, restore drills, and monitoring. Public real-value use requires external audit and operational runbooks.
        """, files, force=force)
    _write(root / "README.md", f'''
        # {title}

        Generated AGILANG/SBQ blockchain starter.

        ```bash
        agi run
        agi run src/chain.agi
        agi chain rpc
        ```

        RPC URL: `http://127.0.0.1:8545`, Chain ID: `{chain_id}`, Symbol: `{symbol}`.
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
    return {"ok": True, "status": node.status(), "head": node.head(), "finalized": node.finalized_head(), "rpc": {"host": cfg.get("host", "127.0.0.1"), "port": cfg.get("port", 8545)}}


def print_project_status(root: str | Path | None = None) -> None:
    print(json.dumps(chain_status(root), indent=2))


def _hex(value: Any) -> str:
    return hex(max(0, int(value or 0)))


def _parse_block_number(value: Any, node: Any) -> int:
    if value in (None, "latest", "pending"):
        return int(node.height())
    if value in ("earliest", "genesis"):
        return 0
    if isinstance(value, str) and value.startswith("0x"):
        return int(value, 16)
    return int(value)


def _parse_tx_value(raw: Any) -> int:
    if raw is None:
        return 0
    if isinstance(raw, str) and raw.startswith("0x"):
        return int(raw, 16)
    return int(raw)


def _canonical_blocks(node: Any) -> List[Dict[str, Any]]:
    return list(node.canonical_chain()) if hasattr(node, "canonical_chain") else [node.head()]


def _block_by_height(node: Any, height: int) -> Dict[str, Any] | None:
    for block in _canonical_blocks(node):
        if int(block.get("height", -1)) == int(height):
            return block
    return None


def _block_by_hash(node: Any, block_hash: str) -> Dict[str, Any] | None:
    if hasattr(node, "db") and hasattr(node.db, "get_block"):
        found = node.db.get_block(block_hash)
        if found:
            return found
    for block in _canonical_blocks(node):
        if str(block.get("hash")) == str(block_hash):
            return block
    return None


def _find_transaction(node: Any, tx_hash: str):
    for block in _canonical_blocks(node):
        for index, tx in enumerate(block.get("transactions") or []):
            if str(tx.get("hash")) == str(tx_hash):
                return block, tx, index
    return None, None, None


def _find_receipt(node: Any, tx_hash: str):
    for block in _canonical_blocks(node):
        for index, receipt in enumerate(block.get("receipts") or []):
            if str(receipt.get("tx_hash")) == str(tx_hash):
                return block, receipt, index
    return None, None, None


def _get_balance(node: Any, address: str) -> int:
    state = node.db.get_state("balances", {}) if hasattr(node, "db") else {}
    head_state = (node.head().get("state_updates") or {}).get("balances") or {}
    balances = state or head_state
    return int(balances.get(address) or balances.get(address.lower()) or 0)


def _get_nonce(node: Any, address: str) -> int:
    state = node.db.get_state("nonces", {}) if hasattr(node, "db") else {}
    head_state = (node.head().get("state_updates") or {}).get("nonces") or {}
    nonces = state or head_state
    return int(nonces.get(address) or nonces.get(address.lower()) or 0)


def _get_code(node: Any, address: str) -> str:
    contracts = node.db.get_state("contracts", {}) if hasattr(node, "db") else {}
    return str(contracts.get(address) or contracts.get(address.lower()) or "0x")


def _tx_to_rpc(tx: Dict[str, Any], block: Dict[str, Any] | None = None, index: int | None = None) -> Dict[str, Any]:
    return {"hash": tx.get("hash"), "nonce": _hex(tx.get("nonce", 0)), "blockHash": block.get("hash") if block else None, "blockNumber": _hex(block.get("height", 0)) if block else None, "transactionIndex": _hex(index or 0) if block is not None else None, "from": tx.get("from"), "to": tx.get("to"), "value": _hex(tx.get("value", 0)), "gas": _hex(tx.get("gas_limit", 21000)), "gasPrice": _hex(tx.get("gas_price", 1)), "input": tx.get("data", "0x"), "type": "0x0", "chainId": _hex(tx.get("chain_id", 0)) if tx.get("chain_id") is not None else None}


def _block_to_rpc(block: Dict[str, Any], full: bool = False) -> Dict[str, Any]:
    txs = block.get("transactions") or []
    return {"number": _hex(block.get("height", 0)), "hash": block.get("hash"), "parentHash": block.get("parent_hash"), "nonce": "0x0000000000000000", "sha3Uncles": "0x" + "0" * 64, "logsBloom": "0x" + "0" * 512, "transactionsRoot": block.get("tx_root"), "stateRoot": block.get("state_root"), "receiptsRoot": block.get("receipts_root"), "miner": block.get("proposer"), "difficulty": "0x0", "totalDifficulty": _hex(block.get("score", 0)), "extraData": "0x", "size": "0x0", "gasLimit": _hex(30000000), "gasUsed": _hex(block.get("gas_used", 0)), "timestamp": _hex(int(block.get("timestamp_ms", 0)) // 1000), "transactions": [_tx_to_rpc(tx, block, i) for i, tx in enumerate(txs)] if full else [tx.get("hash") for tx in txs], "uncles": []}


def _receipt_to_rpc(block: Dict[str, Any], receipt: Dict[str, Any], index: int) -> Dict[str, Any]:
    tx_hash = str(receipt.get("tx_hash"))
    txs = block.get("transactions") or []
    tx = next((item for item in txs if str(item.get("hash")) == tx_hash), {})
    cumulative_gas = sum(int(r.get("gas_used", 0)) for r in (block.get("receipts") or [])[: index + 1])
    contract_address = None
    if tx.get("type") == "deploy_contract":
        contract_address = tx.get("to") or ("0x" + tx_hash[-40:])
    return {"transactionHash": tx_hash, "transactionIndex": _hex(index), "blockHash": block.get("hash"), "blockNumber": _hex(block.get("height", 0)), "from": tx.get("from"), "to": tx.get("to"), "contractAddress": contract_address, "cumulativeGasUsed": _hex(cumulative_gas), "gasUsed": _hex(receipt.get("gas_used", 0)), "effectiveGasPrice": _hex(tx.get("gas_price", 1)), "logs": [], "logsBloom": "0x" + "0" * 512, "status": "0x1" if bool(receipt.get("ok", True)) else "0x0", "type": "0x0"}


def rpc_supported_methods() -> List[str]:
    return sorted({"web3_clientVersion", "web3_sha3", "net_version", "net_listening", "net_peerCount", "eth_chainId", "eth_syncing", "eth_protocolVersion", "eth_blockNumber", "eth_accounts", "eth_coinbase", "eth_mining", "eth_hashrate", "eth_gasPrice", "eth_maxPriorityFeePerGas", "eth_feeHistory", "eth_getBalance", "eth_getTransactionCount", "eth_getCode", "eth_call", "eth_estimateGas", "eth_getBlockByNumber", "eth_getBlockByHash", "eth_getBlockTransactionCountByNumber", "eth_getBlockTransactionCountByHash", "eth_getTransactionByHash", "eth_getTransactionReceipt", "eth_getLogs", "eth_sendTransaction", "eth_sendRawTransaction", "dev_sendTransaction", "sbq_sendTransaction", "sbq_supportedMethods", "rpc_modules"})


def serve_project_rpc(root: str | Path | None = None, host: str | None = None, port: int | None = None) -> None:
    """Serve an Ethereum-compatible JSON-RPC shim for a generated project."""
    project = _project_root(root)
    _, cfg = load_project_chain(project)
    host = host or str(cfg.get("host") or "127.0.0.1")
    port = int(port or cfg.get("port") or 8545)
    chain_id = int((cfg.get("chain") or {}).get("chain_id") or 1900)
    max_body = int(cfg.get("max_body_bytes") or 1_048_576)
    rate_limit = int(cfg.get("rate_limit_per_minute") or cfg.get("rate_limit") or 600)
    write_lock = threading.Lock()
    request_windows: dict[str, deque[float]] = defaultdict(deque)

    def fresh_node():
        return load_project_chain(project)[0]

    def rate_limited(client: str) -> bool:
        now = time.monotonic()
        window = request_windows[client]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= rate_limit:
            return True
        window.append(now)
        return False

    class Handler(BaseHTTPRequestHandler):
        def _send(self, payload: Any, status: int = 200) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", str(cfg.get("cors_origin") or "*"))
            self.send_header("Access-Control-Allow-Headers", "content-type")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._send({"ok": True})

        def do_POST(self) -> None:  # noqa: N802
            client = self.client_address[0] if self.client_address else "unknown"
            if rate_limited(client):
                self._send({"jsonrpc": "2.0", "id": None, "error": {"code": -32005, "message": "rate limit exceeded"}}, status=429)
                return
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length < 0 or length > max_body:
                self._send({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "request body too large"}}, status=413)
                return
            try:
                request = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception as exc:
                self._send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}})
                return
            self._send([self._handle(item) for item in request] if isinstance(request, list) else self._handle(request))

        def _result(self, request_id: Any, result: Any) -> Dict[str, Any]:
            return {"jsonrpc": "2.0", "id": request_id, "result": result}

        def _error(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

        def _handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
            request_id = request.get("id")
            method = request.get("method")
            params = request.get("params") or []
            try:
                node = fresh_node()
                if method == "sbq_supportedMethods": return self._result(request_id, rpc_supported_methods())
                if method == "rpc_modules": return self._result(request_id, {"eth": "1.0", "net": "1.0", "web3": "1.0", "sbq": "1.0"})
                if method == "eth_chainId": return self._result(request_id, hex(chain_id))
                if method == "net_version": return self._result(request_id, str(chain_id))
                if method == "net_listening": return self._result(request_id, True)
                if method == "net_peerCount": return self._result(request_id, _hex(len(getattr(node, "peers", []))))
                if method == "web3_clientVersion": return self._result(request_id, f"AGILANG-SBQ/{__version__}")
                if method == "web3_sha3":
                    raw = str(params[0] if params else "0x")
                    payload = bytes.fromhex(raw[2:]) if raw.startswith("0x") else raw.encode("utf-8")
                    return self._result(request_id, "0x" + hashlib.sha3_256(payload).hexdigest())
                if method == "eth_syncing": return self._result(request_id, False)
                if method == "eth_protocolVersion": return self._result(request_id, "0x1")
                if method == "eth_blockNumber": return self._result(request_id, _hex(node.height()))
                if method == "eth_accounts": return self._result(request_id, list(DEFAULT_BALANCES.keys()))
                if method == "eth_coinbase": return self._result(request_id, next(iter(DEFAULT_VALIDATORS.keys())))
                if method == "eth_mining": return self._result(request_id, True)
                if method == "eth_hashrate": return self._result(request_id, "0x0")
                if method == "eth_gasPrice": return self._result(request_id, _hex(max(1, int((cfg.get("chain") or {}).get("mempool_min_gas_price") or 1))))
                if method == "eth_maxPriorityFeePerGas": return self._result(request_id, _hex(1))
                if method == "eth_feeHistory":
                    count = max(1, _parse_tx_value(params[0]) if params else 1)
                    return self._result(request_id, {"oldestBlock": _hex(max(0, node.height() - count + 1)), "baseFeePerGas": [_hex(1) for _ in range(count + 1)], "gasUsedRatio": [0 for _ in range(count)], "reward": [[_hex(1)] for _ in range(count)]})
                if method == "eth_getBalance": return self._result(request_id, _hex(_get_balance(node, str(params[0]).lower())))
                if method == "eth_getTransactionCount": return self._result(request_id, _hex(_get_nonce(node, str(params[0]).lower())))
                if method == "eth_getCode": return self._result(request_id, _get_code(node, str(params[0]).lower()))
                if method == "eth_call": return self._result(request_id, dict(params[0] if params else {}).get("data", "0x"))
                if method == "eth_estimateGas":
                    data = str(dict(params[0] if params else {}).get("data", "0x"))
                    return self._result(request_id, _hex(21000 + max(0, len(data) - 2) // 2))
                if method == "eth_getBlockByNumber":
                    block = _block_by_height(node, _parse_block_number(params[0] if params else "latest", node)); return self._result(request_id, _block_to_rpc(block, bool(params[1]) if len(params) > 1 else False) if block else None)
                if method == "eth_getBlockByHash":
                    block = _block_by_hash(node, str(params[0])) if params else None; return self._result(request_id, _block_to_rpc(block, bool(params[1]) if len(params) > 1 else False) if block else None)
                if method == "eth_getBlockTransactionCountByNumber":
                    block = _block_by_height(node, _parse_block_number(params[0] if params else "latest", node)); return self._result(request_id, _hex(len(block.get("transactions") or [])) if block else None)
                if method == "eth_getBlockTransactionCountByHash":
                    block = _block_by_hash(node, str(params[0])) if params else None; return self._result(request_id, _hex(len(block.get("transactions") or [])) if block else None)
                if method == "eth_getTransactionByHash":
                    block, tx, index = _find_transaction(node, str(params[0])) if params else (None, None, None); return self._result(request_id, _tx_to_rpc(tx, block, index) if tx else None)
                if method == "eth_getTransactionReceipt":
                    block, receipt, index = _find_receipt(node, str(params[0])) if params else (None, None, None); return self._result(request_id, _receipt_to_rpc(block, receipt, index or 0) if block and receipt else None)
                if method == "eth_getLogs": return self._result(request_id, [])
                if method == "eth_sendRawTransaction": return self._error(request_id, -32000, "signed raw transaction decoding is not enabled in this RPC shim; use eth_sendTransaction/dev_sendTransaction for controlled private-chain testing")
                if method in ("sbq_sendTransaction", "dev_sendTransaction", "eth_sendTransaction"):
                    with write_lock:
                        node = fresh_node(); txp = dict(params[0] if params else {})
                        sender = str(txp.get("from", "")).lower()
                        tx = blockchain_transaction(sender, str(txp.get("to", "")).lower(), _parse_tx_value(txp.get("value", 0)), data=str(txp.get("data", "0x")), nonce=_parse_tx_value(txp.get("nonce")) if txp.get("nonce") is not None else _get_nonce(node, sender) + 1, gas_limit=_parse_tx_value(txp.get("gas", txp.get("gasLimit", 21000))), gas_price=_parse_tx_value(txp.get("gasPrice", 1)))
                        added = node.submit_tx(tx)
                        if not added.get("ok", True): return self._error(request_id, -32000, json.dumps(added))
                        parent = node.head(); slot = parent.get("slot", node.height()) + 1; proposer = node.consensus.select_proposer(parent["hash"], slot); produced = node.produce_and_import_block(proposer, slot); imported = produced.get("import", {})
                        if not imported.get("ok", True): return self._error(request_id, -32000, json.dumps(imported))
                        return self._result(request_id, added.get("hash"))
                return self._error(request_id, -32601, f"Method not found: {method}")
            except Exception as exc:
                return self._error(request_id, -32000, str(exc))

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    initial = fresh_node()
    print(f"AGILANG/SBQ JSON-RPC running at http://{host}:{port}")
    print(f"chain_id={chain_id} height={initial.height()} head={initial.head().get('hash')}")
    server.serve_forever()


__all__ = ["generate_blockchain_app", "serve_project_rpc", "print_project_status", "chain_status", "load_project_chain", "rpc_supported_methods"]
