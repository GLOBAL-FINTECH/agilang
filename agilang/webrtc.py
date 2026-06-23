"""AGILANG WebRTC signaling package.

This module implements the AGILANG-side WebRTC control plane: room membership,
offer/answer/ICE envelopes, and WebSocket signaling. Browsers and React Native
clients still use their own WebRTC engines for media and data channels; AGILANG
coordinates peers and secures the signaling path.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .realtime import WebSocketPeer, WebSocketServer, json_event, websocket_listen


class WebRTCError(RuntimeError):
    """Base error for AGILANG WebRTC signaling failures."""


@dataclass
class WebRTCPeer:
    """Application-level WebRTC peer identity used by the signaling layer."""

    peer_id: str = field(default_factory=lambda: secrets.token_hex(8))
    room: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    connected_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "peer_id": self.peer_id,
            "room": self.room,
            "metadata": dict(self.metadata),
            "connected_at": self.connected_at,
        }


@dataclass
class WebRTCSignal:
    """JSON serialisable WebRTC signaling envelope."""

    type: str
    from_peer: str
    to_peer: str | None = None
    room: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        data = {"type": self.type, "from": self.from_peer, "payload": dict(self.payload), "ts": self.ts}
        if self.to_peer is not None:
            data["to"] = self.to_peer
        if self.room is not None:
            data["room"] = self.room
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))


class WebRTCRoom:
    """In-process WebRTC room registry for AGILANG signaling servers."""

    def __init__(self, name: str):
        self.name = name
        self.peers: dict[str, WebRTCPeer] = {}
        self._sockets: dict[str, WebSocketPeer] = {}
        self._lock = threading.RLock()

    def join(self, peer: WebRTCPeer, socket_peer: WebSocketPeer | None = None) -> dict[str, Any]:
        with self._lock:
            peer.room = self.name
            self.peers[peer.peer_id] = peer
            if socket_peer is not None:
                self._sockets[peer.peer_id] = socket_peer
            return self.snapshot()

    def leave(self, peer_id: str) -> dict[str, Any]:
        with self._lock:
            self.peers.pop(peer_id, None)
            self._sockets.pop(peer_id, None)
            return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {"room": self.name, "peers": [p.to_dict() for p in self.peers.values()]}

    def send_to(self, peer_id: str, message: str | Mapping[str, Any]) -> bool:
        with self._lock:
            sock = self._sockets.get(peer_id)
        if sock is None:
            return False
        sock.send(dict(message) if isinstance(message, Mapping) else message)
        return True

    def broadcast(self, message: str | Mapping[str, Any], *, exclude: str | None = None) -> int:
        with self._lock:
            sockets = [(pid, sock) for pid, sock in self._sockets.items() if pid != exclude]
        delivered = 0
        for _, sock in sockets:
            try:
                sock.send(dict(message) if isinstance(message, Mapping) else message)
                delivered += 1
            except Exception:
                pass
        return delivered


class WebRTCSignalServer:
    """WebSocket-backed WebRTC signaling server.

    Supported messages:
      {"type":"webrtc.join","peer_id":"alice","room":"chat"}
      {"type":"webrtc.offer","from":"alice","to":"bob","payload":{"sdp":"..."}}
      {"type":"webrtc.answer", ...}
      {"type":"webrtc.ice", ...}
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        path: str = "/webrtc",
        *,
        auth_token: str | None = None,
        allowed_rooms: set[str] | None = None,
    ):
        self.server: WebSocketServer = websocket_listen(host, port, path)
        self.auth_token = auth_token
        self.allowed_rooms = allowed_rooms
        self.rooms: dict[str, WebRTCRoom] = {}
        self.peer_index: dict[WebSocketPeer, tuple[str, str]] = {}
        self._lock = threading.RLock()
        self._on_signal: Callable[[dict[str, Any]], None] | None = None
        self.server.on_message(self._handle_message)
        self.server.on_disconnect(self._handle_disconnect)

    @property
    def actual_port(self) -> int:
        return self.server.actual_port

    def on_signal(self, handler: Callable[[dict[str, Any]], None]) -> "WebRTCSignalServer":
        self._on_signal = handler
        return self

    def room(self, name: str) -> WebRTCRoom:
        with self._lock:
            self.rooms.setdefault(name, WebRTCRoom(name))
            return self.rooms[name]

    def run_background(self) -> "WebRTCSignalServer":
        self.server.run_background()
        return self

    def serve_forever(self) -> None:
        self.server.serve_forever()

    def stop(self) -> None:
        self.server.stop()

    def _authorize(self, data: Mapping[str, Any]) -> bool:
        if self.auth_token is None:
            return True
        return secrets.compare_digest(str(data.get("token", "")), self.auth_token)

    def _handle_message(self, client: WebSocketPeer, raw: str) -> None:
        try:
            data = json.loads(raw)
        except Exception:
            client.send(json_event("webrtc.error", {"error": "invalid_json"}, "webrtc"))
            return
        if not isinstance(data, dict):
            client.send(json_event("webrtc.error", {"error": "invalid_message"}, "webrtc"))
            return
        if not self._authorize(data):
            client.send(json_event("webrtc.error", {"error": "unauthorized"}, "webrtc"))
            client.close()
            return
        msg_type = str(data.get("type", ""))
        payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
        if msg_type == "webrtc.join":
            room_name = str(data.get("room") or payload.get("room") or "default")
            if self.allowed_rooms is not None and room_name not in self.allowed_rooms:
                client.send(json_event("webrtc.error", {"error": "room_not_allowed"}, "webrtc"))
                return
            peer_id = str(data.get("peer_id") or payload.get("peer_id") or secrets.token_hex(8))
            peer = WebRTCPeer(peer_id=peer_id, room=room_name, metadata=dict(data.get("metadata") or payload.get("metadata") or {}))
            room = self.room(room_name)
            snapshot = room.join(peer, client)
            self.peer_index[client] = (room_name, peer_id)
            room.broadcast(json_event("webrtc.peer_joined", {"peer": peer.to_dict(), "room": snapshot}, room_name), exclude=peer_id)
            client.send(json_event("webrtc.joined", {"peer": peer.to_dict(), "room": snapshot}, room_name))
            return

        payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
        room_name = str(data.get("room") or payload.get("room") or self.peer_index.get(client, ("default", ""))[0])
        from_peer = str(data.get("from") or payload.get("from") or self.peer_index.get(client, ("", secrets.token_hex(8)))[1])
        to_peer = data.get("to") or payload.get("to")
        signal = dict(data)
        signal.setdefault("from", from_peer)
        signal.setdefault("room", room_name)
        if self._on_signal:
            self._on_signal(signal)
        room = self.room(room_name)
        if to_peer:
            delivered = room.send_to(str(to_peer), signal)
            if not delivered:
                client.send(json_event("webrtc.error", {"error": "peer_not_found", "to": to_peer}, room_name))
        else:
            room.broadcast(signal, exclude=from_peer)

    def _handle_disconnect(self, client: WebSocketPeer) -> None:
        indexed = self.peer_index.pop(client, None)
        if not indexed:
            return
        room_name, peer_id = indexed
        room = self.room(room_name)
        snapshot = room.leave(peer_id)
        room.broadcast(json_event("webrtc.peer_left", {"peer_id": peer_id, "room": snapshot}, room_name))


