from __future__ import annotations

import json
import socket
import threading
import time
import urllib.request
from pathlib import Path

from agilang.blockchain_runtime_gateway import generate_blockchain_app, rpc_supported_methods, serve_project_rpc


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def rpc(port: int, method: str, params=None, request_id: int = 1):
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params or [], "id": request_id}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        return json.loads(res.read().decode())


def start_rpc(root: Path, port: int) -> threading.Thread:
    thread = threading.Thread(target=serve_project_rpc, args=(root, "127.0.0.1", port), daemon=True)
    thread.start()
    for _ in range(50):
        try:
            rpc(port, "eth_chainId")
            return thread
        except Exception:
            time.sleep(0.1)
    raise AssertionError("RPC server did not start")


def test_supported_rpc_method_catalog_is_metamask_compatible():
    methods = set(rpc_supported_methods())
    required = {
        "web3_clientVersion",
        "net_version",
        "net_listening",
        "eth_chainId",
        "eth_blockNumber",
        "eth_accounts",
        "eth_getBalance",
        "eth_getTransactionCount",
        "eth_gasPrice",
        "eth_estimateGas",
        "eth_getBlockByNumber",
        "eth_getBlockByHash",
        "eth_getTransactionByHash",
        "eth_getTransactionReceipt",
        "eth_sendTransaction",
        "eth_sendRawTransaction",
        "rpc_modules",
    }
    assert required.issubset(methods)


def test_rpc_methods_work_against_generated_chain(tmp_path: Path):
    generated = generate_blockchain_app("rpc coverage", tmp_path, force=True)
    root = Path(generated["root"])
    port = free_port()
    start_rpc(root, port)

    assert rpc(port, "eth_chainId")["result"] == "0x76c"
    assert rpc(port, "net_version")["result"] == "1900"
    assert rpc(port, "net_listening")["result"] is True
    assert rpc(port, "eth_syncing")["result"] is False
    assert rpc(port, "eth_blockNumber")["result"].startswith("0x")
    accounts = rpc(port, "eth_accounts")["result"]
    assert accounts
    sender, receiver = accounts[0], accounts[1]
    assert rpc(port, "eth_getBalance", [sender, "latest"])["result"].startswith("0x")
    assert rpc(port, "eth_getTransactionCount", [sender, "latest"])["result"].startswith("0x")
    assert rpc(port, "eth_gasPrice")["result"] == "0x1"
    assert rpc(port, "eth_estimateGas", [{"from": sender, "to": receiver, "value": "0x1"}])["result"].startswith("0x")

    sent = rpc(port, "eth_sendTransaction", [{"from": sender, "to": receiver, "value": "0x1", "gasPrice": "0x1"}])
    assert "result" in sent, sent
    tx_hash = sent["result"]
    assert tx_hash

    assert int(rpc(port, "eth_blockNumber")["result"], 16) >= 1
    latest = rpc(port, "eth_getBlockByNumber", ["latest", True])["result"]
    assert latest["hash"]
    assert latest["transactions"]
    assert rpc(port, "eth_getBlockByHash", [latest["hash"], False])["result"]["hash"] == latest["hash"]
    assert int(rpc(port, "eth_getBlockTransactionCountByNumber", ["latest"])["result"], 16) >= 1
    assert int(rpc(port, "eth_getBlockTransactionCountByHash", [latest["hash"]])["result"], 16) >= 1

    tx = rpc(port, "eth_getTransactionByHash", [tx_hash])["result"]
    assert tx["hash"] == tx_hash
    receipt = rpc(port, "eth_getTransactionReceipt", [tx_hash])["result"]
    assert receipt["transactionHash"] == tx_hash
    assert receipt["status"] == "0x1"
    assert rpc(port, "eth_getLogs", [{}])["result"] == []
    assert "eth" in rpc(port, "rpc_modules")["result"]
    assert "eth_chainId" in rpc(port, "sbq_supportedMethods")["result"]


def test_rpc_batch_requests_work(tmp_path: Path):
    generated = generate_blockchain_app("rpc batch", tmp_path, force=True)
    root = Path(generated["root"])
    port = free_port()
    start_rpc(root, port)
    payload = json.dumps([
        {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1},
        {"jsonrpc": "2.0", "method": "net_listening", "params": [], "id": 2},
    ]).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        data = json.loads(res.read().decode())
    assert [item["result"] for item in data] == ["0x76c", True]
