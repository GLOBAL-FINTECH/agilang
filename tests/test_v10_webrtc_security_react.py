import json
import shutil
import subprocess
from pathlib import Path

import pytest

from agilang.security import api_key_hash, hmac_sign, hmac_verify, rate_limit, security_headers, verify_api_key
from agilang.web import Request, json_response, web_app
from agilang.webrtc import parse_webrtc_signal, webrtc_offer, webrtc_signal_server
from agilang.realtime import websocket_connect
from agilang.react_support import create_react_mobile_project, create_react_web_project, write_react_sdk


def test_webrtc_signal_envelopes():
    raw = webrtc_offer("fake-sdp", "alice", to_peer="bob", room="demo")
    data = parse_webrtc_signal(raw)
    assert data["type"] == "webrtc.offer"
    assert data["from"] == "alice"
    assert data["to"] == "bob"
    assert data["room"] == "demo"
    assert data["payload"]["sdp"] == "fake-sdp"


def test_webrtc_signal_server_forwards_offer():
    server = webrtc_signal_server("127.0.0.1", 0, "/webrtc").run_background()
    try:
        alice = websocket_connect(f"ws://127.0.0.1:{server.actual_port}/webrtc")
        bob = websocket_connect(f"ws://127.0.0.1:{server.actual_port}/webrtc")
        alice.send({"type": "webrtc.join", "peer_id": "alice", "room": "demo"})
        bob.send({"type": "webrtc.join", "peer_id": "bob", "room": "demo"})
        alice.receive(2.0)
        bob.receive(2.0)
        alice.send(webrtc_offer("fake-sdp", "alice", to_peer="bob", room="demo"))
        forwarded = json.loads(bob.receive(2.0))
        assert forwarded["type"] == "webrtc.offer"
        assert forwarded["from"] == "alice"
        assert forwarded["payload"]["sdp"] == "fake-sdp"
        alice.close(); bob.close()
    finally:
        server.stop()


def test_security_helpers_and_headers():
    sig = hmac_sign("payload", "secret")
    assert hmac_verify("payload", "secret", sig)
    encoded = api_key_hash("agi_test_key")
    assert verify_api_key("agi_test_key", encoded)

    app = web_app("secure-test", True)
    app.after(security_headers())
    app.get("/", lambda request: json_response({"ok": True}))
    request = Request("GET", "/", "", {"x-forwarded-proto": "https"}, b"")
    response = app.handle(request)
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Content-Security-Policy" in response.headers
    assert "Strict-Transport-Security" in response.headers


def test_rate_limit_middleware_blocks_after_limit():
    middleware = rate_limit(1, 60)
    req = Request("GET", "/", "", {}, b"", client=("127.0.0.1", 1))
    assert middleware(req) is None
    blocked = middleware(req)
    assert blocked.status == 429


def test_react_scaffolds_and_sdk(tmp_path: Path):
    web = create_react_web_project("web_client", tmp_path)
    mobile = create_react_mobile_project("mobile_client", tmp_path)
    sdk = write_react_sdk(tmp_path / "sdk")
    assert (web / "src" / "agilangClient.ts").exists()
    assert (mobile / "src" / "agilangClient.ts").exists()
    assert sdk.exists()
    assert "AgiRealtimeClient" in sdk.read_text()


def test_native_c_websocket_runtime_compile_check():
    if shutil.which("gcc") is None:
        pytest.skip("gcc is required for native C compile check")
    root = Path(__file__).resolve().parents[1]
    src = root / "native" / "agilang_net_runtime.c"
    out = root / "build" / "agilang_net_runtime_test.o"
    out.parent.mkdir(exist_ok=True)
    proc = subprocess.run(["gcc", "-std=c11", "-Wall", "-Wextra", "-c", str(src), "-o", str(out), "-pthread"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
