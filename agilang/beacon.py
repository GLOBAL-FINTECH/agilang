"""Native SBQ Beacon Chain consensus layer for AGILANG.

This module implements a Beacon-chain-inspired consensus layer for AGILANG/SBQ
custom chains. It is intentionally separate from Ethereum mainnet consensus.
For live Ethereum mainnet validation, use official Ethereum execution,
consensus, and validator clients.

The SBQ Beacon layer provides:
- configurable slots and epochs
- validator registry
- proposer selection
- beacon blocks with execution payloads
- validator attestations
- checkpoint justification/finalization
- attestation-weighted fork choice
- slashing-rule detection hooks
- SQLite persistence for local/staging chains
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_SLOT_SECONDS = 6
DEFAULT_SLOTS_PER_EPOCH = 16
DEFAULT_FINALITY_THRESHOLD = 2 / 3
DEFAULT_CHAIN_ID = 1900
GENESIS_ROOT = "0x" + "00" * 32


def _sha256_hex(value: str) -> str:
    return "0x" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> int:
    return int(time.time())


@dataclass
class BeaconConfig:
    chain_id: int = DEFAULT_CHAIN_ID
    network: str = "sbq-beacon"
    consensus: str = "sbq-beacon"
    slot_seconds: int = DEFAULT_SLOT_SECONDS
    slots_per_epoch: int = DEFAULT_SLOTS_PER_EPOCH
    finality_threshold: float = DEFAULT_FINALITY_THRESHOLD
    min_validator_stake: int = 1_000
    genesis_time: int = field(default_factory=_now)

    def epoch_for_slot(self, slot: int) -> int:
        return int(slot) // max(1, int(self.slots_per_epoch))

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BeaconValidator:
    address: str
    stake: int
    status: str = "active"  # active, pending, exited, slashed
    index: int = 0

    def active(self) -> bool:
        return self.status == "active" and int(self.stake) > 0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionPayload:
    block_hash: str
    block_number: int
    state_root: str = GENESIS_ROOT
    tx_root: str = GENESIS_ROOT
    receipts_root: str = GENESIS_ROOT
    gas_used: int = 0
    extra_data: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Checkpoint:
    epoch: int
    root: str

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BeaconAttestation:
    validator: str
    slot: int
    source_epoch: int
    target_epoch: int
    head_root: str
    signature: str = ""

    def signing_root(self) -> str:
        return _sha256_hex(json.dumps({
            "validator": self.validator,
            "slot": int(self.slot),
            "source_epoch": int(self.source_epoch),
            "target_epoch": int(self.target_epoch),
            "head_root": self.head_root,
        }, sort_keys=True))

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BeaconBlock:
    slot: int
    epoch: int
    parent_root: str
    proposer: str
    execution_payload: ExecutionPayload
    attestations: List[BeaconAttestation] = field(default_factory=list)
    timestamp: int = field(default_factory=_now)
    root: str = ""

    def compute_root(self) -> str:
        return _sha256_hex(json.dumps({
            "slot": int(self.slot),
            "epoch": int(self.epoch),
            "parent_root": self.parent_root,
            "proposer": self.proposer,
            "execution_payload": self.execution_payload.as_dict(),
            "attestations": [a.as_dict() for a in self.attestations],
            "timestamp": int(self.timestamp),
        }, sort_keys=True))

    def ensure_root(self) -> str:
        if not self.root:
            self.root = self.compute_root()
        return self.root

    def as_dict(self) -> Dict[str, Any]:
        self.ensure_root()
        return {
            "slot": int(self.slot),
            "epoch": int(self.epoch),
            "parent_root": self.parent_root,
            "proposer": self.proposer,
            "execution_payload": self.execution_payload.as_dict(),
            "attestations": [a.as_dict() for a in self.attestations],
            "timestamp": int(self.timestamp),
            "root": self.root,
        }


@dataclass
class BeaconState:
    config: BeaconConfig = field(default_factory=BeaconConfig)
    validators: List[BeaconValidator] = field(default_factory=list)
    blocks: Dict[str, BeaconBlock] = field(default_factory=dict)
    head_root: str = GENESIS_ROOT
    current_slot: int = 0
    justified_checkpoint: Checkpoint = field(default_factory=lambda: Checkpoint(0, GENESIS_ROOT))
    finalized_checkpoint: Checkpoint = field(default_factory=lambda: Checkpoint(0, GENESIS_ROOT))

    def active_validators(self) -> List[BeaconValidator]:
        return [v for v in self.validators if v.active()]

    def total_active_stake(self) -> int:
        return sum(int(v.stake) for v in self.active_validators())

    def epoch(self) -> int:
        return self.config.epoch_for_slot(self.current_slot)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.as_dict(),
            "validators": [v.as_dict() for v in self.validators],
            "head_root": self.head_root,
            "current_slot": int(self.current_slot),
            "current_epoch": self.epoch(),
            "justified_checkpoint": self.justified_checkpoint.as_dict(),
            "finalized_checkpoint": self.finalized_checkpoint.as_dict(),
            "block_count": len(self.blocks),
        }


def default_validators() -> List[BeaconValidator]:
    return [
        BeaconValidator("0x04aac0173878aee604c1eaec3455ca8b5719f39b", 40_000, "active", 0),
        BeaconValidator("0x95e3673f703cb53b3c1848cd3def70a64c59fb08", 35_000, "active", 1),
        BeaconValidator("0x42753c26f7ef0deedcd27967b34ed48b294e1443", 25_000, "active", 2),
    ]


def sbq_beacon_config(**overrides: Any) -> BeaconConfig:
    cfg = BeaconConfig()
    for key, value in overrides.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
    return cfg


def create_beacon_state(config: Optional[BeaconConfig] = None, validators: Optional[List[BeaconValidator]] = None) -> BeaconState:
    return BeaconState(config=config or BeaconConfig(), validators=validators or default_validators())


def beacon_capabilities() -> Dict[str, Any]:
    return {
        "name": "AGILANG Native SBQ Beacon Consensus Layer",
        "version": "2.1.0",
        "consensus": "sbq-beacon",
        "ethereum_mainnet_replacement": False,
        "ethereum_mainnet_boundary": "Use official Ethereum clients for live Ethereum mainnet validation.",
        "features": [
            "slots",
            "epochs",
            "validator_registry",
            "proposer_selection",
            "beacon_blocks",
            "execution_payload_bridge",
            "attestations",
            "checkpoint_justification",
            "checkpoint_finalization",
            "attestation_weighted_fork_choice",
            "double_proposal_slashing_detection",
            "double_vote_slashing_detection",
            "sqlite_persistence",
            "simulation",
        ],
        "defaults": BeaconConfig().as_dict(),
    }


def select_proposer(validators: List[BeaconValidator], slot: int) -> BeaconValidator:
    active = [v for v in validators if v.active()]
    if not active:
        raise ValueError("no active validators available")
    total = sum(int(v.stake) for v in active)
    if total <= 0:
        return active[int(slot) % len(active)]
    pointer = int(slot) % total
    running = 0
    for validator in active:
        running += int(validator.stake)
        if pointer < running:
            return validator
    return active[-1]


def committee_for_slot(validators: List[BeaconValidator], slot: int, size: Optional[int] = None) -> List[BeaconValidator]:
    active = [v for v in validators if v.active()]
    if not active:
        return []
    committee_size = size or len(active)
    start = int(slot) % len(active)
    return [active[(start + i) % len(active)] for i in range(min(committee_size, len(active)))]


def make_execution_payload(slot: int, parent_root: str, block_number: Optional[int] = None, extra_data: Optional[Dict[str, Any]] = None) -> ExecutionPayload:
    number = int(block_number if block_number is not None else slot)
    payload_seed = json.dumps({"slot": int(slot), "parent_root": parent_root, "block_number": number, "extra_data": extra_data or {}}, sort_keys=True)
    return ExecutionPayload(
        block_hash=_sha256_hex("execution:" + payload_seed),
        block_number=number,
        state_root=_sha256_hex("state:" + payload_seed),
        tx_root=_sha256_hex("tx:" + payload_seed),
        receipts_root=_sha256_hex("receipts:" + payload_seed),
        gas_used=0,
        extra_data=extra_data or {},
    )


def produce_beacon_block(state: BeaconState, execution_payload: Optional[ExecutionPayload] = None) -> BeaconBlock:
    slot = int(state.current_slot) + 1
    epoch = state.config.epoch_for_slot(slot)
    proposer = select_proposer(state.validators, slot)
    payload = execution_payload or make_execution_payload(slot, state.head_root)
    block = BeaconBlock(
        slot=slot,
        epoch=epoch,
        parent_root=state.head_root,
        proposer=proposer.address,
        execution_payload=payload,
    )
    block.ensure_root()
    state.blocks[block.root] = block
    state.head_root = block.root
    state.current_slot = slot
    return block


def attest_to_head(state: BeaconState, slot: Optional[int] = None, validators: Optional[Iterable[BeaconValidator]] = None) -> List[BeaconAttestation]:
    attest_slot = int(slot if slot is not None else state.current_slot)
    target_epoch = state.config.epoch_for_slot(attest_slot)
    source_epoch = int(state.justified_checkpoint.epoch)
    committee = list(validators) if validators is not None else committee_for_slot(state.validators, attest_slot)
    attestations: List[BeaconAttestation] = []
    for validator in committee:
        if not validator.active():
            continue
        att = BeaconAttestation(
            validator=validator.address,
            slot=attest_slot,
            source_epoch=source_epoch,
            target_epoch=target_epoch,
            head_root=state.head_root,
            signature=f"agisig:{validator.address}:{_sha256_hex(validator.address + state.head_root + str(attest_slot))[2:]}",
        )
        attestations.append(att)
    block = state.blocks.get(state.head_root)
    if block:
        block.attestations.extend(attestations)
    return attestations


def attestation_weight(state: BeaconState, attestations: Iterable[BeaconAttestation], head_root: Optional[str] = None) -> int:
    validator_stake = {v.address: int(v.stake) for v in state.validators if v.active()}
    target = head_root
    weight = 0
    seen: set[str] = set()
    for att in attestations:
        if target is not None and att.head_root != target:
            continue
        if att.validator in seen:
            continue
        seen.add(att.validator)
        weight += validator_stake.get(att.validator, 0)
    return weight


def process_epoch_finality(state: BeaconState, attestations: Optional[Iterable[BeaconAttestation]] = None) -> Dict[str, Any]:
    all_attestations = list(attestations or [])
    if not all_attestations:
        for block in state.blocks.values():
            all_attestations.extend(block.attestations)

    target_epoch = state.config.epoch_for_slot(state.current_slot)
    epoch_attestations = [a for a in all_attestations if int(a.target_epoch) == int(target_epoch)]
    total = max(1, state.total_active_stake())
    weight = attestation_weight(state, epoch_attestations)
    participation = weight / total
    justified = False
    finalized = False

    if participation >= float(state.config.finality_threshold):
        previous_justified = state.justified_checkpoint
        state.justified_checkpoint = Checkpoint(target_epoch, state.head_root)
        justified = True
        if previous_justified.epoch < target_epoch:
            state.finalized_checkpoint = previous_justified
            finalized = True

    return {
        "ok": True,
        "target_epoch": target_epoch,
        "attesting_stake": weight,
        "total_active_stake": total,
        "participation": participation,
        "threshold": state.config.finality_threshold,
        "justified": justified,
        "finalized": finalized,
        "justified_checkpoint": state.justified_checkpoint.as_dict(),
        "finalized_checkpoint": state.finalized_checkpoint.as_dict(),
    }


def fork_choice_head(state: BeaconState) -> Dict[str, Any]:
    candidates: Dict[str, int] = {}
    for block in state.blocks.values():
        candidates.setdefault(block.root, 0)
        candidates[block.root] += attestation_weight(state, block.attestations, block.root)
    if not candidates:
        return {"ok": True, "head": state.head_root, "reason": "no_blocks"}
    chosen = max(candidates.items(), key=lambda item: (item[1], state.blocks[item[0]].slot, item[0]))
    state.head_root = chosen[0]
    return {
        "ok": True,
        "head": chosen[0],
        "attestation_weight": chosen[1],
        "slot": state.blocks[chosen[0]].slot,
        "epoch": state.blocks[chosen[0]].epoch,
    }


def detect_slashable_events(blocks: Iterable[BeaconBlock], attestations: Iterable[BeaconAttestation]) -> Dict[str, Any]:
    slashable: List[Dict[str, Any]] = []
    proposals: Dict[Tuple[str, int], str] = {}
    votes: Dict[Tuple[str, int], str] = {}

    for block in blocks:
        key = (block.proposer, int(block.slot))
        prior = proposals.get(key)
        if prior and prior != block.root:
            slashable.append({"type": "double_proposal", "validator": block.proposer, "slot": block.slot, "roots": [prior, block.root]})
        proposals[key] = block.root

    for att in attestations:
        key = (att.validator, int(att.target_epoch))
        prior = votes.get(key)
        if prior and prior != att.head_root:
            slashable.append({"type": "double_vote", "validator": att.validator, "target_epoch": att.target_epoch, "heads": [prior, att.head_root]})
        votes[key] = att.head_root

    return {"ok": True, "slashable": slashable, "count": len(slashable)}


class BeaconStore:
    """SQLite persistence adapter for the native SBQ Beacon layer."""

    def __init__(self, path: str | Path = "storage/beacon.sqlite") -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                create table if not exists meta (
                    key text primary key,
                    value text not null
                );
                create table if not exists validators (
                    address text primary key,
                    stake integer not null,
                    status text not null,
                    idx integer not null
                );
                create table if not exists blocks (
                    root text primary key,
                    slot integer not null,
                    epoch integer not null,
                    parent_root text not null,
                    proposer text not null,
                    execution_payload text not null,
                    timestamp integer not null
                );
                create table if not exists attestations (
                    id integer primary key autoincrement,
                    validator text not null,
                    slot integer not null,
                    source_epoch integer not null,
                    target_epoch integer not null,
                    head_root text not null,
                    signature text not null
                );
                """
            )

    def save_state(self, state: BeaconState) -> None:
        self.init()
        with self.connect() as conn:
            conn.execute("delete from attestations")
            conn.execute("delete from blocks")
            conn.execute("delete from validators")
            for key, value in {
                "config": state.config.as_dict(),
                "head_root": state.head_root,
                "current_slot": state.current_slot,
                "justified_checkpoint": state.justified_checkpoint.as_dict(),
                "finalized_checkpoint": state.finalized_checkpoint.as_dict(),
            }.items():
                conn.execute("insert or replace into meta (key, value) values (?, ?)", (key, json.dumps(value)))
            for v in state.validators:
                conn.execute(
                    "insert or replace into validators (address, stake, status, idx) values (?, ?, ?, ?)",
                    (v.address, int(v.stake), v.status, int(v.index)),
                )
            for block in state.blocks.values():
                block.ensure_root()
                conn.execute(
                    "insert or replace into blocks (root, slot, epoch, parent_root, proposer, execution_payload, timestamp) values (?, ?, ?, ?, ?, ?, ?)",
                    (block.root, int(block.slot), int(block.epoch), block.parent_root, block.proposer, json.dumps(block.execution_payload.as_dict()), int(block.timestamp)),
                )
                for att in block.attestations:
                    conn.execute(
                        "insert into attestations (validator, slot, source_epoch, target_epoch, head_root, signature) values (?, ?, ?, ?, ?, ?)",
                        (att.validator, int(att.slot), int(att.source_epoch), int(att.target_epoch), att.head_root, att.signature),
                    )

    def load_state(self) -> BeaconState:
        self.init()
        with self.connect() as conn:
            meta = {row["key"]: json.loads(row["value"]) for row in conn.execute("select key, value from meta")}
            if "config" in meta:
                cfg = BeaconConfig(**meta["config"])
            else:
                cfg = BeaconConfig()
            validators = [
                BeaconValidator(row["address"], int(row["stake"]), row["status"], int(row["idx"]))
                for row in conn.execute("select address, stake, status, idx from validators order by idx")
            ] or default_validators()
            state = BeaconState(config=cfg, validators=validators)
            state.head_root = meta.get("head_root", GENESIS_ROOT)
            state.current_slot = int(meta.get("current_slot", 0))
            if "justified_checkpoint" in meta:
                state.justified_checkpoint = Checkpoint(**meta["justified_checkpoint"])
            if "finalized_checkpoint" in meta:
                state.finalized_checkpoint = Checkpoint(**meta["finalized_checkpoint"])

            blocks: Dict[str, BeaconBlock] = {}
            for row in conn.execute("select * from blocks order by slot"):
                payload = ExecutionPayload(**json.loads(row["execution_payload"]))
                block = BeaconBlock(
                    slot=int(row["slot"]),
                    epoch=int(row["epoch"]),
                    parent_root=row["parent_root"],
                    proposer=row["proposer"],
                    execution_payload=payload,
                    timestamp=int(row["timestamp"]),
                    root=row["root"],
                )
                blocks[block.root] = block

            for row in conn.execute("select * from attestations order by id"):
                att = BeaconAttestation(
                    validator=row["validator"],
                    slot=int(row["slot"]),
                    source_epoch=int(row["source_epoch"]),
                    target_epoch=int(row["target_epoch"]),
                    head_root=row["head_root"],
                    signature=row["signature"],
                )
                if att.head_root in blocks:
                    blocks[att.head_root].attestations.append(att)
            state.blocks = blocks
            return state


