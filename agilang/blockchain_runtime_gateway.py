"""Hardened generated-project JSON-RPC gateway.

The original generator implementation is retained in
``_blockchain_runtime_gateway_legacy`` for project scaffolding and read-only
formatting helpers.  Public RPC execution is replaced with a signed-raw-only,
fail-closed service.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List

from . import __version__
from . import _blockchain_runtime_gateway_legacy as legacy
from .blockchain import BlockchainNode
from .evm import evm_keccak
from .rpc import EthJsonRpcService, MAX_BODY_BYTES, _jsonrpc_error


def generate_blockchain_app(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Generate a project, then apply secure RPC defaults.

    Existing projects are not silently changed.  Operators should update their
    ``config/rpc.json`` using the same settings before restarting production.
    """
    result = legacy.generate_blockchain_app(*args, **kwargs)
    root = Path(result["root"])
    config_path = root / "config" / "rpc.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["auto_mine"] = False
        config["dev_send"] = False
        config["cors_origin"] = ""
        config["max_body_bytes"] = min(int(config.get("max_body_bytes") or 262_144), 262_144)
        config["max_batch_size"] = 20
        config["public_write_method"] = "eth_sendRawTransaction"
        config["security_profile"] = "signed-raw-only"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return result


load_project_chain = legacy.load_project_chain
chain_status = legacy.chain_status
print_project_status = legacy.print_project_status


def rpc_supported_methods() -> List[str]:
    """Methods truthfully implemented by the hardened public gateway."""
    return sorted(
        {
            "web3_clientVersion",
            "web3_sha3",
            "net_version",
            "net_listening",
            "net_peerCount",
            "eth_chainId",
            "eth_syncing",
            "eth_protocolVersion",
            "eth_blockNumber",
            "eth_accounts",
            "eth_mining",
            "eth_hashrate",
            "eth_gasPrice",
            "eth_maxPriorityFeePerGas",
            "eth_feeHistory",
            "eth_getBalance",
            "eth_getTransactionCount",
            "eth_getCode",
            "eth_getBlockByNumber",
            "eth_getBlockByHash",
            "eth_getBlockTransactionCountByNumber",
            "eth_getBlockTransactionCountByHash",
            "eth_getTransactionByHash",
            "eth_getTransactionReceipt",
            "eth_sendRawTransaction",
            "txpool_status",
            "sbq_supportedMethods",
            "rpc_modules",
        }
    )


class ProjectRpcService(EthJsonRpcService):
    def __init__(self, node: BlockchainNode, *, auto_mine: bool = False) -> None:
        super().__init__(node, auto_mine=auto_mine)
        self.project_auto_mine = bool(auto_mine)

    def dispatch(self, method: str, params: list[Any]) -> Any:
        if method == "sbq_supportedMethods":
            return rpc_supported_methods()
        if method == "rpc_modules":
            return {"eth": "1.0", "net": "1.0", "web3": "1.0", "sbq": "1.0"}
        if method == "net_listening":
            return True
        if method == "net_peerCount":
            return legacy._hex(len(getattr(self.node, "peers", [])))
        if method == "web3_sha3":
            if len(params) != 1 or not isinstance(params[0], str):
                raise ValueError("web3_sha3 expects one hex string")
            raw = params[0]
            if not raw.startswith("0x") or len(raw[2:]) % 2:
                raise ValueError("web3_sha3 requires 0x-prefixed even-length hex")
            return evm_keccak(bytes.fromhex(raw[2:]))
        if method == "eth_syncing":
            return False
        if method == "eth_protocolVersion":
            return "0x1"
        if method == "eth_accounts":
            # Public RPCs must not advertise node-managed or pre-funded accounts.
            return []
        if method == "eth_coinbase":
            raise NotImplementedError("eth_coinbase is not exposed on public RPC")
        if method == "eth_mining":
            return self.project_auto_mine
        if method == "eth_hashrate":
            return "0x0"
        if method == "eth_feeHistory":
            count = legacy._parse_tx_value(params[0]) if params else 1
            count = max(1, min(int(count), 1024))
            return {
                "oldestBlock": legacy._hex(max(0, self.node.height() - count + 1)),
                "baseFeePerGas": [legacy._hex(1) for _ in range(count + 1)],
                "gasUsedRatio": [0 for _ in range(count)],
                "reward": [[legacy._hex(1)] for _ in range(count)],
            }
        if method == "eth_getBlockByNumber":
            block = legacy._block_by_height(
                self.node,
                legacy._parse_block_number(params[0] if params else "latest", self.node),
            )
            return legacy._block_to_rpc(block, bool(params[1]) if len(params) > 1 else False) if block else None
        if method == "eth_getBlockByHash":
            block = legacy._block_by_hash(self.node, str(params[0])) if params else None
            return legacy._block_to_rpc(block, bool(params[1]) if len(params) > 1 else False) if block else None
        if method == "eth_getBlockTransactionCountByNumber":
            block = legacy._block_by_height(
                self.node,
                legacy._parse_block_number(params[0] if params else "latest", self.node),
            )
            return legacy._hex(len(block.get("transactions") or [])) if block else None
        if method == "eth_getBlockTransactionCountByHash":
            block = legacy._block_by_hash(self.node, str(params[0])) if params else None
            return legacy._hex(len(block.get("transactions") or [])) if block else None
        if method == "eth_getLogs":
            raise NotImplementedError("eth_getLogs unavailable until canonical log indexing is implemented")
        return super().dispatch(method, params)


