# Deploy AGILANG behind Caddy

```caddyfile
example.com {
    reverse_proxy 127.0.0.1:9000
}

realtime.example.com {
    reverse_proxy 127.0.0.1:9001
}
```

Caddy can manage HTTPS automatically. For WebSocket endpoints, `reverse_proxy` supports upgrade traffic by default.
