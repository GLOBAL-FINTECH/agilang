# AGILANG Programming Book

Version: **1.0 Secure Realtime + React Platform Edition**

This book is a practical guide for using AGILANG as a small production-oriented language toolkit. AGILANG currently targets Python for the full web/realtime platform and C for the native subset plus native networking runtime.

## 1. Install and verify

```bash
python -m pip install -e .
agilang --version
agilang doctor
agilang test-examples
```

## 2. Hello world

```agi
fn main() -> i32:
    print("Hello from AGILANG")
    return 0
```

Run it:

```bash
agilang run examples/hello.agi
```

## 3. Variables, functions, and types

```agi
type Money = f64

fn fee(amount: Money) -> Money:
    return amount * 0.025

fn main() -> i32:
    let total = fee(1000.0)
    print(total)
    return 0
```

Useful checks:

```bash
agilang check examples
agilang typecheck examples
agilang ast examples/hello.agi --pretty
agilang tokens examples/hello.agi
```

## 4. Building

Python backend launcher:

```bash
agilang build examples/hello.agi -o build/hello.py
python build/hello.py
```

Native C subset:

```bash
agilang to-c examples/native_hello.agi -o build/native_hello.c
agilang native-build examples/native_hello.agi -o build/native_hello
```

## 5. Web apps

```agi
fn create_app():
    let app = web_app("demo", True)

    fn home(request):
        return html_response("<h1>AGILANG Web</h1>")

    fn api(request):
        return json_response({"ok": True})

    app.get("/", home)
    app.get("/api", api)
    return app
```

Serve:

```bash
agilang serve examples/web_basic.agi --host 127.0.0.1 --port 8000
```

## 6. ORM and migrations

```agi
fn main() -> i32:
    let db = sqlite_db("app.db")
    let User = model("User", {
        "id": integer(primary_key=True, nullable=False),
        "email": string(nullable=False, unique=True),
        "name": string(nullable=False)
    })

    fn create_users(db):
        User.create_table(db)

    migrate(db, [("001_create_users", create_users)])
    User(email="ada@example.com", name="Ada").save(db)
    return 0
```

## 7. Validation

```agi
let result = validate(request.json({}), {
    "email": "required|email",
    "name": "required|min:2|max:80"
})
if not result.ok:
    return json_response({"errors": result.errors}, status=422)
```

## 8. Auth and CSRF

```agi
let secret = "change-this-secret"
app.middleware_group("secure", [auth_required(secret), csrf_protect(secret)])
```

For browser forms:

```agi
let token = csrf_token(secret)
let hidden = csrf_input(token)
```

## 9. Security middleware

```agi
let app = web_app("secure", True)
app.before(body_limit(65536))
app.before(rate_limit(100, 60))
app.after(security_headers())
```

Security helpers include:

- `security_headers()`
- `rate_limit(limit, window_seconds)`
- `body_limit(max_bytes)`
- `secure_random_token()`
- `hmac_sign()` / `hmac_verify()`
- `api_key_hash()` / `verify_api_key()`

## 10. WebSocket realtime

```agi
fn main() -> i32:
    let server = websocket_listen("127.0.0.1", 9000, "/chat")

    fn on_message(client, message):
        server.broadcast(json_event("chat.message", {"text": message}, "chat"))

    server.on_message(on_message)
    server.serve_forever()
    return 0
```

Client:

```agi
let client = websocket_connect("ws://127.0.0.1:9000/chat")
client.send("hello")
print(client.receive(2.0))
client.close()
```

## 11. WebRTC signaling

AGILANG provides WebRTC signaling, not browser media capture. The browser/React app uses real WebRTC APIs. AGILANG coordinates peers:

```agi
let server = webrtc_signal_server("127.0.0.1", 9000, "/webrtc")
server.serve_forever()
```

Message types:

- `webrtc.join`
- `webrtc.offer`
- `webrtc.answer`
- `webrtc.ice`
- `webrtc.peer_joined`
- `webrtc.peer_left`

Create envelopes:

```agi
let offer = webrtc_offer("sdp-offer", "alice", to_peer="bob", room="demo")
let answer = webrtc_answer("sdp-answer", "bob", to_peer="alice", room="demo")
let ice = webrtc_ice({"candidate": "candidate..."}, "alice", to_peer="bob", room="demo")
```

## 12. React web support

Create a React web project:

```bash
agilang react web agil-react-client
cd agil-react-client
npm install
npm run dev
```

The generated React client uses `AgiRealtimeClient` and can connect to:

```text
ws://127.0.0.1:9000/realtime
```

## 13. React Native / mobile support

Create a mobile project:

```bash
agilang react mobile agil-mobile-client
cd agil-mobile-client
npm install
npm run start
```

