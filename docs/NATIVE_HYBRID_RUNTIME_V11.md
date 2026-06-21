# AGILANG v1.1 Native Hybrid Web Runtime

AGILANG v1.1 introduces a cross-integrated **C + Python web runtime**.  The goal is practical production deployment today while preparing the compiler for deeper native lowering later.

## Runtime modes

| Mode | Purpose |
|---|---|
| `python` | Full AGILANG web platform: routing, ORM, migrations, auth, CSRF, validation, jobs, WebSockets, WebRTC signaling, React/mobile support. |
| `native-c` | Native C HTTP/WebSocket transport ABI for low-level servers and future direct compiler lowering. |
| `hybrid` | Recommended mode: Python runs the full framework while the C runtime is compiled/loaded as the native transport layer. |

## AGILANG API

```agi
fn main() -> i32:
    let runtime = agilab_web_runtime("hybrid")
    let caps = runtime.capabilities()
    print(caps["mode"])
    print(caps["python_http"])
    print(caps["c_websocket"])
    return 0
```

Available functions:

```text
hybrid_web_runtime(mode, auto_build_native=False)
native_web_runtime(auto_build=True)
native_runtime_status(build=False)
native_runtime_available()
agilab_web_runtime(mode, auto_build_native=False)
agilab_native_runtime(auto_build=True)
```

`AGILANG` remains the language name. `AGILAB` aliases are provided for branded runtime/application deployments.

## CLI

```bash
agilang runtime status
agilang runtime status --build
agilang runtime build -o build/native
agilang runtime doctor
```

`runtime doctor` builds the C runtime, loads it through Python `ctypes`, checks exported ABI functions, and runs a WebSocket SHA-1 accept-key self-test.

## Native ABI additions

The C runtime now exposes:

```c
const char *agi_net_runtime_version(void);
const char *agi_net_runtime_capabilities(void);
int agi_net_runtime_selftest(void);
```

Existing HTTP/WebSocket functions remain available:

```c
int agi_http_listen(const char *host, int port, agi_http_handler handler);
int agi_ws_server_start(agi_ws_server **out, const agi_ws_server_config *config);
int agi_ws_server_stop(agi_ws_server *server);
int agi_ws_server_broadcast(agi_ws_server *server, const char *message);
```

## Production deployment pattern

Recommended deployment today:

```text
Internet
  ↓
Nginx/Caddy TLS termination
  ↓
AGILANG Python web platform for full framework features
  ↓
Native C runtime loaded for native transport ABI / edge-websocket path
```

Future compiler direction:

```text
AGILANG source
  ↓
AGILANG AST + type checker
  ↓
Native web IR
  ↓
C runtime calls / static native binary
```

## Current boundary

v1.1 is a real bridge: Python can compile, load, inspect, and call the C runtime ABI.  Full automatic compilation of every high-level web route, ORM model, WebRTC signaling handler, and middleware stack into a single standalone C binary is still the next compiler/runtime pass.
