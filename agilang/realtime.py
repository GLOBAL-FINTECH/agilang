"""AGILANG realtime transport runtime.

This module provides a small, dependency-free WebSocket implementation for
AGILANG's Python runtime target. It is intentionally pragmatic: it supports
RFC 6455 text frames, close, ping/pong, broadcast, reconnectable clients,
realtime channels, an in-process pub/sub bus, and a JSON event envelope.

Production note: TLS (wss://), HTTP/2, compression extensions, horizontal
cluster fan-out, and backpressure tuning are intentionally left for the native
networking layer and framework adapters. The current runtime is suitable for
local services, tests, prototypes, dashboards, and language-level examples.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional
from urllib.parse import urlparse

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
DEFAULT_MAX_FRAME_BYTES = 1024 * 1024


class RealtimeError(RuntimeError):
    """Base error for AGILANG realtime transport failures."""


class WebSocketProtocolError(RealtimeError):
    """Raised when a peer sends an invalid WebSocket frame or handshake."""


@dataclass
class JsonEvent:
    """Structured realtime message envelope used by AGILANG examples/frameworks."""

    type: str
    payload: Any = None
    topic: str | None = None
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        data = {
            "id": self.event_id,
            "type": self.type,
            "ts": self.ts,
            "payload": self.payload,
        }
        if self.topic is not None:
            data["topic"] = self.topic
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str | bytes) -> "JsonEvent":
        data = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
        return cls(
            type=data.get("type", "message"),
            payload=data.get("payload"),
            topic=data.get("topic"),
            event_id=data.get("id", uuid.uuid4().hex),
            ts=data.get("ts", datetime.now(timezone.utc).isoformat()),
        )


def json_event(event_type: str, payload: Any = None, topic: str | None = None) -> str:
    """Create a compact JSON realtime event string."""

    return JsonEvent(type=event_type, payload=payload, topic=topic).to_json()


def parse_json_event(raw: str | bytes) -> dict[str, Any]:
    """Parse a JSON event and return a normal dictionary for AGILANG scripts."""

    return JsonEvent.from_json(raw).to_dict()


def _read_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("WebSocket peer closed the connection")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _encode_frame(payload: str | bytes, *, opcode: int = 0x1, mask: bool = False) -> bytes:
    if isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
    else:
        payload_bytes = payload

    length = len(payload_bytes)
    first = 0x80 | opcode
    mask_bit = 0x80 if mask else 0
    if length < 126:
        header = struct.pack("!BB", first, mask_bit | length)
    elif length <= 0xFFFF:
        header = struct.pack("!BBH", first, mask_bit | 126, length)
    else:
        header = struct.pack("!BBQ", first, mask_bit | 127, length)

    if not mask:
        return header + payload_bytes

    masking_key = os.urandom(4)
    masked = bytes(byte ^ masking_key[i % 4] for i, byte in enumerate(payload_bytes))
    return header + masking_key + masked


def _read_frame(sock: socket.socket, *, max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES) -> tuple[int, bytes]:
    b1, b2 = _read_exact(sock, 2)
    fin = b1 & 0x80
    opcode = b1 & 0x0F
    masked = b2 & 0x80
    length = b2 & 0x7F

    if not fin:
        raise WebSocketProtocolError("Fragmented frames are not supported by this runtime yet")
    if length == 126:
        length = struct.unpack("!H", _read_exact(sock, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", _read_exact(sock, 8))[0]
    if length > max_frame_bytes:
        raise WebSocketProtocolError(f"Frame too large: {length} bytes")

    masking_key = _read_exact(sock, 4) if masked else b""
    payload = _read_exact(sock, length) if length else b""
    if masked:
        payload = bytes(byte ^ masking_key[i % 4] for i, byte in enumerate(payload))
    return opcode, payload


def _parse_headers(raw: bytes) -> tuple[str, dict[str, str]]:
    text = raw.decode("iso-8859-1")
    lines = text.split("\r\n")
    start_line = lines[0]
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line or ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()
    return start_line, headers


def _read_http_header(sock: socket.socket, limit: int = 65536) -> bytes:
    data = bytearray()
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(1024)
        if not chunk:
            raise ConnectionError("Connection closed during WebSocket handshake")
        data.extend(chunk)
        if len(data) > limit:
            raise WebSocketProtocolError("Handshake header is too large")
    return bytes(data)


class WebSocketPeer:
    """A connected WebSocket peer shared by server-side and client-side code."""

    def __init__(self, sock: socket.socket, *, address: Any = None, client_mode: bool = False, max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES):
        self.sock = sock
        self.address = address
        self.client_mode = client_mode
        self.max_frame_bytes = max_frame_bytes
        self.connected = True
        self._send_lock = threading.Lock()

    def send(self, message: str | bytes | dict[str, Any]) -> None:
        if not self.connected:
            raise ConnectionError("WebSocket peer is not connected")
        if isinstance(message, dict):
            message = json.dumps(message, separators=(",", ":"))
        frame = _encode_frame(message, opcode=0x1, mask=self.client_mode)
        with self._send_lock:
            self.sock.sendall(frame)

    def receive(self, timeout: float | None = None) -> str | None:
        old_timeout = self.sock.gettimeout()
        if timeout is not None:
            self.sock.settimeout(timeout)
        try:
            while self.connected:
                opcode, payload = _read_frame(self.sock, max_frame_bytes=self.max_frame_bytes)
                if opcode == 0x1:  # text
                    return payload.decode("utf-8")
                if opcode == 0x2:  # binary; expose as UTF-8 if possible
                    return payload.decode("utf-8", errors="replace")
                if opcode == 0x8:  # close
                    self.connected = False
                    try:
                        self.sock.sendall(_encode_frame(b"", opcode=0x8, mask=self.client_mode))
                    except Exception:
                        pass
                    return None
                if opcode == 0x9:  # ping
                    with self._send_lock:
                        self.sock.sendall(_encode_frame(payload, opcode=0xA, mask=self.client_mode))
                    continue
                if opcode == 0xA:  # pong
                    continue
                raise WebSocketProtocolError(f"Unsupported opcode: {opcode}")
            return None
        finally:
            if timeout is not None:
                self.sock.settimeout(old_timeout)

    def close(self) -> None:
        if not self.connected:
            return
        self.connected = False
        try:
            with self._send_lock:
                self.sock.sendall(_encode_frame(b"", opcode=0x8, mask=self.client_mode))
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


class PubSubBus:
    """In-process topic pub/sub used by AGILANG realtime services."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Any], None]]] = {}
        self._lock = threading.RLock()

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> Callable[[], None]:
        with self._lock:
            self._subscribers.setdefault(topic, []).append(handler)

        def unsubscribe() -> None:
            with self._lock:
                handlers = self._subscribers.get(topic, [])
                if handler in handlers:
                    handlers.remove(handler)

        return unsubscribe

    def publish(self, topic: str, payload: Any) -> int:
        with self._lock:
            handlers = list(self._subscribers.get(topic, []))
            wildcard = list(self._subscribers.get("*", []))
        for handler in handlers + wildcard:
            handler(payload)
        return len(handlers) + len(wildcard)

    def topics(self) -> list[str]:
        with self._lock:
            return sorted(self._subscribers.keys())


