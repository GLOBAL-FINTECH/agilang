"""Nonce-aware mempool and RPC safety patch for AGILANG blockchain runtime.

This module is intentionally imported by ``agilang.__init__`` so existing public
imports such as ``from agilang.blockchain import blockchain_node`` and
``from agilang.blockchain_runtime_gateway import serve_project_rpc`` receive the
patched behavior without changing the external API surface.

The patch adds Ethereum-style queued nonce handling for local/private-chain
execution:

* ready pool for executable transactions
* queued pool for future-nonce transactions
* duplicate sender/nonce rejection
* nonce-too-low rejection
* nonce-gap limits
* nonce-ordered block selection
* single-writer block import/production lock
* optional signed raw transaction decoding for the JSON-RPC shim when
  ``eth-account``/``rlp`` are installed

Production public networks still require persistent mempool storage,
peer-scoring, DoS hardening, cryptographic networking review, and independent
security audit before handling real value.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
from collections import defaultdict, deque
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bytes):
        return int.from_bytes(value, "big") if value else default
    if isinstance(value, str):
        if value.startswith("0x"):
            return int(value, 16)
        if value == "":
            return default
    return int(value)


def _to_hex_bytes(value: bytes) -> str:
    return "0x" + value.hex()


def _normalize_address(value: Any) -> str:
    if value in (None, b"", ""):
        return ""
    if isinstance(value, bytes):
        return "0x" + value.hex()
    return str(value).lower()


def _hash_raw_tx(raw_bytes: bytes) -> str:
    try:
        from eth_utils import keccak  # type: ignore

        return "0x" + keccak(raw_bytes).hex()
    except Exception:
        # Fallback keeps the RPC deterministic when eth_utils is absent. Ethereum
        # clients should install eth-account/eth-utils so this becomes Keccak-256.
        return "0x" + hashlib.sha3_256(raw_bytes).hexdigest()


def _patch_blockchain_core() -> None:
    import agilang.blockchain as bc

    if getattr(bc, "_nonce_mempool_patch_applied", False):
        return

    original_blockchain_config = bc.blockchain_config
    original_node_init = bc.BlockchainNode.__init__
    original_config_as_dict = bc.BlockchainConfig.as_dict
    original_capabilities = bc.blockchain_capabilities

    def blockchain_config(*args: Any, max_account_queue_gap: int = 128, **kwargs: Any) -> Any:
        # Allow config dictionaries to include the new setting without breaking
        # the existing dataclass constructor.
        max_account_queue_gap = int(kwargs.pop("max_account_queue_gap", max_account_queue_gap))
        cfg = original_blockchain_config(*args, **kwargs)
        setattr(cfg, "max_account_queue_gap", max_account_queue_gap)
        return cfg

    def config_as_dict(self: Any) -> Dict[str, Any]:
        data = original_config_as_dict(self)
        data["max_account_queue_gap"] = int(getattr(self, "max_account_queue_gap", 128))
        return data

    def mempool_init(self: Any, max_txs: int = 100_000, min_gas_price: int = 0, max_account_queue_gap: int = 128) -> None:
        self.max_txs = int(max_txs)
        self.min_gas_price = int(min_gas_price)
        self.max_account_queue_gap = int(max_account_queue_gap)
        self.ready_pool: Dict[str, Dict[str, Any]] = {}
        self.queued_pool: Dict[str, Dict[str, Any]] = {}
        self._txs: Dict[str, Dict[str, Any]] = {}
        self._by_sender_nonce: Dict[Tuple[str, int], str] = {}

    def mempool_validate_tx(self: Any, tx: Dict[str, Any]) -> Dict[str, Any]:
        errors: List[str] = []
        if not tx.get("hash"):
            errors.append("missing_hash")
        if not tx.get("from"):
            errors.append("missing_sender")
        if int(tx.get("gas_limit", 0)) <= 0:
            errors.append("invalid_gas_limit")
        if int(tx.get("gas_price", 0)) < 0:
            errors.append("invalid_gas_price")
        if int(tx.get("gas_price", 0)) < self.min_gas_price:
            errors.append("gas_price_below_minimum")
        if int(tx.get("value", 0)) < 0:
            errors.append("invalid_negative_value")
        if int(tx.get("nonce", 0)) < 0:
            errors.append("invalid_negative_nonce")
        if tx.get("hash") in self._txs:
            errors.append("duplicate_tx_hash")
        key = (str(tx.get("from")), int(tx.get("nonce", 0)))
        if key in self._by_sender_nonce:
            errors.append("duplicate_account_nonce")
        if len(self._txs) >= self.max_txs:
            errors.append("mempool_full")
        return {"ok": not errors, "errors": errors}

    def mempool_add(self: Any, tx: Dict[str, Any], confirmed_nonce: Optional[int] = None) -> Dict[str, Any]:
        tx = dict(tx)
        if not tx.get("hash"):
            tx["hash"] = bc._sha256_hex(tx)
        sender = str(tx.get("from", ""))
        nonce = int(tx.get("nonce", 0))
        confirmed = 0 if confirmed_nonce is None else int(confirmed_nonce)
        report = self.validate_tx(tx)
        if not report.get("ok"):
            return report
        if nonce < confirmed:
            return {"ok": False, "errors": ["nonce_too_low"], "hash": tx.get("hash"), "expected_nonce": confirmed}
        if nonce - confirmed > int(getattr(self, "max_account_queue_gap", 128)):
            return {"ok": False, "errors": ["nonce_gap_too_large"], "hash": tx.get("hash"), "expected_nonce": confirmed}
        self._txs[tx["hash"]] = tx
        self._by_sender_nonce[(sender, nonce)] = tx["hash"]
        if nonce == confirmed:
            self.ready_pool[tx["hash"]] = tx
            status = "ready"
        else:
            self.queued_pool[tx["hash"]] = tx
            status = "queued"
        return {"ok": True, "hash": tx["hash"], "status": status, "size": len(self._txs)}

    def mempool_remove_many(self: Any, tx_hashes: Iterable[str]) -> None:
        for h in list(tx_hashes):
            tx = self._txs.pop(h, None)
            self.ready_pool.pop(h, None)
            self.queued_pool.pop(h, None)
            if tx:
                self._by_sender_nonce.pop((str(tx.get("from")), int(tx.get("nonce", 0))), None)

    def mempool_promote_queued(self: Any, confirmed_nonces: Dict[str, Any]) -> Dict[str, Any]:
        promoted: List[str] = []
        confirmed = {str(k): int(v) for k, v in dict(confirmed_nonces or {}).items()}
        changed = True
        while changed:
            changed = False
            for tx_hash, tx in list(self.queued_pool.items()):
                sender = str(tx.get("from", ""))
                nonce = int(tx.get("nonce", 0))
                if nonce == int(confirmed.get(sender, 0)):
                    self.queued_pool.pop(tx_hash, None)
                    self.ready_pool[tx_hash] = tx
                    promoted.append(tx_hash)
                    confirmed[sender] = nonce + 1
                    changed = True
        return {"ok": True, "promoted": promoted, "ready_size": len(self.ready_pool), "queued_size": len(self.queued_pool)}

    def mempool_select_for_block(
        self: Any,
        max_txs: int,
        block_gas_limit: int,
        account_nonces: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        next_nonce = defaultdict(int)
        for sender, nonce in dict(account_nonces or {}).items():
            next_nonce[str(sender)] = int(nonce)
        selected: List[Dict[str, Any]] = []
        selected_hashes: set[str] = set()
        used_gas = 0
        while len(selected) < int(max_txs):
            eligible: List[Dict[str, Any]] = []
            for tx_hash, tx in self._txs.items():
                if tx_hash in selected_hashes:
                    continue
                sender = str(tx.get("from", ""))
                if int(tx.get("nonce", 0)) == int(next_nonce[sender]):
                    eligible.append(tx)
            if not eligible:
                break
            eligible.sort(key=lambda t: (-int(t.get("gas_price", 0)), str(t.get("from", "")), int(t.get("nonce", 0)), str(t.get("hash", ""))))
            picked = None
            for candidate in eligible:
                gas = int(candidate.get("gas_limit", 21_000))
                if used_gas + gas <= int(block_gas_limit):
                    picked = candidate
                    break
            if picked is None:
                break
            selected.append(copy.deepcopy(picked))
            selected_hashes.add(str(picked.get("hash")))
            used_gas += int(picked.get("gas_limit", 21_000))
            next_nonce[str(picked.get("from", ""))] = int(picked.get("nonce", 0)) + 1
        return selected

    def mempool_size(self: Any) -> int:
        return len(self._txs)

    def mempool_pending(self: Any) -> List[Dict[str, Any]]:
        return sorted(
            [copy.deepcopy(tx) for tx in self._txs.values()],
            key=lambda t: (str(t.get("from", "")), int(t.get("nonce", 0)), str(t.get("hash", ""))),
        )

    def mempool_as_dict(self: Any) -> Dict[str, Any]:
        return {
            "size": self.size(),
            "ready_size": len(self.ready_pool),
            "queued_size": len(self.queued_pool),
            "max_txs": self.max_txs,
            "min_gas_price": self.min_gas_price,
            "max_account_queue_gap": int(getattr(self, "max_account_queue_gap", 128)),
            "ready": list(self.ready_pool.values()),
            "queued": list(self.queued_pool.values()),
        }

    def node_init(self: Any, config: Any = None, db_path: Any = ":memory:", node_id: Optional[str] = None) -> None:
        original_node_init(self, config=config, db_path=db_path, node_id=node_id)
        self._chain_write_lock = threading.RLock()
        gap = int(getattr(self.config, "max_account_queue_gap", 128))
        if not hasattr(self.mempool, "max_account_queue_gap"):
            self.mempool.max_account_queue_gap = gap

    def node_validate_tx_against_state(self: Any, tx: Dict[str, Any]) -> Dict[str, Any]:
        errors: List[str] = []
        balances = dict(self.db.get_state("balances", {}))
        nonces = dict(self.db.get_state("nonces", {}))
        sender = str(tx.get("from", ""))
        expected_nonce = int(nonces.get(sender, 0))
        if self.config.strict_accounting and tx.get("type") == "transfer":
            value = int(tx.get("value", 0))
            if int(balances.get(sender, 0)) < value:
                errors.append("insufficient_balance")
        if self.config.enforce_nonce_order and self.config.strict_accounting:
            nonce = int(tx.get("nonce", 0))
            if nonce < expected_nonce:
                errors.append(f"nonce_too_low_expected_{expected_nonce}")
            elif nonce - expected_nonce > int(getattr(self.config, "max_account_queue_gap", 128)):
                errors.append(f"nonce_gap_too_large_expected_{expected_nonce}")
        return {"ok": not errors, "errors": errors, "hash": tx.get("hash"), "expected_nonce": expected_nonce}

    def node_submit_tx(self: Any, tx: Dict[str, Any]) -> Dict[str, Any]:
        state_report = self.validate_tx_against_state(tx)
        if not state_report.get("ok"):
            return state_report
        sender = str(tx.get("from", ""))
        confirmed_nonce = int(state_report.get("expected_nonce", dict(self.db.get_state("nonces", {})).get(sender, 0)))
        report = self.mempool.add(tx, confirmed_nonce=confirmed_nonce)
        if report.get("ok"):
            self.gossip({"type": "tx", "tx": tx}, exclude=None)
        return report

    def node_apply_successful_tx_to_state(self: Any, tx: Dict[str, Any], balances: Dict[str, Any], contracts: Dict[str, Any], nonces: Dict[str, int]) -> None:
        sender = str(tx.get("from", ""))
        if tx.get("type") == "transfer":
            to = str(tx.get("to", ""))
            value = int(tx.get("value", 0))
            balances[sender] = int(balances.get(sender, 0)) - value
            balances[to] = int(balances.get(to, 0)) + value
        elif tx.get("type") == "deploy_contract":
            address = str(tx.get("to") or ("0x" + str(tx.get("hash", ""))[-40:]))
            contracts[address] = tx.get("data", "0x")
        nonces[sender] = max(int(nonces.get(sender, 0)), int(tx.get("nonce", 0)) + 1)

    def node_execute_transactions(self: Any, txs: List[Dict[str, Any]], base_state: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any], int]:
        if base_state is None:
            base_state = {
                "balances": self.db.get_state("balances", {}),
                "contracts": self.db.get_state("contracts", {}),
                "nonces": self.db.get_state("nonces", {}),
            }
        balances = dict(base_state.get("balances", {}))
        contracts = dict(base_state.get("contracts", {}))
        nonces = dict(base_state.get("nonces", {}))
        receipts: List[Dict[str, Any]] = []
        gas_used = 0
        for tx in txs:
            used = min(int(tx.get("gas_limit", 21_000)), 21_000 + len(str(tx.get("data", ""))))
            ok = True
            error = ""
            sender = str(tx.get("from", ""))
            if self.config.strict_accounting and self.config.enforce_nonce_order:
                expected_nonce = int(nonces.get(sender, 0))
                if int(tx.get("nonce", 0)) != expected_nonce:
                    ok = False
                    error = f"invalid_nonce_expected_{expected_nonce}"
            if ok and tx.get("type") == "transfer":
                to = str(tx.get("to"))
                value = int(tx.get("value", 0))
                if self.config.strict_accounting and int(balances.get(sender, 0)) < value:
                    ok = False
                    error = "insufficient_balance"
                else:
                    balances[sender] = int(balances.get(sender, 0)) - value
                    balances[to] = int(balances.get(to, 0)) + value
            elif ok and tx.get("type") in {"contract_call", "evm_call"} and self.config.evm_enabled and bc.evm_simulate_call:
                bytecode = contracts.get(str(tx.get("to")), tx.get("code", "0x"))
                try:
                    result = bc.evm_simulate_call(bytecode, tx.get("data", "0x"), gas=int(tx.get("gas_limit", 1000000)))
                    ok = bool(result.get("ok", True))
                    error = str(result.get("error", ""))
                    used = int(result.get("gas_used", used))
                except Exception as exc:  # pragma: no cover - defensive
                    ok = False
                    error = str(exc)
            elif ok and tx.get("type") == "deploy_contract":
                address = str(tx.get("to") or ("0x" + tx["hash"][-40:]))
                contracts[address] = tx.get("data", "0x")
            if ok:
                nonces[sender] = max(int(nonces.get(sender, 0)), int(tx.get("nonce", 0)) + 1)
            gas_used += used
            receipts.append({"tx_hash": tx["hash"], "ok": ok, "gas_used": used, "error": error})
        return receipts, {"balances": balances, "contracts": contracts, "nonces": nonces}, gas_used

    def node_produce_block(self: Any, validator: Optional[str] = None, slot: Optional[int] = None, max_txs: Optional[int] = None) -> Dict[str, Any]:
        with self._chain_write_lock:
            parent = self.head()
            slot_value = int(slot if slot is not None else max(int(parent.get("slot", 0)) + 1, self._current_slot()))
            expected = self.consensus.select_proposer(parent["hash"], slot_value)
            proposer = validator or expected
            if proposer != expected:
                raise ValueError(f"invalid proposer for slot {slot_value}: expected {expected}, got {proposer}")
            account_nonces = dict(self.db.get_state("nonces", {}))
            txs = self.mempool.select_for_block(max_txs or self.config.max_block_txs, self.config.block_gas_limit, account_nonces=account_nonces)
            if not txs and not self.config.allow_empty_blocks:
                raise ValueError("empty block production disabled")
            receipts, state_updates, gas_used = self._execute_transactions(txs)
            block = {
                "chain_id": self.config.chain_id,
                "height": int(parent["height"]) + 1,
                "slot": slot_value,
                "parent_hash": parent["hash"],
                "proposer": proposer,
                "timestamp_ms": bc._now_ms(),
                "transactions": txs,
                "receipts": receipts,
                "tx_root": bc.blockchain_merkle_root(txs),
                "state_updates": state_updates,
                "state_root": bc._sha256_hex(state_updates),
                "receipts_root": bc.blockchain_merkle_root(receipts),
                "gas_used": gas_used,
                "extra_data": {"node_id": self.node_id, "consensus_mode": self.config.consensus_mode},
            }
            block["score"] = self.consensus.block_score(block)
            signature = self.consensus.sign_block(block)
            if signature:
                block["validator_signature"] = signature
            block["hash"] = bc._sha256_hex({k: v for k, v in block.items() if k != "hash"})
            return block

    def node_import_block(self: Any, block: Dict[str, Any], *, validate: bool = True) -> Dict[str, Any]:
        with self._chain_write_lock:
            if int(block.get("height", 0)) > 0:
                current_head = self.head()
                if str(block.get("parent_hash")) != str(current_head.get("hash")) and not self.db.has_block(str(block.get("hash", ""))):
                    return {"ok": False, "errors": ["stale_parent_hash"], "hash": block.get("hash"), "canonical_head": current_head.get("hash")}
            report = self.validate_block(block) if validate else {"ok": True, "errors": [], "hash": block.get("hash")}
            if not report.get("ok"):
                return report
            old_head = self.head().get("hash")
            self.db.put_block(block, canonical=False, finalized=False)
            self.apply_fork_choice()
            new_head = self.head().get("hash")
            if new_head != old_head or self.db.get_block(block.get("hash", "")):
                self._rebuild_canonical_state()
            self.mempool.remove_many([tx["hash"] for tx in block.get("transactions", [])])
            self.mempool.promote_queued(dict(self.db.get_state("nonces", {})))
            return {"ok": True, "hash": block["hash"], "height": block["height"], "canonical_head": self.head()["hash"]}

    def node_produce_and_import_block(self: Any, validator: Optional[str] = None, slot: Optional[int] = None) -> Dict[str, Any]:
        with self._chain_write_lock:
            block = self.produce_block(validator=validator, slot=slot)
            result = self.import_block(block)
            if result.get("ok"):
                self.gossip({"type": "block", "block": block}, exclude=None)
            return {"block": block, "import": result}

    def node_receive_gossip(self: Any, message: Dict[str, Any], from_peer: Optional[Any] = None) -> Dict[str, Any]:
        mtype = message.get("type")
        if mtype == "tx":
            return self.submit_tx(message["tx"])
        if mtype == "block":
            return self.import_block(message["block"])
        if mtype == "status":
            return {"ok": True, "status": self.status()}
        return {"ok": False, "error": "unknown_gossip_type"}

    def node_sync_from(self: Any, peer: Any) -> Dict[str, Any]:
        imported = 0
        for block in peer.canonical_chain():
            if not self.db.has_block(block["hash"]):
                result = self.import_block(block, validate=(int(block.get("height", 0)) != 0))
                if result.get("ok"):
                    imported += 1
        for tx in peer.mempool.pending():
            self.submit_tx(tx)
        return {"ok": True, "imported_blocks": imported, "height": self.height(), "head": self.head()["hash"]}

    def blockchain_capabilities() -> Dict[str, Any]:
        data = original_capabilities()
        data["nonce_aware_mempool"] = [
            "ready_pool",
            "queued_future_nonce_pool",
            "duplicate_account_nonce_rejection",
            "nonce_too_low_rejection",
            "nonce_gap_limit",
            "nonce_ordered_block_selection",
            "queued_transaction_promotion",
            "single_writer_block_lock",
        ]
        return data

    bc.blockchain_config = blockchain_config
    bc.BlockchainConfig.as_dict = config_as_dict
    bc.Mempool.__init__ = mempool_init
    bc.Mempool.validate_tx = mempool_validate_tx
    bc.Mempool.add = mempool_add
    bc.Mempool.remove_many = mempool_remove_many
    bc.Mempool.promote_queued = mempool_promote_queued
    bc.Mempool.select_for_block = mempool_select_for_block
    bc.Mempool.size = mempool_size
    bc.Mempool.pending = mempool_pending
    bc.Mempool.as_dict = mempool_as_dict
    bc.BlockchainNode.__init__ = node_init
    bc.BlockchainNode.validate_tx_against_state = node_validate_tx_against_state
    bc.BlockchainNode.submit_tx = node_submit_tx
    bc.BlockchainNode._apply_successful_tx_to_state = node_apply_successful_tx_to_state
    bc.BlockchainNode._execute_transactions = node_execute_transactions
    bc.BlockchainNode.produce_block = node_produce_block
    bc.BlockchainNode.import_block = node_import_block
    bc.BlockchainNode.produce_and_import_block = node_produce_and_import_block
    bc.BlockchainNode.receive_gossip = node_receive_gossip
    bc.BlockchainNode.sync_from = node_sync_from
    bc.blockchain_capabilities = blockchain_capabilities
    bc._nonce_mempool_patch_applied = True


def _decode_raw_transaction(raw_tx: str, default_chain_id: int, blockchain_transaction: Any) -> Dict[str, Any]:
    raw = str(raw_tx or "")
    if raw.startswith("0x"):
        raw_bytes = bytes.fromhex(raw[2:])
    else:
        raw_bytes = bytes.fromhex(raw)
    try:
        import rlp  # type: ignore
        from eth_account import Account  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency path
        raise RuntimeError("eth_sendRawTransaction requires eth-account and rlp to decode signed wallet transactions") from exc

    sender = str(Account.recover_transaction(raw)).lower()
    tx_hash = _hash_raw_tx(raw_bytes)
    tx_type = raw_bytes[0] if raw_bytes and raw_bytes[0] in (1, 2) else 0

    if tx_type == 0:
        fields = rlp.decode(raw_bytes)
        nonce = _as_int(fields[0])
        gas_price = _as_int(fields[1])
        gas_limit = _as_int(fields[2])
        to = _normalize_address(fields[3])
        value = _as_int(fields[4])
        data = _to_hex_bytes(fields[5])
        v = _as_int(fields[6])
        chain_id = (v - 35) // 2 if v >= 35 else default_chain_id
    elif tx_type == 1:
        fields = rlp.decode(raw_bytes[1:])
        chain_id = _as_int(fields[0], default_chain_id)
        nonce = _as_int(fields[1])
        gas_price = _as_int(fields[2])
        gas_limit = _as_int(fields[3])
        to = _normalize_address(fields[4])
        value = _as_int(fields[5])
        data = _to_hex_bytes(fields[6])
    else:
        fields = rlp.decode(raw_bytes[1:])
        chain_id = _as_int(fields[0], default_chain_id)
        nonce = _as_int(fields[1])
        max_priority_fee = _as_int(fields[2])
        max_fee = _as_int(fields[3])
        gas_price = max(max_fee, max_priority_fee, 1)
        gas_limit = _as_int(fields[4])
        to = _normalize_address(fields[5])
        value = _as_int(fields[6])
        data = _to_hex_bytes(fields[7])

    if int(chain_id) != int(default_chain_id):
        raise RuntimeError(f"wrong chainId: expected {default_chain_id}, got {chain_id}")

    tx = blockchain_transaction(
        sender,
        to,
        value,
        data=data,
        nonce=nonce,
        gas_limit=gas_limit,
        gas_price=gas_price,
    )
    tx["hash"] = tx_hash
    tx["chain_id"] = int(chain_id)
    tx["raw"] = "0x" + raw_bytes.hex()
    return tx


def _patch_runtime_gateway() -> None:
    try:
        import agilang.blockchain_runtime_gateway as gw
    except Exception:
        return

    if getattr(gw, "_nonce_mempool_gateway_patch_applied", False):
        return

    def serve_project_rpc(root: Any = None, host: Optional[str] = None, port: Optional[int] = None) -> None:
        project = gw._project_root(root)
        node, cfg = gw.load_project_chain(project)
        host_value = host or str(cfg.get("host") or "127.0.0.1")
        port_value = int(port or cfg.get("port") or 8545)
        chain_id = int((cfg.get("chain") or {}).get("chain_id") or getattr(node.config, "chain_id", 1900))
        max_body = int(cfg.get("max_body_bytes") or 1_048_576)
        rate_limit = int(cfg.get("rate_limit_per_minute") or cfg.get("rate_limit") or 600)
        write_lock = threading.RLock()
        request_windows: Dict[str, deque[float]] = defaultdict(deque)

        def rate_limited(client: str) -> bool:
            now = time.monotonic()
            window = request_windows[client]
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) >= rate_limit:
                return True
            window.append(now)
            return False

        def mine_ready() -> None:
            for _ in range(max(1, int(getattr(node.config, "max_block_txs", 1024)))):
                parent = node.head()
                slot = int(parent.get("slot", node.height())) + 1
                proposer = node.consensus.select_proposer(parent["hash"], slot)
                produced = node.produce_and_import_block(proposer, slot)
                block = produced.get("block", {})
                imported = produced.get("import", {})
                if not imported.get("ok", True):
                    raise RuntimeError(json.dumps(imported))
                if not block.get("transactions"):
                    break
                if node.mempool.size() <= 0:
                    break

        class Handler(gw.BaseHTTPRequestHandler):
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
                    if method == "sbq_supportedMethods": return self._result(request_id, gw.rpc_supported_methods())
                    if method == "rpc_modules": return self._result(request_id, {"eth": "1.0", "net": "1.0", "web3": "1.0", "sbq": "1.0"})
                    if method == "eth_chainId": return self._result(request_id, hex(chain_id))
                    if method == "net_version": return self._result(request_id, str(chain_id))
                    if method == "net_listening": return self._result(request_id, True)
                    if method == "net_peerCount": return self._result(request_id, gw._hex(len(getattr(node, "peers", []))))
                    if method == "web3_clientVersion": return self._result(request_id, f"AGILANG-SBQ/{gw.__version__}")
                    if method == "web3_sha3":
                        raw = str(params[0] if params else "0x")
                        payload = bytes.fromhex(raw[2:]) if raw.startswith("0x") else raw.encode("utf-8")
                        return self._result(request_id, "0x" + hashlib.sha3_256(payload).hexdigest())
                    if method == "eth_syncing": return self._result(request_id, False)
                    if method == "eth_protocolVersion": return self._result(request_id, "0x1")
                    if method == "eth_blockNumber": return self._result(request_id, gw._hex(node.height()))
                    if method == "eth_accounts": return self._result(request_id, list(gw.DEFAULT_BALANCES.keys()))
                    if method == "eth_coinbase": return self._result(request_id, next(iter(gw.DEFAULT_VALIDATORS.keys())))
                    if method == "eth_mining": return self._result(request_id, True)
                    if method == "eth_hashrate": return self._result(request_id, "0x0")
                    if method == "eth_gasPrice": return self._result(request_id, gw._hex(max(1, int((cfg.get("chain") or {}).get("mempool_min_gas_price") or 1))))
                    if method == "eth_maxPriorityFeePerGas": return self._result(request_id, gw._hex(1))
                    if method == "eth_feeHistory":
                        count = max(1, gw._parse_tx_value(params[0]) if params else 1)
                        return self._result(request_id, {"oldestBlock": gw._hex(max(0, node.height() - count + 1)), "baseFeePerGas": [gw._hex(1) for _ in range(count + 1)], "gasUsedRatio": [0 for _ in range(count)], "reward": [[gw._hex(1)] for _ in range(count)]})
                    if method == "eth_getBalance": return self._result(request_id, gw._hex(gw._get_balance(node, str(params[0]).lower())))
                    if method == "eth_getTransactionCount": return self._result(request_id, gw._hex(gw._get_nonce(node, str(params[0]).lower())))
                    if method == "eth_getCode": return self._result(request_id, gw._get_code(node, str(params[0]).lower()))
                    if method == "eth_call": return self._result(request_id, dict(params[0] if params else {}).get("data", "0x"))
                    if method == "eth_estimateGas":
                        data = str(dict(params[0] if params else {}).get("data", "0x"))
                        return self._result(request_id, gw._hex(21000 + max(0, len(data) - 2) // 2))
                    if method == "eth_getBlockByNumber":
                        block = gw._block_by_height(node, gw._parse_block_number(params[0] if params else "latest", node)); return self._result(request_id, gw._block_to_rpc(block, bool(params[1]) if len(params) > 1 else False) if block else None)
                    if method == "eth_getBlockByHash":
                        block = gw._block_by_hash(node, str(params[0])) if params else None; return self._result(request_id, gw._block_to_rpc(block, bool(params[1]) if len(params) > 1 else False) if block else None)
                    if method == "eth_getBlockTransactionCountByNumber":
                        block = gw._block_by_height(node, gw._parse_block_number(params[0] if params else "latest", node)); return self._result(request_id, gw._hex(len(block.get("transactions") or [])) if block else None)
                    if method == "eth_getBlockTransactionCountByHash":
                        block = gw._block_by_hash(node, str(params[0])) if params else None; return self._result(request_id, gw._hex(len(block.get("transactions") or [])) if block else None)
                    if method == "eth_getTransactionByHash":
                        block, tx, index = gw._find_transaction(node, str(params[0])) if params else (None, None, None); return self._result(request_id, gw._tx_to_rpc(tx, block, index) if tx else None)
                    if method == "eth_getTransactionReceipt":
                        block, receipt, index = gw._find_receipt(node, str(params[0])) if params else (None, None, None); return self._result(request_id, gw._receipt_to_rpc(block, receipt, index or 0) if block and receipt else None)
                    if method == "eth_getLogs": return self._result(request_id, [])
                    if method == "eth_sendRawTransaction":
                        with write_lock:
                            tx = _decode_raw_transaction(str(params[0]), chain_id, gw.blockchain_transaction)
                            added = node.submit_tx(tx)
                            if not added.get("ok", True): return self._error(request_id, -32000, json.dumps(added))
                            mine_ready()
                            return self._result(request_id, added.get("hash") or tx.get("hash"))
                    if method in ("sbq_sendTransaction", "dev_sendTransaction", "eth_sendTransaction"):
                        with write_lock:
                            txp = dict(params[0] if params else {})
                            sender = str(txp.get("from", "")).lower()
                            nonce = gw._parse_tx_value(txp.get("nonce")) if txp.get("nonce") is not None else gw._get_nonce(node, sender)
                            tx = gw.blockchain_transaction(sender, str(txp.get("to", "")).lower(), gw._parse_tx_value(txp.get("value", 0)), data=str(txp.get("data", "0x")), nonce=nonce, gas_limit=gw._parse_tx_value(txp.get("gas", txp.get("gasLimit", 21000))), gas_price=gw._parse_tx_value(txp.get("gasPrice", 1)))
                            added = node.submit_tx(tx)
                            if not added.get("ok", True): return self._error(request_id, -32000, json.dumps(added))
                            mine_ready()
                            return self._result(request_id, added.get("hash"))
                    return self._error(request_id, -32601, f"Method not found: {method}")
                except Exception as exc:
                    return self._error(request_id, -32000, str(exc))

            def log_message(self, fmt: str, *args: Any) -> None:
                return

        server = gw.ThreadingHTTPServer((host_value, port_value), Handler)
        print(f"AGILANG/SBQ JSON-RPC running at http://{host_value}:{port_value}")
        print(f"chain_id={chain_id} height={node.height()} head={node.head().get('hash')}")
        server.serve_forever()

    gw.serve_project_rpc = serve_project_rpc
    gw._nonce_mempool_gateway_patch_applied = True


def apply_blockchain_nonce_mempool_patch() -> None:
    _patch_blockchain_core()
    _patch_runtime_gateway()


__all__ = ["apply_blockchain_nonce_mempool_patch"]
