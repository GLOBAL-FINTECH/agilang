# AGILANG v1.0 WebRTC, React, and Security Notes

## WebRTC package scope

AGILANG v1.0 adds WebRTC signaling primitives:

- `webrtc_signal_server()`
- `webrtc_peer()`
- `webrtc_room()`
- `webrtc_offer()`
- `webrtc_answer()`
- `webrtc_ice()`
- `parse_webrtc_signal()`

This is production-correct architecture: AGILANG coordinates signaling, while web/mobile clients use their native WebRTC engines for ICE, DTLS, SRTP, media tracks, and data channels.

## React support

AGILANG can scaffold:

```bash
agilang react web my-client
agilang react mobile my-mobile
agilang react sdk ./sdk
```

The generated TypeScript SDK includes:

- `AgiRealtimeClient`
- `AgiWebRTCSignaling`

## Native C WebSocket runtime

The C runtime now includes a real WebSocket server implementation with:

- SHA-1 + Base64 WebSocket accept calculation
- RFC 6455 handshake handling
- path validation
- origin and token hooks
- masked client frame validation
- text-frame parsing
- ping/pong
- close frame handling
- max-frame limit
- broadcast
- threaded client handling

TLS is expected at the reverse proxy layer via Nginx/Caddy.