def webrtc_peer(peer_id: str | None = None, metadata: Mapping[str, Any] | None = None) -> WebRTCPeer:
    return WebRTCPeer(peer_id=peer_id or secrets.token_hex(8), metadata=dict(metadata or {}))


def webrtc_room(name: str) -> WebRTCRoom:
    return WebRTCRoom(name)


def webrtc_signal(signal_type: str, from_peer: str, payload: Mapping[str, Any] | None = None, *, to_peer: str | None = None, room: str | None = None) -> str:
    return WebRTCSignal(type=signal_type, from_peer=from_peer, to_peer=to_peer, room=room, payload=dict(payload or {})).to_json()


def webrtc_offer(sdp: str, from_peer: str, *, to_peer: str | None = None, room: str | None = None) -> str:
    return webrtc_signal("webrtc.offer", from_peer, {"sdp": sdp}, to_peer=to_peer, room=room)


def webrtc_answer(sdp: str, from_peer: str, *, to_peer: str | None = None, room: str | None = None) -> str:
    return webrtc_signal("webrtc.answer", from_peer, {"sdp": sdp}, to_peer=to_peer, room=room)


def webrtc_ice(candidate: Mapping[str, Any], from_peer: str, *, to_peer: str | None = None, room: str | None = None) -> str:
    return webrtc_signal("webrtc.ice", from_peer, {"candidate": dict(candidate)}, to_peer=to_peer, room=room)


def parse_webrtc_signal(raw: str | bytes) -> dict[str, Any]:
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    data = json.loads(text)
    if not isinstance(data, dict):
        raise WebRTCError("WebRTC signal must be a JSON object")
    if "type" not in data:
        raise WebRTCError("WebRTC signal missing type")
    return data


def webrtc_signal_server(host: str = "127.0.0.1", port: int = 0, path: str = "/webrtc", *, auth_token: str | None = None) -> WebRTCSignalServer:
    return WebRTCSignalServer(host, port, path, auth_token=auth_token)


__all__ = [
    "WebRTCError", "WebRTCPeer", "WebRTCRoom", "WebRTCSignal", "WebRTCSignalServer",
    "webrtc_peer", "webrtc_room", "webrtc_signal", "webrtc_offer", "webrtc_answer",
    "webrtc_ice", "parse_webrtc_signal", "webrtc_signal_server",
]
