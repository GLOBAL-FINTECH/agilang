# AGILANG Native C HTTP/WebSocket Runtime

AGILANG v1.0 replaces the old WebSocket ABI placeholder with a compileable native C WebSocket runtime.

## Location

```text
native/agilang_net_runtime.h
native/agilang_net_runtime.c
```

## HTTP API

```c
typedef agi_http_response (*agi_http_handler)(agi_http_request request);
int agi_http_listen(const char *host, int port, agi_http_handler handler);
```

## WebSocket API

```c
typedef void (*agi_ws_message_handler)(agi_ws_peer *peer, const char *message, void *userdata);

typedef struct agi_ws_server_config {
    const char *host;
    int port;
    const char *path;
    const char *allowed_origin;
    const char *auth_token;
    size_t max_frame_bytes;
    int backlog;
    agi_ws_message_handler on_message;
    agi_ws_event_handler on_connect;
    agi_ws_event_handler on_disconnect;
    void *userdata;
} agi_ws_server_config;

int agi_ws_server_start(agi_ws_server **out, const agi_ws_server_config *config);
int agi_ws_server_stop(agi_ws_server *server);
int agi_ws_server_broadcast(agi_ws_server *server, const char *message);
int agi_ws_peer_send_text(agi_ws_peer *peer, const char *message);
int agi_ws_peer_close(agi_ws_peer *peer);
```

## Runtime behavior

Implemented:

- RFC 6455 upgrade handshake
- SHA-1 + Base64 `Sec-WebSocket-Accept`
- path validation
- optional origin check
- optional query-token check
- client-to-server masking validation
- text frames
- close frames
- ping/pong
- max-frame limits
- threaded peer handling
- broadcast
- backwards-compatible `agi_ws_listen()` and `agi_ws_broadcast()` API

## Compile check

```bash
gcc -std=c11 -Wall -Wextra -c native/agilang_net_runtime.c -o build/agilang_net_runtime.o -pthread
```

## Production deployment note

For internet-facing use, place the runtime behind Nginx or Caddy and terminate TLS there. The C runtime is deliberately focused on HTTP/WebSocket protocol handling; TLS, certificate renewal, WAF rules and public edge hardening belong at the proxy/load-balancer layer.
