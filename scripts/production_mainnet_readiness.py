"""Production mainnet readiness gate for AGILANG/SBQ blockchain work.

This script is intentionally strict. It can verify local engineering checks,
but it will not mark external audit requirements as passed without evidence
artifacts committed or supplied in the workspace.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import urllib.error
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agilang.beacon import BeaconConfig, attest_to_head, create_beacon_state, process_epoch_finality, produce_beacon_block
from agilang.blockchain import blockchain_config, blockchain_devnet, blockchain_node, blockchain_transaction
from agilang.blockchain_runtime_gateway import generate_blockchain_app, serve_project_rpc


@dataclass
class GateResult:
    gate: str
    ok: bool
    status: str
    details: dict[str, Any]


def _result(gate: str, ok: bool, status: str, **details: Any) -> GateResult:
    return GateResult(gate, ok, status, details)


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _evidence_file_exists(evidence_dir: Path, names: list[str]) -> bool:
    return any((evidence_dir / name).exists() for name in names)


def independent_external_security_audit(evidence_dir: Path) -> GateResult:
    names = ["independent-security-audit.json", "independent-security-audit.pdf", "security-audit-attestation.md"]
    ok = _evidence_file_exists(evidence_dir, names)
    return _result(
        "independent_external_security_audit",
        ok,
        "pass" if ok else "blocked",
        required=names,
        evidence_dir=str(evidence_dir),
        reason=None if ok else "No independent third-party audit evidence was found.",
    )


def validator_key_management_audit(evidence_dir: Path) -> GateResult:
    names = ["validator-key-management-audit.json", "validator-key-management-audit.pdf", "validator-key-runbook.md"]
    evidence_ok = _evidence_file_exists(evidence_dir, names)
    generated = generate_blockchain_app("key audit chain", tempfile.mkdtemp(prefix="agilang-key-audit-"), force=True)
    root = Path(generated["root"])
    config_text = "\n".join(path.read_text(encoding="utf-8") for path in (root / "config").rglob("*.json"))
    dev_keys_present = "dev-signing-key-" in config_text
    shutil.rmtree(root.parent, ignore_errors=True)
    ok = evidence_ok and not dev_keys_present
    if ok:
        reason = None
    elif dev_keys_present:
        reason = "Generated config still contains dev signing keys; replace them with audited key-management integration."
    else:
        reason = "Generated dev signing keys are absent, but external key-management audit evidence is required."
    return _result(
        "validator_key_management_audit",
        ok,
        "pass" if ok else "blocked",
        required=names,
        evidence_dir=str(evidence_dir),
        dev_signing_keys_present=dev_keys_present,
        reason=reason,
    )


def p2p_abuse_load_test(nodes: int, blocks: int) -> GateResult:
    validators = {f"validator-{i}": 100 + i for i in range(nodes)}
    cfg = blockchain_config(
        chain_id=1900,
        name="p2p-load",
        validators=validators,
        genesis_state={"balances": {"validator-0": 10_000}},
        strict_accounting=True,
        slot_seconds=1,
    )
    net = blockchain_devnet(cfg, validators=list(validators))
    for nonce in range(1, blocks + 1):
        tx = blockchain_transaction("validator-0", f"receiver-{nonce}", 1, nonce=nonce, gas_price=1)
        submit = net.submit_tx(tx)
        if not submit.get("ok"):
            return _result("p2p_abuse_load_testing", False, "fail", submit=submit, nonce=nonce)
        step = net.step()
        if not step.get("ok"):
            return _result("p2p_abuse_load_testing", False, "fail", step=step, nonce=nonce)
    heights = [node["height"] for node in net.status()["nodes"]]
    synced = len(set(heights)) == 1 and heights[0] >= blocks
    return _result("p2p_abuse_load_testing", synced, "pass" if synced else "fail", nodes=nodes, blocks=blocks, heights=heights)


def _rpc_post(port: int, method: str, params: list[Any] | None = None, request_id: int = 1) -> dict[str, Any]:
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params or [], "id": request_id}).encode("utf-8")
    request = urllib.request.Request(f"http://127.0.0.1:{port}", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body)
        except Exception:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": exc.code, "message": body or str(exc)}}


def rpc_rate_limit_load_test(requests: int, workers: int) -> GateResult:
    temp = Path(tempfile.mkdtemp(prefix="agilang-rpc-load-"))
    generated = generate_blockchain_app("rpc load chain", temp, force=True)
    root = Path(generated["root"])
    rpc_cfg = root / "config" / "rpc.json"
    data = json.loads(rpc_cfg.read_text(encoding="utf-8"))
    port = _free_local_port()
    data["port"] = port
    # Support both older and newer runtime config keys.
    data["rate_limit"] = 20
    data["rate_limit_per_minute"] = 20
    data["rate_window_seconds"] = 60
    rpc_cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")

    errors: list[dict[str, Any]] = []
    ready = threading.Event()

    def run_server() -> None:
        ready.set()
        serve_project_rpc(root, host="127.0.0.1", port=port)

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    ready.wait(2)
    time.sleep(0.5)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_rpc_post, port, "eth_blockNumber", [], i) for i in range(requests)]
            for fut in concurrent.futures.as_completed(futures):
                try:
                    response = fut.result()
                    if "error" in response:
                        errors.append(response["error"])
                except Exception as exc:
                    errors.append({"exception": str(exc)})
        rate_limited = any(err.get("code") == -32005 for err in errors)
        unexpected = [err for err in errors if err.get("code") != -32005]
        ok = rate_limited and not unexpected
        return _result(
            "rpc_rate_limit_load_testing",
            ok,
            "pass" if ok else "fail",
            requests=requests,
            workers=workers,
            rate_limited=rate_limited,
            unexpected_errors=unexpected[:5],
        )
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def long_running_staging_soak_test(blocks: int) -> GateResult:
    temp = Path(tempfile.mkdtemp(prefix="agilang-soak-"))
    try:
        cfg = blockchain_config(
            chain_id=1900,
            name="soak-chain",
            validators={"alice": 100, "bob": 80},
            validator_signing_keys={"alice": "alice-soak-key", "bob": "bob-soak-key"},
            genesis_state={"balances": {"alice": 1_000_000}},
            mainnet_profile=True,
            slot_seconds=1,
        )
        node = blockchain_node(cfg, temp / "chain.sqlite", "soak-node")
        for nonce in range(1, blocks + 1):
            tx = blockchain_transaction("alice", "bob", 1, nonce=nonce, gas_price=1)
            submit = node.submit_tx(tx)
            if not submit.get("ok"):
                return _result("long_running_staging_soak_tests", False, "fail", nonce=nonce, submit=submit)
            parent = node.head()
            proposer = node.consensus.select_proposer(parent["hash"], parent["slot"] + 1)
            produced = node.produce_and_import_block(proposer, parent["slot"] + 1)
            if not produced["import"].get("ok"):
                return _result("long_running_staging_soak_tests", False, "fail", nonce=nonce, produced=produced)
        reopened = blockchain_node(cfg, temp / "chain.sqlite", "soak-reopen")
        ok = reopened.height() >= blocks
        return _result("long_running_staging_soak_tests", ok, "pass" if ok else "fail", blocks=blocks, height=reopened.height())
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def consensus_finality_review(evidence_dir: Path, epochs: int) -> GateResult:
    names = ["consensus-finality-review.json", "consensus-finality-review.pdf", "formal-consensus-review.md"]
    evidence_ok = _evidence_file_exists(evidence_dir, names)
    cfg = BeaconConfig(slots_per_epoch=4)
    state = create_beacon_state(cfg)
    finality = None
    for _ in range(epochs * cfg.slots_per_epoch):
        block = produce_beacon_block(state)
        attest_to_head(state)
        if block.slot % cfg.slots_per_epoch == 0:
            finality = process_epoch_finality(state)
    local_ok = bool(finality and finality["ok"] and state.justified_checkpoint.epoch >= 1)
    ok = local_ok and evidence_ok
    return _result(
        "consensus_finality_review",
        ok,
        "pass" if ok else "blocked",
        local_simulation_ok=local_ok,
        justified_epoch=state.justified_checkpoint.epoch,
        finalized_epoch=state.finalized_checkpoint.epoch,
        required=evidence_dir.as_posix(),
        reason=None if ok else "Local finality simulation passed, but independent consensus/finality review evidence is required.",
    )


def storage_recovery_database_durability_test(blocks: int) -> GateResult:
    temp = Path(tempfile.mkdtemp(prefix="agilang-storage-"))
    try:
        db = temp / "chain.sqlite"
        cfg = blockchain_config(
            chain_id=1900,
            name="durability-chain",
            validators={"alice": 100},
            genesis_state={"balances": {"alice": 100_000}},
            strict_accounting=True,
            slot_seconds=1,
        )
        node = blockchain_node(cfg, db, "durability-node")
        for nonce in range(1, blocks + 1):
            tx = blockchain_transaction("alice", f"sink-{nonce}", 1, nonce=nonce, gas_price=1)
            node.submit_tx(tx)
            parent = node.head()
            block = node.produce_block("alice", parent["slot"] + 1)
            imported = node.import_block(block)
            if not imported.get("ok"):
                return _result("storage_recovery_database_durability_testing", False, "fail", imported=imported)
        backup = temp / "chain.backup.sqlite"
        shutil.copy2(db, backup)
        with sqlite3.connect(db) as conn:
            integrity = conn.execute("pragma integrity_check").fetchone()[0]
        recovered = blockchain_node(cfg, backup, "recovered-node")
        ok = integrity == "ok" and recovered.height() == node.height()
        return _result(
            "storage_recovery_database_durability_testing",
            ok,
            "pass" if ok else "fail",
            integrity=integrity,
            height=node.height(),
            recovered_height=recovered.height(),
            backup=str(backup),
        )
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def run_command_gate(name: str, command: list[str]) -> GateResult:
    proc = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, timeout=120)
    return _result(
        name,
        proc.returncode == 0,
        "pass" if proc.returncode == 0 else "fail",
        command=command,
        returncode=proc.returncode,
        stdout_tail=proc.stdout[-2000:],
        stderr_tail=proc.stderr[-2000:],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", default="audits/mainnet-readiness")
    parser.add_argument("--json", action="store_true", help="accepted for compatibility; output is JSON by default")
    parser.add_argument("--p2p-nodes", type=int, default=8)
    parser.add_argument("--p2p-blocks", type=int, default=20)
    parser.add_argument("--rpc-requests", type=int, default=48)
    parser.add_argument("--rpc-workers", type=int, default=12)
    parser.add_argument("--soak-blocks", type=int, default=50)
    parser.add_argument("--finality-epochs", type=int, default=3)
    parser.add_argument("--storage-blocks", type=int, default=25)
    args = parser.parse_args()

    evidence_dir = (REPO_ROOT / args.evidence_dir).resolve()
    results = [
        independent_external_security_audit(evidence_dir),
        validator_key_management_audit(evidence_dir),
        p2p_abuse_load_test(args.p2p_nodes, args.p2p_blocks),
        rpc_rate_limit_load_test(args.rpc_requests, args.rpc_workers),
        long_running_staging_soak_test(args.soak_blocks),
        consensus_finality_review(evidence_dir, args.finality_epochs),
        storage_recovery_database_durability_test(args.storage_blocks),
        run_command_gate("compileall", [sys.executable, "-m", "compileall", "-q", "agilang", "tests"]),
    ]
    payload = {
        "ok": all(item.ok for item in results),
        "passed": sum(1 for item in results if item.ok),
        "total": len(results),
        "results": [item.__dict__ for item in results],
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
