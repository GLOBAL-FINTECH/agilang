# AGILANG v2.0.0 Ethereum External-Client Stack

AGILANG v2.0.0 adds first-class orchestration for real Ethereum mainnet client connectivity while keeping AGILANG/SBQ custom consensus separate from Ethereum consensus.

## Architecture

Ethereum mainnet mode is a three-client stack:

1. **Execution client** — Geth, Nethermind, Besu or Erigon.
2. **Consensus / beacon client** — Lighthouse, Prysm, Teku, Nimbus or Lodestar.
3. **Validator client** — Lighthouse, Prysm, Teku, Nimbus or Lodestar.

AGILANG does not replace Ethereum consensus. It generates config, validates ports, creates an Engine API JWT secret, builds startup commands, detects installed clients and can supervise the external client processes.

## Commands

```bash
agi chain ethereum-clients
agi chain ethereum-detect
agi chain ethereum-jwt --jwt-secret ethereum-data/jwt.hex
agi chain ethereum-write-config --mode full
agi chain ethereum-write-config --mode archive
agi chain ethereum-write-config --mode validator --fee-recipient 0x0000000000000000000000000000000000000000
agi chain ethereum-plan --mode full
agi chain ethereum-plan --mode archive
agi chain ethereum-plan --mode validator --fee-recipient 0x0000000000000000000000000000000000000000
agi chain ethereum-check
agi chain ethereum-start --mode full --dry-run
agi chain ethereum-start --mode archive --dry-run
agi chain ethereum-start --mode validator --dry-run
```

## One-command chain profile modes

```bash
agi chain plan --mode ethereum-full
agi chain plan --mode ethereum-archive
agi chain plan --mode ethereum-validator
agi chain plan --mode ethereum-all
```

These modes do not start AGILANG custom consensus on Ethereum. They plan or start the real Ethereum client stack.

## Default private port separation

| Service | Default host | Default port | Purpose |
|---|---:|---:|---|
| Execution JSON-RPC | `127.0.0.1` | `8545` | Ethereum user/app RPC |
| Execution Engine API | `127.0.0.1` | `8551` | Authenticated EL/CL Engine API |
| Execution WebSocket RPC | `127.0.0.1` | `8546` | WebSocket RPC |
| Consensus Beacon REST API | `127.0.0.1` | `5052` | Beacon HTTP API |
| Validator HTTP/API | `127.0.0.1` | `5062` | Private validator operations |
| Metrics | `127.0.0.1` | `9101` | Private monitoring |

The validator API and Engine API must remain private and should not be exposed directly to the public internet.

## Archive mode

`agi chain ethereum-plan --mode archive` adds execution-client archive flags where supported. For Geth this uses full sync plus archive state retention flags in the command plan.

## Boundary

AGILANG v2.0.0 now closes the earlier missing integration layer by adding real Ethereum external-client orchestration. It still cannot honestly claim that SBQ/AGILANG custom consensus itself validates Ethereum mainnet. Ethereum mainnet validation must be performed by the Ethereum consensus and validator clients.