def serve_project_rpc(
    root: str | Path | None = None,
    host: str | None = None,
    port: int | None = None,
) -> None:
    """Serve a bounded, signed-raw-only RPC for a generated project."""
    project = legacy._project_root(root)
    node, cfg = load_project_chain(project)
    host = host or str(cfg.get("host") or "127.0.0.1")
    port = int(port or cfg.get("port") or 8545)

    if host not in {"127.0.0.1", "localhost", "::1"} and os.getenv("AGILANG_ALLOW_PUBLIC_RPC_BIND") != "1":
        raise RuntimeError("refusing non-loopback RPC bind; use a hardened TLS reverse proxy or explicitly acknowledge the risk")

    if cfg.get("dev_send"):
        sys.stderr.write("security_warning: ignoring legacy dev_send=true; unsigned transaction methods remain disabled\n")

    auto_mine = bool(cfg.get("auto_mine", False))
    service = ProjectRpcService(node, auto_mine=auto_mine)
    max_body = max(1_024, min(int(cfg.get("max_body_bytes") or MAX_BODY_BYTES), 2 * 1024 * 1024))
    rate_limit = max(1, min(int(cfg.get("rate_limit_per_minute") or cfg.get("rate_limit") or 600), 100_000))
    cors_origin = str(cfg.get("cors_origin") or "").strip()
    if cors_origin == "*":
        sys.stderr.write("security_warning: wildcard RPC CORS ignored; configure one explicit origin\n")
        cors_origin = ""

    request_windows: dict[str, deque[float]] = defaultdict(deque)

    def rate_limited(client: str) -> bool:
        now = time.monotonic()
        window = request_windows[client]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= rate_limit:
            return True
        window.append(now)
        if len(request_windows) > 10_000:
            request_windows.clear()
        return False

    class Handler(BaseHTTPRequestHandler):
        server_version = "AGILANG-SBQ-RPC"
        sys_version = ""

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(10)

        def version_string(self) -> str:
            return "AGILANG-SBQ-RPC"

        def _send(self, payload: Any, status: int = 200) -> None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
            self.send_header("Referrer-Policy", "no-referrer")
            if cors_origin:
                self.send_header("Access-Control-Allow-Origin", cors_origin)
                self.send_header("Access-Control-Allow-Headers", "content-type")
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._send({}, status=204 if cors_origin else 405)

        def do_GET(self) -> None:  # noqa: N802
            self._send(
                {
                    "ok": True,
                    "client": f"AGILANG-SBQ/{__version__}",
                    "chainId": hex(node.config.chain_id),
                    "blockNumber": hex(node.height()),
                }
            )

        def do_POST(self) -> None:  # noqa: N802
            client = self.client_address[0] if self.client_address else "unknown"
            if rate_limited(client):
                self._send(_jsonrpc_error(None, -32005, "rate limit exceeded"), status=429)
                return
            try:
                if self.headers.get("Transfer-Encoding"):
                    self._send(_jsonrpc_error(None, -32600, "transfer encoding not supported"), status=400)
                    return
                content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                if content_type != "application/json":
                    self._send(_jsonrpc_error(None, -32600, "content type must be application/json"), status=415)
                    return
                raw_length = self.headers.get("Content-Length")
                if raw_length is None:
                    self._send(_jsonrpc_error(None, -32600, "content length required"), status=411)
                    return
                try:
                    length = int(raw_length)
                except ValueError:
                    self._send(_jsonrpc_error(None, -32600, "invalid content length"), status=400)
                    return
                if length < 1 or length > max_body:
                    self._send(_jsonrpc_error(None, -32600, "request body size invalid"), status=413)
                    return
                raw = self.rfile.read(length)
                if len(raw) != length:
                    self._send(_jsonrpc_error(None, -32700, "incomplete JSON body"), status=400)
                    return
                try:
                    request = json.loads(raw)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._send(_jsonrpc_error(None, -32700, "parse error"), status=400)
                    return
                response = service.handle_many(request)
                if response is None or response == []:
                    self.send_response(204)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self._send(response)
            except (BrokenPipeError, ConnectionResetError, socket.timeout):
                return
            except Exception as exc:
                sys.stderr.write(f"project_rpc_internal_error:{type(exc).__name__}\n")
                self._send(_jsonrpc_error(None, -32603, "internal RPC error"), status=500)

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    # Single-threaded by design: ChainDatabase uses one SQLite connection and is
    # not safe to share across handler threads.  Put concurrency and TLS at the
    # reverse proxy until the database layer gains explicit transaction locks.
    server = HTTPServer((host, port), Handler)
    print(f"AGILANG/SBQ hardened JSON-RPC running at http://{host}:{port}")
    print(f"chain_id={node.config.chain_id} height={node.height()}")
    server.serve_forever()


__all__ = [
    "generate_blockchain_app",
    "serve_project_rpc",
    "print_project_status",
    "chain_status",
    "load_project_chain",
    "rpc_supported_methods",
]
