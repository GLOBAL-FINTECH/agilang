"""In-house production chain supervisor for AGILANG Smart Chain.

This module unifies the execution node, JSON-RPC endpoint, built-in validator
producer, and SBQ beacon loop behind JSON configuration. It is designed for
private-chain/staging/production-style operation, not the legacy dev profile.
"""
from __future__ import annotations

import argparse
import json
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from .beacon import (
    BeaconConfig,
    BeaconStore,
    ExecutionPayload,
    attest_to_head,
    fork_choice_head,
    process_epoch_finality,
    produce_beacon_block,
)
from .blockchain_runtime_gateway import load_project_chain
from .rpc import EthJsonRpcService


DEFAULT_CONFIG_PATH = "config/chain-services.json"


def _load_json(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON config must be an object: {path}")
    return data


def _enabled(config: Dict[str, Any], service: str, default: bool = False) -> bool:
    value = (config.get("services") or {}).get(service, {})
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, dict):
        return bool(value.get("enabled", default))
    return default


def _service(config: Dict[str, Any], service: str) -> Dict[str, Any]:
    value = (config.get("services") or {}).get(service, {})
    return value if isinstance(value, dict) else {"enabled": bool(value)}


def _beacon_config_from_file(path: Path) -> BeaconConfig:
    data = _load_json(path, {})
    return BeaconConfig(
        chain_id=int(data.get("chain_id", 1923)),
        network=str(data.get("network", "sbq-beacon")),
        consensus=str(data.get("consensus", "sbq-beacon")),
        slot_seconds=int(data.get("slot_seconds", 1)),
        slots_per_epoch=int(data.get("slots_per_epoch", 16)),
        finality_threshold=float(data.get("finality_threshold", 2 / 3)),
        min_validator_stake=int(data.get("min_validator_stake", 1000)),
        genesis_time=int(data.get("genesis_time", time.time())),
    )


