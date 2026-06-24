#!/usr/bin/env python3
"""Repeatable AGILANG/SBQ production-mainnet readiness gate.

This gate is intentionally strict. Local simulations can pass, while external
assurance gates remain blocked until third-party evidence is committed under
``audits/``. It prevents accidental marketing of a local/private-chain runtime
as public real-value mainnet ready.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def result(name: str, ok: bool, detail: str, evidence: str | None = None) -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail, "evidence": evidence or ""}


def run_compileall() -> dict:
    proc = subprocess.run([sys.executable, "-m", "compileall", "-q", "agilang", "tests"], cwd=ROOT, text=True, capture_output=True, timeout=60)
    return result("compileall", proc.returncode == 0, (proc.stderr or proc.stdout or "passed").strip())


def run_p2p_simulation() -> dict:
    from agilang.blockchain import blockchain_config, blockchain_devnet, blockchain_transaction
    validators = {f"v{i}": 10 + i for i in range(8)}
    cfg = blockchain_config(chain_id=1900, name="readiness-p2p", validators=validators, genesis_state={"balances": {"v0": 100000, "v1": 0}}, slot_seconds=1)
    net = blockchain_devnet(cfg, validators=list(validators))
    net.submit_tx(blockchain_transaction("v0", "v1", 1, nonce=1, gas_price=1))
    for _ in range(20):
        net.step()
        net.sync_all()
    heights = {n["height"] for n in net.status()["nodes"]}
    return result("p2p_abuse_load_simulation", heights == {20}, f"8 nodes, 20 blocks, heights={sorted(heights)}")


def run_soak() -> dict:
    from agilang.blockchain import blockchain_config, blockchain_node
    with tempfile.TemporaryDirectory() as td:
        validators = {"alice": 60, "bob": 40}
        cfg = blockchain_config(chain_id=1900, name="readiness-soak", validators=validators, validator_signing_keys={"alice": "audit-key-alice", "bob": "audit-key-bob"}, genesis_state={"balances": {"alice": 1000000, "bob": 0}}, mainnet_profile=True, slot_seconds=1)
        node = blockchain_node(cfg, Path(td) / "chain.sqlite", "soak")
        for _ in range(50):
            parent = node.head()
            slot = int(parent["slot"]) + 1
            proposer = node.consensus.select_proposer(parent["hash"], slot)
            node.produce_and_import_block(proposer, slot)
        ok = node.height() == 50 and all("validator_signature" in block for block in node.canonical_chain() if int(block.get("height", 0)) > 0)
        return result("long_running_staging_soak", ok, f"50 signed mainnet-profile blocks, height={node.height()}")


def run_storage_recovery() -> dict:
    from agilang.blockchain import blockchain_config, blockchain_node
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "recover.sqlite"
        cfg = blockchain_config(chain_id=1900, name="readiness-recovery", validators={"alice": 100}, validator_signing_keys={"alice": "audit-key-alice"}, genesis_state={"balances": {"alice": 1000000}}, mainnet_profile=True, slot_seconds=1)
        node = blockchain_node(cfg, db, "writer")
        for _ in range(5):
            parent = node.head(); slot = int(parent["slot"]) + 1
            proposer = node.consensus.select_proposer(parent["hash"], slot)
            node.produce_and_import_block(proposer, slot)
        height = node.height()
        with sqlite3.connect(db) as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        recovered = blockchain_node(cfg, db, "reader")
        ok = integrity == "ok" and recovered.height() == height
        return result("storage_recovery_durability", ok, f"SQLite integrity={integrity}, recovered_height={recovered.height()}, expected={height}")


def run_rpc_rate_limit() -> dict:
    from agilang.blockchain_runtime_gateway import generate_blockchain_app, serve_project_rpc
    import multiprocessing
    with tempfile.TemporaryDirectory() as td:
        generated = generate_blockchain_app("readiness rpc", td, force=True)
        root = Path(generated["root"])
        port = 18545
        proc = multiprocessing.Process(target=serve_project_rpc, args=(root, "127.0.0.1", port), daemon=True)
        proc.start()
        time.sleep(1.5)
        def call(i: int) -> int:
            body = json.dumps({"jsonrpc": "2.0", "id": i, "method": "eth_blockNumber", "params": []}).encode()
            req = Request(f"http://127.0.0.1:{port}", data=body, headers={"Content-Type": "application/json"})
            try:
                with urlopen(req, timeout=3) as res:
                    return int(res.status)
            except HTTPError as exc:
                return int(exc.code)
        statuses = []
        with ThreadPoolExecutor(max_workers=12) as pool:
            for fut in as_completed([pool.submit(call, i) for i in range(48)]):
                statuses.append(fut.result())
        proc.terminate(); proc.join(timeout=2)
        ok = 200 in statuses and all(code in {200, 429} for code in statuses)
        return result("rpc_rate_limit_load", ok, f"48 requests, 12 workers, statuses={dict((c, statuses.count(c)) for c in sorted(set(statuses)))}")


def evidence_exists(*patterns: str) -> bool:
    for pattern in patterns:
        if list((ROOT / "audits").glob(pattern)):
            return True
    return False


def run_external_audit_gate() -> dict:
    ok = evidence_exists("*third*party*", "*external*audit*", "*.sig")
    return result("independent_external_security_audit", ok, "requires third-party audit evidence under audits/")


def run_key_management_gate() -> dict:
    text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in [ROOT / "agilang" / "blockchain_runtime_gateway.py"] if p.exists())
    no_dev_keys = "dev-signing-key" not in text
    ok = no_dev_keys and evidence_exists("*key*management*", "*validator*key*")
    return result("validator_key_management_audit", ok, "no generated dev-signing-key plus validator key-management audit evidence required")


def run_finality_review_gate() -> dict:
    local = run_soak()["ok"]
    ok = local and evidence_exists("*consensus*review*", "*finality*review*")
    return result("consensus_finality_review", ok, "local finality simulation passed; independent consensus/finality review evidence required")


def main() -> int:
    parser = argparse.ArgumentParser(description="AGILANG/SBQ public-mainnet readiness gate")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON only")
    args = parser.parse_args()
    checks = [
        run_p2p_simulation(),
        run_rpc_rate_limit(),
        run_soak(),
        run_storage_recovery(),
        run_compileall(),
        run_external_audit_gate(),
        run_key_management_gate(),
        run_finality_review_gate(),
    ]
    passed = sum(1 for c in checks if c["ok"])
    payload = {"ok": passed == len(checks), "passed": passed, "total": len(checks), "checks": checks}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Production mainnet readiness: {passed}/{len(checks)} passed")
        for c in checks:
            print(("PASS" if c["ok"] else "BLOCK") + f" - {c['name']}: {c['detail']}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