class RealtimeChannel:
    """Named realtime channel that can publish locally and/or over a WebSocket server."""

    def __init__(self, name: str, *, bus: PubSubBus | None = None, server: "WebSocketServer" | None = None):
        self.name = name
        self.bus = bus or PubSubBus()
        self.server = server

    def subscribe(self, handler: Callable[[Any], None]) -> Callable[[], None]:
        return self.bus.subscribe(self.name, handler)

    def publish(self, payload: Any) -> int:
        delivered = self.bus.publish(self.name, payload)
        if self.server is not None:
            self.server.publish(self.name, payload)
        return delivered


class WebSocketServer:
    """Native AGILANG WebSocket server for realtime scripts and frameworks."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0, *, path: str = "/", max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES):
        self.host = host
        self.port = int(port)
        self.path = path if path.startswith("/") else f"/{path}"
        self.max_frame_bytes = max_frame_bytes
        self.bus = PubSubBus()
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = threading.Event()
        self._clients: set[WebSocketPeer] = set()
        self._clients_lock = threading.RLock()
        self._on_connect: Callable[[WebSocketPeer], None] | None = None
        self._on_message: Callable[[WebSocketPeer, str], None] | None = None
        self._on_disconnect: Callable[[WebSocketPeer], None] | None = None
        self._on_error: Callable[[Exception], None] | None = None

    @property
    def actual_port(self) -> int:
        if self._sock is None:
            return self.port
        return int(self._sock.getsockname()[1])

    @property
    def clients_count(self) -> int:
        with self._clients_lock:
            return len(self._clients)

    def on_connect(self, handler: Callable[[WebSocketPeer], None]) -> "WebSocketServer":
        self._on_connect = handler
        return self

    def on_message(self, handler: Callable[[WebSocketPeer, str], None]) -> "WebSocketServer":
        self._on_message = handler
        return self

    def on_disconnect(self, handler: Callable[[WebSocketPeer], None]) -> "WebSocketServer":
        self._on_disconnect = handler
        return self

    def on_error(self, handler: Callable[[Exception], None]) -> "WebSocketServer":
        self._on_error = handler
        return self

    def channel(self, name: str) -> RealtimeChannel:
        return RealtimeChannel(name, bus=self.bus, server=self)

    def run_background(self) -> "WebSocketServer":
        if self._thread and self._thread.is_alive():
            return self
        self._start_socket()
        self._running.set()
        self._thread = threading.Thread(target=self._accept_loop, name="agilang-ws-server", daemon=True)
        self._thread.start()
        return self

    def serve_forever(self) -> None:
        self._start_socket()
        self._running.set()
        self._accept_loop()

    def run_forever(self) -> None:
        self.serve_forever()

    def stop(self) -> None:
        self._running.clear()
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
        with self._clients_lock:
            clients = list(self._clients)
        for client in clients:
            client.close()
        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=1.0)

    def broadcast(self, message: str | bytes | dict[str, Any]) -> int:
        with self._clients_lock:
            clients = list(self._clients)
        delivered = 0
        for client in clients:
            try:
                client.send(message)
                delivered += 1
            except Exception as exc:
                self._handle_error(exc)
                client.close()
        return delivered

    def publish(self, topic: str, payload: Any) -> int:
        local = self.bus.publish(topic, payload)
        remote = self.broadcast(JsonEvent(type="pubsub.message", topic=topic, payload=payload).to_json())
        return local + remote

    def _start_socket(self) -> None:
        if self._sock is not None:
            return
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(128)
        self._sock.settimeout(0.2)

    def _accept_loop(self) -> None:
        assert self._sock is not None
        while self._running.is_set():
            try:
                conn, addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            thread = threading.Thread(target=self._client_loop, args=(conn, addr), name="agilang-ws-client", daemon=True)
            thread.start()

    def _client_loop(self, conn: socket.socket, addr: Any) -> None:
        peer: WebSocketPeer | None = None
        try:
            self._server_handshake(conn)
            peer = WebSocketPeer(conn, address=addr, client_mode=False, max_frame_bytes=self.max_frame_bytes)
            with self._clients_lock:
                self._clients.add(peer)
            if self._on_connect:
                self._on_connect(peer)
            while self._running.is_set() and peer.connected:
                message = peer.receive()
                if message is None:
                    break
                if self._on_message:
                    self._on_message(peer, message)
        except Exception as exc:
            self._handle_error(exc)
        finally:
            if peer is not None:
                peer.connected = False
                with self._clients_lock:
                    self._clients.discard(peer)
                if self._on_disconnect:
                    try:
                        self._on_disconnect(peer)
                    except Exception as exc:
                        self._handle_error(exc)
                try:
                    conn.close()
                except Exception:
                    pass

    def _server_handshake(self, conn: socket.socket) -> None:
        raw = _read_http_header(conn)
        start_line, headers = _parse_headers(raw)
        parts = start_line.split()
        if len(parts) < 3 or parts[0].upper() != "GET":
            raise WebSocketProtocolError("Invalid WebSocket handshake request")
        request_path = parts[1].split("?", 1)[0]
        if request_path != self.path:
            response = b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n"
            conn.sendall(response)
            raise WebSocketProtocolError(f"Unexpected WebSocket path: {request_path}")
        key = headers.get("sec-websocket-key")
        if not key:
            raise WebSocketProtocolError("Missing Sec-WebSocket-Key header")
        accept = base64.b64encode(hashlib.sha1((key + GUID).encode("ascii")).digest()).decode("ascii")
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        ).encode("ascii")
        conn.sendall(response)

    def _handle_error(self, exc: Exception) -> None:
        if self._on_error:
            try:
                self._on_error(exc)
                return
            except Exception:
                pass


class WebSocketClient:
    """AGILANG WebSocket client with explicit reconnect support."""

    def __init__(self, url: str, *, timeout: float = 5.0, max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES):
        self.url = url
        self.timeout = timeout
        self.max_frame_bytes = max_frame_bytes
        self.peer: WebSocketPeer | None = None

    @property
    def connected(self) -> bool:
        return bool(self.peer and self.peer.connected)

    def connect(self) -> "WebSocketClient":
        parsed = urlparse(self.url)
        if parsed.scheme != "ws":
            raise ValueError("Only ws:// URLs are supported by the stdlib runtime. Use a TLS proxy for wss://.")
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        sock = socket.create_connection((host, port), timeout=self.timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        ).encode("ascii")
        sock.sendall(request)
        raw = _read_http_header(sock)
        start_line, headers = _parse_headers(raw)
        if " 101 " not in f" {start_line} ":
            raise WebSocketProtocolError(f"WebSocket server rejected handshake: {start_line}")
        expected = base64.b64encode(hashlib.sha1((key + GUID).encode("ascii")).digest()).decode("ascii")
        if headers.get("sec-websocket-accept") != expected:
            raise WebSocketProtocolError("Invalid Sec-WebSocket-Accept response")
        sock.settimeout(None)
        self.peer = WebSocketPeer(sock, client_mode=True, max_frame_bytes=self.max_frame_bytes)
        return self

    def reconnect(self, *, delay: float = 0.1, attempts: int = 3) -> "WebSocketClient":
        self.close()
        last_error: Exception | None = None
        for _ in range(max(1, attempts)):
            try:
                return self.connect()
            except Exception as exc:
                last_error = exc
                time.sleep(delay)
        assert last_error is not None
        raise last_error

    def send(self, message: str | bytes | dict[str, Any]) -> None:
        if not self.peer:
            raise ConnectionError("WebSocket client is not connected")
        self.peer.send(message)

    def receive(self, timeout: float | None = None) -> str | None:
        if not self.peer:
            raise ConnectionError("WebSocket client is not connected")
        return self.peer.receive(timeout=timeout)

    def close(self) -> None:
        if self.peer:
            self.peer.close()
            self.peer = None


def websocket_listen(host: str = "127.0.0.1", port: int = 0, path: str = "/") -> WebSocketServer:
    """Create a WebSocket server. Call `.run_background()` or `.serve_forever()`."""

    return WebSocketServer(host, port, path=path)


def websocket_connect(url: str, timeout: float = 5.0) -> WebSocketClient:
    """Connect to a WebSocket server and return a client."""

    return WebSocketClient(url, timeout=timeout).connect()


def pubsub_bus() -> PubSubBus:
    """Create an in-process pub/sub bus."""

    return PubSubBus()


def realtime_channel(name: str) -> RealtimeChannel:
    """Create a standalone realtime channel."""

    return RealtimeChannel(name)


__all__ = [
    "JsonEvent",
    "PubSubBus",
    "RealtimeChannel",
    "RealtimeError",
    "WebSocketClient",
    "WebSocketPeer",
    "WebSocketProtocolError",
    "WebSocketServer",
    "json_event",
    "parse_json_event",
    "pubsub_bus",
    "realtime_channel",
    "websocket_connect",
    "websocket_listen",
]
