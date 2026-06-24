"""Runtime CLI shim for AGILANG blockchain/Ethereum consensus commands.

This wrapper keeps the existing AGILANG CLI intact while adding first-class
blockchain, native SBQ Beacon, and Ethereum PoS replica commands. Unknown
commands are delegated to agilang.cli.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .beacon import (
    BeaconConfig,
    BeaconStore,
    attest_to_head,
    beacon_capabilities,
    fork_choice_head,
    init_beacon_runtime,
    process_epoch_finality,
    produce_beacon_block,
    simulate_beacon,
)
from .ethereum_consensus_replica import (
    ethereum_consensus_capabilities,
    ethereum_consensus_check,
    ethereum_consensus_replica_config,
    ethereum_consensus_simulation,
    write_ethereum_consensus_config,
)


def _print_json(value):
    print(json.dumps(value, indent=2, sort_keys=True))


def _safe_project_name(parts: list[str]) -> str:
    raw = "-".join(part.strip() for part in parts if part.strip()) or "my-chain"
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in raw)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "my-chain"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def _handle_new(argv: list[str]) -> bool:
    if not argv or argv[0] != "new":
        return False
    if "--template" not in argv:
        return False
    template_idx = argv.index("--template")
    template = argv[template_idx + 1] if template_idx + 1 < len(argv) else ""
    if template != "blockchain":
        return False

    name_parts = argv[1:template_idx]
    name = _safe_project_name(name_parts)
    root = Path(name).resolve()
    root.mkdir(parents=True, exist_ok=True)

    eth_cfg = ethereum_consensus_replica_config()
    beacon_cfg = BeaconConfig()
    genesis = {
        "chain_id": 1900,
        "name": "SBQ-Blockchain",
        "symbol": "SBQ",
        "decimals": 18,
        "mainnet_profile": True,
        "require_block_signatures": True,
        "native_beacon_consensus": "sbq-beacon",
        "ethereum_derived_consensus_default": "ethereum-pos-replica",
    }
    network = {
        "mode": "sbq-beacon",
        "rpc": {"host": "127.0.0.1", "port": 8545},
        "beacon_api": {"host": "127.0.0.1", "port": 5052, "public": False},
        "validator_api": {"host": "127.0.0.1", "port": 8651, "public": False},
        "p2p": {"host": "0.0.0.0", "port": 30333},
    }

    _write(root / "agilang.toml", "[project]\nname = \"" + name + "\"\nentry = \"src/main.agi\"\n")
    _write(root / "src/main.agi", "fn main() -> i32:\n    print(\"SBQ Blockchain starter\")\n    print(\"run: agi beacon status\")\n    print(\"run: agi chain ethereum-consensus-check\")\n    return 0\n")
    _write(root / "src/chain.agi", "fn main() -> i32:\n    print(\"SBQ chain status entrypoint\")\n    return 0\n")
    _write(root / "src/beacon.agi", "fn main() -> i32:\n    print(\"SBQ native Beacon consensus layer\")\n    print(\"commands: agi beacon status, agi beacon produce-block, agi beacon attest, agi beacon finalize\")\n    return 0\n")
    _write(root / "src/staking.agi", "fn main() -> i32:\n    print(\"staking profile placeholder\")\n    return 0\n")
    _write(root / "src/network.agi", "fn main() -> i32:\n    print(\"network profile placeholder\")\n    return 0\n")
    _write(root / "src/ethereum_clients.agi", "fn main() -> i32:\n    print(\"Ethereum external client orchestration profile\")\n    return 0\n")
    _write(root / "src/ethereum_consensus.agi", "fn main() -> i32:\n    print(\"Ethereum PoS replica consensus profile\")\n    return 0\n")
    _write(root / "config/genesis.json", json.dumps(genesis, indent=2))
    _write(root / "config/network.json", json.dumps(network, indent=2))
    _write(root / "config/rpc.json", json.dumps({"host": "127.0.0.1", "port": 8545, "chain_id": 1900}, indent=2))
    _write(root / "config/beacon.json", json.dumps(beacon_cfg.as_dict(), indent=2))
    _write(root / "config/ethereum-consensus-replica.json", json.dumps(eth_cfg.as_dict(), indent=2))
    _write(root / "config/ethereum-clients.json", json.dumps({"mode": "full", "execution_client": "geth", "consensus_client": "lighthouse", "validator_client": "lighthouse"}, indent=2))
    _write(root / "config/wallets/wallets.example.json", json.dumps({"warning": "Do not commit real private keys. Replace this file locally."}, indent=2))
    _write(root / "storage/logs/.gitkeep", "")
    init_beacon_runtime(root, beacon_cfg)
    _write(root / "docs/SBQ_BEACON_CHAIN_V21.md", "# SBQ Beacon Chain\n\nThis starter includes the native AGILANG/SBQ Beacon consensus layer with slots, epochs, validators, attestations, fork choice, checkpoint finality, slashing detection hooks, and SQLite persistence.\n")
    _write(root / "docs/ETHEREUM_CONSENSUS_REPLICA_V20_2.md", "# Ethereum Consensus Replica\n\nThis blockchain starter keeps Ethereum-derived private fork mode on `ethereum-pos-replica`.\n")
    _write(root / "docs/BLOCKCHAIN_RUNBOOK.md", "# Blockchain Runbook\n\nRun `agi run`, then `agi beacon status`, `agi beacon produce-block`, `agi beacon attest`, `agi beacon finalize`, and configure RPC, wallets, validators, and networking.\n")
    print(f"Created AGILANG blockchain project: {root}")
    return True


def _consensus_replacement_plan(args):
    consensus = args.consensus or "ethereum-pos-replica"
    plan = {
        "ok": consensus == "ethereum-pos-replica",
        "network": args.network,
        "chain_id": int(args.chain_id),
        "default_consensus": "ethereum-pos-replica",
        "requested_consensus": consensus,
        "agilang_legacy_consensus_preserved": True,
        "ethereum_derived_fork_default": consensus == "ethereum-pos-replica",
        "architecture": {
            "execution_consensus_split": True,
            "slot_seconds": 12,
            "slots_per_epoch": 32,
            "proposer_duties": True,
            "attestation_committees": True,
            "lmd_ghost_style_head_choice": True,
            "casper_ffg_style_finality": True,
            "private_engine_api_boundary": True,
            "private_beacon_api": True,
        },
        "production_boundary": "Private/custom Ethereum-derived forks only. Live Ethereum mainnet validation requires official Ethereum clients.",
    }
    _print_json(plan)
    if not plan["ok"]:
        raise SystemExit(1)


def _plan(args):
    mode = args.mode
    if mode in {"sbq-beacon", "beacon"}:
        _print_json({
            "ok": True,
            "mode": "sbq-beacon",
            "services": ["beacon_state", "validator_registry", "block_producer", "attestation_processor", "fork_choice", "finality", "slashing_hooks", "execution_payload_bridge", "sqlite_store"],
            "capabilities": beacon_capabilities(),
        })
        return
    if mode != "ethereum-consensus-replica":
        _print_json({"ok": False, "error": "unsupported_mode", "mode": mode})
        raise SystemExit(1)
    cfg = ethereum_consensus_replica_config()
    _print_json({
        "ok": True,
        "mode": mode,
        "services": ["execution_json_rpc", "private_engine_api", "private_beacon_api", "private_validator_api", "p2p_sync_profile", "metrics"],
        "config": cfg.as_dict(),
    })


def _start(args):
    mode = args.mode
    if mode in {"sbq-beacon", "beacon"}:
        store = BeaconStore("storage/beacon.sqlite")
        state = store.load_state()
        continuous = bool(getattr(args, "continuous", False))
        if args.dry_run or not continuous:
            _print_json({
                "ok": True,
                "mode": "sbq-beacon",
                "dry_run": bool(args.dry_run),
                "continuous": continuous,
                "message": "Native SBQ Beacon runtime plan is valid. Add --continuous to keep producing/attesting/finalizing slots until stopped, or use --max-slots for a bounded test run.",
                "state": state.as_dict(),
            })
            return

        slot_seconds = max(1, int(getattr(args, "slot_seconds", 0) or state.config.slot_seconds))
        max_slots = int(getattr(args, "max_slots", 0) or 0)
        produced = 0
        print(json.dumps({
            "ok": True,
            "mode": "sbq-beacon",
            "continuous": True,
            "slot_seconds": slot_seconds,
            "max_slots": max_slots,
            "message": "AGILANG/SBQ continuous beacon loop started. Press Ctrl+C to stop.",
            "start_slot": state.current_slot,
        }, sort_keys=True))
        try:
            while True:
                block = produce_beacon_block(state)
                attestations = attest_to_head(state)
                finality = process_epoch_finality(state, attestations) if block.slot % state.config.slots_per_epoch == 0 else None
                head = fork_choice_head(state)
                store.save_state(state)
                produced += 1
                print(json.dumps({
                    "event": "slot",
                    "slot": block.slot,
                    "epoch": block.epoch,
                    "block_root": block.root,
                    "proposer": block.proposer,
                    "attestations": len(attestations),
                    "head": head.get("head", state.head_root) if isinstance(head, dict) else state.head_root,
                    "finality": finality,
                }, sort_keys=True))
                if max_slots and produced >= max_slots:
                    break
                time.sleep(slot_seconds)
        except KeyboardInterrupt:
            print(json.dumps({"event": "stopped", "reason": "keyboard_interrupt", "last_slot": state.current_slot}, sort_keys=True))
        return
    if mode != "ethereum-consensus-replica":
        _print_json({"ok": False, "error": "unsupported_mode", "mode": mode})
        raise SystemExit(1)
    cfg = ethereum_consensus_replica_config()
    check = ethereum_consensus_check(cfg)
    _print_json({
        "ok": check["ok"],
        "mode": mode,
        "config_path": args.config,
        "dry_run": bool(args.dry_run),
        "continuous": bool(getattr(args, "continuous", False)),
        "message": "Ethereum PoS replica runtime plan is valid. Long-running serving must still be supervised and must not be used as an Ethereum mainnet validator replacement.",
        "check": check,
        "services": cfg.as_dict()["endpoints"],
    })
    if not check["ok"]:
        raise SystemExit(1)


def _beacon_api_boundary(args):
    cfg = ethereum_consensus_replica_config()
    cfg.beacon_api.host = args.host
    cfg.beacon_api.port = int(args.port)
    _print_json({
        "ok": True,
        "service": "private_beacon_api",
        "host": cfg.beacon_api.host,
        "port": cfg.beacon_api.port,
        "url": f"http://{cfg.beacon_api.host}:{cfg.beacon_api.port}",
        "note": "This command defines the private Beacon API runtime boundary. Production serving should run under the AGILANG chain supervisor.",
    })


def _handle_chain(argv: list[str]) -> bool:
    if not argv or argv[0] != "chain":
        return False
    command = argv[1] if len(argv) > 1 else ""

    if command == "ethereum-consensus-capabilities":
        _print_json(ethereum_consensus_capabilities())
        return True

    if command == "ethereum-consensus-write-config":
        parser = argparse.ArgumentParser(prog="agi chain ethereum-consensus-write-config")
        parser.add_argument("--chain-id", type=int, default=901900)
        parser.add_argument("--path", default="config/ethereum-consensus-replica.json")
        args = parser.parse_args(argv[2:])
        _print_json(write_ethereum_consensus_config(args.path, chain_id=args.chain_id))
        return True

    if command == "ethereum-consensus-check":
        _print_json(ethereum_consensus_check())
        return True

    if command == "ethereum-consensus-sim":
        parser = argparse.ArgumentParser(prog="agi chain ethereum-consensus-sim")
        parser.add_argument("--slots", type=int, default=8)
        args = parser.parse_args(argv[2:])
        _print_json(ethereum_consensus_simulation(slots=args.slots))
        return True

    if command == "consensus-replacement-plan":
        parser = argparse.ArgumentParser(prog="agi chain consensus-replacement-plan")
        parser.add_argument("--network", default="private-fork")
        parser.add_argument("--consensus", default="ethereum-pos-replica")
        parser.add_argument("--chain-id", type=int, default=901900)
        _consensus_replacement_plan(parser.parse_args(argv[2:]))
        return True

    if command == "plan":
        parser = argparse.ArgumentParser(prog="agi chain plan")
        parser.add_argument("--mode", required=True)
        _plan(parser.parse_args(argv[2:]))
        return True

    if command == "start":
        parser = argparse.ArgumentParser(prog="agi chain start")
        parser.add_argument("--mode", required=True)
        parser.add_argument("--config", default="config/network.json")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--continuous", action="store_true", help="Keep the local chain loop running until Ctrl+C or --max-slots is reached")
        parser.add_argument("--slot-seconds", type=int, default=0, help="Override local beacon slot interval for continuous mode")
        parser.add_argument("--max-slots", type=int, default=0, help="Stop after this many produced slots; 0 means run until interrupted")
        _start(parser.parse_args(argv[2:]))
        return True

    if command == "ethereum-consensus-beacon":
        parser = argparse.ArgumentParser(prog="agi chain ethereum-consensus-beacon")
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=5052)
        _beacon_api_boundary(parser.parse_args(argv[2:]))
        return True

    return False


def _load_beacon_store(path: str = "storage/beacon.sqlite") -> BeaconStore:
    store = BeaconStore(path)
    store.init()
    return store


def _handle_beacon(argv: list[str]) -> bool:
    if not argv or argv[0] != "beacon":
        return False

    command = argv[1] if len(argv) > 1 else "status"

    if command == "capabilities":
        _print_json(beacon_capabilities())
        return True

    if command == "init":
        parser = argparse.ArgumentParser(prog="agi beacon init")
        parser.add_argument("--path", default=".")
        parser.add_argument("--slot-seconds", type=int, default=6)
        parser.add_argument("--slots-per-epoch", type=int, default=16)
        parser.add_argument("--chain-id", type=int, default=1900)
        args = parser.parse_args(argv[2:])
        cfg = BeaconConfig(chain_id=args.chain_id, slot_seconds=args.slot_seconds, slots_per_epoch=args.slots_per_epoch)
        _print_json(init_beacon_runtime(args.path, cfg))
        return True

    if command == "status":
        store = _load_beacon_store()
        state = store.load_state()
        _print_json({
            "ok": True,
            "head": state.head_root,
            "slot": state.current_slot,
            "epoch": state.config.epoch_for_slot(state.current_slot),
            "validators": len(state.validators),
            "justified_checkpoint": state.justified_checkpoint.as_dict(),
            "finalized_checkpoint": state.finalized_checkpoint.as_dict(),
        })
        return True

    if command == "produce-block":
        store = _load_beacon_store()
        state = store.load_state()
        block = produce_beacon_block(state)
        store.save_state(state)
        _print_json({"ok": True, "block": block.as_dict(), "state": state.as_dict()})
        return True

    if command == "attest":
        store = _load_beacon_store()
        state = store.load_state()
        attestations = attest_to_head(state)
        store.save_state(state)
        _print_json({"ok": True, "attestations": [a.as_dict() for a in attestations]})
        return True

    if command == "finalize":
        store = _load_beacon_store()
        state = store.load_state()
        attestations = attest_to_head(state)
        result = process_epoch_finality(state, attestations)
        store.save_state(state)
        _print_json({"ok": True, "finality": result, "state": state.as_dict()})
        return True

    if command == "fork-choice":
        store = _load_beacon_store()
        state = store.load_state()
        result = fork_choice_head(state)
        store.save_state(state)
        _print_json(result)
        return True

    if command == "simulate":
        parser = argparse.ArgumentParser(prog="agi beacon simulate")
        parser.add_argument("--validators", type=int, default=64)
        parser.add_argument("--epochs", type=int, default=2)
        parser.add_argument("--slot-seconds", type=int, default=6)
        parser.add_argument("--slots-per-epoch", type=int, default=16)
        args = parser.parse_args(argv[2:])
        _print_json(simulate_beacon(args.validators, args.epochs, args.slot_seconds, args.slots_per_epoch))
        return True

    return False


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if _handle_new(args):
        return 0
    if _handle_chain(args):
        return 0
    if _handle_beacon(args):
        return 0

    from .cli import main as base_main
    return base_main(args)


if __name__ == "__main__":
    main()
