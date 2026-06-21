"""AGILANG v1.7 low-level networking primitives.

This module intentionally uses Python's standard library only.  It gives
AGILANG a small systems-level networking surface that can later be lowered to
native C, while remaining immediately usable from the Python backend.
"""
from __future__ import annotations

import json
import socket
import struct
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

NETWORK_VERSION = "1.7.0"


@dataclass(frozen=True)
class NetAddress:
    host: str
    port: int

    def as_tuple(self) -> tuple[str, int]:
        return (self.host, int(self.port))

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"


class PacketCodec:
    """Length-prefixed JSON/binary framing helper.

    The frame format is a 4-byte unsigned big-endian payload length followed by
    raw bytes.  JSON helpers encode dictionaries/lists as UTF-8 JSON inside the
    frame.  This is deliberately simple so the same format can be implemented
    in C, mobile bridges, and other AGILANG runtimes.
    """

    HEADER = struct.Struct("!I")

    @classmethod
    def frame(cls, payload: bytes | str | dict[str, Any] | list[Any]) -> bytes:
        if isinstance(payload, (dict, list)):
            raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        elif isinstance(payload, str):
            raw = payload.encode("utf-8")
        else:
            raw = bytes(payload)
        return cls.HEADER.pack(len(raw)) + raw

    @classmethod
    def unframe(cls, data: bytes) -> tuple[bytes, bytes]:
        if len(data) < cls.HEADER.size:
            raise ValueError("frame is incomplete: missing length header")
        (size,) = cls.HEADER.unpack(data[: cls.HEADER.size])
        end = cls.HEADER.size + size
        if len(data) < end:
            raise ValueError("frame is incomplete: payload shorter than declared length")
        return data[cls.HEADER.size:end], data[end:]

    @classmethod
    def json_frame(cls, event_type: str, payload: Any = None, *, topic: str | None = None) -> bytes:
        return cls.frame({"type": event_type, "topic": topic, "payload": payload, "ts": time.time()})

    @classmethod
    def json_unframe(cls, data: bytes) -> tuple[dict[str, Any], bytes]:
        raw, rest = cls.unframe(data)
        return json.loads(raw.decode("utf-8")), rest


def net_address(host: str, port: int) -> NetAddress:
    return NetAddress(host, int(port))


def packet_frame(payload: bytes | str | dict[str, Any] | list[Any]) -> bytes:
    return PacketCodec.frame(payload)


def packet_unframe(data: bytes) -> bytes:
    payload, _ = PacketCodec.unframe(data)
    return payload


def packet_json(event_type: str, payload: Any = None, topic: str | None = None) -> bytes:
    return PacketCodec.json_frame(event_type, payload, topic=topic)


def packet_json_parse(data: bytes) -> dict[str, Any]:
    event, _ = PacketCodec.json_unframe(data)
    return event


class TCPConnection:
    def __init__(self, sock: socket.socket, address: tuple[str, int] | None = None, timeout: float | None = None) -> None:
        self.sock = sock
        self.address = address
        if timeout is not None:
            self.sock.settimeout(timeout)

    def send(self, data: bytes | str) -> int:
        raw = data.encode("utf-8") if isinstance(data, str) else data
        self.sock.sendall(raw)
        return len(raw)

    def send_frame(self, payload: bytes | str | dict[str, Any] | list[Any]) -> int:
        raw = PacketCodec.frame(payload)
        self.sock.sendall(raw)
        return len(raw)

    def recv(self, size: int = 4096) -> bytes:
        return self.sock.recv(size)

    def recv_text(self, size: int = 4096) -> str:
        return self.recv(size).decode("utf-8", errors="replace")

    def recv_frame(self, max_size: int = 16 * 1024 * 1024) -> bytes:
        header = self._recv_exact(PacketCodec.HEADER.size)
        (size,) = PacketCodec.HEADER.unpack(header)
        if size > max_size:
            raise ValueError(f"frame too large: {size} > {max_size}")
        return self._recv_exact(size)

    def recv_json_frame(self) -> dict[str, Any]:
        return json.loads(self.recv_frame().decode("utf-8"))

    def _recv_exact(self, size: int) -> bytes:
        chunks: list[bytes] = []
        remaining = size
        while remaining > 0:
            chunk = self.sock.recv(remaining)
            if not chunk:
                raise ConnectionError("connection closed before enough bytes were received")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def close(self) -> None:
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()


class TCPServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0, *, backlog: int = 64) -> None:
        self.host = host
        self.port = int(port)
        self.backlog = backlog
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._handler: Callable[[TCPConnection], Any] | None = None
        self._clients: list[TCPConnection] = []

    @property
    def actual_port(self) -> int:
        if self._sock is None:
            return self.port
        return int(self._sock.getsockname()[1])

    @property
    def address(self) -> NetAddress:
        return NetAddress(self.host, self.actual_port)

    def on_client(self, handler: Callable[[TCPConnection], Any]) -> "TCPServer":
        self._handler = handler
        return self

    def listen(self) -> "TCPServer":
        if self._sock is not None:
            return self
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(self.backlog)
        sock.settimeout(0.2)
        self._sock = sock
        return self

    def serve_forever(self) -> None:
        self.listen()
        assert self._sock is not None
        while not self._stop.is_set():
            try:
                client_sock, address = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            conn = TCPConnection(client_sock, address)
            self._clients.append(conn)
            if self._handler:
                threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def _handle_client(self, conn: TCPConnection) -> None:
        try:
            self._handler(conn)  # type: ignore[misc]
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def run_background(self) -> "TCPServer":
        self.listen()
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)
        self._thread.start()
        return self

    def broadcast(self, data: bytes | str) -> int:
        delivered = 0
        for client in list(self._clients):
            try:
                client.send(data)
                delivered += 1
            except OSError:
                try:
                    client.close()
                except OSError:
                    pass
                self._clients.remove(client)
        return delivered

    def stop(self) -> None:
        self._stop.set()
        for client in list(self._clients):
            try:
                client.close()
            except OSError:
                pass
        self._clients.clear()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)


