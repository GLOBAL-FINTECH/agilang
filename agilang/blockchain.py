"""AGILANG full blockchain framework primitives.

This module is designed for private-chain/devnet blockchain development.  It
provides configurable Proof-of-Stake consensus, persistent chain storage,
canonical fork choice, block production, mempool management, simple p2p/devnet
sync helpers and EVM execution hooks.

It is intentionally deterministic and dependency-light so it can be shipped as
part of the AGILANG standard library.  Production public networks should still
add external audits, cryptographic signing, peer scoring, DoS controls and
formal consensus review before handling real value.
"""
from __future__ import annotations

import copy
import hmac
import hashlib
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:  # optional, used when AGILANG EVM runtime is available
    from .evm import evm_simulate_call
except Exception:  # pragma: no cover - standalone embedding safety
    evm_simulate_call = None  # type: ignore


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_hex(value: Any) -> str:
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = _stable_json(value).encode("utf-8")
    return "0x" + hashlib.sha256(data).hexdigest()


def _now_ms() -> int:
    return int(time.time() * 1000)


def blockchain_hash(value: Any) -> str:
    """Return a deterministic 0x-prefixed SHA-256 hash for blockchain data."""
    return _sha256_hex(value)


def _normalize_consensus_mode(value: str | None) -> str:
    """Normalize user-facing consensus labels into engine identifiers."""
    raw = str(value or "pos").strip().lower().replace("-", "_")
    aliases = {
        "pos": "pos",
        "proof_of_stake": "pos",
        "proof_of_stake_engine": "pos",
        "dpos": "dpos",
        "dpo": "dpos",
        "delegated_pos": "dpos",
        "delegated_proof_of_stake": "dpos",
        "dev": "dev",
        "developer": "dev",
        "dev_consensus": "dev",
    }
    if raw not in aliases:
        raise ValueError(f"unsupported consensus mode: {value!r}; expected pos, dpos/dpo or dev")
    return aliases[raw]


def _block_signature_payload(block: Dict[str, Any]) -> Dict[str, Any]:
    """Return the canonical block payload covered by validator signatures."""
    payload = copy.deepcopy(block)
    payload.pop("hash", None)
    payload.pop("validator_signature", None)
    return payload


@dataclass
class BlockchainConfig:
    chain_id: int = 7777
    name: str = "agilang-chain"
    consensus_mode: str = "pos"
    slot_seconds: int = 6
    epoch_length: int = 32
    block_gas_limit: int = 30_000_000
    max_block_txs: int = 1024
    mempool_max_txs: int = 100_000
    mempool_min_gas_price: int = 0
    finality_depth: int = 8
    validators: Dict[str, int] = field(default_factory=lambda: {"validator-1": 100})
    delegates: List[str] = field(default_factory=list)
    delegations: Dict[str, Any] = field(default_factory=dict)
    validator_signing_keys: Dict[str, str] = field(default_factory=dict)
    genesis_state: Dict[str, Any] = field(default_factory=dict)
    fork_choice: str = "stake_weighted_height"
    allow_empty_blocks: bool = True
    evm_enabled: bool = True
    strict_accounting: bool = False
    enforce_nonce_order: bool = True
    require_block_signatures: bool = False
    mainnet_profile: bool = False
    min_validator_stake: int = 1
    max_clock_drift_ms: int = 120_000
    dev_allow_any_proposer: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "consensus_mode": _normalize_consensus_mode(self.consensus_mode),
            "slot_seconds": self.slot_seconds,
            "epoch_length": self.epoch_length,
            "block_gas_limit": self.block_gas_limit,
            "max_block_txs": self.max_block_txs,
            "mempool_max_txs": self.mempool_max_txs,
            "mempool_min_gas_price": self.mempool_min_gas_price,
            "finality_depth": self.finality_depth,
            "validators": dict(self.validators),
            "delegates": list(self.delegates),
            "delegations": copy.deepcopy(self.delegations),
            "validator_signing_keys": dict(self.validator_signing_keys),
            "genesis_state": copy.deepcopy(self.genesis_state),
            "fork_choice": self.fork_choice,
            "allow_empty_blocks": self.allow_empty_blocks,
            "evm_enabled": self.evm_enabled,
            "strict_accounting": self.strict_accounting,
            "enforce_nonce_order": self.enforce_nonce_order,
            "require_block_signatures": self.require_block_signatures,
            "mainnet_profile": self.mainnet_profile,
            "min_validator_stake": self.min_validator_stake,
            "max_clock_drift_ms": self.max_clock_drift_ms,
            "dev_allow_any_proposer": self.dev_allow_any_proposer,
        }


def blockchain_config(
    chain_id: int = 7777,
    name: str = "agilang-chain",
    consensus_mode: str = "pos",
    validators: Optional[Dict[str, int]] = None,
    delegates: Optional[List[str]] = None,
    delegations: Optional[Dict[str, Any]] = None,
    validator_signing_keys: Optional[Dict[str, str]] = None,
    slot_seconds: int = 6,
    epoch_length: int = 32,
    block_gas_limit: int = 30_000_000,
    max_block_txs: int = 1024,
    mempool_max_txs: int = 100_000,
    mempool_min_gas_price: int = 0,
    finality_depth: int = 8,
    genesis_state: Optional[Dict[str, Any]] = None,
    fork_choice: str = "stake_weighted_height",
    evm_enabled: bool = True,
    strict_accounting: bool = False,
    enforce_nonce_order: bool = True,
    require_block_signatures: bool = False,
    mainnet_profile: bool = False,
    min_validator_stake: int = 1,
    max_clock_drift_ms: int = 120_000,
    dev_allow_any_proposer: bool = False,
) -> BlockchainConfig:
    """Create a configurable AGILANG blockchain config."""
    mode = _normalize_consensus_mode(consensus_mode)
    if mainnet_profile:
        strict_accounting = True
        enforce_nonce_order = True
        require_block_signatures = True
        finality_depth = max(int(finality_depth), 32)
        mempool_min_gas_price = max(int(mempool_min_gas_price), 1)
        fork_choice = fork_choice or "stake_weighted_height"
    return BlockchainConfig(
        chain_id=int(chain_id),
        name=name,
        consensus_mode=mode,
        validators=dict(validators or {"validator-1": 100}),
        delegates=list(delegates or []),
        delegations=copy.deepcopy(delegations or {}),
        validator_signing_keys=dict(validator_signing_keys or {}),
        slot_seconds=int(slot_seconds),
        epoch_length=int(epoch_length),
        block_gas_limit=int(block_gas_limit),
        max_block_txs=int(max_block_txs),
        mempool_max_txs=int(mempool_max_txs),
        mempool_min_gas_price=int(mempool_min_gas_price),
        finality_depth=int(finality_depth),
        genesis_state=copy.deepcopy(genesis_state or {}),
        fork_choice=fork_choice,
        evm_enabled=bool(evm_enabled),
        strict_accounting=bool(strict_accounting),
        enforce_nonce_order=bool(enforce_nonce_order),
        require_block_signatures=bool(require_block_signatures),
        mainnet_profile=bool(mainnet_profile),
        min_validator_stake=int(min_validator_stake),
        max_clock_drift_ms=int(max_clock_drift_ms),
        dev_allow_any_proposer=bool(dev_allow_any_proposer),
    )


