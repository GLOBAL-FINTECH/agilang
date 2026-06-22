"""Runtime CLI shim for AGILANG blockchain/Ethereum consensus commands.

This wrapper keeps the existing AGILANG CLI intact while adding first-class
Ethereum PoS replica commands. Unknown commands are delegated to agilang.cli.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .ethereum_consensus_replica import (
    ethereum_consensus_capabilities,
    ethereum_consensus_check,
    ethereum_consensus_replica_config,
    ethereum_consensus_simulation,
    write_ethereum_consensus_config,
)


def _print_json(value):
    print(json.dumps(value, indent=2, sort_keys=True))


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
    if mode != "ethereum-consensus-replica":
        _print_json({"ok": False, "error": "unsupported_mode", "mode": mode})
        raise SystemExit(1)
    cfg = ethereum_consensus_replica_config()
    _print_json({
        "ok": True,
        "mode": mode,
        "services": [
            "execution_json_rpc",
            "private_engine_api",
            "private_beacon_api",
            "private_validator_api",
            "p2p_sync_profile",
            "metrics",
        ],
        "config": cfg.as_dict(),
    })


def _start(args):
    mode = args.mode
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
        "message": "Ethereum PoS replica runtime plan is valid. Long-running service supervision should be enabled by the chain host runtime.",
        "check": check,
        "services": cfg.as_dict()["endpoints"],
    })
    if not check["ok"]:
        raise SystemExit(1)


def _beacon(args):
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
        _start(parser.parse_args(argv[2:]))
        return True

    if command == "ethereum-consensus-beacon":
        parser = argparse.ArgumentParser(prog="agi chain ethereum-consensus-beacon")
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=5052)
        _beacon(parser.parse_args(argv[2:]))
        return True

    return False


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if _handle_chain(args):
        return
    from .cli import main as legacy_main
    legacy_main()


if __name__ == "__main__":
    main()
