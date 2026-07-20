from __future__ import annotations

import json
import socket
import threading
import time
import urllib.request
from pathlib import Path

from agilang.blockchain_runtime_gateway import (
    generate_blockchain_app,
    rpc_supported_methods,
    serve_project_rpc,
)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def rpc(port: int, method: str, params=None, request_id: int = 1):
    payload = json.dumps(
        {"jsonrpc": "2.0", "method": method, "params": params or [], "id": request_id}
    ).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        return json.loads(res.read().decode())


def start_rpc(root: Path, port: int) -> threading.Thread:
    thread = threading.Thread(
        target=serve_project_rpc,
        args=(root, "127.0.0.1", port),
        daemon=True,
    )
    thread.start()
    for _ in range(50):
        try:
            rpc(port, "eth_chainId")
            return thread
        except Exception:
            time.sleep(0.1)
    raise AssertionError("RPC server did not start")


def test_supported_rpc_method_catalog_is_truthful_and_signed_raw_only():
    methods = set(rpc_supported_methods())
    required = {
        "web3_clientVersion",
        "web3_sha3",
        "net_version",
        "net_listening",
        "eth_chainId",
        "eth_blockNumber",
        "eth_accounts",
        "eth_getBalance",
        "eth_getTransactionCount",
        "eth_gasPrice",
        "eth_getBlockByNumber",
        "eth_getBlockByHash",
        "eth_getTransactionByHash",
        "eth_getTransactionReceipt",
        "eth_sendRawTransaction",
        "rpc_modules",
    }
    assert required.issubset(methods)
    assert "eth_sendTransaction" not in methods
    assert "dev_sendTransaction" not in methods
    assert "sbq_sendTransaction" not in methods
    assert "eth_call" not in methods
    assert "eth_estimateGas" not in methods
    assert "eth_getLogs" not in methods


def test_generated_rpc_config_defaults_to_secure_public_behavior(tmp_path: Path):
    generated = generate_blockchain_app("secure rpc defaults", tmp_path, force=True)
    config = json.loads(
        (Path(generated["root"]) / "config" / "rpc.json").read_text(encoding="utf-8")
    )
    assert config["dev_send"] is False
    assert config["auto_mine"] is False
    assert config["cors_origin"] == ""
    assert config["max_batch_size"] == 20
    assert config["public_write_method"] == "eth_sendRawTransaction"
    assert config["security_profile"] == "signed-raw-only"


def test_rpc_read_methods_and_security_failures(tmp_path: Path):
    generated = generate_blockchain_app("rpc coverage", tmp_path, force=True)
    root = Path(generated["root"])
    port = free_port()
    start_rpc(root, port)

    assert rpc(port, "eth_chainId")["result"] == "0x76c"
    assert rpc(port, "net_version")["result"] == "1900"
    assert rpc(port, "net_listening")["result"] is True
    assert rpc(port, "eth_syncing")["result"] is False
    assert rpc(port, "eth_blockNumber")["result"].startswith("0x")
    assert rpc(port, "eth_accounts")["result"] == []
    assert rpc(port, "eth_gasPrice")["result"] == "0x1"

    # Ethereum Keccak-256 of empty bytes, not NIST SHA3-256.
    assert (
        rpc(port, "web3_sha3", ["0x"])["result"]
        == "0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    )

    unsigned = rpc(
        port,
        "eth_sendTransaction",
        [
            {
                "from": "0x04aac0173878aee604c1eaec3455ca8b5719f39b",
                "to": "0x95e3673f703cb53b3c1848cd3def70a64c59fb08",
                "value": "0x1",
            }
        ],
    )
    assert unsigned["error"]["code"] == -32000
    assert "eth_sendRawTransaction" in unsigned["error"]["message"]

    fake_call = rpc(
        port,
        "eth_call",
        [{"to": "0x0000000000000000000000000000000000000001", "data": "0x1234"}, "latest"],
    )
    fake_estimate = rpc(
        port,
        "eth_estimateGas",
        [{"to": "0x0000000000000000000000000000000000000001"}],
    )
    fake_logs = rpc(port, "eth_getLogs", [{}])
    assert fake_call["error"]["code"] == -32601
    assert fake_estimate["error"]["code"] == -32601
    assert fake_logs["error"]["code"] == -32601

    latest = rpc(port, "eth_getBlockByNumber", ["latest", True])["result"]
    assert latest["hash"]
    assert latest["transactions"] == []
    assert rpc(port, "eth_getBlockByHash", [latest["hash"], False])["result"]["hash"] == latest["hash"]
    assert rpc(port, "eth_getBlockTransactionCountByNumber", ["latest"])["result"] == "0x0"
    assert rpc(port, "eth_getBlockTransactionCountByHash", [latest["hash"]])["result"] == "0x0"
    assert "eth" in rpc(port, "rpc_modules")["result"]
    assert "eth_sendRawTransaction" in rpc(port, "sbq_supportedMethods")["result"]


def test_rpc_batch_requests_work(tmp_path: Path):
    generated = generate_blockchain_app("rpc batch", tmp_path, force=True)
    root = Path(generated["root"])
    port = free_port()
    start_rpc(root, port)
    payload = json.dumps(
        [
            {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1},
            {"jsonrpc": "2.0", "method": "net_listening", "params": [], "id": 2},
        ]
    ).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        data = json.loads(res.read().decode())
    assert [item["result"] for item in data] == ["0x76c", True]