def validate_chain_services(root: str | Path = ".", config_path: str | Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    project = Path(root).resolve()
    full_config = project / config_path
    config = _load_json(full_config)
    errors: list[str] = []
    warnings: list[str] = []

    profile = str(config.get("profile", "production")).lower()
    mode = str(config.get("mode", "inhouse")).lower()
    if profile != "production":
        errors.append("profile_must_be_production")
    if mode not in {"inhouse", "inhouse-production", "production"}:
        errors.append("mode_must_be_inhouse_production")

    if not _enabled(config, "node", True):
        errors.append("node_service_must_be_enabled")
    if not _enabled(config, "validator", True):
        warnings.append("validator_service_disabled")
    if not _enabled(config, "beacon", True):
        warnings.append("beacon_service_disabled")
    if _enabled(config, "dev", False):
        errors.append("dev_service_must_be_disabled_for_production_profile")

    rpc_cfg = _load_json(project / "config" / "rpc.json", {})
    if bool(rpc_cfg.get("dev_send", False)):
        warnings.append("rpc_dev_send_enabled_use_only_private_loopback")
    if str(rpc_cfg.get("cors_origin", "*")) == "*":
        warnings.append("rpc_cors_origin_is_wildcard")

    chain_cfg = rpc_cfg.get("chain", {}) if isinstance(rpc_cfg.get("chain", {}), dict) else {}
    if not bool(chain_cfg.get("mainnet_profile", False)):
        errors.append("chain_mainnet_profile_must_be_true")
    if not bool(chain_cfg.get("require_block_signatures", False)):
        errors.append("require_block_signatures_must_be_true")
    if str(chain_cfg.get("consensus", chain_cfg.get("consensus_mode", "pos"))).lower() == "dev":
        errors.append("consensus_must_not_be_dev")
    if int(chain_cfg.get("max_account_queue_gap", 0) or 0) <= 0:
        errors.append("max_account_queue_gap_missing_or_invalid")

    keys = dict(chain_cfg.get("validator_signing_keys", {}) or {})
    key_file = chain_cfg.get("validator_signing_key_file") or chain_cfg.get("validator_key_file")
    if key_file:
        key_data = _load_json(project / str(key_file), {})
        keys.update(dict(key_data.get("validator_signing_keys", key_data.get("keys", {})) or {}))
    validators = dict(chain_cfg.get("validators", {}) or {})
    missing_keys = [addr for addr in validators if not str(keys.get(addr, "")).strip()]
    weak_keys = [addr for addr, key in keys.items() if len(str(key)) < 32 or "REPLACE_WITH" in str(key)]
    if missing_keys:
        errors.append("validator_signing_keys_missing")
    if weak_keys:
        errors.append("validator_signing_keys_weak_or_placeholder")

    beacon_cfg_path = project / str(_service(config, "beacon").get("config", "config/beacon.json"))
    if _enabled(config, "beacon", True) and not beacon_cfg_path.exists():
        errors.append("beacon_config_missing")

    return {
        "ok": not errors,
        "profile": profile,
        "mode": mode,
        "config": str(full_config),
        "errors": errors,
        "warnings": warnings,
        "services": {name: _enabled(config, name, False) for name in ("node", "rpc", "validator", "beacon", "dev")},
    }


class InHouseChainSupervisor:
    """Single-process supervisor for in-house production Smart Chain services."""

    def __init__(self, root: str | Path = ".", config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        self.root = Path(root).resolve()
        self.config_path = Path(config_path)
        self.config = _load_json(self.root / self.config_path)
        validation = validate_chain_services(self.root, self.config_path)
        if not validation["ok"]:
            raise ValueError(json.dumps(validation, sort_keys=True))
        self.validation = validation
        self.node, self.rpc_config = load_project_chain(self.root)
        self.stop_event = threading.Event()
        self.threads: list[threading.Thread] = []
        self.rpc_server: Optional[ThreadingHTTPServer] = None
        self.beacon_store: Optional[BeaconStore] = None
        self.beacon_state = None
        self._lock = threading.RLock()

    def status(self) -> Dict[str, Any]:
        beacon_status = None
        if self.beacon_state is not None:
            beacon_status = self.beacon_state.as_dict()
        return {
            "ok": True,
            "mode": self.config.get("mode", "inhouse"),
            "profile": self.config.get("profile", "production"),
            "services": self.validation["services"],
            "chain": self.node.status(),
            "head": self.node.head(),
            "beacon": beacon_status,
        }

    def _produce_execution_slot(self) -> Dict[str, Any]:
        with self._lock:
            parent = self.node.head()
            slot = max(int(parent.get("slot", 0)) + 1, self.node._current_slot())
            proposer = self.node.consensus.select_proposer(parent["hash"], slot)
            return self.node.produce_and_import_block(proposer, slot)

    def validator_once(self, allow_empty: bool = True) -> Dict[str, Any]:
        ready = len(getattr(self.node.mempool, "ready_pool", {}))
        if not allow_empty and ready == 0:
            return {"ok": True, "skipped": True, "reason": "no_ready_transactions"}
        produced = self._produce_execution_slot()
        imported = produced.get("import", {})
        return {
            "ok": bool(imported.get("ok", False)),
            "slot": produced.get("block", {}).get("slot"),
            "height": produced.get("block", {}).get("height"),
            "txs": len(produced.get("block", {}).get("transactions") or []),
            "import": imported,
        }

    def beacon_once(self) -> Dict[str, Any]:
        if self.beacon_state is None:
            self._init_beacon()
        assert self.beacon_state is not None
        head = self.node.head()
        payload = ExecutionPayload(
            block_hash=str(head.get("hash")),
            block_number=int(head.get("height", 0)),
            state_root=str(head.get("state_root", "0x" + "00" * 32)),
            tx_root=str(head.get("tx_root", "0x" + "00" * 32)),
            receipts_root=str(head.get("receipts_root", "0x" + "00" * 32)),
            gas_used=int(head.get("gas_used", 0)),
            extra_data={"execution_chain_id": self.node.config.chain_id, "execution_height": int(head.get("height", 0))},
        )
        block = produce_beacon_block(self.beacon_state, execution_payload=payload)
        attestations = attest_to_head(self.beacon_state)
        finality = process_epoch_finality(self.beacon_state, attestations) if block.slot % self.beacon_state.config.slots_per_epoch == 0 else None
        fork_choice = fork_choice_head(self.beacon_state)
        if self.beacon_store is not None:
            self.beacon_store.save_state(self.beacon_state)
        return {
            "ok": True,
            "slot": block.slot,
            "epoch": block.epoch,
            "root": block.root,
            "execution_block": payload.block_number,
            "execution_hash": payload.block_hash,
            "attestations": len(attestations),
            "fork_choice": fork_choice,
            "finality": finality,
        }

    def _init_beacon(self) -> None:
        beacon_service = _service(self.config, "beacon")
        beacon_cfg = _beacon_config_from_file(self.root / str(beacon_service.get("config", "config/beacon.json")))
        store_path = self.root / str(beacon_service.get("db_path", "storage/beacon.sqlite"))
        self.beacon_store = BeaconStore(store_path)
        self.beacon_store.init()
        state = self.beacon_store.load_state()
        state.config = beacon_cfg
        self.beacon_state = state

    def _validator_loop(self) -> None:
        service = _service(self.config, "validator")
        slot_seconds = max(0.1, float(service.get("slot_seconds", self.node.config.slot_seconds)))
        produce_empty = bool(service.get("produce_empty_blocks", True))
        while not self.stop_event.is_set():
            try:
                event = self.validator_once(allow_empty=produce_empty)
                print(json.dumps({"service": "validator", **event}, sort_keys=True, default=str))
            except Exception as exc:
                print(json.dumps({"service": "validator", "ok": False, "error": str(exc)}, sort_keys=True))
            self.stop_event.wait(slot_seconds)

    def _beacon_loop(self) -> None:
        service = _service(self.config, "beacon")
        self._init_beacon()
        slot_seconds = max(0.1, float(service.get("slot_seconds", getattr(self.beacon_state.config, "slot_seconds", 1))))
        while not self.stop_event.is_set():
            try:
                print(json.dumps({"service": "beacon", **self.beacon_once()}, sort_keys=True, default=str))
            except Exception as exc:
                print(json.dumps({"service": "beacon", "ok": False, "error": str(exc)}, sort_keys=True))
            self.stop_event.wait(slot_seconds)

    def _rpc_loop(self) -> None:
        rpc_cfg = self.rpc_config
        rpc_service = _service(self.config, "rpc")
        host = str(rpc_service.get("host") or rpc_cfg.get("host") or "127.0.0.1")
        port = int(rpc_service.get("port") or rpc_cfg.get("port") or 8545)
        auto_mine = bool(rpc_service.get("auto_mine", False))
        dev_send = bool(rpc_service.get("dev_send", False))
        cors_origin = str(rpc_cfg.get("cors_origin") or rpc_service.get("cors_origin") or "*")
        service = EthJsonRpcService(self.node, auto_mine=auto_mine, expose_dev_send_transaction=dev_send)
        supervisor = self

        class Handler(BaseHTTPRequestHandler):
            def _send_json(self, status: int, payload: Any) -> None:
                body = json.dumps(payload, default=str).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", cors_origin)
                self.send_header("Access-Control-Allow-Headers", "content-type")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self) -> None:  # noqa: N802
                self._send_json(200, {"ok": True})

            def do_GET(self) -> None:  # noqa: N802
                if self.path in {"/", "/health", "/api/status"}:
                    self._send_json(200, supervisor.status())
                else:
                    self._send_json(404, {"ok": False, "error": "not_found", "path": self.path})

            def do_POST(self) -> None:  # noqa: N802
                try:
                    length = int(self.headers.get("Content-Length", "0") or 0)
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                    with supervisor._lock:
                        response = service.handle_many(payload)
                    self._send_json(200, response)
                except Exception as exc:
                    self._send_json(500, {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(exc)}})

            def log_message(self, fmt: str, *args: Any) -> None:
                return

        self.rpc_server = ThreadingHTTPServer((host, port), Handler)
        print(json.dumps({"ok": True, "service": "rpc", "url": f"http://{host}:{port}", "auto_mine": auto_mine, "dev_send": dev_send}, sort_keys=True))
        self.rpc_server.serve_forever()

    def start(self, max_slots: int = 0) -> Dict[str, Any]:
        print(json.dumps({"ok": True, "event": "inhouse_chain_starting", "config": str(self.root / self.config_path), "status": self.status()}, sort_keys=True, default=str))
        if _enabled(self.config, "beacon", True):
            t = threading.Thread(target=self._beacon_loop, name="agilang-beacon", daemon=True)
            t.start()
            self.threads.append(t)
        if _enabled(self.config, "validator", True):
            t = threading.Thread(target=self._validator_loop, name="agilang-validator", daemon=True)
            t.start()
            self.threads.append(t)
        if _enabled(self.config, "rpc", True):
            t = threading.Thread(target=self._rpc_loop, name="agilang-rpc", daemon=True)
            t.start()
            self.threads.append(t)
        if max_slots > 0:
            for _ in range(max_slots):
                time.sleep(max(0.1, float(_service(self.config, "validator").get("slot_seconds", 1))))
            self.stop()
            return self.status()
        try:
            while not self.stop_event.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop()
        return self.status()

    def stop(self) -> None:
        self.stop_event.set()
        if self.rpc_server is not None:
            self.rpc_server.shutdown()
            self.rpc_server.server_close()
        try:
            self.node.close()
        except Exception:
            pass


def start_inhouse_chain(root: str | Path = ".", config: str | Path = DEFAULT_CONFIG_PATH, *, dry_run: bool = False, once: bool = False, max_slots: int = 0) -> Dict[str, Any]:
    validation = validate_chain_services(root, config)
    if dry_run:
        return validation
    supervisor = InHouseChainSupervisor(root, config)
    if once:
        events: Dict[str, Any] = {"validation": validation}
        if _enabled(supervisor.config, "validator", True):
            events["validator"] = supervisor.validator_once(allow_empty=True)
        if _enabled(supervisor.config, "beacon", True):
            events["beacon"] = supervisor.beacon_once()
        events["status"] = supervisor.status()
        supervisor.stop()
        return {"ok": True, **events}
    return supervisor.start(max_slots=max_slots)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="agilang-inhouse-chain")
    parser.add_argument("--root", default=".")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--max-slots", type=int, default=0)
    args = parser.parse_args(argv)
    result = start_inhouse_chain(args.root, args.config, dry_run=args.dry_run, once=args.once, max_slots=args.max_slots)
    if args.dry_run or args.once or args.max_slots:
        print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("ok", False) else 1


__all__ = ["InHouseChainSupervisor", "validate_chain_services", "start_inhouse_chain", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