def tcp_listen(host: str = "127.0.0.1", port: int = 0, handler: Callable[[TCPConnection], Any] | None = None) -> TCPServer:
    server = TCPServer(host, int(port))
    if handler is not None:
        server.on_client(handler)
    return server


def tcp_connect(host: str, port: int, timeout: float = 5.0) -> TCPConnection:
    sock = socket.create_connection((host, int(port)), timeout=timeout)
    return TCPConnection(sock, (host, int(port)), timeout=timeout)


class UDPSocket:
    def __init__(self, host: str = "127.0.0.1", port: int = 0, *, broadcast: bool = False) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if broadcast:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind((host, int(port)))
        self.sock.settimeout(1.0)

    @property
    def address(self) -> NetAddress:
        host, port = self.sock.getsockname()[:2]
        return NetAddress(str(host), int(port))

    def send_to(self, data: bytes | str | dict[str, Any], host: str, port: int) -> int:
        if isinstance(data, dict):
            raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
        elif isinstance(data, str):
            raw = data.encode("utf-8")
        else:
            raw = data
        return self.sock.sendto(raw, (host, int(port)))

    def recv_from(self, size: int = 65535, timeout: float | None = None) -> tuple[bytes, NetAddress]:
        old_timeout = self.sock.gettimeout()
        if timeout is not None:
            self.sock.settimeout(timeout)
        try:
            data, address = self.sock.recvfrom(size)
            return data, NetAddress(str(address[0]), int(address[1]))
        finally:
            if timeout is not None:
                self.sock.settimeout(old_timeout)

    def close(self) -> None:
        self.sock.close()


def udp_socket(host: str = "127.0.0.1", port: int = 0, broadcast: bool = False) -> UDPSocket:
    return UDPSocket(host, int(port), broadcast=broadcast)


class GossipNode:
    """Tiny UDP gossip node for local/distributed experiments.

    This is not a consensus engine.  It is a primitive for peer discovery and
    event propagation that can be used to prototype blockchain, clustering, and
    realtime systems.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0, *, node_id: str | None = None, seeds: list[tuple[str, int]] | None = None) -> None:
        self.node_id = node_id or f"agi-{uuid.uuid4().hex[:12]}"
        self.udp = UDPSocket(host, int(port))
        self.peers: set[tuple[str, int]] = set((h, int(p)) for h, p in (seeds or []))
        self._seen: set[str] = set()
        self._handlers: list[Callable[[dict[str, Any]], Any]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def address(self) -> NetAddress:
        return self.udp.address

    def on_event(self, handler: Callable[[dict[str, Any]], Any]) -> "GossipNode":
        self._handlers.append(handler)
        return self

    def start(self) -> "GossipNode":
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.announce()
        return self

    def announce(self) -> str:
        return self.publish("peer.hello", {"node_id": self.node_id, "address": str(self.address)})

    def publish(self, event_type: str, payload: Any = None) -> str:
        event_id = uuid.uuid4().hex
        event = {"id": event_id, "type": event_type, "from": self.node_id, "payload": payload, "ts": time.time()}
        self._seen.add(event_id)
        raw = json.dumps(event, separators=(",", ":"))
        for host, port in list(self.peers):
            try:
                self.udp.send_to(raw, host, port)
            except OSError:
                pass
        return event_id

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                raw, source = self.udp.recv_from(timeout=0.2)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                event = json.loads(raw.decode("utf-8"))
            except Exception:
                continue
            self.peers.add(source.as_tuple())
            event_id = str(event.get("id", ""))
            if not event_id or event_id in self._seen:
                continue
            self._seen.add(event_id)
            for handler in list(self._handlers):
                handler(event)
            for host, port in list(self.peers):
                if (host, port) != source.as_tuple():
                    try:
                        self.udp.send_to(raw, host, port)
                    except OSError:
                        pass

    def stop(self) -> None:
        self._stop.set()
        self.udp.close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)


def gossip_node(host: str = "127.0.0.1", port: int = 0, node_id: str | None = None, seeds: list[tuple[str, int]] | None = None) -> GossipNode:
    return GossipNode(host, int(port), node_id=node_id, seeds=seeds)


def lowlevel_network_capabilities() -> dict[str, Any]:
    return {
        "version": NETWORK_VERSION,
        "tcp_client": True,
        "tcp_server": True,
        "udp_socket": True,
        "packet_framing": True,
        "json_event_framing": True,
        "gossip_udp": True,
        "stdlib_only": True,
        "native_c_lowering_planned": True,
    }