def blockchain_mainnet_config(**kwargs: Any) -> BlockchainConfig:
    """Create a stricter mainnet-style config for simulation and staging.

    This enables strict accounting, nonce ordering, validator block signatures,
    a higher finality depth and a non-zero minimum gas price.  It is a hardened
    framework profile; real public-value launches still require audited network
    cryptography and independent consensus/security review.
    """
    kwargs["mainnet_profile"] = True
    return blockchain_config(**kwargs)


def blockchain_transaction(
    sender: str,
    to: str = "",
    value: int = 0,
    data: str = "0x",
    nonce: int = 0,
    gas_limit: int = 21_000,
    gas_price: int = 0,
    tx_type: str = "transfer",
    signature: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a deterministic transaction dictionary with a hash."""
    payload = {
        "from": sender,
        "to": to,
        "value": int(value),
        "data": data or "0x",
        "nonce": int(nonce),
        "gas_limit": int(gas_limit),
        "gas_price": int(gas_price),
        "type": tx_type,
        "signature": signature or "",
        "metadata": copy.deepcopy(metadata or {}),
    }
    payload["hash"] = _sha256_hex(payload)
    return payload


def blockchain_merkle_root(items: Iterable[Any]) -> str:
    """Compute a deterministic binary Merkle root over serialized items."""
    leaves = [_sha256_hex(item) for item in list(items)]
    if not leaves:
        return _sha256_hex("")
    level = leaves
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [_sha256_hex(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


class ChainDatabase:
    """SQLite-backed canonical chain database."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS blocks (
                hash TEXT PRIMARY KEY,
                height INTEGER NOT NULL,
                parent_hash TEXT NOT NULL,
                slot INTEGER NOT NULL,
                proposer TEXT NOT NULL,
                score INTEGER NOT NULL,
                canonical INTEGER NOT NULL DEFAULT 0,
                finalized INTEGER NOT NULL DEFAULT 0,
                json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_blocks_height ON blocks(height);
            CREATE INDEX IF NOT EXISTS idx_blocks_parent ON blocks(parent_hash);
            CREATE INDEX IF NOT EXISTS idx_blocks_canonical ON blocks(canonical, height);
            CREATE TABLE IF NOT EXISTS transactions (
                hash TEXT PRIMARY KEY,
                block_hash TEXT,
                json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def put_metadata(self, key: str, value: Any) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES(?, ?)",
            (key, _stable_json(value)),
        )
        self.conn.commit()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        row = self.conn.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def put_state(self, key: str, value: Any) -> None:
        self.conn.execute("INSERT OR REPLACE INTO state(key, value) VALUES(?, ?)", (key, _stable_json(value)))
        self.conn.commit()

    def get_state(self, key: str, default: Any = None) -> Any:
        row = self.conn.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def all_state(self) -> Dict[str, Any]:
        return {row["key"]: json.loads(row["value"]) for row in self.conn.execute("SELECT key, value FROM state")}

    def put_block(self, block: Dict[str, Any], canonical: bool = False, finalized: bool = False) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO blocks(hash, height, parent_hash, slot, proposer, score, canonical, finalized, json)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                block["hash"],
                int(block["height"]),
                block["parent_hash"],
                int(block["slot"]),
                block["proposer"],
                int(block.get("score", 0)),
                1 if canonical else int(block.get("canonical", 0)),
                1 if finalized else int(block.get("finalized", 0)),
                _stable_json(block),
            ),
        )
        for tx in block.get("transactions", []):
            self.conn.execute(
                "INSERT OR REPLACE INTO transactions(hash, block_hash, json) VALUES(?, ?, ?)",
                (tx["hash"], block["hash"], _stable_json(tx)),
            )
        self.conn.commit()

    def get_block(self, block_hash: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute("SELECT json, canonical, finalized FROM blocks WHERE hash=?", (block_hash,)).fetchone()
        if not row:
            return None
        block = json.loads(row["json"])
        block["canonical"] = bool(row["canonical"])
        block["finalized"] = bool(row["finalized"])
        return block

    def has_block(self, block_hash: str) -> bool:
        return self.conn.execute("SELECT 1 FROM blocks WHERE hash=?", (block_hash,)).fetchone() is not None

    def canonical_head(self) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT json, canonical, finalized FROM blocks WHERE canonical=1 ORDER BY height DESC, score DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        block = json.loads(row["json"])
        block["canonical"] = bool(row["canonical"])
        block["finalized"] = bool(row["finalized"])
        return block

    def candidate_heads(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT b.json FROM blocks b
            LEFT JOIN blocks child ON child.parent_hash = b.hash
            WHERE child.hash IS NULL
            ORDER BY b.score DESC, b.height DESC
            """
        ).fetchall()
        return [json.loads(row["json"]) for row in rows]

    def set_canonical_chain(self, head_hash: str, finality_depth: int = 8) -> None:
        path: List[Dict[str, Any]] = []
        current = self.get_block(head_hash)
        while current is not None:
            path.append(current)
            if current["height"] == 0:
                break
            current = self.get_block(current["parent_hash"])
        canonical_hashes = {b["hash"] for b in path}
        self.conn.execute("UPDATE blocks SET canonical=0")
        finalized_cutoff = max([b["height"] for b in path] or [0]) - max(0, finality_depth)
        for block in path:
            finalized = 1 if block["height"] <= finalized_cutoff else 0
            self.conn.execute("UPDATE blocks SET canonical=1, finalized=? WHERE hash=?", (finalized, block["hash"]))
        self.conn.commit()

    def list_canonical(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute("SELECT json, finalized FROM blocks WHERE canonical=1 ORDER BY height ASC").fetchall()
        result = []
        for row in rows:
            block = json.loads(row["json"])
            block["finalized"] = bool(row["finalized"])
            block["canonical"] = True
            result.append(block)
        return result


class Mempool:
    """Managed transaction pool with validation, replacement and ordering."""

    def __init__(self, max_txs: int = 100_000, min_gas_price: int = 0) -> None:
        self.max_txs = int(max_txs)
        self.min_gas_price = int(min_gas_price)
        self._txs: Dict[str, Dict[str, Any]] = {}
        self._by_sender_nonce: Dict[Tuple[str, int], str] = {}

    def validate_tx(self, tx: Dict[str, Any]) -> Dict[str, Any]:
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
        existing_hash = self._by_sender_nonce.get(key)
        if existing_hash and existing_hash in self._txs:
            existing = self._txs[existing_hash]
            if int(tx.get("gas_price", 0)) <= int(existing.get("gas_price", 0)):
                errors.append("nonce_already_used_with_higher_or_equal_gas_price")
        if len(self._txs) >= self.max_txs:
            errors.append("mempool_full")
        return {"ok": not errors, "errors": errors}

    def add(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        tx = dict(tx)
        if not tx.get("hash"):
            tx["hash"] = _sha256_hex(tx)
        report = self.validate_tx(tx)
        key = (str(tx.get("from")), int(tx.get("nonce", 0)))
        if tx.get("hash") in self._txs:
            return report
        if "nonce_already_used_with_higher_or_equal_gas_price" in report["errors"]:
            return report
        existing_hash = self._by_sender_nonce.get(key)
        if existing_hash:
            self._txs.pop(existing_hash, None)
        remaining_errors = [e for e in report["errors"] if e != "duplicate_tx_hash"]
        if remaining_errors:
            return {"ok": False, "errors": remaining_errors}
        self._txs[tx["hash"]] = tx
        self._by_sender_nonce[key] = tx["hash"]
        return {"ok": True, "hash": tx["hash"], "size": len(self._txs)}

    def remove_many(self, tx_hashes: Iterable[str]) -> None:
        for h in list(tx_hashes):
            tx = self._txs.pop(h, None)
            if tx:
                self._by_sender_nonce.pop((str(tx.get("from")), int(tx.get("nonce", 0))), None)

    def select_for_block(self, max_txs: int, block_gas_limit: int) -> List[Dict[str, Any]]:
        ordered = sorted(
            self._txs.values(),
            key=lambda t: (int(t.get("gas_price", 0)), -int(t.get("nonce", 0)), str(t.get("hash"))),
            reverse=True,
        )
        selected: List[Dict[str, Any]] = []
        used_gas = 0
        for tx in ordered:
            gas = int(tx.get("gas_limit", 21_000))
            if len(selected) >= max_txs:
                break
            if used_gas + gas > block_gas_limit:
                continue
            selected.append(copy.deepcopy(tx))
            used_gas += gas
        return selected

    def size(self) -> int:
        return len(self._txs)

    def pending(self) -> List[Dict[str, Any]]:
        return list(self._txs.values())

    def as_dict(self) -> Dict[str, Any]:
        return {"size": self.size(), "max_txs": self.max_txs, "min_gas_price": self.min_gas_price, "txs": self.pending()}


class BaseConsensusEngine:
    """Consensus engine interface used by BlockchainNode."""

    mode_name = "base"

    def __init__(self, config: BlockchainConfig) -> None:
        self.config = config
        if not self.validator_set():
            raise ValueError("At least one validator/proposer is required")

    def validator_set(self) -> Dict[str, int]:
        raise NotImplementedError

    def total_stake(self) -> int:
        return sum(self.validator_set().values())

    def select_proposer(self, parent_hash: str, slot: int) -> str:
        raise NotImplementedError

    def validate_proposer(self, parent_hash: str, slot: int, proposer: str) -> bool:
        return self.select_proposer(parent_hash, slot) == proposer

    def block_score(self, block: Dict[str, Any]) -> int:
        stake = int(self.validator_set().get(str(block.get("proposer")), 0))
        return int(block.get("height", 0)) * max(1, self.total_stake()) + stake

    def _signing_key(self, proposer: str) -> str:
        return str(self.config.validator_signing_keys.get(str(proposer), ""))

    def sign_block(self, block: Dict[str, Any]) -> str:
        proposer = str(block.get("proposer", ""))
        key = self._signing_key(proposer)
        if not key:
            if self.config.require_block_signatures:
                raise ValueError(f"missing signing key for proposer {proposer}")
            return ""
        payload = _stable_json(_block_signature_payload(block)).encode("utf-8")
        digest = hmac.new(key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return f"agisig:{proposer}:{digest}"

    def validate_block_signature(self, block: Dict[str, Any]) -> Tuple[bool, str]:
        signature = str(block.get("validator_signature", ""))
        if not signature:
            if self.config.require_block_signatures:
                return False, "missing_validator_signature"
            return True, ""
        proposer = str(block.get("proposer", ""))
        key = self._signing_key(proposer)
        if not key:
            return False, "unknown_validator_signing_key"
        expected = self.sign_block(block)
        if not hmac.compare_digest(signature, expected):
            return False, "invalid_validator_signature"
        return True, ""


class ProofOfStakeEngine(BaseConsensusEngine):
    """Deterministic weighted Proof-of-Stake engine for private chains/devnets."""

    mode_name = "pos"

    def validator_set(self) -> Dict[str, int]:
        minimum = max(1, int(self.config.min_validator_stake))
        return {str(k): int(v) for k, v in self.config.validators.items() if int(v) >= minimum}

    def select_proposer(self, parent_hash: str, slot: int) -> str:
        validators = sorted(self.validator_set().items())
        total = sum(stake for _, stake in validators)
        if total <= 0:
            raise ValueError("Validator set has zero total stake")
        seed = int(hashlib.sha256(f"pos:{parent_hash}:{slot}:{self.config.chain_id}".encode()).hexdigest(), 16)
        pick = seed % total
        cursor = 0
        for validator, stake in validators:
            cursor += stake
            if pick < cursor:
                return validator
        return validators[-1][0]


class DelegatedProofOfStakeEngine(BaseConsensusEngine):
    """Deterministic delegated proof-of-stake consensus engine.

    The engine accepts both the common DPoS name and the user's DPO shorthand.
    ``delegations`` can be supplied either as direct producer weights, e.g.
    ``{"alice": 80, "bob": 20}``, or voter records, e.g.
    ``{"voter1": {"delegate": "alice", "stake": 80}}``.
    """

    mode_name = "dpos"

    def validator_set(self) -> Dict[str, int]:
        weights: Dict[str, int] = {}
        active_delegates = {str(d) for d in self.config.delegates} if self.config.delegates else set()
        if self.config.delegations:
            for key, value in self.config.delegations.items():
                if isinstance(value, dict):
                    delegate = str(value.get("delegate") or value.get("producer") or key)
                    stake = int(value.get("stake", value.get("weight", 0)))
                else:
                    delegate = str(key)
                    stake = int(value)
                if stake > 0 and (not active_delegates or delegate in active_delegates):
                    weights[delegate] = weights.get(delegate, 0) + stake
        if not weights:
            base = {str(k): int(v) for k, v in self.config.validators.items() if int(v) > 0}
            if active_delegates:
                base = {k: v for k, v in base.items() if k in active_delegates}
            weights = base
        minimum = max(1, int(self.config.min_validator_stake))
        return {k: v for k, v in weights.items() if v >= minimum}

    def select_proposer(self, parent_hash: str, slot: int) -> str:
        producers = sorted(self.validator_set().items())
        total = sum(weight for _, weight in producers)
        if total <= 0:
            raise ValueError("DPoS producer set has zero total delegated stake")
        seed = int(hashlib.sha256(f"dpos:{parent_hash}:{slot}:{self.config.chain_id}".encode()).hexdigest(), 16)
        pick = seed % total
        cursor = 0
        for producer, weight in producers:
            cursor += weight
            if pick < cursor:
                return producer
        return producers[-1][0]


class DevConsensusEngine(BaseConsensusEngine):
    """Fast deterministic consensus for local development and simulation."""

    mode_name = "dev"

    def validator_set(self) -> Dict[str, int]:
        validators = {str(k): int(v) for k, v in self.config.validators.items() if int(v) > 0}
        return validators or {"dev-validator": 1}

    def select_proposer(self, parent_hash: str, slot: int) -> str:
        validators = sorted(self.validator_set().keys())
        if not validators:
            raise ValueError("Dev consensus has no proposers")
        return validators[int(slot) % len(validators)]

    def validate_proposer(self, parent_hash: str, slot: int, proposer: str) -> bool:
        if self.config.dev_allow_any_proposer:
            return bool(proposer)
        return str(proposer) in self.validator_set()

    def block_score(self, block: Dict[str, Any]) -> int:
        return int(block.get("height", 0))


def consensus_engine(config: BlockchainConfig | Dict[str, Any]) -> BaseConsensusEngine:
    """Create the configured consensus engine: pos, dpos/dpo or dev."""
    if isinstance(config, dict):
        config = blockchain_config(**config)
    mode = _normalize_consensus_mode(config.consensus_mode)
    if mode == "pos":
        return ProofOfStakeEngine(config)
    if mode == "dpos":
        return DelegatedProofOfStakeEngine(config)
    if mode == "dev":
        return DevConsensusEngine(config)
    raise ValueError(f"unsupported consensus mode: {mode}")


def pos_consensus_engine(config: BlockchainConfig | Dict[str, Any]) -> ProofOfStakeEngine:
    """Create a Proof-of-Stake consensus engine from a config."""
    if isinstance(config, dict):
        config = blockchain_config(**config)
    return ProofOfStakeEngine(config)


def dpos_consensus_engine(config: BlockchainConfig | Dict[str, Any]) -> DelegatedProofOfStakeEngine:
    """Create a DPoS/DPO consensus engine from a config."""
    if isinstance(config, dict):
        config = blockchain_config(**config)
    config.consensus_mode = "dpos"
    return DelegatedProofOfStakeEngine(config)


def dev_consensus_engine(config: BlockchainConfig | Dict[str, Any]) -> DevConsensusEngine:
    """Create a developer consensus engine from a config."""
    if isinstance(config, dict):
        config = blockchain_config(**config)
    config.consensus_mode = "dev"
    return DevConsensusEngine(config)


class BlockchainNode:
    """Full private-chain node framework with PoS consensus, mempool and DB."""

    def __init__(self, config: BlockchainConfig | Dict[str, Any] | None = None, db_path: str | Path = ":memory:", node_id: str | None = None) -> None:
        if config is None:
            config = blockchain_config()
        if isinstance(config, dict):
            config = blockchain_config(**config)
        self.config = config
        self.node_id = node_id or f"node-{uuid.uuid4().hex[:8]}"
        self.db = ChainDatabase(db_path)
        self.mempool = Mempool(config.mempool_max_txs, config.mempool_min_gas_price)
        self.consensus = consensus_engine(config)
        self.peers: List["BlockchainNode"] = []
        self.started_at = _now_ms()
        self._ensure_genesis()

    def _ensure_genesis(self) -> None:
        if self.db.canonical_head() is not None:
            return
        genesis = {
            "chain_id": self.config.chain_id,
            "height": 0,
            "slot": 0,
            "parent_hash": "0x" + "00" * 32,
            "proposer": "genesis",
            "timestamp_ms": 0,
            "transactions": [],
            "tx_root": blockchain_merkle_root([]),
            "state_root": _sha256_hex(self.config.genesis_state),
            "receipts_root": blockchain_merkle_root([]),
            "gas_used": 0,
            "score": 0,
            "extra_data": {
                "name": self.config.name,
                "validators": self.config.validators,
                "consensus_mode": self.config.consensus_mode,
                "mainnet_profile": self.config.mainnet_profile,
            },
        }
        genesis["hash"] = _sha256_hex({k: v for k, v in genesis.items() if k != "hash"})
        self.db.put_block(genesis, canonical=True, finalized=True)
        self.db.put_metadata("head", genesis["hash"])
        self.db.put_state("balances", copy.deepcopy(self.config.genesis_state.get("balances", {})))
        self.db.put_state("contracts", copy.deepcopy(self.config.genesis_state.get("contracts", {})))
        self.db.put_state("nonces", copy.deepcopy(self.config.genesis_state.get("nonces", {})))

    def status(self) -> Dict[str, Any]:
        head = self.head()
        return {
            "node_id": self.node_id,
            "chain_id": self.config.chain_id,
            "name": self.config.name,
            "height": int(head["height"]),
            "head": head["hash"],
            "mempool_size": self.mempool.size(),
            "peers": len(self.peers),
            "validators": self.config.validators,
            "consensus": self.config.consensus_mode,
            "consensus_engine": self.consensus.__class__.__name__,
            "mainnet_profile": self.config.mainnet_profile,
            "require_block_signatures": self.config.require_block_signatures,
            "fork_choice": self.config.fork_choice,
        }

    def head(self) -> Dict[str, Any]:
        head = self.db.canonical_head()
        if head is None:
            raise RuntimeError("chain has no canonical head")
        return head

    def height(self) -> int:
        return int(self.head()["height"])

    def connect_peer(self, peer: "BlockchainNode") -> None:
        if peer is self:
            return
        if peer not in self.peers:
            self.peers.append(peer)
        if self not in peer.peers:
            peer.peers.append(self)

    def submit_tx(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        state_report = self.validate_tx_against_state(tx)
        if not state_report.get("ok"):
            return state_report
        report = self.mempool.add(tx)
        if report.get("ok"):
            self.gossip({"type": "tx", "tx": tx}, exclude=None)
        return report

    def mempool_status(self) -> Dict[str, Any]:
        return self.mempool.as_dict()

    def _current_slot(self) -> int:
        return max(1, int(time.time() // max(1, self.config.slot_seconds)))

    def produce_block(self, validator: str | None = None, slot: int | None = None, max_txs: Optional[int] = None) -> Dict[str, Any]:
        parent = self.head()
        slot = int(slot if slot is not None else max(int(parent.get("slot", 0)) + 1, self._current_slot()))
        expected = self.consensus.select_proposer(parent["hash"], slot)
        proposer = validator or expected
        if proposer != expected:
            raise ValueError(f"invalid proposer for slot {slot}: expected {expected}, got {proposer}")
        txs = self.mempool.select_for_block(max_txs or self.config.max_block_txs, self.config.block_gas_limit)
        if not txs and not self.config.allow_empty_blocks:
            raise ValueError("empty block production disabled")
        receipts, state_updates, gas_used = self._execute_transactions(txs)
        block = {
            "chain_id": self.config.chain_id,
            "height": int(parent["height"]) + 1,
            "slot": slot,
            "parent_hash": parent["hash"],
            "proposer": proposer,
            "timestamp_ms": _now_ms(),
            "transactions": txs,
            "receipts": receipts,
            "tx_root": blockchain_merkle_root(txs),
            "state_updates": state_updates,
            "state_root": _sha256_hex(state_updates),
            "receipts_root": blockchain_merkle_root(receipts),
            "gas_used": gas_used,
            "extra_data": {"node_id": self.node_id, "consensus_mode": self.config.consensus_mode},
        }
        block["score"] = self.consensus.block_score(block)
        signature = self.consensus.sign_block(block)
        if signature:
            block["validator_signature"] = signature
        block["hash"] = _sha256_hex({k: v for k, v in block.items() if k != "hash"})
        return block

    def validate_tx_against_state(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        """Validate account-level rules against the current canonical state.

        The default private-chain profile is permissive so users can prototype
        protocols quickly.  When ``strict_accounting`` is enabled, transfer
        transactions must have sufficient balance and nonces must match the
        sender account nonce tracked in state.
        """
        errors: List[str] = []
        balances = dict(self.db.get_state("balances", {}))
        nonces = dict(self.db.get_state("nonces", {}))
        sender = str(tx.get("from", ""))
        if self.config.strict_accounting and tx.get("type") == "transfer":
            value = int(tx.get("value", 0))
            if int(balances.get(sender, 0)) < value:
                errors.append("insufficient_balance")
        if self.config.enforce_nonce_order and self.config.strict_accounting:
            expected_nonce = int(nonces.get(sender, 0)) + 1
            if int(tx.get("nonce", 0)) != expected_nonce:
                errors.append(f"invalid_nonce_expected_{expected_nonce}")
        return {"ok": not errors, "errors": errors, "hash": tx.get("hash")}

    def _genesis_state_copy(self) -> Dict[str, Any]:
        """Return a normalized mutable copy of the configured genesis state."""
        return {
            "balances": dict(self.config.genesis_state.get("balances", {})),
            "contracts": dict(self.config.genesis_state.get("contracts", {})),
            "nonces": dict(self.config.genesis_state.get("nonces", {})),
        }

    def _apply_successful_tx_to_state(
        self,
        tx: Dict[str, Any],
        balances: Dict[str, Any],
        contracts: Dict[str, Any],
        nonces: Dict[str, int],
    ) -> None:
        """Apply only successful transaction effects during deterministic replay."""
        sender = str(tx.get("from", ""))
        nonces[sender] = max(int(nonces.get(sender, 0)), int(tx.get("nonce", 0)))
        if tx.get("type") == "transfer":
            to = str(tx.get("to", ""))
            value = int(tx.get("value", 0))
            balances[sender] = int(balances.get(sender, 0)) - value
            balances[to] = int(balances.get(to, 0)) + value
        elif tx.get("type") == "deploy_contract":
            address = str(tx.get("to") or ("0x" + str(tx.get("hash", ""))[-40:]))
            contracts[address] = tx.get("data", "0x")

    def _apply_block_to_state(
        self,
        block: Dict[str, Any],
        balances: Dict[str, Any],
        contracts: Dict[str, Any],
        nonces: Dict[str, int],
    ) -> None:
        """Replay a block using receipts so failed transactions do not mutate state."""
        receipts = {str(r.get("tx_hash", "")): r for r in block.get("receipts", [])}
        for tx in block.get("transactions", []):
            receipt = receipts.get(str(tx.get("hash", "")), {"ok": True})
            if bool(receipt.get("ok", True)):
                self._apply_successful_tx_to_state(tx, balances, contracts, nonces)

    def _state_at_block(self, block_hash: str) -> Dict[str, Any]:
        """Rebuild state from genesis through the requested known block."""
        path: List[Dict[str, Any]] = []
        cursor = self.db.get_block(block_hash)
        while cursor is not None and int(cursor.get("height", 0)) > 0:
            path.append(cursor)
            cursor = self.db.get_block(str(cursor.get("parent_hash", "")))
        state = self._genesis_state_copy()
        balances = state["balances"]
        contracts = state["contracts"]
        nonces = state["nonces"]
        for block in reversed(path):
            self._apply_block_to_state(block, balances, contracts, nonces)
        return state

    def _rebuild_canonical_state(self) -> Dict[str, Any]:
        """Replay the canonical chain to rebuild balances, nonces and contracts.

        This keeps state deterministic after fork-choice changes/reorgs and uses
        receipts so failed transactions never mutate canonical state.
        """
        state = self._genesis_state_copy()
        balances = state["balances"]
        contracts = state["contracts"]
        nonces = state["nonces"]
        for block in self.canonical_chain():
            if int(block.get("height", 0)) == 0:
                continue
            self._apply_block_to_state(block, balances, contracts, nonces)
        self.db.put_state("balances", balances)
        self.db.put_state("contracts", contracts)
        self.db.put_state("nonces", nonces)
        return {"balances": balances, "contracts": contracts, "nonces": nonces}

    def _execute_transactions(
        self,
        txs: List[Dict[str, Any]],
        base_state: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], int]:
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
                expected_nonce = int(nonces.get(sender, 0)) + 1
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
                    nonces[sender] = max(int(nonces.get(sender, 0)), int(tx.get("nonce", 0)))
            elif ok and tx.get("type") in {"contract_call", "evm_call"} and self.config.evm_enabled and evm_simulate_call:
                bytecode = contracts.get(str(tx.get("to")), tx.get("code", "0x"))
                try:
                    result = evm_simulate_call(bytecode, tx.get("data", "0x"), gas=int(tx.get("gas_limit", 1000000)))
                    ok = bool(result.get("ok", True))
                    error = str(result.get("error", ""))
                    used = int(result.get("gas_used", used))
                except Exception as exc:  # pragma: no cover - defensive
                    ok = False
                    error = str(exc)
            elif ok and tx.get("type") == "deploy_contract":
                address = str(tx.get("to") or ("0x" + tx["hash"][-40:]))
                contracts[address] = tx.get("data", "0x")
                nonces[sender] = max(int(nonces.get(sender, 0)), int(tx.get("nonce", 0)))
            gas_used += used
            receipts.append({"tx_hash": tx["hash"], "ok": ok, "gas_used": used, "error": error})
        return receipts, {"balances": balances, "contracts": contracts, "nonces": nonces}, gas_used

    def validate_block(self, block: Dict[str, Any]) -> Dict[str, Any]:
        errors: List[str] = []
        if int(block.get("chain_id", -1)) != self.config.chain_id:
            errors.append("wrong_chain_id")
        parent = self.db.get_block(block.get("parent_hash", ""))
        if parent is None:
            errors.append("unknown_parent")
        else:
            if int(block.get("height", -1)) != int(parent["height"]) + 1:
                errors.append("invalid_height")
            if not self.consensus.validate_proposer(parent["hash"], int(block.get("slot", 0)), str(block.get("proposer", ""))):
                errors.append(f"invalid_{self.config.consensus_mode}_proposer")
            if self.config.mainnet_profile and int(block.get("timestamp_ms", 0)) > _now_ms() + max(0, self.config.max_clock_drift_ms):
                errors.append("future_block_timestamp")
            sig_ok, sig_error = self.consensus.validate_block_signature(block)
            if not sig_ok:
                errors.append(sig_error)
        txs = block.get("transactions", [])
        receipts = block.get("receipts", [])
        if len(txs) > self.config.max_block_txs:
            errors.append("too_many_transactions")
        tx_hashes = [tx.get("hash") for tx in txs]
        if len(tx_hashes) != len(set(tx_hashes)):
            errors.append("duplicate_transactions_in_block")
        for tx in txs:
            if not tx.get("hash"):
                errors.append("missing_tx_hash")
            if not tx.get("from"):
                errors.append("missing_tx_sender")
            if int(tx.get("gas_limit", 0)) <= 0:
                errors.append("invalid_tx_gas_limit")
            if int(tx.get("gas_price", 0)) < 0:
                errors.append("invalid_tx_gas_price")
            if int(tx.get("gas_price", 0)) < self.config.mempool_min_gas_price:
                errors.append("tx_gas_price_below_minimum")
            if int(tx.get("value", 0)) < 0:
                errors.append("invalid_tx_negative_value")
            if int(tx.get("nonce", 0)) < 0:
                errors.append("invalid_tx_negative_nonce")
        if blockchain_merkle_root(txs) != block.get("tx_root"):
            errors.append("invalid_tx_root")
        if blockchain_merkle_root(receipts) != block.get("receipts_root"):
            errors.append("invalid_receipts_root")
        if int(block.get("gas_used", 0)) != sum(int(r.get("gas_used", 0)) for r in receipts):
            errors.append("invalid_gas_used")
        if parent is not None:
            expected_receipts, expected_state, expected_gas = self._execute_transactions(
                copy.deepcopy(txs),
                base_state=self._state_at_block(parent["hash"]),
            )
            if receipts != expected_receipts:
                errors.append("invalid_receipts")
            if int(block.get("gas_used", 0)) != int(expected_gas):
                errors.append("invalid_execution_gas_used")
            if block.get("state_updates") != expected_state:
                errors.append("invalid_state_updates")
            if block.get("state_root") != _sha256_hex(expected_state):
                errors.append("invalid_state_root")
        candidate = copy.deepcopy(block)
        h = candidate.pop("hash", None)
        if h != _sha256_hex(candidate):
            errors.append("invalid_block_hash")
        if int(block.get("gas_used", 0)) > self.config.block_gas_limit:
            errors.append("block_gas_limit_exceeded")
        return {"ok": not errors, "errors": errors, "hash": block.get("hash")}

    def import_block(self, block: Dict[str, Any], *, validate: bool = True) -> Dict[str, Any]:
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
        return {"ok": True, "hash": block["hash"], "height": block["height"], "canonical_head": self.head()["hash"]}

    def produce_and_import_block(self, validator: str | None = None, slot: int | None = None) -> Dict[str, Any]:
        block = self.produce_block(validator=validator, slot=slot)
        result = self.import_block(block)
        if result.get("ok"):
            self.gossip({"type": "block", "block": block}, exclude=None)
        return {"block": block, "import": result}

    def apply_fork_choice(self) -> Dict[str, Any]:
        candidates = self.db.candidate_heads()
        if not candidates:
            return {"ok": False, "error": "no_heads"}
        best = max(candidates, key=lambda b: (int(b.get("score", 0)), int(b.get("height", 0)), str(b.get("hash", ""))))
        self.db.set_canonical_chain(best["hash"], finality_depth=self.config.finality_depth)
        self.db.put_metadata("head", best["hash"])
        return {"ok": True, "head": best["hash"], "height": best["height"], "score": best.get("score", 0)}

    def fork_choice(self) -> Dict[str, Any]:
        return self.apply_fork_choice()

    def canonical_chain(self) -> List[Dict[str, Any]]:
        return self.db.list_canonical()

    def finalized_head(self) -> Optional[Dict[str, Any]]:
        chain = self.canonical_chain()
        finalized = [b for b in chain if b.get("finalized")]
        return finalized[-1] if finalized else None

    def gossip(self, message: Dict[str, Any], exclude: Optional["BlockchainNode"] = None) -> Dict[str, Any]:
        delivered = 0
        for peer in list(self.peers):
            if peer is exclude:
                continue
            peer.receive_gossip(message, from_peer=self)
            delivered += 1
        return {"ok": True, "delivered": delivered, "type": message.get("type")}

    def receive_gossip(self, message: Dict[str, Any], from_peer: Optional["BlockchainNode"] = None) -> Dict[str, Any]:
        mtype = message.get("type")
        if mtype == "tx":
            return self.mempool.add(message["tx"])
        if mtype == "block":
            return self.import_block(message["block"])
        if mtype == "status":
            return {"ok": True, "status": self.status()}
        return {"ok": False, "error": "unknown_gossip_type"}

    def sync_from(self, peer: "BlockchainNode") -> Dict[str, Any]:
        imported = 0
        for block in peer.canonical_chain():
            if not self.db.has_block(block["hash"]):
                result = self.import_block(block, validate=(int(block.get("height", 0)) != 0))
                if result.get("ok"):
                    imported += 1
        for tx in peer.mempool.pending():
            self.mempool.add(tx)
        return {"ok": True, "imported_blocks": imported, "height": self.height(), "head": self.head()["hash"]}

    def export_genesis(self) -> Dict[str, Any]:
        chain = self.canonical_chain()
        return chain[0] if chain else {}

    def export_config(self) -> Dict[str, Any]:
        return self.config.as_dict()


class Devnet:
    """In-process p2p/devnet harness for testing blockchain configurations."""

    def __init__(self, config: BlockchainConfig | Dict[str, Any] | None = None, validators: Optional[List[str]] = None) -> None:
        if config is None:
            config = blockchain_config()
        if isinstance(config, dict):
            config = blockchain_config(**config)
        self.config = config
        validators = validators or list(config.validators.keys())
        self.nodes = [BlockchainNode(config, node_id=f"{v}-node") for v in validators]
        for i, node in enumerate(self.nodes):
            for peer in self.nodes[i + 1:]:
                node.connect_peer(peer)

    def status(self) -> Dict[str, Any]:
        return {"nodes": [n.status() for n in self.nodes]}

    def submit_tx(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        return self.nodes[0].submit_tx(tx)

    def step(self, validator: Optional[str] = None) -> Dict[str, Any]:
        proposer_node = self.nodes[0]
        parent = proposer_node.head()
        slot = max(int(parent.get("slot", 0)) + 1, proposer_node._current_slot())
        proposer = validator or proposer_node.consensus.select_proposer(parent["hash"], slot)
        for node in self.nodes:
            if node.node_id.startswith(proposer) or proposer in node.node_id:
                proposer_node = node
                break
        produced = proposer_node.produce_and_import_block(validator=proposer, slot=slot)
        for node in self.nodes:
            if node is not proposer_node:
                node.sync_from(proposer_node)
        return {"ok": True, "proposer": proposer, "block": produced["block"], "network": self.status()}

    def sync_all(self) -> Dict[str, Any]:
        for node in self.nodes:
            for peer in self.nodes:
                if node is not peer:
                    node.sync_from(peer)
        return self.status()


def blockchain_node(config: BlockchainConfig | Dict[str, Any] | None = None, db_path: str | Path = ":memory:", node_id: str | None = None) -> BlockchainNode:
    return BlockchainNode(config=config, db_path=db_path, node_id=node_id)


def blockchain_devnet(config: BlockchainConfig | Dict[str, Any] | None = None, validators: Optional[List[str]] = None) -> Devnet:
    return Devnet(config=config, validators=validators)


def blockchain_consensus_simulation() -> Dict[str, Any]:
    """Run a deterministic local simulation across PoS, DPoS/DPO and Dev modes."""
    scenarios = [
        blockchain_config(
            chain_id=1930,
            name="agilang-pos-sim",
            consensus_mode="pos",
            validators={"alice": 60, "bob": 40},
            genesis_state={"balances": {"alice": 1000, "bob": 100}},
            slot_seconds=1,
            strict_accounting=True,
        ),
        blockchain_config(
            chain_id=1931,
            name="agilang-dpos-sim",
            consensus_mode="dpo",
            validators={"alice": 1, "bob": 1},
            delegates=["alice", "bob"],
            delegations={"voter-a": {"delegate": "alice", "stake": 90}, "voter-b": {"delegate": "bob", "stake": 30}},
            genesis_state={"balances": {"alice": 1000, "bob": 100}},
            slot_seconds=1,
            strict_accounting=True,
        ),
        blockchain_config(
            chain_id=1932,
            name="agilang-dev-sim",
            consensus_mode="dev",
            validators={"dev-a": 1, "dev-b": 1},
            genesis_state={"balances": {"dev-a": 1000, "dev-b": 100}},
            slot_seconds=1,
            strict_accounting=True,
        ),
        blockchain_mainnet_config(
            chain_id=1933,
            name="agilang-mainnet-profile-sim",
            consensus_mode="pos",
            validators={"alice": 100, "bob": 80},
            validator_signing_keys={"alice": "alice-mainnet-key", "bob": "bob-mainnet-key"},
            genesis_state={"balances": {"alice": 1000, "bob": 100}},
            slot_seconds=1,
        ),
    ]
    results: List[Dict[str, Any]] = []
    for cfg in scenarios:
        net = blockchain_devnet(cfg, validators=list(cfg.validators.keys()))
        sender = list(cfg.validators.keys())[0]
        receiver = list(cfg.validators.keys())[1] if len(cfg.validators) > 1 else "receiver"
        tx = blockchain_transaction(sender, receiver, 5, nonce=1, gas_price=max(1, cfg.mempool_min_gas_price))
        submit = net.submit_tx(tx)
        step = net.step()
        heights = [node["height"] for node in net.status()["nodes"]]
        results.append(
            {
                "name": cfg.name,
                "consensus_mode": cfg.consensus_mode,
                "mainnet_profile": cfg.mainnet_profile,
                "submit_ok": bool(submit.get("ok")),
                "height": step["block"]["height"],
                "proposer": step["proposer"],
                "signed": bool(step["block"].get("validator_signature")),
                "network_heights": heights,
                "synced": len(set(heights)) == 1,
            }
        )
    return {"ok": all(r["submit_ok"] and r["synced"] and r["height"] >= 1 for r in results), "scenarios": results}


def blockchain_capabilities() -> Dict[str, Any]:
    return {
        "chain_database": "sqlite_canonical_blocks_transactions_state_replayable_reorgs",
        "mempool": ["validation", "replacement", "gas_price_ordering", "capacity_limits", "duplicate_rejection", "state_aware_submission"],
        "consensus": [
            "proof_of_stake",
            "pos",
            "delegated_proof_of_stake",
            "dpos",
            "dpo_alias",
            "dev_consensus",
            "pluggable_consensus_engine",
            "weighted_validator_selection",
            "delegated_producer_selection",
            "proposer_validation",
        ],
        "fork_choice": ["stake_weighted_height", "canonical_reorg", "finality_depth"],
        "block_production": ["tx_selection", "gas_limit", "receipts", "state_root", "tx_root", "gas_used_validation", "validator_signature_hooks"],
        "p2p_sync": ["in_process_devnet", "gossip_tx", "gossip_block", "sync_from_peer"],
        "evm_hooks": ["contract_call", "deploy_contract", "evm_runtime_bridge"],
        "mainnet_profile": ["strict_accounting", "nonce_ordering", "required_block_signatures", "minimum_gas_price", "higher_finality_depth", "timestamp_drift_check"],
        "templates": ["blockchain", "systems", "web", "zk"],
        "production_boundary": "mainnet-capable framework profile for simulation/staging; public real-value networks still require audited cryptographic networking, peer scoring, slashing economics, DoS hardening and independent security review",
    }


def blockchain_demo() -> Dict[str, Any]:
    config = blockchain_config(
        name="agilang-demo-chain",
        chain_id=1900,
        validators={"alice": 60, "bob": 40},
        genesis_state={"balances": {"alice": 1000, "bob": 500}},
        slot_seconds=1,
    )
    net = blockchain_devnet(config, validators=["alice", "bob"])
    tx = blockchain_transaction("alice", "bob", 25, nonce=1, gas_price=1)
    submit = net.submit_tx(tx)
    step = net.step()
    return {
        "capabilities": blockchain_capabilities(),
        "config": config.as_dict(),
        "submit": submit,
        "block_hash": step["block"]["hash"],
        "height": step["block"]["height"],
        "network": net.status(),
    }