def init_beacon_runtime(root: str | Path = ".", config: Optional[BeaconConfig] = None) -> Dict[str, Any]:
    base = Path(root)
    cfg = config or BeaconConfig()
    (base / "config").mkdir(parents=True, exist_ok=True)
    (base / "storage").mkdir(parents=True, exist_ok=True)
    (base / "docs").mkdir(parents=True, exist_ok=True)
    (base / "config/beacon.json").write_text(json.dumps(cfg.as_dict(), indent=2), encoding="utf-8")
    state = create_beacon_state(cfg)
    store = BeaconStore(base / "storage/beacon.sqlite")
    store.save_state(state)
    return {"ok": True, "config": str(base / "config/beacon.json"), "store": str(store.path), "state": state.as_dict()}


def simulate_beacon(validators: int = 64, epochs: int = 2, slot_seconds: int = DEFAULT_SLOT_SECONDS, slots_per_epoch: int = DEFAULT_SLOTS_PER_EPOCH) -> Dict[str, Any]:
    validator_count = max(1, int(validators))
    cfg = BeaconConfig(slot_seconds=int(slot_seconds), slots_per_epoch=max(1, int(slots_per_epoch)))
    vals = [BeaconValidator(f"0x{i + 1:040x}", 1_000, "active", i) for i in range(validator_count)]
    state = create_beacon_state(cfg, vals)
    total_slots = max(0, int(epochs)) * int(cfg.slots_per_epoch)
    events: List[Dict[str, Any]] = []

    for _ in range(total_slots):
        block = produce_beacon_block(state)
        attestations = attest_to_head(state)
        finality = process_epoch_finality(state, attestations) if block.slot % cfg.slots_per_epoch == 0 else None
        events.append({
            "slot": block.slot,
            "epoch": block.epoch,
            "block_root": block.root,
            "proposer": block.proposer,
            "attestations": len(attestations),
            "finality": finality,
        })
        fork_choice_head(state)

    return {
        "ok": True,
        "validators": validator_count,
        "epochs": int(epochs),
        "slots": total_slots,
        "head": state.head_root,
        "justified_checkpoint": state.justified_checkpoint.as_dict(),
        "finalized_checkpoint": state.finalized_checkpoint.as_dict(),
        "events": events,
    }


__all__ = [
    "BeaconAttestation",
    "BeaconBlock",
    "BeaconConfig",
    "BeaconState",
    "BeaconStore",
    "BeaconValidator",
    "Checkpoint",
    "ExecutionPayload",
    "attest_to_head",
    "beacon_capabilities",
    "committee_for_slot",
    "create_beacon_state",
    "default_validators",
    "detect_slashable_events",
    "fork_choice_head",
    "init_beacon_runtime",
    "make_execution_payload",
    "process_epoch_finality",
    "produce_beacon_block",
    "sbq_beacon_config",
    "select_proposer",
    "simulate_beacon",
]
