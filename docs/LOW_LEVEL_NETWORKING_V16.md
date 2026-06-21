# AGILANG v1.6 Low-Level Networking

AGILANG v1.6 introduces `agilang.lowlevel_network`, a standard-library networking layer for systems prototypes.

## Functions

```agi
tcp_listen(host, port, handler)
tcp_connect(host, port, timeout)
udp_socket(host, port, broadcast)
packet_frame(payload)
packet_unframe(data)
packet_json(type, payload, topic)
packet_json_parse(data)
gossip_node(host, port, node_id, seeds)
lowlevel_network_capabilities()
```

## UDP example

```agi
fn main() -> i32:
    let udp = udp_socket("127.0.0.1", 0)
    let addr = udp.address
    udp.send_to("hello", addr.host, addr.port)
    let received = udp.recv_from(1024, 2.0)
    print(received[0].decode("utf-8"))
    udp.close()
    return 0
```

## Gossip note

The gossip primitive is intentionally simple. It is for peer-discovery and event propagation experiments, not a full blockchain consensus engine. Consensus, mempools, slashing rules, finality, block validation, and peer scoring should be implemented as separate modules on top.
