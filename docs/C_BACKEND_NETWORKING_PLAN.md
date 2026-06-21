# C Backend Networking and Web Runtime Plan

AGILANG v0.8 has working HTTP and WebSocket support on the Python runtime backend. The C backend still targets a safe native subset and does not yet compile networking-enabled binaries.

## Current backend matrix

| Capability | Python backend | C backend |
|---|---:|---:|
| Core functions | Working | Working subset |
| Arithmetic / typed lets | Working | Working subset |
| Print / return | Working | Working subset |
| WebSocket server/client | Working | Planned |
| Pub/sub channels | Working | Planned |
| HTTP server/router | Working | Planned |
| Static files/templates | Working | Planned |
| TLS | External proxy recommended | Planned via OpenSSL/BoringSSL adapter |

## Native networking roadmap

### Phase 1: C socket runtime

- `agi_net_tcp_listen(host, port)`
- `agi_net_tcp_accept(server)`
- `agi_net_tcp_connect(host, port)`
- `agi_net_send(socket, bytes)`
- `agi_net_recv(socket, max_bytes)`
- Windows Winsock and POSIX socket compatibility.

### Phase 2: HTTP runtime

- Request parser with method/path/query/headers/body.
- Response writer with status/headers/body.
- Static file streaming.
- Router table generated from AGILANG route declarations.

### Phase 3: WebSocket runtime

- RFC 6455 handshake.
- Text frames.
- Close, ping, pong.
- Broadcast groups.
- Max frame size limits.
- Backpressure and slow-client handling.

### Phase 4: Security and deployment

- TLS termination guidance first through Nginx/Caddy/HAProxy.
- Optional OpenSSL adapter later.
- Rate limiting.
- Request body limits.
- Header limits.
- Origin checks for WebSocket endpoints.
- Auth middleware hooks.

## Recommended production deployment today

For AGILANG v0.8 production-like prototypes:

```text
Browser / API client
    ↓
Nginx / Caddy / HAProxy for TLS, gzip, rate limits
    ↓
AGILANG Python runtime HTTP/WebSocket app
    ↓
SQLite/Postgres/Redis/etc. through Python adapters
```

## Native target rule

Do not claim C-native HTTP/WebSocket support until the C runtime implements socket lifecycle, HTTP parsing, WebSocket framing, and platform-specific event loops.
