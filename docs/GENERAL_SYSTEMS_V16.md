# AGILANG v1.6 General Systems Design

## Goal

AGILANG should be a general coding language, not only a web-app framework. The right architecture is to separate **language syntax** from **capability providers**.

```text
AGILANG code syntax
  -> stable standard-library API
  -> Python adapter for immediate use
  -> C/Rust/precompiled native adapter for performance-critical modules
  -> platform-specific packaged runtime artifacts
```

This lets AGILANG define its own developer-facing functions while still reusing mature Python/C packages behind the interface.

## New capability layers

### Low-level networking

- TCP server/client
- UDP socket
- packet framing
- JSON event frames
- UDP gossip node

### EVM tooling

- function selectors
- static ABI encoding
- call-data generation
- bytecode builder
- disassembler
- JSON-RPC client

### Interop bridge

- `python_package()` imports existing Python packages
- `native_library()` loads C shared libraries
- `capability_manifest()` reads packaged capability manifests
- `systems_capabilities()` reports the whole stack

## Why this is the best path

Writing every subsystem from scratch is possible but slow. The production path is:

1. Define the AGILANG API surface.
2. Provide Python implementations for fast iteration.
3. Add C/native implementations for speed-critical modules.
4. Ship precompiled artifacts for platforms where native speed matters.
5. Keep the AGILANG syntax stable so apps do not change when the backend improves.

## Next recommended versions

- v1.7: native C lowering for TCP/UDP packet APIs
- v1.8: full EVM interpreter core or integration with a precompiled EVM engine
- v1.9: package registry and signed capability packs
- v2.0: native executable target for full AGILANG systems apps
