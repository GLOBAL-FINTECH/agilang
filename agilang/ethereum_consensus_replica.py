"""Ethereum proof-of-stake replica consensus profile for AGILANG private forks.

This module models an Ethereum-derived private/custom network profile. It is not
an Ethereum mainnet validator implementation. Live Ethereum mainnet validation
must continue to use official Ethereum execution, consensus, and validator
clients. AGILANG uses this module for private-fork planning, simulation, scaffold
configuration, Beacon/Engine API boundary checks, and developer education.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_SLOT_SECONDS = 12
DEFAULT_SLOTS_PER_EPOCH = 32
DEFAULT_CHAIN_ID = 901900
PRIVATE_HOSTS = {"127.0.0.1", "localhost", "::1"}
PUBLIC_HOSTS = {"0.0.0.0", "::", "", "*"}


@dataclass
class ReplicaEndpoint:
    name: str
    host: str
    port: int
    public: bool = False
    purpose: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "host": self.host,
            "port": int(self.port),
            "public": bool(self.public),
            "url": f"http://{self.host}:{int(self.port)}",
            "purpose": self.purpose,
        }


@dataclass
class EthereumConsensusReplicaConfig:
    chain_id: int = DEFAULT_CHAIN_ID
    network: str = "private-fork"
    consensus: str = "ethereum-pos-replica"
    slot_seconds: int = DEFAULT_SLOT_SECONDS
    slots_per_epoch: int = DEFAULT_SLOTS_PER_EPOCH
    genesis_time: int = field(default_factory=lambda: int(time.time()))
    validators: List[str] = field(default_factory=lambda: [
        "0x04aac0173878aee604c1eaec3455ca8b5719f39b",
        "0x95e3673f703cb53b3c1848cd3def70a64c59fb08",
        "0x42753c26f7ef0deedcd27967b34ed48b294e1443",
    ])
    execution_rpc: ReplicaEndpoint = field(default_factory=lambda: ReplicaEndpoint("execution_rpc", "127.0.0.1", 8545, True, "Wallet and dApp JSON-RPC"))
    engine_api: ReplicaEndpoint = field(default_factory=lambda: ReplicaEndpoint("engine_api", "127.0.0.1", 8551, False, "Private Engine API boundary"))
    beacon_api: ReplicaEndpoint = field(default_factory=lambda: ReplicaEndpoint("beacon_api", "127.0.0.1", 5052, False, "Private Beacon API"))
    validator_api: ReplicaEndpoint = field(default_factory=lambda: ReplicaEndpoint("validator_api", "127.0.0.1", 8651, False, "Private validator/admin API"))
    p2p: ReplicaEndpoint = field(default_factory=lambda: ReplicaEndpoint("p2p", "0.0.0.0", 30333, True, "Node gossip/sync profile"))
    metrics: ReplicaEndpoint = field(default_factory=lambda: ReplicaEndpoint("metrics", "127.0.0.1", 9100, False, "Metrics and health"))

    def endpoints(self) -> List[ReplicaEndpoint]:
        return [self.execution_rpc, self.engine_api, self.beacon_api, self.validator_api, self.p2p, self.metrics]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": int(self.chain_id),
            "network": self.network,
            "consensus": self.consensus,
            "slot_seconds": int(self.slot_seconds),
            "slots_per_epoch": int(self.slots_per_epoch),
            "genesis_time": int(self.genesis_time),
            "validators": list(self.validators),
            "endpoints": {endpoint.name: endpoint.as_dict() for endpoint in self.endpoints()},
            "ethereum_replica_boundary": {
                "private_or_custom_fork_only": True,
                "live_ethereum_mainnet_validation": False,
                "mainnet_validation_requires_official_clients": True,
            },
            "modeled_primitives": [
                "execution_consensus_split",
                "private_engine_api_boundary",
                "private_beacon_api",
                "twelve_second_slots",
                "thirty_two_slot_epochs",
                "validator_registry",
                "proposer_duties",
                "attestation_committees",
                "source_target_head_votes",
                "lmd_ghost_style_head_choice",
                "casper_ffg_style_finality",
                "reward_penalty_hooks",
                "double_vote_slashing_hooks",
                "private_validator_api_isolation",
            ],
        }


def ethereum_consensus_capabilities() -> Dict[str, Any]:
    """Return the Ethereum PoS replica feature matrix."""

    return {
        "default_ethereum_derived_consensus": "ethereum-pos-replica",
        "legacy_agilang_consensus_preserved": True,
        "slot_seconds": DEFAULT_SLOT_SECONDS,
        "slots_per_epoch": DEFAULT_SLOTS_PER_EPOCH,
        "features": [
            "execution_consensus_split",
            "beacon_chain_style_slots_epochs",
            "proposer_duty_simulation",
            "attestation_committee_simulation",
            "source_target_head_votes",
            "lmd_ghost_style_head_choice",
            "casper_ffg_style_finality",
            "double_vote_slashing_hook_simulation",
            "private_beacon_api_service",
            "private_engine_api_boundary",
            "private_validator_api",
        ],
        "production_boundary": "For private/custom Ethereum-derived networks only. Live Ethereum mainnet requires official Ethereum clients.",
    }


def ethereum_consensus_replica_config(**overrides: Any) -> EthereumConsensusReplicaConfig:
    cfg = EthereumConsensusReplicaConfig()
    for key, value in overrides.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
    return cfg


def write_ethereum_consensus_config(path: str | Path = "config/ethereum-consensus-replica.json", **overrides: Any) -> Dict[str, Any]:
    cfg = ethereum_consensus_replica_config(**overrides)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg.as_dict(), indent=2), encoding="utf-8")
    return {"ok": True, "path": str(p), "config": cfg.as_dict()}


def load_ethereum_consensus_config(path: str | Path = "config/ethereum-consensus-replica.json") -> EthereumConsensusReplicaConfig:
    p = Path(path)
    if not p.exists():
        return ethereum_consensus_replica_config()
    data = json.loads(p.read_text(encoding="utf-8"))
    cfg = ethereum_consensus_replica_config(
        chain_id=int(data.get("chain_id", DEFAULT_CHAIN_ID)),
        network=str(data.get("network", "private-fork")),
        consensus=str(data.get("consensus", "ethereum-pos-replica")),
        slot_seconds=int(data.get("slot_seconds", DEFAULT_SLOT_SECONDS)),
        slots_per_epoch=int(data.get("slots_per_epoch", DEFAULT_SLOTS_PER_EPOCH)),
        genesis_time=int(data.get("genesis_time", int(time.time()))),
        validators=list(data.get("validators", [])) or None,
    )
    if cfg.validators is None:
        cfg.validators = EthereumConsensusReplicaConfig().validators
    return cfg


def _endpoint_problem(endpoint: ReplicaEndpoint) -> Optional[str]:
    if not endpoint.public and endpoint.host in PUBLIC_HOSTS:
        return f"{endpoint.name} must remain private; bind it to 127.0.0.1 or localhost"
    if endpoint.port <= 0 or endpoint.port > 65535:
        return f"{endpoint.name} has invalid port {endpoint.port}"
    return None


def ethereum_consensus_check(config: Optional[EthereumConsensusReplicaConfig] = None) -> Dict[str, Any]:
    cfg = config or ethereum_consensus_replica_config()
    errors: List[str] = []
    warnings: List[str] = []

    if cfg.consensus != "ethereum-pos-replica":
        errors.append("Ethereum-derived fork mode must default to ethereum-pos-replica")
    if int(cfg.slot_seconds) != DEFAULT_SLOT_SECONDS:
        warnings.append("Ethereum replica default slot_seconds should normally remain 12")
    if int(cfg.slots_per_epoch) != DEFAULT_SLOTS_PER_EPOCH:
        warnings.append("Ethereum replica default slots_per_epoch should normally remain 32")
    if int(cfg.chain_id) in {1, 11155111, 17000}:
        errors.append("Replica mode must use a custom/private chain ID, not an Ethereum public-network chain ID")
    if len(cfg.validators) < 1:
        errors.append("At least one validator is required for replica simulation")

    seen_ports: Dict[int, str] = {}
    for endpoint in cfg.endpoints():
        problem = _endpoint_problem(endpoint)
        if problem:
            errors.append(problem)
        if endpoint.port in seen_ports:
            errors.append(f"port collision: {endpoint.name} and {seen_ports[endpoint.port]} both use {endpoint.port}")
        seen_ports[endpoint.port] = endpoint.name

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "ethereum_pos_replica_private_fork_ready": not errors,
        "slot_seconds": cfg.slot_seconds,
        "slots_per_epoch": cfg.slots_per_epoch,
        "chain_id": cfg.chain_id,
        "consensus": cfg.consensus,
        "network_runtime_isolation": cfg.engine_api.host in PRIVATE_HOSTS and cfg.beacon_api.host in PRIVATE_HOSTS and cfg.validator_api.host in PRIVATE_HOSTS,
        "public_ethereum_mainnet_boundary": True,
    }


def _proposer_for_slot(validators: List[str], slot: int) -> str:
    return validators[slot % len(validators)]


def _committee_for_slot(validators: List[str], slot: int) -> List[str]:
    if len(validators) <= 2:
        return validators[:]
    start = slot % len(validators)
    return [validators[(start + offset) % len(validators)] for offset in range(min(3, len(validators)))]


def ethereum_consensus_simulation(slots: int = 8, config: Optional[EthereumConsensusReplicaConfig] = None) -> Dict[str, Any]:
    cfg = config or ethereum_consensus_replica_config()
    events: List[Dict[str, Any]] = []
    justified_epoch = -1
    finalized_epoch = -1
    head = "genesis"

    for slot in range(max(0, int(slots))):
        epoch = slot // int(cfg.slots_per_epoch)
        proposer = _proposer_for_slot(cfg.validators, slot)
        committee = _committee_for_slot(cfg.validators, slot)
        block_root = f"0xreplica{slot:064x}"[-66:]
        head = block_root
        participation = len(committee) / max(1, len(cfg.validators))
        if participation >= 2 / 3:
            justified_epoch = max(justified_epoch, epoch)
            if epoch > 0:
                finalized_epoch = max(finalized_epoch, epoch - 1)
        events.append({
            "slot": slot,
            "epoch": epoch,
            "proposer": proposer,
            "committee": committee,
            "source_epoch": max(0, justified_epoch),
            "target_epoch": epoch,
            "head_vote": head,
            "block_root": block_root,
            "participation": participation,
        })

    return {
        "ok": True,
        "consensus": cfg.consensus,
        "slot_seconds": cfg.slot_seconds,
        "slots_per_epoch": cfg.slots_per_epoch,
        "slots_simulated": max(0, int(slots)),
        "head": head,
        "justified_epoch": justified_epoch,
        "finalized_epoch": finalized_epoch,
        "events": events,
        "notes": [
            "Replica simulation models proposer/attestation flow for private forks.",
            "It is not a substitute for official Ethereum mainnet clients.",
        ],
    }


__all__ = [
    "EthereumConsensusReplicaConfig",
    "ReplicaEndpoint",
    "ethereum_consensus_capabilities",
    "ethereum_consensus_replica_config",
    "write_ethereum_consensus_config",
    "load_ethereum_consensus_config",
    "ethereum_consensus_check",
    "ethereum_consensus_simulation",
]
