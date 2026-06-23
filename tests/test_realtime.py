import time

from agilang.realtime import (
    JsonEvent,
    pubsub_bus,
    realtime_channel,
    websocket_connect,
    websocket_listen,
)
from agilang.translator import AGILTranslator


def test_json_event_roundtrip():
    raw = JsonEvent(type="txn.update", topic="merchant.txn", payload={"status": "approved"}).to_json()
    event = JsonEvent.from_json(raw)
    assert event.type == "txn.update"
    assert event.topic == "merchant.txn"
    assert event.payload["status"] == "approved"
    assert event.event_id


def test_pubsub_bus_publish_subscribe():
    bus = pubsub_bus()
    seen = []
    unsubscribe = bus.subscribe("prices", lambda payload: seen.append(payload))
    delivered = bus.publish("prices", {"symbol": "AGI", "price": 10})
    unsubscribe()
    bus.publish("prices", {"symbol": "AGI", "price": 20})
    assert delivered == 1
    assert seen == [{"symbol": "AGI", "price": 10}]


def test_realtime_channel_publish():
    channel = realtime_channel("dashboard")
    seen = []
    channel.subscribe(lambda payload: seen.append(payload))
    assert channel.publish({"active": 5}) == 1
    assert seen[0]["active"] == 5


def test_websocket_connect_broadcast_disconnect_reconnect():
    server = websocket_listen("127.0.0.1", 0, "/ws")
    events = {"connect": 0, "disconnect": 0, "messages": []}

    def on_connect(client):
        events["connect"] += 1

    def on_message(client, message):
        events["messages"].append(message)
        server.broadcast({"type": "echo", "payload": message})

    def on_disconnect(client):
        events["disconnect"] += 1

    server.on_connect(on_connect).on_message(on_message).on_disconnect(on_disconnect)
    server.run_background()
    url = f"ws://127.0.0.1:{server.actual_port}/ws"

    client1 = websocket_connect(url)
    client2 = websocket_connect(url)
    client1.send("hello")
    assert client2.receive(2.0) == '{"type":"echo","payload":"hello"}'
    client1.close()

    # Reconnect path: a fresh connection to the same URL should receive broadcasts.
    client1.reconnect(attempts=2)
    server.broadcast("after reconnect")
    assert client1.receive(2.0) == "after reconnect"

    client1.close()
    client2.close()
    server.stop()
    time.sleep(0.05)

    assert events["connect"] >= 3
    assert "hello" in events["messages"]
    assert events["disconnect"] >= 2


def test_translator_exposes_realtime_functions():
    py = AGILTranslator().translate('fn main() -> i32:\n    let event = json_event("ready", {"ok": True}, "system")\n    return 0\n')
    assert 'event = json_event("ready", {"ok": True}, "system")' in py