Set:

```text
EXPO_PUBLIC_AGILANG_WS=ws://127.0.0.1:9000/realtime
```

## 14. Native C networking runtime

The native runtime is in:

```text
native/agilang_net_runtime.c
native/agilang_net_runtime.h
```

It includes:

- HTTP listener API
- WebSocket server API
- WebSocket handshake
- frame parsing and writing
- masking validation
- ping/pong handling
- close handling
- broadcast
- max-frame limits
- origin/token checks

Compile check:

```bash
gcc -std=c11 -Wall -Wextra -c native/agilang_net_runtime.c -o build/agilang_net_runtime.o -pthread
```

## 15. Production deployment pattern

Recommended topology:

```text
Browser / Mobile / React
        ↓ HTTPS/WSS
Nginx or Caddy TLS reverse proxy
        ↓ localhost HTTP/WS
AGILANG Python web/realtime app or native C runtime
        ↓
SQLite/Postgres/queue/storage
```

Use TLS at the proxy. Do not expose development servers directly to the public internet.

---

# Chapter: Native Hybrid Web Runtime (v1.1)

AGILANG v1.1 adds the `hybrid_web_runtime` and `agilab_web_runtime` APIs. These APIs allow one AGILANG application to coordinate the feature-complete Python runtime with the native C HTTP/WebSocket runtime.

```agi
fn main() -> i32:
    let runtime = agilab_web_runtime("hybrid")
    let caps = runtime.capabilities()
    print("mode", caps["mode"])
    print("python framework", caps["python_http"])
    print("native websocket", caps["c_websocket"])
    return 0
```

Use `hybrid` mode for most real deployments. It keeps the Python backend for ORM, migrations, auth, CSRF, validation, queues, WebRTC signaling, and React/mobile support while enabling a compiled C runtime ABI for native transport.

CLI commands:

```bash
agilang runtime status
agilang runtime build -o build/native
agilang runtime doctor
```

The native C runtime exposes version, capability, and self-test functions so Python can verify the runtime before serving traffic.

---

# Chapter: Zero-Knowledge Systems in AGILANG v1.7

AGILANG v1.7 adds zero-knowledge systems primitives so AGILANG can be used for privacy-preserving protocols, blockchain tooling, commitments, membership proofs, and verifier integration.

## Create a ZK app

```bash
agi new private proof app --template zk
cd private-proof-app
agi run
agi run src/circuit.agi
agi run src/schnorr.agi
```

## Build a simple circuit

```agi
fn main() -> i32:
    let circuit = zk_circuit("square_proof")
    circuit.var("secret", 12, public=False)
    circuit.var("square", 144, public=True)
    circuit.assert_mul("secret", "secret", "square")
    print(circuit.check())
    return 0
```

## Commitments and Merkle proofs

```agi
let commitment = zk_commit({"amount": 100}, "salt")
print(zk_verify_commitment(commitment, {"amount": 100}))

let proof = zk_merkle_proof(["alice", "bob", "carol"], 1)
print(zk_verify_merkle_proof("bob", proof["index"], proof["proof"], proof["root"]))
```

## Production guidance

Use AGILANG's built-in primitives for application modeling, tests, and protocol development. For production SNARK/STARK proving, bridge to audited external engines or precompiled native prover packages.

# Chapter: Full Blockchain Framework in AGILANG v1.9

AGILANG v1.9 adds a configurable blockchain framework so AGILANG is not limited to web or EVM helper tooling. The framework gives you the core modules needed for a private chain or devnet: Proof-of-Stake validator configuration, mempool management, block production, block validation, fork choice, canonical chain storage and peer/devnet sync.

## Create a blockchain project

```bash
agi new my chain --template blockchain
cd my-chain
agi run
agi run src/devnet.agi
```

## Minimal node

```agi
fn main() -> i32:
    let cfg = blockchain_config(chain_id=1900, name="my-chain", validators={"alice": 60, "bob": 40})
    let node = blockchain_node(cfg, "storage/chain.sqlite", "alice-node")
    let tx = blockchain_transaction("alice", "bob", 10, nonce=1, gas_price=1)
    node.submit_tx(tx)
    let parent = node.head()
    let slot = parent["slot"] + 1
    let proposer = node.consensus.select_proposer(parent["hash"], slot)
    node.produce_and_import_block(proposer, slot)
    print(node.status())
    return 0
```

## CLI

```bash
agi blockchain capabilities
agi blockchain demo
agi blockchain init-genesis --db storage/chain.sqlite --validator alice:60 --validator bob:40
agi blockchain devnet --blocks 3
```

Use this layer for custom chain development, private chains, internal settlement chains and protocol experimentation. Public real-value chains require additional security hardening and independent audits.
