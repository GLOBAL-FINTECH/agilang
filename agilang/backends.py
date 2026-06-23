"""Backend registry for AGILANG."""

from __future__ import annotations

SUPPORTED_BACKENDS = {
    "python": "Primary production runtime backend for web, ORM, jobs, security, WebSocket, WebRTC signaling, React/mobile integration, and hybrid native bridge orchestration.",
    "c": "Native C backend for a typed systems subset plus production-oriented native HTTP/WebSocket runtime source.",
    "native-c-http": "Compileable native C HTTP listener runtime.",
    "native-c-websocket": "Compileable native C WebSocket server runtime with handshake, frames, ping/pong, close, limits, origin/token hooks, broadcast, and ctypes-loadable ABI.",
    "hybrid-c-python": "AGILANG/AGILAB web runtime mode that cross-integrates Python WebApp features with a compiled native C HTTP/WebSocket transport runtime through ctypes.",
    "react-web": "Vite/React/TypeScript client scaffold with AGILANG realtime SDK.",
    "react-mobile": "React Native/Expo-style mobile scaffold with AGILANG realtime SDK.",
    "llvm": "Planned backend scaffold; use C backend today for native builds.",
    "wasm": "Planned backend scaffold; use C backend plus Emscripten externally today.",
}


def describe_backends() -> str:
    return "\n".join(f"{name}: {desc}" for name, desc in SUPPORTED_BACKENDS.items())
