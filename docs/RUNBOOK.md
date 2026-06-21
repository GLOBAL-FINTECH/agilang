# AGILANG Operations Runbook

## Common development commands

```bash
python -m pip install -e .
agilang --version
agilang doctor
agilang check examples
agilang test-examples
pytest
```

## Run the secure React/mobile backend

```bash
agilang run examples/react_mobile_backend.agi
```

Connect clients to:

```text
ws://127.0.0.1:9000/realtime
```

## Run WebRTC signaling

```bash
agilang run examples/webrtc_signaling.agi
```

For a long-running signaling service, use a file that calls:

```agi
webrtc_signal_server("127.0.0.1", 9000, "/webrtc").serve_forever()
```

## Generate React clients

```bash
agilang react web web-client
agilang react mobile mobile-client
agilang react sdk ./sdk
```

## Security checklist

Before production:

1. Put AGILANG behind Nginx/Caddy with HTTPS and WSS.
2. Enable `security_headers()`.
3. Enable `body_limit()`.
4. Enable `rate_limit()`.
5. Use strong secrets from environment variables.
6. Use CSRF protection on browser form routes.
7. Use auth middleware on private APIs.
8. Validate every request body.
9. Log failed authentication and rate-limit events.
10. Keep WebRTC signaling tokens short-lived.

## Native C runtime compile check

```bash
mkdir -p build
gcc -std=c11 -Wall -Wextra -c native/agilang_net_runtime.c -o build/agilang_net_runtime.o -pthread
```

## Deployment with Nginx

See `deployment/NGINX.md`. WebSocket proxying must include `Upgrade` and `Connection` headers.

## Deployment with Caddy

See `deployment/CADDY.md`. Caddy automatically manages TLS for supported public domains.

## Troubleshooting

### WebSocket connects locally but not in production

Check:

- TLS certificate is valid.
- Reverse proxy forwards `Upgrade` and `Connection` headers.
- The backend is listening on localhost and the expected port.
- Firewall allows 443.
- The frontend uses `wss://`, not `ws://`, on HTTPS pages.

### WebRTC peers join but media does not connect

AGILANG only handles signaling. Check:

- Browser permission for camera/microphone.
- ICE servers/STUN/TURN configuration in the React app.
- NAT/firewall conditions.
- Whether corporate/mobile networks require TURN relay.

### Rate limiter blocks too aggressively

Tune:

```agi
app.before(rate_limit(300, 60))
```

For multiple server processes, replace the in-memory limiter with Redis or another shared store.
