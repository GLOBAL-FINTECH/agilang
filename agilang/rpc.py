"""Hardened public JSON-RPC boundary for AGILANG Smart Chain.

The previous implementation is retained in ``_rpc_legacy`` for transaction
codec and node-construction compatibility.  This module deliberately removes
unsigned sender-controlled transaction methods from the public surface and
fails closed for contract calls that the legacy state engine cannot execute
correctly yet.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from . import __version__
from . import _rpc_legacy as legacy
from .blockchain import BlockchainConfig, BlockchainNode, blockchain_config, blockchain_mainnet_config, blockchain_node

JSONRPC_VERSION = legacy.JSONRPC_VERSION
MAX_BODY_BYTES = max(1_024, min(int(os.getenv("AGILANG_RPC_MAX_BODY_BYTES", str(256 * 1024))), 2 * 1024 * 1024))
MAX_BATCH_SIZE = max(1, min(int(os.getenv("AGILANG_RPC_MAX_BATCH_SIZE", "20")), 100))
MAX_CONNECTIONS = max(1, min(int(os.getenv("AGILANG_RPC_MAX_CONNECTIONS", "64")), 512))
SOCKET_TIMEOUT_SECONDS = max(1, min(int(os.getenv("AGILANG_RPC_SOCKET_TIMEOUT_SECONDS", "10")), 120))
MAX_RAW_TRANSACTION_BYTES = max(1_024, min(int(os.getenv("AGILANG_RPC_MAX_RAW_TX_BYTES", str(128 * 1024))), MAX_BODY_BYTES))

# Public compatibility exports.
decode_ethereum_signed_raw_transaction = legacy.decode_ethereum_signed_raw_transaction
node_from_rpc_config = legacy.node_from_rpc_config


def _jsonrpc_result(request_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}


def _jsonrpc_error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": {"code": code, "message": message}}


def _safe_error_message(exc: Exception) -> str:
    if isinstance(exc, NotImplementedError):
        return str(exc) or "method not supported"
    if isinstance(exc, PermissionError):
        return str(exc) or "method disabled"
    if isinstance(exc, ValueError):
        # Known validation failures use short symbolic messages in AGILANG.
        text = str(exc)
        if text and len(text) <= 160 and all(ch.isalnum() or ch in "_:- .{}[],'\"" for ch in text):
            return text
        return "invalid request parameters"
    return "internal RPC error"


class EthJsonRpcService(legacy.EthJsonRpcService):
    """Strict public RPC service.

    Only locally signed raw transactions may mutate chain state.  The legacy
    unsigned methods are never exposed because they trust a requester-supplied
    ``from`` address without cryptographic authorization.
    """

    def __init__(
        self,
        node: BlockchainNode,
        *,
        auto_mine: bool = False,
        expose_dev_send_transaction: bool = False,
        expose_txpool_content: bool = False,
    ) -> None:
        # Keep the legacy flag false even if a caller accidentally asks for it.
        super().__init__(node, auto_mine=auto_mine, expose_dev_send_transaction=False)
        self.expose_txpool_content = bool(expose_txpool_content)
        if expose_dev_send_transaction:
            raise ValueError("unsigned_transaction_methods_removed")

    def handle_many(self, payload: Any) -> Any:
        if isinstance(payload, list):
            if not payload:
                return _jsonrpc_error(None, -32600, "empty batch is invalid")
            if len(payload) > MAX_BATCH_SIZE:
                return _jsonrpc_error(None, -32600, "batch limit exceeded")
            responses = [self.handle_one(item) for item in payload]
            return [item for item in responses if item is not None]
        return self.handle_one(payload)

    def handle_one(self, request: Any) -> Dict[str, Any] | None:
        if not isinstance(request, dict):
            return _jsonrpc_error(None, -32600, "invalid request")
        request_id = request.get("id")
        is_notification = "id" not in request
        if request.get("jsonrpc") != JSONRPC_VERSION:
            return None if is_notification else _jsonrpc_error(request_id, -32600, "jsonrpc must be 2.0")
        method = request.get("method")
        params = request.get("params", [])
        if not isinstance(method, str) or not method:
            return None if is_notification else _jsonrpc_error(request_id, -32600, "method must be a string")
        if not isinstance(params, list):
            return None if is_notification else _jsonrpc_error(request_id, -32602, "params must be an array")
        try:
            result = self.dispatch(method, params)
            return None if is_notification else _jsonrpc_result(request_id, result)
        except NotImplementedError as exc:
            return None if is_notification else _jsonrpc_error(request_id, -32601, _safe_error_message(exc))
        except (PermissionError, ValueError, TypeError, IndexError) as exc:
            return None if is_notification else _jsonrpc_error(request_id, -32000, _safe_error_message(exc))
        except Exception as exc:
            # Never expose paths, stack traces, signing material, or database details.
            sys.stderr.write(f"rpc_internal_error:{type(exc).__name__}\n")
            return None if is_notification else _jsonrpc_error(request_id, -32603, "internal RPC error")

    def dispatch(self, method: str, params: list[Any]) -> Any:
        if method in {"eth_sendTransaction", "dev_sendTransaction", "sbq_sendTransaction"}:
            raise PermissionError("unsigned transaction methods are disabled; use eth_sendRawTransaction")
        if method == "txpool_content" and not self.expose_txpool_content:
            raise PermissionError("txpool_content is disabled on public RPC")
        if method in {"eth_call", "eth_estimateGas"}:
            raise NotImplementedError(
                f"{method} unavailable until stateful EVM call execution is enabled; refusing a false-success response"
            )
        if method == "eth_sendRawTransaction":
            if len(params) != 1 or not isinstance(params[0], str):
                raise ValueError("eth_sendRawTransaction expects one hex string")
            raw = params[0]
            raw_hex = raw[2:] if raw.startswith("0x") else raw
            if len(raw_hex) % 2 or len(raw_hex) // 2 > MAX_RAW_TRANSACTION_BYTES:
                raise ValueError("signed raw transaction size invalid")
        return super().dispatch(method, params)


def make_rpc_service(
    config: BlockchainConfig | Dict[str, Any] | None = None,
    *,
    db_path: str | Path = ":memory:",
    auto_mine: bool = False,
    expose_dev_send_transaction: bool = False,
) -> EthJsonRpcService:
    if expose_dev_send_transaction:
        raise ValueError("unsigned_transaction_methods_removed")
    return EthJsonRpcService(
        blockchain_node(config or blockchain_config(), db_path=db_path, node_id="rpc-node"),
        auto_mine=auto_mine,
    )


class LimitedThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 128

    def __init__(self, server_address: tuple[str, int], handler: type[BaseHTTPRequestHandler]):
        self._slots = threading.BoundedSemaphore(MAX_CONNECTIONS)
        super().__init__(server_address, handler)

    def process_request(self, request: socket.socket, client_address: tuple[str, int]) -> None:
        if not self._slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._slots.release()
            raise

    def process_request_thread(self, request: socket.socket, client_address: tuple[str, int]) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


def serve_json_rpc(
    node: BlockchainNode,
    *,
    host: str = "127.0.0.1",
    port: int = 8545,
    auto_mine: bool = False,
    expose_dev_send_transaction: bool = False,
) -> None:
    if expose_dev_send_transaction:
        raise ValueError("unsigned_transaction_methods_removed")
    service = EthJsonRpcService(node, auto_mine=auto_mine)
    cors_origin = os.getenv("AGILANG_RPC_CORS_ORIGIN", "").strip()

    class Handler(BaseHTTPRequestHandler):
        server_version = "AGILANG-RPC"
        sys_version = ""

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(SOCKET_TIMEOUT_SECONDS)

        def version_string(self) -> str:
            return "AGILANG-RPC"

        def _send_json(self, status: int, payload: Any) -> None:
            encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
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
            self.wfile.write(encoded)

        def do_OPTIONS(self) -> None:
            if not cors_origin:
                self._send_json(405, {"ok": False, "error": "cors_disabled"})
                return
            self._send_json(204, {})

        def do_GET(self) -> None:
            # Minimal liveness only; do not expose validators, peer topology, or head hash.
            self._send_json(
                200,
                {
                    "ok": True,
                    "client": f"AGILANG/{__version__}",
                    "chainId": hex(node.config.chain_id),
                    "blockNumber": hex(node.height()),
                },
            )

        def do_POST(self) -> None:
            try:
                if self.headers.get("Transfer-Encoding"):
                    self._send_json(400, _jsonrpc_error(None, -32600, "transfer encoding not supported"))
                    return
                content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                if content_type != "application/json":
                    self._send_json(415, _jsonrpc_error(None, -32600, "content type must be application/json"))
                    return
                raw_length = self.headers.get("Content-Length")
                if raw_length is None:
                    self._send_json(411, _jsonrpc_error(None, -32600, "content length required"))
                    return
                try:
                    length = int(raw_length)
                except ValueError:
                    self._send_json(400, _jsonrpc_error(None, -32600, "invalid content length"))
                    return
                if length < 1 or length > MAX_BODY_BYTES:
                    self._send_json(413, _jsonrpc_error(None, -32600, "request body size invalid"))
                    return
                raw = self.rfile.read(length)
                if len(raw) != length:
                    self._send_json(400, _jsonrpc_error(None, -32700, "incomplete JSON body"))
                    return
                try:
                    payload = json.loads(raw)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._send_json(400, _jsonrpc_error(None, -32700, "parse error"))
                    return
                response = service.handle_many(payload)
                if response is None or response == []:
                    self.send_response(204)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self._send_json(200, response)
            except (BrokenPipeError, ConnectionResetError, socket.timeout):
                return
            except Exception as exc:
                sys.stderr.write(f"rpc_http_internal_error:{type(exc).__name__}\n")
                self._send_json(500, _jsonrpc_error(None, -32603, "internal RPC error"))

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = LimitedThreadingHTTPServer((host, int(port)), Handler)
    print(f"AGILANG hardened JSON-RPC listening on http://{host}:{port} chain_id={node.config.chain_id}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run hardened AGILANG Ethereum JSON-RPC server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8545)
    parser.add_argument("--db", default=".agilang/chain.sqlite")
    parser.add_argument("--config", default="")
    parser.add_argument("--auto-mine", action="store_true")
    ns = parser.parse_args()
    node = node_from_rpc_config(ns.config, ns.db) if ns.config else blockchain_node(
        blockchain_mainnet_config(), db_path=ns.db, node_id="rpc-node"
    )
    serve_json_rpc(node, host=ns.host, port=ns.port, auto_mine=ns.auto_mine)


if __name__ == "__main__":
    main()
